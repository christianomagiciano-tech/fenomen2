"""
Centralized configuration loading and validation.

Design: one root YAML file holds one top-level section per module (plus a
`kernel:` section for the kernel itself). The `ConfigManager` does not
know or care what any section other than `kernel:` contains — each module
declares its own Pydantic schema and asks for its section by name via
`get_section()`. This keeps the kernel decoupled from every module's
configuration shape while still getting centralized, fail-fast validation
(a malformed config is caught at startup, not the first time a module
happens to read the bad field).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from backend.contracts.errors import ConfigurationError

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ConfigManager:
    """Holds raw configuration data and hands out validated, typed sections of it."""

    def __init__(self, raw_config: dict[str, Any]) -> None:
        self._raw = raw_config

    @classmethod
    def from_yaml_file(cls, path: Path) -> "ConfigManager":
        """
        Load configuration from a YAML file. Raises
        :class:`ConfigurationError` if the file is missing or is not a
        valid YAML mapping.
        """
        if not path.is_file():
            raise ConfigurationError(f"Config file not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Config file {path} is not valid YAML: {exc}") from exc

        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Config file {path} must contain a top-level mapping, got {type(data).__name__}."
            )
        return cls(raw_config=data)

    def has_section(self, section_name: str) -> bool:
        return section_name in self._raw

    def get_section(self, section_name: str, schema: type[SchemaT]) -> SchemaT:
        """
        Validate and return the named top-level section as an instance of
        `schema`. A missing section is treated as an empty mapping, so
        modules with an all-default config schema don't need an entry in
        the YAML file at all. Raises :class:`ConfigurationError` if the
        section fails schema validation.
        """
        section_data = self._raw.get(section_name, {})
        if not isinstance(section_data, dict):
            raise ConfigurationError(
                f"Config section {section_name!r} must be a mapping, "
                f"got {type(section_data).__name__}."
            )
        try:
            return schema.model_validate(section_data)
        except ValidationError as exc:
            raise ConfigurationError(
                f"Config section {section_name!r} failed validation:\n{exc}"
            ) from exc
