@AGENTS.md

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

## Active Technologies

- Python >=3.11, <3.15 (`pyproject.toml`) + `ansible-core>=2.19.0`; `infrahub-sdk[all]>=1.19.0,<2.0` (synchronous client only) (001-inventory-fetch-performance)

## Recent Changes

- 001-inventory-fetch-performance: Cut dynamic inventory fetch round-trips — query projection, bounded peer fetches, batched refill
