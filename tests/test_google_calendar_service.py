import os
import pytest
from unittest.mock import patch

os.environ.setdefault("CLOUD_BACKUP_CONFD", "/tmp/test_conf")
os.environ.setdefault("CLOUD_BACKUP_DATAD", "/tmp/test_data")

from cloud_services_backup_cli.services.google_calendar import GoogleCalendar

TOOL_MOD = "cloud_services_backup_cli.tools.vdirsyncer"


@pytest.fixture
def service(tmp_path):
    confd = tmp_path / "conf"
    datad = tmp_path / "data"
    confd.mkdir()
    datad.mkdir()
    with patch.dict(os.environ, {
        "CLOUD_BACKUP_CONFD": str(confd),
        "CLOUD_BACKUP_DATAD": str(datad),
    }):
        yield GoogleCalendar("rtomac@gmail.com")


class TestGoogleCalendarService:

    def test_user_confd_is_under_vdirsyncer_google_calendar(self, service):
        assert "vdirsyncer" in str(service.user_confd)
        assert "google_calendar" in str(service.user_confd)

    def test_user_backupd_is_under_google_calendar(self, service):
        assert "google_calendar" in str(service.user_backupd)

    def test_username_defaults_to_gmail_dot_com(self, tmp_path):
        confd = tmp_path / "conf"
        datad = tmp_path / "data"
        confd.mkdir(); datad.mkdir()
        with patch.dict(os.environ, {
            "CLOUD_BACKUP_CONFD": str(confd),
            "CLOUD_BACKUP_DATAD": str(datad),
        }):
            s = GoogleCalendar("rtomac")
        assert s.username == "rtomac@gmail.com"

    def test_setup_required_true_when_not_configured(self, service):
        assert service.setup_required() is True

    def test_setup_required_false_when_fully_configured(self, service):
        service.config_path.write_text('')
        service.token_path.write_text('')
        assert service.setup_required() is False

    def test_setup_calls_vdirsyncer_discover(self, service):
        with patch(f"{TOOL_MOD}.vdirsyncer_discover") as mock_discover:
            service.setup()
        mock_discover.assert_called_once_with(service.config_path)

    def test_backup_calls_vdirsyncer_sync(self, service):
        with patch(f"{TOOL_MOD}.vdirsyncer_discover"), \
             patch(f"{TOOL_MOD}.vdirsyncer_sync") as mock_sync, \
             patch(f"{TOOL_MOD}.rsync.rsync"):
            service._backup("copy")
        mock_sync.assert_called_once_with(service.config_path)

    def test_backup_copy_does_not_delete(self, service):
        with patch(f"{TOOL_MOD}.vdirsyncer_discover"), \
             patch(f"{TOOL_MOD}.vdirsyncer_sync"), \
             patch(f"{TOOL_MOD}.rsync.rsync") as mock_rsync:
            service._backup("copy")
        assert "--delete" not in mock_rsync.call_args[0]

    def test_backup_sync_uses_delete(self, service):
        with patch(f"{TOOL_MOD}.vdirsyncer_discover"), \
             patch(f"{TOOL_MOD}.vdirsyncer_sync"), \
             patch(f"{TOOL_MOD}.rsync.rsync") as mock_rsync:
            service._backup("sync")
        assert "--delete" in mock_rsync.call_args[0]
