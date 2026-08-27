---
title: Backend-API-Reference
tags: [backend, api, reference, admin-api]
updated: 2026-08-27
---

# Backend-API-Reference

[Back to README](../../README.md)

Vollständige, mechanisch generierte Liste aller HTTP-Endpunkte unter
`adapters/admin-api/`. **Diese Doku wird automatisch erzeugt** —
regeneriere sie mit `.venv/bin/python scripts/dump_endpoints.py > docs/reference/20-backend-api-reference.md`
(Quelle: `scripts/dump_endpoints.py`).

This generated inventory includes both WebUI-facing and internal endpoints.
It describes the code surface; it does not imply that the development stack is
safe to expose to an untrusted network.

## Hinweise

- Effektiver Pfad = `APIRouter(prefix=...)` + Decorator-Pfad.
- `commander_api/*`-Sub-Router werden in `commander_routes.py` ohne Prefix eingehängt — die Pfade gelten so wie im Decorator.
- `trion_memory_router` ist zusätzlich unter `/trion/memory/...` gemountet (Sonderfall, hier nicht doppelt gelistet).
- Diese Liste enthält *alle* Backend-Endpunkte, auch interne (z. B. `/api/secrets/resolve/{name}`, Bearer-geschützt) und Übergangspfade (`/api/storage-broker/*`).

## `adapters/admin-api/autonomy_profile_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/settings/autonomy/profile` | `get_autonomy_profile()` | — |
| `POST` | `/api/settings/autonomy/profile` | `update_autonomy_profile()` | — |

## `adapters/admin-api/autonomy_tool_policy_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/settings/autonomy/tool-policy` | `get_tool_policy()` | Effective autonomy tool policy with source tracking. |
| `POST` | `/api/settings/autonomy/tool-policy` | `update_tool_policy()` | Persist autonomy tool policy overrides. |

## `adapters/admin-api/chat_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `POST` | `/api/chat` | `chat()` | — |

## `adapters/admin-api/commander_api/audit.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/audit` | `api_audit_log()` | — |
| `GET` | `/audit/secrets` | `api_secret_audit_log()` | — |

## `adapters/admin-api/commander_api/containers.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `POST` | `/cleanup` | `api_cleanup_all()` | Emergency: stop and remove ALL TRION containers. |
| `GET` | `/containers` | `api_list_containers()` | List all TRION-managed containers with live status. |
| `POST` | `/containers/{container_id}/exec` | `api_exec_in_container()` | Execute a command inside a running container. |
| `GET` | `/containers/{container_id}/host-companion/check` | `api_check_host_companion()` | Run host-companion checks for the blueprint behind a managed container. |
| `POST` | `/containers/{container_id}/host-companion/repair` | `api_repair_host_companion()` | Repair host-companion files/service for the blueprint behind a managed container. |
| `POST` | `/containers/{container_id}/host-companion/uninstall` | `api_uninstall_host_companion()` | Uninstall host-companion files/service for a stopped managed container. |
| `GET` | `/containers/{container_id}/logs` | `api_container_logs()` | Get logs from a container. |
| `POST` | `/containers/{container_id}/start` | `api_start_existing_container()` | Start a previously stopped TRION-managed container. |
| `GET` | `/containers/{container_id}/stats` | `api_container_stats()` | Get live resource stats + efficiency score. |
| `POST` | `/containers/{container_id}/stop` | `api_stop_container()` | Stop a container. Service containers may be preserved instead of removed. |
| `POST` | `/containers/{container_id}/trion-debug` | `api_trion_debug_container()` | Run a focused TRION debugging pass for the selected container. |
| `POST` | `/containers/{container_id}/trion-shell/start` | `api_trion_shell_start()` | Enter TRION shell-control mode for the attached container. |
| `POST` | `/containers/{container_id}/trion-shell/step` | `api_trion_shell_step()` | Generate the next shell action for an active TRION shell session. |
| `POST` | `/containers/{container_id}/trion-shell/stop` | `api_trion_shell_stop()` | Stop TRION shell-control mode and persist a compact session summary. |
| `POST` | `/containers/{container_id}/uninstall` | `api_uninstall_container()` | Remove a stopped managed container and uninstall its host companion when configured. |
| `GET` | `/home/status` | `api_home_status()` | Return TRION home identity + runtime health status. |
| `GET` | `/quota` | `api_get_quota()` | Get current session quota usage. |

