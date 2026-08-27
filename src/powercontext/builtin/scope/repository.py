# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0

"""Relational persistence for durable Scope organization."""

from __future__ import annotations

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from powercontext.builtin.persistence.tables import (
    SCOPE_BINDINGS_TABLE,
    SCOPE_CONTEXT_REFERENCES_TABLE,
    SCOPE_CREATION_REQUESTS_TABLE,
    SCOPE_EXTERNAL_REFERENCES_TABLE,
    SCOPE_SETTINGS_TABLE,
    SCOPES_TABLE,
)
from powercontext.builtin.scope.models import (
    ScopeBinding,
    ScopeBindingKey,
    ScopeDescriptor,
    ScopeDraft,
    ScopeExternalReference,
    ScopeMutation,
)

_DEFAULT_SETTING = "default"


class ScopeRepository:
    async def get(self, connection: AsyncConnection, scope_id: str, /) -> ScopeDescriptor | None:
        row = (
            (await connection.execute(select(SCOPES_TABLE).where(SCOPES_TABLE.c.scope_id == scope_id)))
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        context_references = tuple(
            str(value)
            for value in (
                await connection.execute(
                    select(SCOPE_CONTEXT_REFERENCES_TABLE.c.referenced_scope_id)
                    .where(SCOPE_CONTEXT_REFERENCES_TABLE.c.scope_id == scope_id)
                    .order_by(SCOPE_CONTEXT_REFERENCES_TABLE.c.referenced_scope_id)
                )
            ).scalars()
        )
        external_references = tuple(
            ScopeExternalReference(kind=str(value.kind), value=str(value.value))
            for value in (
                await connection.execute(
                    select(
                        SCOPE_EXTERNAL_REFERENCES_TABLE.c.kind,
                        SCOPE_EXTERNAL_REFERENCES_TABLE.c.value,
                    )
                    .where(SCOPE_EXTERNAL_REFERENCES_TABLE.c.scope_id == scope_id)
                    .order_by(SCOPE_EXTERNAL_REFERENCES_TABLE.c.ordinal)
                )
            )
        )
        return ScopeDescriptor(
            scope_id=str(row["scope_id"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            parent_scope_id=None if row["parent_scope_id"] is None else str(row["parent_scope_id"]),
            context_references=context_references,
            external_references=external_references,
            version=int(row["version"]),
        )

    async def list(self, connection: AsyncConnection, /) -> tuple[ScopeDescriptor, ...]:
        scope_ids = tuple(
            str(value)
            for value in (
                await connection.execute(select(SCOPES_TABLE.c.scope_id).order_by(SCOPES_TABLE.c.scope_id))
            ).scalars()
        )
        scopes: list[ScopeDescriptor] = []
        for scope_id in scope_ids:
            scope = await self.get(connection, scope_id)
            if scope is None:
                raise AssertionError
            scopes.append(scope)
        return tuple(scopes)

    async def children(self, connection: AsyncConnection, parent_scope_id: str, /) -> tuple[str, ...]:
        return tuple(
            str(value)
            for value in (
                await connection.execute(
                    select(SCOPES_TABLE.c.scope_id)
                    .where(SCOPES_TABLE.c.parent_scope_id == parent_scope_id)
                    .order_by(SCOPES_TABLE.c.scope_id)
                )
            ).scalars()
        )

    async def creation(self, connection: AsyncConnection, idempotency_key: str, /) -> tuple[str, str] | None:
        row = (
            await connection.execute(
                select(
                    SCOPE_CREATION_REQUESTS_TABLE.c.request_digest,
                    SCOPE_CREATION_REQUESTS_TABLE.c.scope_id,
                ).where(SCOPE_CREATION_REQUESTS_TABLE.c.idempotency_key == idempotency_key)
            )
        ).one_or_none()
        return None if row is None else (str(row.request_digest), str(row.scope_id))

    async def add(
        self,
        connection: AsyncConnection,
        scope_id: str,
        draft: ScopeDraft,
        request_digest: str,
        /,
    ) -> ScopeDescriptor:
        await connection.execute(
            insert(SCOPES_TABLE).values(
                scope_id=scope_id,
                title=draft.title,
                summary=draft.summary,
                parent_scope_id=draft.parent_scope_id,
                version=1,
            )
        )
        await self._replace_relationships(
            connection,
            scope_id,
            draft.context_references,
            draft.external_references,
        )
        await connection.execute(
            insert(SCOPE_CREATION_REQUESTS_TABLE).values(
                idempotency_key=draft.idempotency_key,
                request_digest=request_digest,
                scope_id=scope_id,
            )
        )
        created = await self.get(connection, scope_id)
        if created is None:
            raise AssertionError
        return created

    async def replace(
        self,
        connection: AsyncConnection,
        scope_id: str,
        mutation: ScopeMutation,
        /,
    ) -> bool:
        result = await connection.execute(
            update(SCOPES_TABLE)
            .where(
                SCOPES_TABLE.c.scope_id == scope_id,
                SCOPES_TABLE.c.version == mutation.expected_version,
            )
            .values(
                title=mutation.title,
                summary=mutation.summary,
                parent_scope_id=mutation.parent_scope_id,
                version=mutation.expected_version + 1,
            )
        )
        if result.rowcount != 1:
            return False
        await self._replace_relationships(
            connection,
            scope_id,
            mutation.context_references,
            mutation.external_references,
        )
        return True

    async def default_scope_id(self, connection: AsyncConnection, /) -> str | None:
        value = (
            await connection.execute(
                select(SCOPE_SETTINGS_TABLE.c.scope_id).where(SCOPE_SETTINGS_TABLE.c.name == _DEFAULT_SETTING)
            )
        ).scalar_one_or_none()
        return None if value is None else str(value)

    async def set_default(self, connection: AsyncConnection, scope_id: str, /) -> None:
        result = await connection.execute(
            update(SCOPE_SETTINGS_TABLE)
            .where(SCOPE_SETTINGS_TABLE.c.name == _DEFAULT_SETTING)
            .values(scope_id=scope_id)
        )
        if result.rowcount == 0:
            await connection.execute(insert(SCOPE_SETTINGS_TABLE).values(name=_DEFAULT_SETTING, scope_id=scope_id))

    async def binding(self, connection: AsyncConnection, key: ScopeBindingKey, /) -> ScopeBinding | None:
        value = (
            await connection.execute(
                select(SCOPE_BINDINGS_TABLE.c.scope_id).where(
                    SCOPE_BINDINGS_TABLE.c.integration == key.integration,
                    SCOPE_BINDINGS_TABLE.c.kind == key.kind,
                    SCOPE_BINDINGS_TABLE.c.external_id == key.external_id,
                )
            )
        ).scalar_one_or_none()
        return None if value is None else ScopeBinding(key=key, scope_id=str(value))

    async def set_binding(
        self,
        connection: AsyncConnection,
        key: ScopeBindingKey,
        scope_id: str,
        /,
    ) -> ScopeBinding:
        result = await connection.execute(
            update(SCOPE_BINDINGS_TABLE)
            .where(
                SCOPE_BINDINGS_TABLE.c.integration == key.integration,
                SCOPE_BINDINGS_TABLE.c.kind == key.kind,
                SCOPE_BINDINGS_TABLE.c.external_id == key.external_id,
            )
            .values(scope_id=scope_id)
        )
        if result.rowcount == 0:
            await connection.execute(
                insert(SCOPE_BINDINGS_TABLE).values(
                    integration=key.integration,
                    kind=key.kind,
                    external_id=key.external_id,
                    scope_id=scope_id,
                )
            )
        return ScopeBinding(key=key, scope_id=scope_id)

    async def clear_binding(self, connection: AsyncConnection, key: ScopeBindingKey, /) -> bool:
        result = await connection.execute(
            delete(SCOPE_BINDINGS_TABLE).where(
                SCOPE_BINDINGS_TABLE.c.integration == key.integration,
                SCOPE_BINDINGS_TABLE.c.kind == key.kind,
                SCOPE_BINDINGS_TABLE.c.external_id == key.external_id,
            )
        )
        return result.rowcount == 1

    async def _replace_relationships(
        self,
        connection: AsyncConnection,
        scope_id: str,
        context_references: tuple[str, ...],
        external_references: tuple[ScopeExternalReference, ...],
    ) -> None:
        await connection.execute(
            delete(SCOPE_CONTEXT_REFERENCES_TABLE).where(SCOPE_CONTEXT_REFERENCES_TABLE.c.scope_id == scope_id)
        )
        if context_references:
            await connection.execute(
                insert(SCOPE_CONTEXT_REFERENCES_TABLE),
                [
                    {"scope_id": scope_id, "referenced_scope_id": referenced_scope_id}
                    for referenced_scope_id in context_references
                ],
            )
        await connection.execute(
            delete(SCOPE_EXTERNAL_REFERENCES_TABLE).where(SCOPE_EXTERNAL_REFERENCES_TABLE.c.scope_id == scope_id)
        )
        if external_references:
            await connection.execute(
                insert(SCOPE_EXTERNAL_REFERENCES_TABLE),
                [
                    {
                        "scope_id": scope_id,
                        "ordinal": ordinal,
                        "kind": reference.kind,
                        "value": reference.value,
                    }
                    for ordinal, reference in enumerate(external_references)
                ],
            )
