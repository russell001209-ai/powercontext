# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import asyncio
import re

import pytest

from powercontext.builtin.persistence.sqlite import SQLiteConfig, SQLiteProfile
from powercontext.builtin.persistence.tables import BUILTIN_TABLES
from powercontext.builtin.scope import (
    ScopeApplication,
    ScopeBindingKey,
    ScopeDraft,
    ScopeIdempotencyConflictError,
    ScopeMutation,
    ScopeRelationshipError,
    ScopeSelection,
    ScopeVersionConflictError,
)


def test_scope_bootstrap_creates_one_ordinary_default() -> None:
    async def scenario() -> None:
        async with SQLiteProfile.open(SQLiteConfig(), tables=BUILTIN_TABLES) as profile:
            scopes = ScopeApplication(profile.database)

            first = await scopes.bootstrap_default()
            second = await scopes.bootstrap_default()

            assert first == second
            assert re.fullmatch(r"scp_[0-7][0-9a-hjkmnp-tv-z]{25}", first.scope_id)
            assert first.parent_scope_id is None
            assert first.context_references == ()
            assert await scopes.list() == (first,)

    asyncio.run(scenario())


def test_scope_creation_is_idempotent_but_not_ambiguous() -> None:
    async def scenario() -> None:
        async with SQLiteProfile.open(SQLiteConfig(), tables=BUILTIN_TABLES) as profile:
            scopes = ScopeApplication(profile.database)
            draft = ScopeDraft(title="Feature", summary="Implement search", idempotency_key="feature-search")

            assert await scopes.create(draft) == await scopes.create(draft)
            with pytest.raises(ScopeIdempotencyConflictError):
                await scopes.create(
                    ScopeDraft(title="Feature", summary="Different work", idempotency_key="feature-search")
                )

    asyncio.run(scenario())


def test_parent_organizes_without_sharing_and_cannot_form_a_cycle() -> None:
    async def scenario() -> None:
        async with SQLiteProfile.open(SQLiteConfig(), tables=BUILTIN_TABLES) as profile:
            scopes = ScopeApplication(profile.database)
            root = await scopes.create(ScopeDraft(title="Root", summary="Root result", idempotency_key="root"))
            child = await scopes.create(
                ScopeDraft(
                    title="Child",
                    summary="Independent result",
                    parent_scope_id=root.scope_id,
                    idempotency_key="child",
                )
            )

            assert child.context_references == ()
            with pytest.raises(ScopeRelationshipError, match="acyclic"):
                await scopes.update(
                    root.scope_id,
                    ScopeMutation(
                        expected_version=root.version,
                        title=root.title,
                        summary=root.summary,
                        parent_scope_id=child.scope_id,
                    ),
                )

    asyncio.run(scenario())


def test_context_references_remain_direct_and_metadata_updates_use_cas() -> None:
    async def scenario() -> None:
        async with SQLiteProfile.open(SQLiteConfig(), tables=BUILTIN_TABLES) as profile:
            scopes = ScopeApplication(profile.database)
            shared = await scopes.create(ScopeDraft(title="Shared", summary="Shared facts", idempotency_key="shared"))
            middle = await scopes.create(
                ScopeDraft(
                    title="Middle",
                    summary="Direct reader",
                    context_references=(shared.scope_id,),
                    idempotency_key="middle",
                )
            )
            current = await scopes.create(
                ScopeDraft(
                    title="Current",
                    summary="Reads only Middle",
                    context_references=(middle.scope_id,),
                    idempotency_key="current",
                )
            )

            assert current.context_references == (middle.scope_id,)
            updated = await scopes.update(
                current.scope_id,
                ScopeMutation(
                    expected_version=current.version,
                    title="Current result",
                    summary=current.summary,
                    context_references=current.context_references,
                ),
            )
            assert updated.version == 2
            with pytest.raises(ScopeVersionConflictError):
                await scopes.update(
                    current.scope_id,
                    ScopeMutation(
                        expected_version=current.version,
                        title=current.title,
                        summary=current.summary,
                    ),
                )

    asyncio.run(scenario())


def test_binding_precedence_and_observation_selection_are_independent() -> None:
    async def scenario() -> None:
        async with SQLiteProfile.open(SQLiteConfig(), tables=BUILTIN_TABLES) as profile:
            scopes = ScopeApplication(profile.database)
            default = await scopes.bootstrap_default()
            root = await scopes.create(ScopeDraft(title="Root", summary="Root result", idempotency_key="root"))
            child = await scopes.create(
                ScopeDraft(
                    title="Child",
                    summary="Child result",
                    parent_scope_id=root.scope_id,
                    idempotency_key="child",
                )
            )
            session = ScopeBindingKey(integration="codex", kind="session", external_id="session-1")
            workspace = ScopeBindingKey(integration="codex", kind="workspace", external_id="workspace-1")
            await scopes.bind(session, child.scope_id)
            await scopes.bind(workspace, root.scope_id)

            assert (await scopes.resolve_binding(binding_keys=(session, workspace))).scope_id == child.scope_id
            assert (await scopes.resolve_binding(binding_keys=(workspace,))).scope_id == root.scope_id
            assert (await scopes.resolve_binding()).scope_id == default.scope_id
            assert tuple(
                scope.scope_id
                for scope in await scopes.resolve_selection(ScopeSelection(mode="subtree", root_scope_id=root.scope_id))
            ) == (root.scope_id, child.scope_id)
            assert {scope.scope_id for scope in await scopes.resolve_selection(ScopeSelection(mode="all"))} == {
                default.scope_id,
                root.scope_id,
                child.scope_id,
            }

    asyncio.run(scenario())