## `adapters/admin-api/commander_api/hardware.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/blueprints/{blueprint_id}/hardware` | `get_blueprint_hardware_intents()` | — |
| `POST` | `/blueprints/{blueprint_id}/hardware/plan` | `plan_blueprint_hardware()` | — |
| `POST` | `/blueprints/{blueprint_id}/hardware/resolve` | `resolve_blueprint_hardware()` | — |
| `POST` | `/blueprints/{blueprint_id}/hardware/validate` | `validate_blueprint_hardware()` | — |

## `adapters/admin-api/commander_api/operations.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/approvals` | `api_get_pending_approvals()` | Get all pending approval requests. |
| `GET` | `/approvals/history` | `api_approval_history()` | Get approval history including resolved entries. |
| `GET` | `/approvals/{approval_id}` | `api_get_approval()` | Get a specific approval request. |
| `POST` | `/approvals/{approval_id}/approve` | `api_approve()` | Approve a pending request — starts the container. |
| `POST` | `/approvals/{approval_id}/reject` | `api_reject()` | Reject a pending approval request. |
| `GET` | `/dashboard` | `api_dashboard()` | Full system dashboard with health, resources, alerts, events. |
| `GET` | `/marketplace/bundles` | `api_list_bundles()` | — |
| `GET` | `/marketplace/catalog` | `api_marketplace_catalog()` | — |
| `POST` | `/marketplace/catalog/install/{blueprint_id}` | `api_marketplace_catalog_install()` | — |
| `POST` | `/marketplace/catalog/sync` | `api_marketplace_catalog_sync()` | — |
| `POST` | `/marketplace/export/{blueprint_id}` | `api_export_bundle()` | — |
| `POST` | `/marketplace/import` | `api_import_bundle()` | — |
| `GET` | `/marketplace/starters` | `api_list_starters()` | — |
| `POST` | `/marketplace/starters/{starter_id}/install` | `api_install_starter()` | — |
| `POST` | `/proxy/start` | `api_start_proxy()` | Start the Squid whitelist proxy. |
| `POST` | `/proxy/stop` | `api_stop_proxy()` | Stop the Squid proxy. |
| `GET` | `/proxy/whitelist/{blueprint_id}` | `api_get_whitelist()` | — |
| `POST` | `/proxy/whitelist/{blueprint_id}` | `api_set_whitelist()` | — |

## `adapters/admin-api/commander_api/secrets.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/secrets` | `api_list_secrets()` | — |
| `POST` | `/secrets` | `api_store_secret()` | — |
| `DELETE` | `/secrets/{secret_name}` | `api_delete_secret()` | — |

