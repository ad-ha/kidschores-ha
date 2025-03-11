# KidsChores Home Assistant Integration - AI Developer Guide

## 📚 Critical Documentation (Read as Needed)

- **Architecture**: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) (Storage-only model, data separation, translation architecture)
- **Quality Standards**: [docs/CODE_REVIEW_GUIDE.md](../docs/CODE_REVIEW_GUIDE.md) (Audit framework, logging, constants)
- **Testing**: [tests/TESTING_AGENT_INSTRUCTIONS.md](../tests/TESTING_AGENT_INSTRUCTIONS.md) (Patterns, execution)

## 🛑 Mandatory Definition of Done

**Work is NOT complete until BOTH commands pass:**

1. **Linting**: `./utils/quick_lint.sh --fix` (Zero tolerance for errors)
2. **Testing**: `python -m pytest tests/ -v --tb=line` (All tests must pass)

## 🏗️ Architectural Non-Negotiables

1. **Storage-Only (v4.2+)**: All entity data lives in `.storage/kidschores_data`. Config entry contains **only** system settings (9 settings: points*label, points_icon, update_interval, calendar_show_period, 4x retention*\*, points_adjust_values).
2. **Identity**: ALWAYS use `internal_id` (UUID) for logic/lookups. NEVER use entity names.
3. **Datetime**: Store ONLY UTC-aware ISO strings. Use `kc_helpers.parse_datetime_to_utc()`.
4. **Helpers**:
   - `kc_helpers.py`: Shared logic, entity lookups, authorization, coordinator retrieval
   - `flow_helpers.py`: Config/Options flow schemas, validation (TWO patterns: simple entities return errors dict, complex entities return (errors, data) tuple)

## 💎 Code Quality Standards (Enforced)

- **Constants**: NO hardcoded strings. Use `const.py` patterns (`DATA_*`, `CONF_*`, `TRANS_KEY_*`, `LABEL_*`).
- **Translations**:
  - **Integration**: Use `translations/en.json` keys for exceptions/config flow (master file, no strings.json)
  - **Dashboard**: Custom system via `translations_dashboard/{language_code}_dashboard.json` (e.g., `en_dashboard.json`) — OUT OF SCOPE for standard HA translations
  - **Notifications**: Use `TRANS_KEY_NOTIF_TITLE_*` / `TRANS_KEY_NOTIF_MESSAGE_*` with `async_get_translations()` wrapper
- **Logging**: Lazy logging ONLY: `const.LOGGER.debug("Val: %s", var)`. NO f-strings in logs. Use `const.LOGGER` not module-level logger.
- **Typing**: 100% type hints required (args + return).
- **Refactoring Patterns**: When editing flow_helpers.py, respect TWO validation patterns:
  - **Simple entities** (kids, parents, rewards, bonuses, penalties): `validate_*_inputs()` returns errors dict
  - **Complex entities** (chores, achievements, challenges): `validate_*_inputs()` returns `(errors, data)` tuple

## 🧪 Testing Strategy

- **Mocking**: Always mock notifications: `patch.object(coordinator, "_notify_kid", new=AsyncMock())`.
- **Suppressions**: Use module-level pylint suppressions for test files (e.g., `protected-access`).
- **Data Loading**: Use helpers from `conftest.py`:
  - `construct_entity_id(type, name, suffix)` - Build entity IDs
  - `get_kid_by_name(data, name)` / `get_chore_by_name(data, name)` - Access by name not index
  - `create_test_datetime(days_offset)` - UTC datetime creation
  - `assert_entity_state(hass, entity_id, state, attrs)` - State verification
- **Scenarios**: Use pytest fixtures (`scenario_minimal`, `scenario_medium`, `scenario_full`, `scenario_stress`) for consistent test data. All fixtures use testdata*scenario*\*.yaml files and automatically load/reload entities.
- **Test Types**:
  - **UI**: `test_config_flow.py`, `test_options_flow*.py` (options flow navigation)
  - **Business Logic**: `test_coordinator.py`, `test_services.py` (direct coordinator access)
  - **Workflow**: `test_workflow_*.py` (reload + state verification)

## 🔍 Code Audit Framework (Required Before Review)

When auditing new files, use [Phase 0 framework](../docs/CODE_REVIEW_GUIDE.md):

1. **Logging**: Count `const.LOGGER.*` calls, verify lazy logging (no f-strings)
2. **User-facing strings**: Identify error messages, field labels, notifications (check for hardcoded strings)
3. **Data constants**: Find repeated string literals, dict keys, magic numbers
4. **Pattern analysis**: Verify constant naming follows `CFOP_ERROR_*` → `TRANS_KEY_CFOF_*` pattern
5. **Translation keys**: Cross-reference all `TRANS_KEY_*` constants against `en.json`

## 🚀 Common Workflows

```bash
# Quick lint (after every change)
./utils/quick_lint.sh --fix

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_coordinator.py -v

# Stop on first failure
python -m pytest tests/ -x

# Platform reload in tests (after direct coordinator changes)
await reload_entity_platforms(hass, config_entry)
```

## 📁 Key File Locations

- **Constants**: `custom_components/kidschores/const.py` (2565 lines - all constants here)
- **Coordinator**: `custom_components/kidschores/coordinator.py` (8987 lines - core business logic)
- **Helpers**: `kc_helpers.py` (shared utils), `flow_helpers.py` (validation/schemas)
- **Storage**: `storage_manager.py` (handles `.storage/kidschores_data` persistence)
- **Translations**: `translations/en.json` (master file for all user-facing text)
- **Test Data**: `tests/testdata_scenario_*.yaml` files loaded via `scenario_*` fixtures (minimal, medium, full, performance_stress)
