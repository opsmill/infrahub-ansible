from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from invoke import Context, task

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-DOCS"

DOCUMENTATION_DIRECTORY = Path("docs")
ANSIBLE_DOCUMENTATION_DIRECTORY = DOCUMENTATION_DIRECTORY / "docs"
PLUGINS_DIRECTORY = Path("plugins")

PLUGIN_TYPES: dict[str, str] = {"modules": "module", "inventory": "inventory", "lookup": "lookup"}


class Role(NamedTuple):
    name: str
    description: str


# ----------------------------------------------------------------------------
# Documentation tasks
# ----------------------------------------------------------------------------
def find_plugin_files() -> dict[str, list[Path]]:
    """
    Find all plugin files excluding __init__.py.

    Returns:
        dict mapping plugin types to list of plugin files
    """
    plugin_files: dict[str, list[Path]] = {}

    for plugin_type in PLUGIN_TYPES:
        plugin_dir = PLUGINS_DIRECTORY / plugin_type
        if plugin_dir.exists():
            files = [f for f in plugin_dir.glob("**/*.py") if f.name != "__init__.py"]
            if files:
                plugin_files[plugin_type] = files

    return plugin_files


def extract_docstring(content: str, variable: str) -> str:
    """
    Extract docstring from Ansible plugin content.

    Args:
        content: Full plugin file content
        variable: Name of the docstring variable to extract (DOCUMENTATION, EXAMPLES, RETURN)

    Returns:
        Extracted docstring content
    """
    markers = [
        (f'{variable} = """', '"""'),
        (f"{variable} = '''", "'''"),
        (f'{variable} = r"""', '"""'),
        (f"{variable} = r'''", "'''"),
    ]

    for start_marker, end_marker in markers:
        if start_marker in content:
            start_idx = content.find(start_marker) + len(start_marker)
            end_idx = content.find(end_marker, start_idx)
            if end_idx != -1:
                return content[start_idx:end_idx].strip()
    return ""


def clean_yaml_content(content: str) -> str:
    """
    Clean and format YAML content from docstrings.

    Args:
        content: Raw YAML content from docstring

    Returns:
        Cleaned and properly formatted YAML content
    """
    if not content:
        return content

    lines = content.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)

    # Specific format for RETURN json/text block
    if "json:" in content and "text:" in content:
        return """json:
  description: Content of the artifact in JSON format.
  type: dict
  returned: success
text:
  description: Content of the artifact in TEXT format.
  type: str
  returned: success"""

    cleaned_lines: list[str] = []
    first_line_indent: int | None = None

    for line in lines:
        if line.strip():
            if first_line_indent is None:
                stripped = line.lstrip()
                first_line_indent = len(line) - len(stripped)
                cleaned_lines.append(stripped)
            elif len(line) > first_line_indent:
                cleaned_lines.append(line[first_line_indent:])
            else:
                cleaned_lines.append(line.lstrip())
        else:
            cleaned_lines.append("")

    content = "\n".join(cleaned_lines)
    if not content.startswith("---"):
        content = "---\n" + content

    return content


def parse_ansible_doc(plugin_file: Path, debug: bool = False) -> dict[str, Any]:
    """
    Parse Ansible plugin documentation.

    Args:
        plugin_file: Path to the plugin file
        debug: Enable debug output

    Returns:
        dictionary containing parsed documentation, examples, and return values
    """
    content = plugin_file.read_text(encoding="utf-8")

    documentation = extract_docstring(content, "DOCUMENTATION")
    examples = extract_docstring(content, "EXAMPLES")
    returns = extract_docstring(content, "RETURN")

    if debug:
        print(f"\nProcessing {plugin_file.name}")

    try:
        cleaned_doc = clean_yaml_content(documentation)
        doc_data = yaml.safe_load(cleaned_doc) if documentation else {}
        if debug:
            print("Cleaned DOCUMENTATION:")
            print(cleaned_doc)
    except yaml.YAMLError:
        print(f"Error parsing DOCUMENTATION for {plugin_file.name}")
        doc_data = {}

    try:
        cleaned_returns = clean_yaml_content(returns)
        returns_data = yaml.safe_load(cleaned_returns) if returns else {}
        if debug:
            print("Cleaned RETURN:")
            print(cleaned_returns)
    except yaml.YAMLError:
        print(f"Error parsing RETURN for {plugin_file.name}")
        returns_data = {}

    if "name" not in doc_data and "module" in doc_data:
        doc_data["name"] = doc_data["module"]

    return {"documentation": doc_data, "examples": examples, "returns": returns_data, "name": plugin_file.stem}


