import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from routers.desktop import UpdatePreparation, prepare_update


class DesktopUpdatePreparationTests(unittest.TestCase):
    def payload(self, **overrides):
        values = {
            "target_version": "0.5.0",
            "target_schema_revision": "0003_next",
            "minimum_schema_revision": "0001_desktop_core",
        }
        values.update(overrides)
        return UpdatePreparation(**values)

    @patch("routers.desktop.prune_database_backups")
    @patch("routers.desktop.create_database_backup")
    @patch("routers.desktop._revision_is_at_least", return_value=True)
    @patch(
        "routers.desktop.current_schema_revision",
        return_value="0002_local_runtime",
    )
    def test_compatible_update_creates_backup_before_install(
        self,
        _current_revision,
        _compatible,
        create_backup,
        prune_backups,
    ):
        create_backup.return_value = Path("pre-update-0.5.0.sqlite3")

        result = prepare_update(self.payload())

        self.assertTrue(result["ready"])
        self.assertEqual(result["schema_revision"], "0002_local_runtime")
        self.assertEqual(result["target_schema_revision"], "0003_next")
        create_backup.assert_called_once_with("pre-update-0.5.0")
        prune_backups.assert_called_once_with("pre-update", 5)

    @patch("routers.desktop.create_database_backup")
    @patch("routers.desktop._revision_is_at_least", return_value=False)
    @patch(
        "routers.desktop.current_schema_revision",
        return_value="0002_local_runtime",
    )
    def test_incompatible_schema_is_rejected_without_backup(
        self,
        _current_revision,
        _compatible,
        create_backup,
    ):
        with self.assertRaises(HTTPException) as raised:
            prepare_update(self.payload())

        self.assertEqual(raised.exception.status_code, 409)
        create_backup.assert_not_called()

    @patch("routers.desktop.prune_database_backups")
    @patch(
        "routers.desktop.create_database_backup",
        side_effect=OSError("disco lleno"),
    )
    @patch("routers.desktop._revision_is_at_least", return_value=True)
    @patch(
        "routers.desktop.current_schema_revision",
        return_value="0002_local_runtime",
    )
    def test_backup_failure_blocks_update(
        self,
        _current_revision,
        _compatible,
        _create_backup,
        prune_backups,
    ):
        with self.assertRaises(HTTPException) as raised:
            prepare_update(self.payload())

        self.assertEqual(raised.exception.status_code, 500)
        prune_backups.assert_not_called()

    @patch("routers.desktop.current_schema_revision")
    def test_non_semver_version_is_rejected_before_reading_database(
        self,
        current_revision,
    ):
        with self.assertRaises(HTTPException) as raised:
            prepare_update(self.payload(target_version="release-next"))

        self.assertEqual(raised.exception.status_code, 422)
        current_revision.assert_not_called()


if __name__ == "__main__":
    unittest.main()
