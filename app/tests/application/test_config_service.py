from fake_ports import FakeConfigRepository
from ledsetup.application.models import DeviceInfo
from ledsetup.application.services.config_service import ConfigService


def test_important_changes_persist_immediately_and_color_waits_for_flush() -> None:
    store = FakeConfigRepository()
    service = ConfigService(store)
    service.set_color((4, 5, 6))
    assert store.saved == []
    service.select_device(DeviceInfo("aabbccddeeff"))
    assert store.saved[-1].last_color == (4, 5, 6)
    service.set_color((7, 8, 9))
    service.flush()
    assert store.saved[-1].last_color == (7, 8, 9)


def test_settings_monitor_and_forget_persist() -> None:
    store = FakeConfigRepository()
    service = ConfigService(store)
    service.update_settings(scan_timeout=2, connect_timeout=3, verbose=True)
    service.select_monitor("monitor-1")
    service.select_device(DeviceInfo("aabbccddeeff"))
    service.forget_device()
    assert len(store.saved) == 4
    assert store.saved[-1].selected_device is None
