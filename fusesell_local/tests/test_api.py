from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fusesell_local.api import (
    build_config,
    execute_pipeline,
    prepare_data_directory,
    validate_config,
)


def base_options(**overrides):
    options = {
        "openai_api_key": "sk-test-123456",
        "org_id": "demo",
        "org_name": "Demo Org",
        "full_input": "Seller: Demo Org, Customer: Example Corp, Communication: English",
        "input_description": "Example Corp, contact@example.com",
        "dry_run": True,
    }
    options.update(overrides)
    return options


def test_build_config_generates_defaults():
    config = build_config(base_options())

    assert config["execution_id"].startswith("fusesell_")
    assert config["output_format"] == "json"
    assert config["skip_stages"] == []
    assert config["send_immediately"] is False


def test_validate_config_detects_missing_sources():
    config = build_config(
        base_options(
            input_description="",
            input_website="",
            input_freetext="",
        )
    )

    valid, errors = validate_config(config)
    assert not valid
    assert any("At least one data source" in err for err in errors)


def test_prepare_data_directory_sets_default_log(tmp_path: Path):
    config = build_config(base_options(data_dir=str(tmp_path / "session-data")))

    data_dir = prepare_data_directory(config)

    assert data_dir.exists()
    assert Path(config["log_file"]).parent == data_dir / "logs"


def test_execute_pipeline_returns_dry_run(tmp_path: Path):
    result = execute_pipeline(
        base_options(data_dir=str(tmp_path / "session"), dry_run=True)
    )

    assert result["status"] == "dry_run"
    assert "execution_id" in result
