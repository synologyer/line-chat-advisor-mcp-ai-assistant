import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('claude_setup', ROOT / 'scripts/configure-claude.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ClaudeSetupTests(unittest.TestCase):
    def test_ambiguous_accounts_require_active_file_or_exact_choice(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / 'qw111.edb'; b = root / 'qw222.edb'
            a.touch(); b.touch()
            with self.assertRaises(ValueError): setup.choose_database(root)
            self.assertEqual(setup.choose_database(root, opened=[str(b)]), b)
            self.assertEqual(setup.choose_database(root, explicit=a.name), a)
            with self.assertRaises(ValueError): setup.choose_database(root, explicit='../qw111.edb')
            with self.assertRaises(ValueError): setup.choose_database(root, explicit='qw333.edb')

    def test_desktop_config_preserves_other_connections(self):
        previous = {'mcpServers': {'mail': {'command': 'mail'}}, 'preferences': {'locale': 'zh'}}
        updated = setup.desktop_config(previous, Path('/node'), Path('/private/project'))
        self.assertEqual(updated['mcpServers']['mail'], previous['mcpServers']['mail'])
        self.assertEqual(updated['preferences'], previous['preferences'])
        self.assertNotIn('work-line-readonly', previous['mcpServers'])

    def test_written_local_config_is_private(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'local.json'
            setup.private_json(p, {'selected': True})
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            self.assertFalse(p.with_name('local.json.new').exists())


if __name__ == '__main__':
    unittest.main()
