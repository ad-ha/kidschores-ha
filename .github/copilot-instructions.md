# KidsChores Home Assistant Integration - AI Coding Instructions

**Core Pattern**: All entities use `internal_id` (UUID) as primary key. Names are changeable; IDs persist across renames.

## Tech Stack

- **Python 3.12+**, PEP 8, Black formatting, mandatory type hints
- **Async I/O**: All I/O must be async; use `hass.async_add_executor_job` only for blocking third-party calls
- **Imports**: Relative (e.g., `from . import const`)
- **Logging**: `const.LOGGER` with `DEBUG:`, `INFO:`, `WARNING:`, `ERROR:` prefixes
- **Shared code**: Add common functions to `kc_helpers.py` or `flow_helpers.py`, not elsewhere

## Architecture Overview

**Storage → Coordinator → Entities**

- **Storage** (`storage_manager.py`): JSON persistence, keyed by `internal_id`
- **Coordinator** (`coordinator.py`): 8000+ lines handling chore lifecycle, badge calculations, notifications, recurring schedules
- **Entities**: `sensor.py` (20+ types), `button.py` (actions), `calendar.py`, `select.py`
- **Config**: `const.py` (2200+ lines) centralizes `DATA_*`, `CONF_*`, `SERVICE_*`, `TRANS_KEY_*` constants

## Critical Patterns

**Entity Identification**: Always use `internal_id`, never names for lookups (names change on renames).

**DateTime**: Store as UTC-aware ISO strings via `kc_helpers.parse_datetime_to_utc()`. Migration logic in `coordinator._migrate_stored_datetimes()`.

**Recurring Chores**: Coordinator resets on midnight via `async_track_time_change` using daily/weekly/monthly intervals.

**Notifications**: Action strings embed `kid_id` and `chore_id` (e.g., `"approve_chore_<kid_id>_<chore_id>"`). Handlers in `notification_action_handler.py` route to coordinator.

**Access Control**: `is_user_authorized_for_kid(hass, user_id, kid_id)` and `is_user_authorized_for_global_action()` in `kc_helpers.py`. Admins always allowed; non-admins checked against parents/kids lists.

**Badges**: Tracked by type (`achievement`, `challenge`, `cumulative`, `daily`, `periodic`, `special`), with progress in kid's `badges_earned` list (includes `internal_id`, `last_awarded_date`, multiplier).

## Configuration & Services

**Config Flow** (`config_flow.py`, 1300+ lines): Multi-step UI setup. **Options Flow** (`options_flow.py`): Manage existing entities. Must sync with storage via `coordinator._merge_and_update_entities()`.

**Services** (18 total in `services.yaml`): Receive entity names → resolve to `internal_id` → call coordinator. Lifecycle: `claim_chore`, `approve_chore`, `disapprove_chore`. Rewards: `redeem_reward`, `approve_reward`, `disapprove_reward`. Points: `adjust_points`, `apply_bonus`, `apply_penalty`. Resets: `reset_all_chores`, `reset_penalties`, etc.

## Helper Utilities

**`kc_helpers.py`** (1400+): Entity lookups, datetime parsing, authorization checks, dashboard translation loading.

**`flow_helpers.py`** (2000+): Schema builders (`build_kid_schema`, `build_chore_schema`, etc.) with Voluptuous & selectors. Input validation for config/options flows.

Add shared functions to these files, not elsewhere.

## Development

**Validation**: HACS & Hassfest via GitHub Actions. Local: `pylint custom_components/kidschores/sensor.py`

**Testing**: No automated suite. Manual: Install, restart HA, add integration via UI, test entity creation/services/notifications.

**Key Files**: `coordinator.py` (business logic), `const.py` (all constants), `storage_manager.py` (persistence), `services.py` (service schemas → coordinator calls), entity platforms (`sensor.py`, `button.py`, `calendar.py`, `select.py`).

## Common Pitfalls

1. Don't use entity names as keys; use `internal_id`
2. Store datetimes as UTC-aware ISO strings via `kc_helpers.parse_datetime_to_utc()`
3. Don't cache entity data outside coordinator; coordinator is single source of truth
4. Never hardcode user-facing strings; use `const.TRANS_KEY_*`
5. Services receive names; resolve to `internal_id` before coordinator calls
6. Notification action strings must embed both `kid_id` and `chore_id`/`reward_id`

## Adding/Modifying Features

- **New entity**: Update `config_flow.py`, `options_flow.py`, coordinator merge logic, entity platform
- **New service**: Schema in `services.py`, add to `services.yaml`, implement in coordinator
- **Data structure change**: Update storage version in `const.py`, add migration in coordinator
- **New constant**: Add to `const.py` with proper prefix; update translations if user-facing

## Entity Design

Inherit from `CoordinatorEntity` for automatic coordinator updates. Set `unique_id` (stable via `internal_id`), `device_info` (for device registry), and override `_handle_coordinator_update()` for data processing.

**Coordinator error handling**: Wrap I/O in try/except, log with `const.LOGGER.error()`, return last known data on transient failures. Use `UpdateFailed` only for persistent errors.

**Dashboard**: Use modern template sensors, standard Lovelace cards (Entities, Tile, Button), or `mushroom-cards`. Reload translations via `_async_reload_translations()`.

## Debugging

- Debug logging: `logger: custom_components.kidschores: debug` in `configuration.yaml`
- Storage: `.storage/kidschores_data` (JSON with `internal_id` keys)
- Entity registry: `.storage/core.entity_registry`
- Services: Developer Tools → Services to test
- Coordinator: Check `last_update_success` property
