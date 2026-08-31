import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ledsetup.adapters.storage.config_store import SCHEMA_VERSION, ConfigStore
from ledsetup.application.models import AppConfig, DeviceInfo


def test_round_trip_writes_schema_and_selected_device(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    config = AppConfig(
        scan_timeout=4.0,
        monitor_id="monitor-1",
        last_color=(1, 2, 3),
        selected_device=DeviceInfo("aabbccddeeff", "strip", -42),
    )
    store.save(config)
    loaded = store.load()
    assert loaded.selected_device == DeviceInfo("AA:BB:CC:DD:EE:FF", "strip")
    assert loaded.last_color == (1, 2, 3)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION
    assert set(raw["selected_device"]) == {"address", "name"}


def test_missing_version_unknown_and_missing_fields_are_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"scan_timeout": 3, "unknown_future_field": True}), encoding="utf-8")
    loaded = ConfigStore(path).load()
    assert loaded.scan_timeout == 3
    assert loaded.connect_timeout == AppConfig().connect_timeout


def test_invalid_field_does_not_reset_valid_fields(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"scan_timeout": -1, "connect_timeout": 12, "last_color": [999, 2, 3]}),
        encoding="utf-8",
    )
    loaded = ConfigStore(path).load()
    assert loaded.scan_timeout == AppConfig().scan_timeout
    assert loaded.connect_timeout == 12
    assert loaded.last_color == AppConfig().last_color


def test_missing_and_corrupt_use_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    assert ConfigStore(path).load() == AppConfig()
    path.write_text("{broken", encoding="utf-8")
    assert ConfigStore(path).load() == AppConfig()


def test_concurrent_writes_are_atomic(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    configs = [AppConfig(last_color=(index, 2, 3)) for index in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(store.save, configs))
    assert store.load() in configs


def test_legacy_files_are_not_read(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "settings.json").write_text('{"scan_timeout": 1}', encoding="utf-8")
    (tmp_path / "selected-device.json").write_text(
        '{"address": "AA:BB:CC:DD:EE:FF"}', encoding="utf-8"
    )
    target = tmp_path / "config.json"
    monkeypatch.setenv("LEDSETUP_CONFIG_FILE", str(target))
    assert ConfigStore().load() == AppConfig()
