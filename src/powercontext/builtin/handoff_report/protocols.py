# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0

"""Read ports used by Handoff Report projection."""

from __future__ import annotations

from typing import Protocol

from powercontext.artifacts import ArtifactRef
from powercontext.builtin.artifacts.handoff import Handoff
from powercontext.builtin.scope.models import ScopeDescriptor, ScopeSelection


class HandoffReadAdapter(Protocol):
    async def latest(self, scope_id: str, /) -> Handoff | None: ...

    async def get(self, scope_id: str, reference: ArtifactRef, /) -> Handoff: ...


class ScopeSelectionResolver(Protocol):
    async def resolve_selection(self, selection: ScopeSelection, /) -> tuple[ScopeDescriptor, ...]: ...


__all__ = ["HandoffReadAdapter", "ScopeSelectionResolver"]