## `adapters/admin-api/commander_api/storage.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/networks` | `api_list_networks()` | List all TRION-managed Docker networks. |
| `POST` | `/networks/cleanup` | `api_cleanup_networks()` | Remove empty isolated TRION networks. |
| `GET` | `/networks/{container_id}/info` | `api_network_info()` | Get network details for a specific container. |
| `GET` | `/snapshots` | `api_list_snapshots()` | List all snapshots, optionally filtered by volume. |
| `POST` | `/snapshots/create` | `api_create_snapshot()` | Create a tarball snapshot of a volume. |
| `POST` | `/snapshots/restore` | `api_restore_snapshot()` | Restore a snapshot into a new or existing volume. |
| `DELETE` | `/snapshots/{filename}` | `api_delete_snapshot()` | Delete a snapshot file. |
| `GET` | `/storage/assets` | `api_list_storage_assets()` | List shared storage assets published by Storage Manager for Commander use. |
| `POST` | `/storage/assets` | `api_upsert_storage_asset()` | Create or update a shared storage asset entry. |
| `DELETE` | `/storage/assets/{asset_id}` | `api_delete_storage_asset()` | Delete one shared storage asset entry. |
| `GET` | `/storage/assets/{asset_id}` | `api_get_storage_asset()` | Get one shared storage asset. |
| `GET` | `/storage/managed-paths` | `api_list_storage_managed_paths()` | List Storage-Broker managed paths as a UI-friendly catalog for deploy pickers. |
| `GET` | `/storage/scopes` | `api_list_storage_scopes()` | List all approved storage scopes. |
| `POST` | `/storage/scopes` | `api_upsert_storage_scope()` | Create or update an approved storage scope. |
| `DELETE` | `/storage/scopes/{scope_name}` | `api_delete_storage_scope()` | Delete a storage scope. |
| `GET` | `/storage/scopes/{scope_name}` | `api_get_storage_scope()` | Get one storage scope. |
| `GET` | `/volumes` | `api_list_volumes()` | List all TRION workspace volumes. |
| `POST` | `/volumes/cleanup` | `api_cleanup_volumes()` | Find and optionally remove orphaned volumes. |
| `DELETE` | `/volumes/{volume_name}` | `api_remove_volume()` | Remove a workspace volume. |
| `GET` | `/volumes/{volume_name}` | `api_get_volume()` | Get details of a specific volume including its snapshots. |

## `adapters/admin-api/commander_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/blueprints` | `api_list_blueprints()` | — |
| `POST` | `/blueprints` | `api_create_blueprint()` | — |
| `POST` | `/blueprints/import` | `api_import_blueprint()` | — |
| `DELETE` | `/blueprints/{blueprint_id}` | `api_delete_blueprint()` | — |
| `GET` | `/blueprints/{blueprint_id}` | `api_get_blueprint()` | — |
| `PUT` | `/blueprints/{blueprint_id}` | `api_update_blueprint()` | — |
| `GET` | `/blueprints/{blueprint_id}/yaml` | `api_export_yaml()` | — |
| `POST` | `/containers/deploy` | `api_deploy_container()` | Deploy a container from a blueprint via Docker Engine. |

## `adapters/admin-api/main.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/` | `root()` | — |
| `GET` | `/health` | `health()` | — |

## `adapters/admin-api/maintenance_routes.py`
_Prefix:_ `/api/maintenance`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `POST` | `/api/maintenance/start` | `start_maintenance()` | — |
| `GET` | `/api/maintenance/status` | `get_maintenance_status()` | — |

## `adapters/admin-api/memory_defaults_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/settings/memory/defaults` | `get_memory_defaults()` | — |
| `POST` | `/api/settings/memory/defaults` | `update_memory_defaults()` | — |

## `adapters/admin-api/memory_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/memory/conversations` | `memory_conversations()` | — |
| `GET` | `/api/memory/conversations/{conversation_id}` | `memory_conversation_drill_in()` | — |
| `GET` | `/api/memory/conversations/{conversation_id}/policy` | `memory_conversation_policy()` | UI-freundlich normalisierte Policy. |
| `POST` | `/api/memory/delete-bulk` | `memory_delete_bulk()` | — |
| `GET` | `/api/memory/recent` | `memory_recent()` | Liefert die juengsten Memory-Eintraege. |
| `POST` | `/api/memory/search` | `memory_search()` | Sucht im Memory. Drei Modi, je eigener MCP-Tool-Pfad. |
| `DELETE` | `/api/memory/{memory_id}` | `memory_delete()` | — |

