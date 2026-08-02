import os
import subprocess
from unittest.mock import patch
import pytest

os.environ.setdefault("CLOUD_BACKUP_CONFD", "/tmp/test_conf")
os.environ.setdefault("CLOUD_BACKUP_DATAD", "/tmp/test_data")

from cloud_services_backup_cli.tools.vdirsyncer import vdirsyncer_discover, vdirsyncer_sync, VDirSyncerService


@pytest.fixture
def config_path(tmp_path):
    p = tmp_path / "vdirsyncer.conf"
    p.write_text("[general]")
    return p


@pytest.fixture
def svc(tmp_path):
    confd = tmp_path / "conf"
    datad = tmp_path / "data"
    confd.mkdir(); datad.mkdir()
    with patch.dict(os.environ, {
        "CLOUD_BACKUP_CONFD": str(confd),
        "CLOUD_BACKUP_DATAD": str(datad),
    }):
        return VDirSyncerService("google_calendar", "user@gmail.com")


class TestVDirSyncerServiceConfig:

    def test_config_calendar_has_correct_pair_name(self, svc):
        svc._ensure_config()
        assert "[pair google_calendar]" in svc.config_path.read_text()

    def test_config_calendar_uses_ics_extension(self, svc):
        svc._ensure_config()
        assert 'fileext = ".ics"' in svc.config_path.read_text()

    def test_config_contacts_uses_vcf_extension(self, tmp_path):
        confd = tmp_path / "conf"; datad = tmp_path / "data"
        confd.mkdir(); datad.mkdir()
        with patch.dict(os.environ, {
            "CLOUD_BACKUP_CONFD": str(confd),
            "CLOUD_BACKUP_DATAD": str(datad),
        }):
            s = VDirSyncerService("google_contacts", "user@gmail.com")
        s._ensure_config()
        assert 'fileext = ".vcf"' in s.config_path.read_text()

    def test_config_includes_credentials_when_env_vars_set(self, svc):
        with patch.dict(os.environ, {
            "GOOGLE_OAUTH_CLIENT_ID": "test-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
        }):
            svc._ensure_config()
        config = svc.config_path.read_text()
        assert 'client_id = "test-client-id"' in config
        assert 'client_secret = "test-client-secret"' in config

    def test_config_omits_credentials_when_env_vars_absent(self, svc):
        env = {k: v for k, v in os.environ.items()
               if k not in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET")}
        with patch.dict(os.environ, env, clear=True):
            svc._ensure_config()
        config = svc.config_path.read_text()
        assert "client_id" not in config
        assert "client_secret" not in config

    def test_config_remote_storage_type_matches_service(self, svc):
        svc._ensure_config()
        assert 'type = "google_calendar"' in svc.config_path.read_text()

    def test_config_status_path_is_inside_user_confd(self, svc):
        svc._ensure_config()
        assert f'status_path = "./{svc.status_path.name}"' in svc.config_path.read_text()

    def test_config_local_path_points_to_staging(self, svc):
        svc._ensure_config()
        assert str(svc.staging_path) in svc.config_path.read_text()

    def test_config_token_file_points_to_token_path(self, svc):
        svc._ensure_config()
        assert str(svc.token_path) in svc.config_path.read_text()

    def test_config_partial_sync_is_revert(self, svc):
        svc._ensure_config()
        assert 'partial_sync = "revert"' in svc.config_path.read_text()

    def test_config_collections_from_remote(self, svc):
        svc._ensure_config()
        assert 'collections = ["from a"]' in svc.config_path.read_text()

    def test_write_config_is_idempotent(self, svc):
        svc._ensure_config()
        first = svc.config_path.read_text()
        svc._ensure_config()
        assert svc.config_path.read_text() == first


class TestVDirSyncerServiceSetup:

    def test_is_setup_false_when_files_absent(self, svc):
        assert svc._is_setup() is False

    def test_is_setup_true_when_both_files_present(self, svc):
        svc.config_path.write_text('')
        svc.token_path.write_text('')
        assert svc._is_setup() is True

    def test_is_setup_false_when_only_config_present(self, svc):
        svc.config_path.write_text('')
        assert svc._is_setup() is False

    def test_reset_removes_config_and_token(self, svc):
        svc.config_path.write_text('')
        svc.token_path.write_text('')
        svc._reset()
        assert not svc.config_path.exists()
        assert not svc.token_path.exists()

    def test_reset_is_safe_when_files_absent(self, svc):
        svc._reset()  # should not raise


class TestVdirsyncerSync:

    def test_sync_runs_sync_subcommand(self, config_path):
        with patch("subprocess.run") as mock_run:
            vdirsyncer_sync(config_path)
        assert mock_run.call_args_list[0].args[0][3] == "sync"

    def test_sync_passes_config_flag(self, config_path):
        with patch("subprocess.run") as mock_run:
            vdirsyncer_sync(config_path)
        cmd = mock_run.call_args_list[0].args[0]
        assert "-c" in cmd and str(config_path) in cmd

    def test_sync_raises_on_subprocess_failure(self, config_path):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "vdirsyncer")):
            with pytest.raises(subprocess.CalledProcessError):
                vdirsyncer_sync(config_path)


class TestVdirsyncerDiscover:

    def test_discover_runs_discover_subcommand(self, config_path):
        with patch("subprocess.run") as mock_run:
            vdirsyncer_discover(config_path)
        assert mock_run.call_args_list[0].args[0][3] == "discover"

    def test_discover_passes_config_flag(self, config_path):
        with patch("subprocess.run") as mock_run:
            vdirsyncer_discover(config_path)
        cmd = mock_run.call_args_list[0].args[0]
        assert "-c" in cmd and str(config_path) in cmd

    def test_discover_passes_newlines_to_stdin(self, config_path):
        with patch("subprocess.run") as mock_run:
            vdirsyncer_discover(config_path)
        assert "\n" in mock_run.call_args_list[0].kwargs["input"]