def get_collection_version() -> str:
    """Get collection version from galaxy.yml."""
    try:
        with open("galaxy.yml", encoding="utf-8") as f:  # noqa: PTH123
            galaxy_info = yaml.safe_load(f)
            return galaxy_info.get("version", "unknown")
    except (FileNotFoundError, yaml.YAMLError):
        return "unknown"


def get_roles() -> list[Role]:
    """Get list of roles from roles directory."""
    roles_dir = Path("roles")
    roles: list[Role] = []

    if roles_dir.exists():
        for role_dir in roles_dir.iterdir():
            if role_dir.is_dir():
                meta_file = role_dir / "meta" / "main.yml"
                if meta_file.exists():
                    try:
                        with open(meta_file, encoding="utf-8") as f:  # noqa: PTH123
                            meta = yaml.safe_load(f)
                            roles.append(
                                Role(name=role_dir.name, description=meta.get("galaxy_info", {}).get("description", ""))
                            )
                    except yaml.YAMLError:
                        continue
    return roles


def get_ansible_core_requirement() -> str:
    """Get required ansible-core version from meta/runtime.yml."""
    try:
        with open("meta/runtime.yml", encoding="utf-8") as f:  # noqa: PTH123
            runtime_info = yaml.safe_load(f)
            return runtime_info.get("requires_ansible", "unknown")
    except (FileNotFoundError, yaml.YAMLError):
        return "unknown"


@task(
    help={
        "debug": "Enable debug output",
        "plugin_type": f"Generate docs for specific plugin type ({', '.join(PLUGIN_TYPES.keys())})",
    }
)
def generate_docs(context: Context, debug: bool = False, plugin_type: str | None = None) -> None:  # noqa: ARG001
    """Generate documentation for Ansible plugins."""
    # Load templates
    import jinja2

    template_dir = DOCUMENTATION_DIRECTORY / "_templates"
    environment = jinja2.Environment(
        autoescape=False,  # noqa: S701
        trim_blocks=False,
        lstrip_blocks=True,
    )

    plugin_template = environment.from_string((template_dir / "plugin.mdx.j2").read_text())
    readme_template = environment.from_string((template_dir / "readme.mdx.j2").read_text())

    # Process plugins
    plugin_files = find_plugin_files()
    if plugin_type:
        if plugin_type not in PLUGIN_TYPES:
            print(f"Invalid plugin type. Choose from: {', '.join(PLUGIN_TYPES.keys())}")
            sys.exit(-1)
        plugin_files = {plugin_type: plugin_files.get(plugin_type, [])}

    # Store processed plugins for landing page
    processed_plugins: dict[str, list[dict[str, Any]]] = {p_type: [] for p_type in PLUGIN_TYPES}

    # Generate individual plugin pages
    for p_type, files in plugin_files.items():
        if debug:
            print(f"\nProcessing {p_type} plugins...")

        for plugin_file in files:
            output_file = (
                ANSIBLE_DOCUMENTATION_DIRECTORY
                / "references"
                / "plugins"
                / f"{plugin_file.stem}_{PLUGIN_TYPES[p_type]}.mdx"
            )

            try:
                plugin_doc = parse_ansible_doc(plugin_file, debug)
                plugin_doc["plugin_type"] = p_type
                rendered_file = plugin_template.render(**plugin_doc)

                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(rendered_file, encoding="utf-8")
                print(f"✓ {output_file.name}")

                processed_plugins[p_type].append(plugin_doc)

            except Exception:
                print(f"✗ Error processing {plugin_file.name}")
                if debug:
                    import traceback

                    print(traceback.format_exc())

    # Generate landing page
    readme_file = ANSIBLE_DOCUMENTATION_DIRECTORY / "readme.mdx"
    readme_content = readme_template.render(
        collection_version=get_collection_version(),
        ansible_core_version=get_ansible_core_requirement(),
        plugins=processed_plugins,
        roles=get_roles(),
    )
    readme_file.write_text(readme_content)
    print(f"✓ {readme_file.name}")


@task
def docusaurus(context: Context) -> None:
    """Build documentation website."""
    exec_cmd = "npm run build"

    with context.cd(DOCUMENTATION_DIRECTORY):
        output = context.run(exec_cmd)

    if output.exited != 0:
        sys.exit(-1)
