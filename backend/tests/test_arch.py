"""Lightweight architecture guardrail — OSS pytest-archon (Apache-2.0).

Reuses code from repo (no from-scratch business logic). Verifies
- api -> services one-way (services must not import api)
- models/config are leaves (no heavy deps)
- circular check is done via Madge for frontend; backend circular is implicitly covered by no self-dependency
"""
from pytest_archon import archrule


def test_services_must_not_import_api():
    (
        archrule("services must not depend on api (api is composition root)")
        .match("app.services.*")
        .should_not_import("app.api.*")
        .check("app", only_direct_imports=True)
    )


def test_models_are_leaf_no_api():
    (
        archrule("models must not import api (leaf)")
        .match("app.models*")
        .should_not_import("app.api.*")
        .check("app", only_direct_imports=True)
    )


def test_models_are_leaf_no_services():
    (
        archrule("models must not import services (leaf)")
        .match("app.models*")
        .should_not_import("app.services.*")
        .check("app", only_direct_imports=True)
    )


def test_config_is_leaf():
    (
        archrule("config must not import services (leaf)")
        .match("app.config*")
        .should_not_import("app.services.*")
        .check("app", only_direct_imports=True)
    )
