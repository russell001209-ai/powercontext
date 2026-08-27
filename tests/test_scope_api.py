# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from fastapi.testclient import TestClient

from powercontext.builtin.persistence.sqlite import SQLiteConfig
from powercontext.server.factory import create_server_app
from powercontext.server.settings import McpConfig, ServerSettings


def test_scope_http_flow_resolves_default_durable_and_observation_ranges(tmp_path) -> None:
    app = create_server_app(
        settings=ServerSettings(
            database=SQLiteConfig(url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}"),
            mcp=McpConfig(enabled=False),
        )
    )

    with TestClient(app) as client:
        default = client.get("/v1/scopes/default")
        assert default.status_code == 200
        default_scope_id = default.json()["scope_id"]

        root = client.post(
            "/v1/scopes",
            json={"title": "Feature", "summary": "Feature result", "idempotency_key": "feature"},
        )
        assert root.status_code == 201
        root_scope_id = root.json()["scope_id"]
        child = client.post(
            "/v1/scopes",
            json={
                "title": "Validation",
                "summary": "Independent validation",
                "parent_scope_id": root_scope_id,
                "idempotency_key": "validation",
            },
        )
        assert child.status_code == 201
        child_scope_id = child.json()["scope_id"]

        binding_key = {"integration": "codex", "kind": "session", "external_id": "session-1"}
        assert (
            client.put(
                "/v1/scope-bindings",
                json={"key": binding_key, "scope_id": child_scope_id},
            ).status_code
            == 200
        )
        resolved = client.post(
            "/v1/scope-bindings/resolve",
            json={"binding_keys": [binding_key]},
        )
        assert resolved.status_code == 200
        assert resolved.json()["scope_id"] == child_scope_id

        subtree = client.post(
            "/v1/scopes/selection/resolve",
            json={"selection": {"mode": "subtree", "root_scope_id": root_scope_id}},
        )
        assert [scope["scope_id"] for scope in subtree.json()["items"]] == [root_scope_id, child_scope_id]
        all_scopes = client.post(
            "/v1/scopes/selection/resolve",
            json={"selection": {"mode": "all"}},
        )
        assert {scope["scope_id"] for scope in all_scopes.json()["items"]} == {
            default_scope_id,
            root_scope_id,
            child_scope_id,
        }


def test_scope_http_flow_rejects_stale_metadata_and_invalid_selection(tmp_path) -> None:
    app = create_server_app(
        settings=ServerSettings(
            database=SQLiteConfig(url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}"),
            mcp=McpConfig(enabled=False),
        )
    )

    with TestClient(app) as client:
        created = client.post(
            "/v1/scopes",
            json={"title": "Work", "summary": "Initial", "idempotency_key": "work"},
        ).json()
        request = {
            "scope_id": created["scope_id"],
            "expected_version": created["version"],
            "title": "Work",
            "summary": "Updated",
        }
        assert client.post("/v1/scopes/update", json=request).status_code == 200
        stale = client.post("/v1/scopes/update", json=request)
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "scope_version_conflict"

        invalid = client.post(
            "/v1/scopes/selection/resolve",
            json={"selection": {"mode": "exact", "scope_ids": []}},
        )
        assert invalid.status_code == 422


def test_scope_http_flow_publishes_one_exact_artifact(tmp_path) -> None:
    app = create_server_app(
        settings=ServerSettings(
            database=SQLiteConfig(url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}"),
            mcp=McpConfig(enabled=False),
        )
    )

    with TestClient(app) as client:
        source_scope_id = client.post(
            "/v1/scopes",
            json={"title": "Source", "summary": "Working state", "idempotency_key": "source"},
        ).json()["scope_id"]
        target_scope_id = client.post(
            "/v1/scopes",
            json={"title": "Target", "summary": "Accepted state", "idempotency_key": "target"},
        ).json()["scope_id"]
        memory = client.post(
            "/v1/memory/remember",
            json={"scope_id": source_scope_id, "kind": "decision", "text": "Publish the accepted decision."},
        ).json()["memory"]
        request = {
            "source": {"scope_id": source_scope_id, "artifact": memory},
            "target_scope_id": target_scope_id,
            "idempotency_key": "accepted-decision",
        }

        created = client.post("/v1/artifact-publications", json=request)
        repeated = client.post("/v1/artifact-publications", json=request)

        assert created.status_code == 201
        assert repeated.status_code == 201
        assert created.json() == repeated.json()
        assert created.json()["source"] == request["source"]
        assert created.json()["target"]["scope_id"] == target_scope_id
        assert created.json()["target"]["artifact"]["revision"] == 1
