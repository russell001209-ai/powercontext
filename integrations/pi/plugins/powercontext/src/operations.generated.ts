/*
 * Copyright (c) 2026 OceanBase.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// generated from openapi/powercontext.yaml; do not edit.

export const OPERATIONS = {
  get_liveness: { method: 'GET', path: '/health/live', location: null, scope: false },
  get_readiness: { method: 'GET', path: '/health/ready', location: null, scope: false },
  get_capabilities: { method: 'GET', path: '/v1/capabilities', location: null, scope: false },
  list_scopes: { method: 'GET', path: '/v1/scopes', location: null, scope: false },
  create_scope: { method: 'POST', path: '/v1/scopes', location: "body", scope: false },
  publish_artifact: { method: 'POST', path: '/v1/artifact-publications', location: "body", scope: false },
  get_scope: { method: 'POST', path: '/v1/scopes/get', location: "body", scope: true },
  update_scope: { method: 'POST', path: '/v1/scopes/update', location: "body", scope: true },
  get_default_scope: { method: 'GET', path: '/v1/scopes/default', location: null, scope: false },
  set_default_scope: { method: 'PUT', path: '/v1/scopes/default', location: "body", scope: true },
  resolve_scope_selection: { method: 'POST', path: '/v1/scopes/selection/resolve', location: "body", scope: false },
  resolve_scope_binding: { method: 'POST', path: '/v1/scope-bindings/resolve', location: "body", scope: false },
  set_scope_binding: { method: 'PUT', path: '/v1/scope-bindings', location: "body", scope: true },
  clear_scope_binding: { method: 'POST', path: '/v1/scope-bindings/clear', location: "body", scope: false },
  capture_content_source: { method: 'POST', path: '/v1/sources/content', location: "body", scope: true },
  prepare_context: { method: 'POST', path: '/v1/context/prepare', location: "body", scope: true },
  create_work_contract: { method: 'POST', path: '/v1/work/contracts/create', location: "body", scope: true },
  handoff_current_work: { method: 'POST', path: '/v1/work/handoffs/prepare-current', location: "body", scope: true },
  acknowledge_handoff: { method: 'POST', path: '/v1/work/handoffs/acknowledge', location: "body", scope: true },
  record_task_outcome: { method: 'POST', path: '/v1/work/outcomes/record', location: "body", scope: true },
  activate_handoff: { method: 'POST', path: '/v1/handoff/activate', location: "body", scope: true },
  prepare_handoff: { method: 'POST', path: '/v1/handoff/prepare', location: "body", scope: true },
  finalize_handoff: { method: 'POST', path: '/v1/handoff/finalize', location: "body", scope: true },
  commit_handoff: { method: 'POST', path: '/v1/handoff/commit', location: "body", scope: true },
  continue_handoff: { method: 'POST', path: '/v1/handoff/continue', location: "body", scope: true },
  flush_memory: { method: 'POST', path: '/v1/memory/flush', location: "body", scope: true },
  remember_memory: { method: 'POST', path: '/v1/memory/remember', location: "body", scope: true },
  search_memory: { method: 'POST', path: '/v1/memory/search', location: "body", scope: true },
  list_memory_entries: { method: 'POST', path: '/v1/memory/entries/list', location: "body", scope: true },
  get_memory_entry: { method: 'POST', path: '/v1/memory/entries/get', location: "body", scope: true },
  revise_memory_entry: { method: 'POST', path: '/v1/memory/entries/revise', location: "body", scope: true },
  retire_memory_entry: { method: 'POST', path: '/v1/memory/entries/retire', location: "body", scope: true },
  list_memory_changes: { method: 'POST', path: '/v1/memory/changes', location: "body", scope: true },
  propose_experience: { method: 'POST', path: '/v1/experience/propose', location: "body", scope: true },
  generate_experience: { method: 'POST', path: '/v1/experience/generate', location: "body", scope: true },
  get_experience: { method: 'POST', path: '/v1/experience/get', location: "body", scope: true },
  propose_skill: { method: 'POST', path: '/v1/skill/propose', location: "body", scope: true },
  generate_skill: { method: 'POST', path: '/v1/skill/generate', location: "body", scope: true },
  get_skill: { method: 'POST', path: '/v1/skill/get', location: "body", scope: true },
  scan_external_skills: { method: 'POST', path: '/v1/external-skills/scan', location: "body", scope: true },
  list_external_skills: { method: 'POST', path: '/v1/external-skills/list', location: "body", scope: true },
  resolve_external_skill: { method: 'POST', path: '/v1/external-skills/resolve', location: "body", scope: true },
  import_external_skill: { method: 'POST', path: '/v1/external-skills/import', location: "body", scope: true },
  list_artifact_candidates: { method: 'POST', path: '/v1/artifact-candidates/list', location: "body", scope: true },
  get_artifact_candidate: { method: 'POST', path: '/v1/artifact-candidates/get', location: "body", scope: true },
  approve_artifact_candidate: { method: 'POST', path: '/v1/artifact-candidates/approve', location: "body", scope: true },
  reject_artifact_candidate: { method: 'POST', path: '/v1/artifact-candidates/reject', location: "body", scope: true },
  revise_artifact_candidate: { method: 'POST', path: '/v1/artifact-candidates/revise', location: "body", scope: true },
  get_stats: { method: 'POST', path: '/v1/stats', location: "body", scope: false },
  get_handoff_report: { method: 'POST', path: '/v1/handoff-reports/get', location: "body", scope: false },
} as const

export type OperationId = keyof typeof OPERATIONS

export type OperationSpec = (typeof OPERATIONS)[OperationId]

export const OPERATION_IDS = Object.keys(OPERATIONS) as OperationId[]
