# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio

import pytest

from powercontext.artifacts import ArtifactAddress
from powercontext.builtin.artifacts.memory import MemoryEntryInput
from powercontext.builtin.persistence.sqlite import SQLiteConfig
from powercontext.builtin.publication import (
    ArtifactPublicationConflictError,
    ArtifactPublicationRequest,
)
from powercontext.builtin.runtime import BuiltinConfig, open_builtin_contexts
from powercontext.builtin.scope import ScopeDraft


def test_publication_copies_only_one_exact_revision_with_resolvable_provenance() -> None:
    async def scenario() -> None:
        async with open_builtin_contexts(BuiltinConfig(database=SQLiteConfig())) as contexts:
            source_scope = await contexts.scopes.create(
                ScopeDraft(title="Source", summary="Private working state", idempotency_key="source")
            )
            target_scope = await contexts.scopes.create(
                ScopeDraft(title="Target", summary="Accepted result", idempotency_key="target")
            )
            source_context = await contexts.get(source_scope.scope_id)
            first = await source_context.artifacts.memory.remember(
                memory=None, entries=(MemoryEntryInput(kind="decision", text="Publish this exact decision."),)
            )
            assert first is not None
            request = ArtifactPublicationRequest(
                source=ArtifactAddress(scope_id=source_scope.scope_id, artifact=first.as_ref()),
                target_scope_id=target_scope.scope_id,
                idempotency_key="accepted-decision",
            )

            publication = await contexts.publications.publish(request)
            repeated = await contexts.publications.publish(request)
            await source_context.artifacts.memory.remember(
                memory=first,
                entries=(MemoryEntryInput(kind="fact", text="Later private material."),),
            )

            assert repeated == publication
            assert publication.source == request.source
            assert publication.target.scope_id == target_scope.scope_id
            assert publication.target.artifact.family == "memory"
            assert publication.target.artifact.artifact_id.startswith("pub_")
            assert len(publication.content_digest) == 64
            assert await contexts.publications.get(publication.target) == publication
            async with contexts.database.transaction() as connection:
                copied = await contexts.repositories.artifacts.get(
                    connection,
                    publication.target.scope_id,
                    publication.target.artifact,
                )
            assert copied.content == first.content
            assert copied.lineage.sources == ()
            assert copied.lineage.artifacts == ()

            with pytest.raises(ArtifactPublicationConflictError):
                await contexts.publications.publish(
                    request.model_copy(
                        update={
                            "source": ArtifactAddress(
                                scope_id=source_scope.scope_id,
                                artifact=first.model_copy(update={"revision": 2}).as_ref(),
                            )
                        }
                    )
                )

    asyncio.run(scenario())
