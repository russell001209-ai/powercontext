# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0

"""Runtime adapter for read-only Handoff report projection."""

from __future__ import annotations

from typing import Protocol

from powercontext.artifacts import ArtifactRef
from powercontext.builtin.artifacts.handoff import Handoff


class _ScopedHandoffReader(Protocol):
    async def latest(self) -> Handoff | None: ...

    async def revision(self, reference: ArtifactRef, /) -> Handoff: ...


class _HandoffApplicationReader(Protocol):
    def for_scope(self, scope_id: str, /) -> _ScopedHandoffReader: ...


class RuntimeHandoffReadAdapter:
    def __init__(self, application: _HandoffApplicationReader, /) -> None:
        self._application = application

    async def latest(self, scope_id: str, /) -> Handoff | None:
        return await self._application.for_scope(scope_id).latest()

    async def get(self, scope_id: str, reference: ArtifactRef, /) -> Handoff:
        return await self._application.for_scope(scope_id).revision(reference)


__all__ = ["RuntimeHandoffReadAdapter"]
