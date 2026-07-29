import sqlite3
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backup_manager
import config
from desktop_security import DesktopApiSecurityMiddleware
from routers import auth


class DesktopSecurityTests(unittest.TestCase):
    TOKEN = "desktop-test-token-" + ("a" * 48)

    def setUp(self):
        app = FastAPI()
        app.add_middleware(DesktopApiSecurityMiddleware, token=self.TOKEN)

        @app.get("/private")
        def private_route():
            return {"ok": True}

        self.client = TestClient(app, base_url="http://127.0.0.1")

    def test_rejects_request_without_desktop_token(self):
        response = self.client.get("/private")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("cache-control"),
            "no-store",
        )

    def test_rejects_non_loopback_host_and_untrusted_origin(self):
        bad_host = self.client.get(
            "/private",
            headers={
                "host": "attacker.example",
                "X-Emovest-Desktop-Token": self.TOKEN,
            },
        )
        bad_origin = self.client.get(
            "/private",
            headers={
                "origin": "https://attacker.example",
                "X-Emovest-Desktop-Token": self.TOKEN,
            },
        )

        self.assertEqual(bad_host.status_code, 400)
        self.assertEqual(bad_origin.status_code, 403)

    def test_accepts_authenticated_tauri_request(self):
        response = self.client.get(
            "/private",
            headers={
                "origin": "http://tauri.localhost",
                "X-Emovest-Desktop-Token": self.TOKEN,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_authentication_uses_the_persisted_desktop_secret(self):
        self.assertEqual(auth.SECRET_KEY, config.SECRET_KEY)
        self.assertGreaterEqual(len(auth.SECRET_KEY), 32)

    def test_password_hashing_uses_bcrypt_without_storing_plaintext(self):
        password = "Desktop-test-2026!"
        hashed = auth.hash_password(password)

        self.assertNotEqual(hashed, password)
        self.assertTrue(auth.verify_password(password, hashed))
        self.assertFalse(auth.verify_password("incorrecta", hashed))


class DesktopBackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="EmoVest datos ñ ",
        )
        self.root = Path(self.temporary_directory.name)
        self.database_path = self.root / "datos con espacios.sqlite3"
        self.backup_dir = self.root / "copias"
        self.image_dir = self.root / "imágenes"
        self.backup_dir.mkdir()
        self.image_dir.mkdir()

        connection = sqlite3.connect(self.database_path)
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES (?)", ("dato local",))
        connection.execute("INSERT INTO alembic_version VALUES (?)", ("0002_local_runtime",))
        connection.commit()
        connection.close()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_consistent_database_backup_preserves_unicode_path_and_data(self):
        with (
            patch.object(backup_manager, "DATABASE_PATH", self.database_path),
            patch.object(backup_manager, "BACKUP_DIR", self.backup_dir),
        ):
            backup = backup_manager.create_database_backup("Prueba actualización")

        connection = sqlite3.connect(backup)
        try:
            value = connection.execute("SELECT value FROM sample").fetchone()[0]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(value, "dato local")
        self.assertEqual(integrity, "ok")

    def test_manual_archive_contains_database_and_images_but_not_logs(self):
        image = self.image_dir / "captura ñ.png"
        image.write_bytes(b"not-a-real-image")
        with (
            patch.object(backup_manager, "DATABASE_PATH", self.database_path),
            patch.object(backup_manager, "BACKUP_DIR", self.backup_dir),
            patch.object(backup_manager, "IMAGE_STORAGE_PATH", self.image_dir),
        ):
            archive = backup_manager.create_manual_backup_archive("0.4.0")

        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            manifest = bundle.read("manifest.json").decode("utf-8")

        self.assertIn("data/emovest.sqlite3", names)
        self.assertIn("images/captura ñ.png", names)
        self.assertNotIn("logs/emovest.log", names)
        self.assertIn('"schema_revision": "0002_local_runtime"', manifest)

    def test_concurrent_backups_have_unique_valid_destinations(self):
        with (
            patch.object(backup_manager, "DATABASE_PATH", self.database_path),
            patch.object(backup_manager, "BACKUP_DIR", self.backup_dir),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            backups = list(executor.map(
                backup_manager.create_database_backup,
                ("concurrent", "concurrent"),
            ))

        self.assertEqual(len(set(backups)), 2)
        for backup in backups:
            connection = sqlite3.connect(backup)
            try:
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )
            finally:
                connection.close()

    def test_prunes_only_old_automatic_backups(self):
        with (
            patch.object(backup_manager, "DATABASE_PATH", self.database_path),
            patch.object(backup_manager, "BACKUP_DIR", self.backup_dir),
        ):
            for version in ("0.4.1", "0.4.2", "0.4.3"):
                backup_manager.create_database_backup(f"pre-update-{version}")
            manual = backup_manager.create_database_backup("manual-keep")
            backup_manager.prune_database_backups("pre-update", retention=2)

        automatic_backups = sorted(self.backup_dir.glob("pre-update-*.sqlite3"))
        self.assertEqual(len(automatic_backups), 2)
        self.assertTrue(manual.exists())

    def test_manual_archive_skips_symbolic_links(self):
        outside_file = self.root / "private.txt"
        outside_file.write_text("do not export", encoding="utf-8")
        link = self.image_dir / "outside.png"
        try:
            link.symlink_to(outside_file)
        except OSError:
            self.skipTest("El entorno no permite crear enlaces simbólicos.")

        with (
            patch.object(backup_manager, "DATABASE_PATH", self.database_path),
            patch.object(backup_manager, "BACKUP_DIR", self.backup_dir),
            patch.object(backup_manager, "IMAGE_STORAGE_PATH", self.image_dir),
        ):
            archive = backup_manager.create_manual_backup_archive("0.4.0")

        with zipfile.ZipFile(archive) as bundle:
            self.assertNotIn("images/outside.png", bundle.namelist())


if __name__ == "__main__":
    unittest.main()
