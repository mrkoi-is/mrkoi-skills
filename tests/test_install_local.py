import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "installer", Path(__file__).resolve().parents[1] / "scripts/install_local.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.dest = self.root / "repo", self.root / "skills"
        self.names = installer.SKILLS[:2]
        for name in self.names:
            (self.repo / name).mkdir(parents=True)
            (self.repo / name / "SKILL.md").write_text("fixture")

    def test_preview_does_not_write(self):
        installer.install(self.repo, self.dest, self.names)
        self.assertFalse(self.dest.exists())

    def test_install_idempotent_and_source_is_single_copy(self):
        self.assertEqual(installer.install(self.repo, self.dest, self.names, True), 2)
        self.assertEqual(installer.install(self.repo, self.dest, self.names, True), 0)
        (self.repo / self.names[0] / "SKILL.md").write_text("updated")
        self.assertEqual((self.dest / self.names[0] / "SKILL.md").read_text(), "updated")

    def test_collision_prevents_partial_install(self):
        existing = self.dest / self.names[1]
        existing.mkdir(parents=True)
        (existing / "keep.txt").write_text("user work")
        with self.assertRaises(FileExistsError):
            installer.install(self.repo, self.dest, self.names, True)
        self.assertFalse((self.dest / self.names[0]).exists())
        self.assertEqual((existing / "keep.txt").read_text(), "user work")

    def test_broken_symlink_is_preserved(self):
        self.dest.mkdir()
        target = self.dest / self.names[0]
        target.symlink_to(self.root / "missing")
        with self.assertRaises(FileExistsError):
            installer.install(self.repo, self.dest, self.names, True)
        self.assertTrue(target.is_symlink())

    def test_failed_link_rolls_back_only_new_links(self):
        original = Path.symlink_to
        def fail_second(path, source, **kwargs):
            if path.name == self.names[1]:
                raise OSError("fixture failure")
            return original(path, source, **kwargs)
        with patch.object(Path, "symlink_to", fail_second):
            with self.assertRaises(OSError):
                installer.install(self.repo, self.dest, self.names, True)
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_unknown_name_cannot_escape_target(self):
        with self.assertRaises(ValueError):
            installer.install(self.repo, self.dest, ["../unrelated"], True)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
