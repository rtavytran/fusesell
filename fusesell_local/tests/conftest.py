import pytest

from fusesell_local.utils.data_manager import LocalDataManager


@pytest.fixture
def data_manager(tmp_path):
    """Provide an isolated LocalDataManager instance backed by a temporary directory."""
    LocalDataManager._initialized_databases.clear()
    LocalDataManager._initialization_lock = False
    return LocalDataManager(data_dir=str(tmp_path))