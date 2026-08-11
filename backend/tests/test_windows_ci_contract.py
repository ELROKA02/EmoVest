import re
import unittest
from pathlib import Path


class WindowsCiContractTests(unittest.TestCase):
    def test_sidecar_smoke_resolves_the_alembic_head_dynamically(self):
        repository_root = Path(__file__).resolve().parents[2]
        smoke_test = (
            repository_root / "scripts" / "test-windows-sidecar.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("get_head_revision", smoke_test)
        self.assertIn("$ExpectedSchemaRevision", smoke_test)
        self.assertIsNone(
            re.search(
                r'schema_revision\s+-ne\s+"\d{4}_[a-z0-9_]+"',
                smoke_test,
                flags=re.IGNORECASE,
            ),
            "El smoke test de Windows no debe fijar una revisión Alembic.",
        )


if __name__ == "__main__":
    unittest.main()