## `adapters/admin-api/models_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/models/catalog` | `models_catalog()` | — |
| `GET` | `/api/tags` | `tags()` | — |

## `adapters/admin-api/persona_routes.py`
_Prefix:_ `/api/personas`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/personas/` | `get_all_personas()` | — |
| `POST` | `/api/personas/` | `upload_persona()` | — |
| `PUT` | `/api/personas/content/{name}` | `update_persona()` | — |
| `PUT` | `/api/personas/switch` | `switch_active_persona()` | — |
| `DELETE` | `/api/personas/{name}` | `delete_persona_endpoint()` | — |
| `GET` | `/api/personas/{name}` | `get_persona_by_name()` | — |

## `adapters/admin-api/plugins_routes.py`
_Prefix:_ `/api/plugins`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `POST` | `/api/plugins/install` | `install_plugin()` | — |
| `GET` | `/api/plugins/installed` | `get_installed_plugins()` | — |
| `GET` | `/api/plugins/runtime/bridge.js` | `get_plugin_bridge_script()` | — |
| `DELETE` | `/api/plugins/{plugin_id}` | `delete_plugin()` | — |
| `GET` | `/api/plugins/{plugin_id}/asset/{asset_path:path}` | `get_plugin_asset()` | — |
| `POST` | `/api/plugins/{plugin_id}/bridge/request` | `bridge_plugin_request()` | — |
| `POST` | `/api/plugins/{plugin_id}/bridge/tools/{tool_name}` | `bridge_plugin_tool()` | — |
| `POST` | `/api/plugins/{plugin_id}/disable` | `disable_plugin()` | — |
| `POST` | `/api/plugins/{plugin_id}/enable` | `enable_plugin()` | — |
| `GET` | `/api/plugins/{plugin_id}/manifest` | `get_plugin_manifest()` | — |

## `adapters/admin-api/protocol_routes.py`
_Prefix:_ `/api/protocol`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `POST` | `/api/protocol/append` | `protocol_append()` | — |
| `GET` | `/api/protocol/list` | `protocol_list()` | — |
| `GET` | `/api/protocol/rolling-summary` | `get_rolling_summary()` | — |
| `POST` | `/api/protocol/summarize-yesterday` | `summarize_yesterday_endpoint()` | — |
| `GET` | `/api/protocol/today` | `protocol_today()` | — |
| `GET` | `/api/protocol/unmerged-count` | `protocol_unmerged_count()` | — |
| `GET` | `/api/protocol/{date}` | `protocol_get()` | — |
| `PUT` | `/api/protocol/{date}` | `protocol_update()` | — |
| `DELETE` | `/api/protocol/{date}/entry/{index}` | `protocol_delete_entry()` | — |
| `POST` | `/api/protocol/{date}/merge` | `protocol_merge()` | — |

## `adapters/admin-api/provider_keys_routes.py`
_Prefix:_ `/api/settings/api-keys`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/settings/api-keys` | `api_keys_list()` | — |
| `POST` | `/api/settings/api-keys` | `api_keys_create()` | — |
| `DELETE` | `/api/settings/api-keys/{key_id}` | `api_keys_delete()` | — |

