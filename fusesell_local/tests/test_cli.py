from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fusesell_local.cli import FuseSellCLI


class TestFuseSellCLI:
    def test_dry_run_pipeline_returns_zero(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        cli = FuseSellCLI()

        data_dir = tmp_path / "cli-run"
        args = [
            "--openai-api-key",
            "sk-test-123456",
            "--org-id",
            "demo",
            "--org-name",
            "Demo Org",
            "--full-input",
            "Seller: Demo Org, Customer: Example Corp, Communication: English",
            "--input-description",
            "Example Corp lead from CLI test",
            "--data-dir",
            str(data_dir),
            "--dry-run",
        ]

        exit_code = cli.run(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "FuseSell Execution Plan" in captured.out
        assert data_dir.exists()
