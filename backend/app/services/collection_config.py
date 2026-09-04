"""Configuration loader and validator for multi-query Twitter collection."""

from pathlib import Path
import re
from typing import List, Union
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class CollectionQueryConfig(BaseModel):
    """Configuration definition for a single search query."""

    id: str = Field(..., description="Unique alphanumeric identifier for the query")
    category: str = Field(..., description="High-level category grouping (e.g. technology, finance)")
    query: str = Field(..., description="Twitter search query string")
    enabled: bool = Field(default=True, description="Whether this query is active in collection cycles")
    default_limit: int = Field(default=30, gt=0, description="Default max tweets to retrieve per cycle")

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query ID cannot be empty.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError(f"Query ID '{v}' must be alphanumeric with underscores or hyphens.")
        return v

    @field_validator("category", "query")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category and query strings cannot be empty.")
        return v


class CollectionConfigFile(BaseModel):
    """Top-level collection queries configuration file."""

    version: int = Field(default=1, description="Configuration schema version")
    queries: List[CollectionQueryConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_query_ids(self) -> "CollectionConfigFile":
        seen_ids = set()
        duplicates = set()
        for q in self.queries:
            if q.id in seen_ids:
                duplicates.add(q.id)
            seen_ids.add(q.id)

        if duplicates:
            raise ValueError(f"Duplicate query IDs found in configuration: {sorted(duplicates)}")
        return self

    def get_enabled_queries(self, filter_ids: list[str] | None = None) -> List[CollectionQueryConfig]:
        """Return enabled queries, optionally filtered to a subset of IDs."""
        enabled = [q for q in self.queries if q.enabled]
        if filter_ids:
            filter_set = set(filter_ids)
            enabled = [q for q in enabled if q.id in filter_set]
        return enabled


def load_collection_config(config_path: Union[str, Path]) -> CollectionConfigFile:
    """Read, parse, and validate collection_queries.yaml.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If YAML syntax is invalid or schema validation fails.
    """
    path = Path(config_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Collection queries configuration not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML in collection config file: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Invalid collection config format: expected top-level dictionary/mapping.")

    return CollectionConfigFile(**data)
