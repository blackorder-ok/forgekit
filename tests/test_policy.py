"""Policy loader tests: schema, tighten-only overrides, fail-closed loading."""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "plugins", "forge", "scripts")
sys.path.insert(0, SCRIPTS)

import kit_policy  # noqa: E402


def base():
    with open(kit_policy.BASE_PATH, encoding="utf-8") as f:
        return json.load(f)


class PolicyCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, name, doc):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(doc if isinstance(doc, str) else json.dumps(doc))
        return p


class SchemaTests(PolicyCase):
    def test_shipped_policy_validates(self):
        policy = kit_policy.load()
        self.assertIn("master", policy["protectedBranches"])
        self.assertEqual(policy["agents"]["ops"]["privilege"], "edit")

    def test_unknown_top_level_key_rejected(self):
        doc = dict(base(), surprise=True)
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_unknown_bash_key_rejected(self):
        doc = base()
        doc["bash"]["allow"] = []
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_bad_privilege_rejected(self):
        doc = base()
        doc["agents"]["ops"]["privilege"] = "root"
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_bad_regex_rejected(self):
        doc = base()
        doc["bash"]["deny"] = ["(unclosed"]
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_list_cap_and_string_cap(self):
        doc = base()
        doc["protectedPaths"] = ["p"] * 201
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)
        doc = base()
        doc["protectedPaths"] = ["x" * 201]
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_version_must_be_1(self):
        doc = base()
        doc["version"] = 2
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_base_must_set_every_section(self):
        doc = base()
        del doc["secretPaths"]
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.validate(doc)

    def test_file_size_cap(self):
        p = self.write("big.json", "{" + " " * (kit_policy.MAX_BYTES + 1) + "}")
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.load(basePath=p)


class OverrideTests(PolicyCase):
    def override(self, doc):
        return self.write("policy.json", doc)

    def test_override_adds_protected_branch_and_bash_rule(self):
        p = self.override({"version": 1, "protectedBranches": ["develop"], "bash": {"deny": ["\\bnpm publish\\b"]}})
        policy = kit_policy.load(overridePath=p)
        self.assertIn("develop", policy["protectedBranches"])
        self.assertIn("master", policy["protectedBranches"])
        self.assertIn("\\bnpm publish\\b", policy["bash"]["deny"])

    def test_override_cannot_remove_base_entries(self):
        p = self.override({"version": 1, "protectedBranches": []})
        policy = kit_policy.load(overridePath=p)
        self.assertEqual(policy["protectedBranches"], kit_policy.load()["protectedBranches"])

    def test_override_can_lower_agent_privilege(self):
        p = self.override({"version": 1, "agents": {"ops": {"privilege": "read"}}})
        self.assertEqual(kit_policy.load(overridePath=p)["agents"]["ops"]["privilege"], "read")

    def test_override_cannot_raise_agent_privilege(self):
        p = self.override({"version": 1, "agents": {"reviewer": {"privilege": "full"}}})
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.load(overridePath=p)

    def test_override_adding_new_agent_is_allowed_only_at_or_below_full(self):
        p = self.override({"version": 1, "agents": {"custom": {"privilege": "read"}}})
        self.assertEqual(kit_policy.load(overridePath=p)["agents"]["custom"]["privilege"], "read")

    def test_override_with_removal_keys_rejected(self):
        p = self.override({"version": 1, "removeProtectedBranches": ["master"]})
        with self.assertRaises(kit_policy.PolicyError):
            kit_policy.load(overridePath=p)

    def test_override_must_not_omit_required_base_sections(self):
        p = self.override({"version": 1, "protectedBranches": ["develop"]})
        policy = kit_policy.load(overridePath=p)  # partial overrides are allowed
        self.assertTrue(policy["bash"]["deny"])

    def test_missing_override_file_means_base(self):
        self.assertEqual(kit_policy.load(overridePath=os.path.join(self.tmp, "none.json")), kit_policy.load())


class FailClosedTests(PolicyCase):
    def test_malformed_base_fails_closed(self):
        p = self.write("bad.json", "{not json")
        policy = kit_policy.loadOrDeny(basePath=p)
        self.assertTrue(policy.get("denyAll"))
        self.assertTrue(kit_policy.isProtectedBranch(policy, "develop"))

    def test_malformed_override_fails_closed(self):
        p = self.write("policy.json", {"version": 1, "agents": {"x": {"privilege": "root"}}})
        policy = kit_policy.loadOrDeny(overridePath=p)
        self.assertTrue(policy.get("denyAll"))

    def test_missing_base_fails_closed(self):
        policy = kit_policy.loadOrDeny(basePath=os.path.join(self.tmp, "absent.json"))
        self.assertTrue(policy.get("denyAll"))

    def test_good_policy_is_not_deny_all(self):
        policy = kit_policy.loadOrDeny()
        self.assertFalse(policy.get("denyAll"))
        self.assertTrue(kit_policy.isProtectedBranch(policy, "qa"))
        self.assertFalse(kit_policy.isProtectedBranch(policy, "develop"))


class PrivilegeTableTests(PolicyCase):
    def test_rows_are_sorted_and_render(self):
        policy = kit_policy.load()
        rows = kit_policy.privilegeTable(policy)
        self.assertEqual(rows, sorted(rows))
        md = kit_policy.privilegeMarkdown(policy)
        self.assertIn("| ops | edit |", md)


if __name__ == "__main__":
    unittest.main()