## `adapters/admin-api/runtime_hardware_routes.py`
_Prefix:_ `/api/runtime-hardware`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/runtime-hardware/capabilities` | `runtime_hardware_capabilities()` | — |
| `GET` | `/api/runtime-hardware/connectors` | `runtime_hardware_connectors()` | — |
| `GET` | `/api/runtime-hardware/health` | `runtime_hardware_health()` | — |
| `POST` | `/api/runtime-hardware/plan` | `runtime_hardware_plan()` | — |
| `GET` | `/api/runtime-hardware/resources` | `runtime_hardware_resources()` | — |
| `GET` | `/api/runtime-hardware/targets/{target_type}/{target_id}/state` | `runtime_hardware_target_state()` | — |
| `POST` | `/api/runtime-hardware/validate` | `runtime_hardware_validate()` | — |

## `adapters/admin-api/runtime_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/runtime/autonomy-status` | `get_autonomy_status()` | Runtime readiness snapshot for autonomous planning. |
| `GET` | `/api/runtime/compute/instances` | `get_compute_instances()` | List managed Ollama compute instances + health + capability. |
| `POST` | `/api/runtime/compute/instances/{instance_id}/start` | `start_compute_instance()` | Start instance from strict template whitelist. |
| `POST` | `/api/runtime/compute/instances/{instance_id}/stop` | `stop_compute_instance()` | Stop managed instance. Idempotent if already stopped/missing. |
| `GET` | `/api/runtime/compute/routing` | `get_compute_routing()` | Return persisted layer routing + effective target resolution snapshot. |
| `POST` | `/api/runtime/compute/routing` | `post_compute_routing()` | Persist layer routing (thinking/control/output/tool_selector/embedding). |
| `GET` | `/api/runtime/digest-state` | `get_digest_state()` | Digest pipeline runtime telemetry. |
| `GET` | `/api/runtime/session` | `get_runtime_session()` | Session telemetry for UI dashboards. |

## `adapters/admin-api/secrets_routes.py`
_Prefix:_ `/api/secrets`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/secrets` | `list_secrets()` | List all secret names — values are never returned. |
| `POST` | `/api/secrets` | `create_secret()` | Store a new encrypted secret. |
| `GET` | `/api/secrets/resolve/{name}` | `resolve_secret()` | Internal: resolve a secret value for skill sandbox use. |
| `DELETE` | `/api/secrets/{name}` | `delete_secret()` | Delete a secret. |
| `PUT` | `/api/secrets/{name}` | `update_secret()` | Update an existing secret. |

## `adapters/admin-api/settings_routes.py`
_Prefix:_ `/api/settings`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/settings/` | `get_settings()` | Get all current setting overrides. |
| `POST` | `/api/settings/` | `update_settings()` | Update settings. |
| `GET` | `/api/settings/autonomy/cron-policy` | `get_autonomy_cron_policy()` | Return effective cron guardrail policy values with source tracking. |
| `POST` | `/api/settings/autonomy/cron-policy` | `update_autonomy_cron_policy()` | Persist cron guardrail policy overrides. |
| `GET` | `/api/settings/compression` | `get_compression_settings()` | Get context compression settings. |
| `POST` | `/api/settings/compression` | `update_compression_settings()` | Update context compression settings. |
| `GET` | `/api/settings/embeddings/runtime` | `get_embedding_runtime()` | Return effective embedding runtime settings with source tracking. |
| `POST` | `/api/settings/embeddings/runtime` | `update_embedding_runtime()` | Typed, validated embedding runtime settings update. |
| `GET` | `/api/settings/master` | `get_master_settings()` | Get current Master Orchestrator settings |
| `POST` | `/api/settings/master` | `update_master_settings()` | Update Master Orchestrator settings |
| `GET` | `/api/settings/models` | `get_model_overrides()` | Return only persisted model setting overrides (no defaults, no env). |
| `POST` | `/api/settings/models` | `update_model_settings()` | Typed, validated model settings update. |
| `GET` | `/api/settings/models/effective` | `get_model_settings_effective()` | Return effective model settings with source tracking. |
| `GET` | `/api/settings/reference-links` | `get_reference_links()` | — |
| `POST` | `/api/settings/reference-links` | `update_reference_links()` | — |
| `GET` | `/api/settings/sequential/runtime` | `get_sequential_runtime_policy()` | Return effective sequential/planning runtime policy values with source tracking. |
| `POST` | `/api/settings/sequential/runtime` | `update_sequential_runtime_policy()` | Persist sequential/planning runtime policy overrides. |

## `adapters/admin-api/storage_broker_routes.py`
_Prefix:_ `/api/storage-broker`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/storage-broker/audit` | `get_audit()` | Proxy: storage audit log from storage-broker MCP. |
| `GET` | `/api/storage-broker/disks` | `get_disks()` | Proxy: list all disks from storage-broker MCP. |
| `POST` | `/api/storage-broker/disks/{disk_id}/policy` | `set_disk_policy_route()` | Update zone and/or policy_state for a single disk/partition. |
| `POST` | `/api/storage-broker/format` | `format_device_route()` | Proxy: preview/apply device format action (destructive). |
| `GET` | `/api/storage-broker/health` | `broker_health()` | Check if storage-broker is reachable via MCP initialize handshake. |
| `GET` | `/api/storage-broker/managed-paths` | `get_managed_paths()` | Proxy: list managed paths from storage-broker MCP. |
| `POST` | `/api/storage-broker/mount` | `mount_device_route()` | Proxy: preview/apply device mount action. |
| `POST` | `/api/storage-broker/partition` | `partition_disk_route()` | Proxy: preview/apply partition table creation (destructive). |
| `POST` | `/api/storage-broker/provision/service-dir` | `provision_service_dir_route()` | Proxy: preview/apply managed service directory provisioning. |
| `GET` | `/api/storage-broker/settings` | `get_settings()` | Return current storage broker policy settings. |
| `POST` | `/api/storage-broker/settings` | `update_settings()` | Update storage broker policy settings. |
| `GET` | `/api/storage-broker/summary` | `get_summary()` | Proxy: storage summary from storage-broker MCP. |
| `POST` | `/api/storage-broker/unmount` | `unmount_device_route()` | Proxy: preview/apply device unmount action. |
| `POST` | `/api/storage-broker/validate-path` | `validate_path_route()` | Proxy: validate one path against storage policy. |

