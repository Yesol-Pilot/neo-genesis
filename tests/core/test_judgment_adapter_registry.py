# -*- coding: utf-8 -*-
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_judgment_adapter_registry_matches_schema():
    registry_path = PROJECT_ROOT / ".agent" / "registries" / "judgment_adapter_registry.json"
    schema_path = PROJECT_ROOT / ".agent" / "schemas" / "judgment_adapter_registry.schema.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=lambda item: list(item.path))

    assert errors == []


def test_judgment_adapter_registry_covers_initial_targets():
    registry = json.loads(
        (PROJECT_ROOT / ".agent" / "registries" / "judgment_adapter_registry.json").read_text(encoding="utf-8")
    )
    kinds = {adapter["kind"] for adapter in registry["adapters"]}

    assert {
        "sbu_growth",
        "sora_execution",
        "rag_memory",
        "frontend_qa",
        "security_dependency",
    }.issubset(kinds)


def test_each_adapter_has_approval_and_red_criteria():
    registry = json.loads(
        (PROJECT_ROOT / ".agent" / "registries" / "judgment_adapter_registry.json").read_text(encoding="utf-8")
    )

    for adapter in registry["adapters"]:
        assert adapter["approvalRules"], adapter["kind"]
        assert adapter["redCriteria"], adapter["kind"]
