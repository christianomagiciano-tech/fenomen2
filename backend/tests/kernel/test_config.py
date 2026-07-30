from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from backend.contracts.errors import ConfigurationError
from backend.kernel.config.manager import ConfigManager
from backend.kernel.config.schema import KernelConfig


class _SampleModuleConfig(BaseModel):
    enabled: bool = True
    threshold: int = 10


def test_get_section_returns_validated_model() -> None:
    manager = ConfigManager(raw_config={"kernel": {"log_level": "DEBUG", "log_format": "json"}})

    kernel_config = manager.get_section("kernel", KernelConfig)

    assert kernel_config.log_level == "DEBUG"
    assert kernel_config.log_format == "json"


def test_missing_section_falls_back_to_schema_defaults() -> None:
    manager = ConfigManager(raw_config={})

    kernel_config = manager.get_section("kernel", KernelConfig)

    assert kernel_config == KernelConfig()


def test_invalid_section_value_raises_configuration_error() -> None:
    manager = ConfigManager(raw_config={"kernel": {"log_level": "NOT_A_REAL_LEVEL"}})

    with pytest.raises(ConfigurationError):
        manager.get_section("kernel", KernelConfig)


def test_section_that_is_not_a_mapping_raises_configuration_error() -> None:
    manager = ConfigManager(raw_config={"kernel": "not-a-mapping"})

    with pytest.raises(ConfigurationError):
        manager.get_section("kernel", KernelConfig)


def test_has_section() -> None:
    manager = ConfigManager(raw_config={"kernel": {}})

    assert manager.has_section("kernel") is True
    assert manager.has_section("nonexistent") is False


def test_multiple_independent_sections() -> None:
    manager = ConfigManager(
        raw_config={
            "kernel": {"log_level": "WARNING"},
            "some_module": {"enabled": False, "threshold": 42},
        }
    )

    kernel_config = manager.get_section("kernel", KernelConfig)
    module_config = manager.get_section("some_module", _SampleModuleConfig)

    assert kernel_config.log_level == "WARNING"
    assert module_config.enabled is False
    assert module_config.threshold == 42


def test_from_yaml_file_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        ConfigManager.from_yaml_file(tmp_path / "does-not-exist.yaml")


def test_from_yaml_file_loads_valid_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("kernel:\n  log_level: ERROR\n")

    manager = ConfigManager.from_yaml_file(config_file)
    kernel_config = manager.get_section("kernel", KernelConfig)

    assert kernel_config.log_level == "ERROR"


def test_from_yaml_file_rejects_non_mapping_top_level(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- just\n- a\n- list\n")

    with pytest.raises(ConfigurationError):
        ConfigManager.from_yaml_file(config_file)


def test_from_yaml_file_rejects_invalid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("kernel: [unclosed\n")

    with pytest.raises(ConfigurationError):
        ConfigManager.from_yaml_file(config_file)


def test_from_yaml_file_handles_empty_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    manager = ConfigManager.from_yaml_file(config_file)

    assert manager.get_section("kernel", KernelConfig) == KernelConfig()