## `adapters/admin-api/tasks_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `POST` | `/api/tasks/{task_id}/approve` | `approve_task()` | — |
| `POST` | `/api/tasks/{task_id}/cancel` | `cancel_task()` | — |

## `adapters/admin-api/tools_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/tools` | `tools()` | — |
| `GET` | `/api/tools/available` | `tools_available()` | Policy-enriched live list of all MCP tools currently reachable via the hub. |

## `adapters/admin-api/trion_memory_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/recall` | `api_trion_memory_recall()` | — |
| `GET` | `/recent` | `api_trion_memory_recent()` | — |
| `POST` | `/remember` | `api_trion_memory_remember()` | — |
| `GET` | `/status` | `api_trion_memory_status()` | — |

## `adapters/admin-api/vault_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/entries` | `list_entries()` | Return all entries (passwords never included). |
| `POST` | `/entries` | `create_entry()` | — |
| `DELETE` | `/entries/{entry_id}` | `delete_entry()` | — |
| `PUT` | `/entries/{entry_id}` | `update_entry()` | — |
| `GET` | `/entries/{entry_id}/password` | `get_password()` | Return decrypted password for a single entry. |
| `POST` | `/lock` | `lock()` | — |
| `POST` | `/setup` | `setup_vault()` | First-time setup: set master password and create setup marker. |
| `GET` | `/status` | `vault_status()` | Check if vault DB exists, whether master password is set, and entry count. |
| `POST` | `/unlock` | `unlock()` | Validate master password and return a session token. |

## `adapters/admin-api/workspace_routes.py`

| Methode | Pfad | Handler | Beschreibung |
|---------|------|---------|--------------|
| `GET` | `/api/workspace` | `workspace_list()` | — |
| `GET` | `/api/workspace-events` | `workspace_events_list()` | — |
| `DELETE` | `/api/workspace/{entry_id}` | `workspace_delete()` | — |
| `GET` | `/api/workspace/{entry_id}` | `workspace_get()` | — |
| `PUT` | `/api/workspace/{entry_id}` | `workspace_update()` | — |

---

**Gesamt:** 194 Endpunkte.
