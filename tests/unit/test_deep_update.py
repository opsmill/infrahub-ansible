import unittest

from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import InfrahubBaseProcessor


class TestDeepUpdate(unittest.TestCase):
    def test_deep_update_nested(self) -> None:
        source = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}, "z": 1}
        overrides = {"a": {"b": {"c": {"d": {"e": {"f": 2, "g": 3}, "h": 4}}, "i": 5}}, "j": 6}
        expected = {"a": {"b": {"c": {"d": {"e": {"f": 2, "g": 3}, "h": 4}}, "i": 5}}, "j": 6, "z": 1}
        result = InfrahubBaseProcessor.deep_update(source, overrides)
        self.assertEqual(result, expected)
