# Testing Agent Instructions - KidsChores Integration

**Quick-start guide for AI agents.** For comprehensive details, see **[TESTING_GUIDE.md](TESTING_GUIDE.md)**.

> **Terminal Requirement**: Run every command (tests, lint, helpers) inside an actual terminal/console session so output is captured and visible; never "simulate" command execution.

---

## Quick Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific file
python -m pytest tests/test_workflow_parent_actions.py -v

# Stop on first failure
python -m pytest tests/ -x
```

---

## Test Creation Workflow

### 1. Identify Test Type → See [TESTING_GUIDE.md § Test Categories](TESTING_GUIDE.md#test-categories)

| Test Type      | File Pattern              | Data Loading       | Full Details                                               |
| -------------- | ------------------------- | ------------------ | ---------------------------------------------------------- |
| UI Workflow    | `test_config_flow.py`     | Options flow       | [Config Flow Tests](TESTING_GUIDE.md#1-config-flow-tests) |
| Options Flow   | `test_options_flow*.py`   | Options flow       | [Options Flow Tests](TESTING_GUIDE.md#2-options-flow-tests) |
| Business Logic | `test_coordinator.py`     | Direct coordinator | [Coordinator Tests](TESTING_GUIDE.md#3-coordinator-tests) |
| Services       | `test_services.py`        | Direct coordinator | [Service Tests](TESTING_GUIDE.md#4-service-tests)         |
| User Workflow  | `test_workflow_*.py`      | Direct + reload    | [Workflow Tests](TESTING_GUIDE.md#5-workflow-tests-kid-chores) |
| Dashboard      | `test_dashboard_templates.py` | Mock states     | [Dashboard Tests](TESTING_GUIDE.md#dashboard-template-testing) |

### 2. Use Helper Functions (conftest.py)

**Entity ID Construction:**
```python
entity_id = construct_entity_id("sensor", "Alex", "points")
# Returns: "sensor.kc_alex_points"
```

**Entity State Verification:**
```python
await assert_entity_state(hass, entity_id, "100", {"icon": "mdi:star"})
# Asserts state and optional attributes
```

**Data Access by Name (not index):**
```python
kid = get_kid_by_name(coordinator.data, "Zoë")
chore = get_chore_by_name(coordinator.data, "Clean Room")
reward = get_reward_by_name(coordinator.data, "Ice Cream")
```

**Datetime Creation:**
```python
overdue_date = create_test_datetime(days_offset=-7)  # 7 days ago
future_date = create_test_datetime(days_offset=7)    # 7 days from now
```

**See [TESTING_GUIDE.md § Test Fixtures](TESTING_GUIDE.md#test-fixtures) for complete helper reference.**

### 3. Load Test Data → See [TESTING_GUIDE.md § Data Loading Methods](TESTING_GUIDE.md#data-loading-methods)

**Options Flow** (UI simulation):
```python
result = await hass.config_entries.options.async_init(config_entry.entry_id)
# Navigate through flow steps...
```

**Direct Loading** (business logic):
```python
config_entry, name_to_id_map = scenario_minimal
coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
kid_id = name_to_id_map["kid:Zoë"]
```

**See [TESTING_GUIDE.md § Data Loading Methods](TESTING_GUIDE.md#data-loading-methods) for detailed comparison.**

---

## Essential Patterns

For detailed explanations, see **[TESTING_GUIDE.md § Testing Patterns](TESTING_GUIDE.md#testing-patterns)**.

1. **Platform Reload**: `await reload_entity_platforms(hass, config_entry)`
2. **Direct Entity Access**: Use helper `get_entity_by_id()` or search `hass.data.get("entity_components", {}).get("button", {}).entities`
3. **Mock Notifications**: `with patch.object(coordinator, "_notify_kid", new=AsyncMock())`
4. **Set User Context**: `button_entity._context = Context(user_id=mock_hass_users["parent1"].id)`
5. **Test Real Structures**: `penalty_applies`, `bonus_applies`, `point_stats`, `badges_earned`

---

## Test Data Scenarios

See **[TESTING_GUIDE.md § Test Fixtures](TESTING_GUIDE.md#test-fixtures)** for complete details.

| Fixture | Kids | Chores | Badges | Bonuses | Penalties | Rewards | Use Case |
|---------|------|--------|--------|---------|-----------|---------|----------|
| `scenario_minimal` | 1 (Zoë) | 2 | 1 | 1 | 1 | 1 | Single-kid workflows |
| `scenario_medium` | 2 | 4 (shared) | 2 | 2 | 2 | 2 | Multi-kid coordination |
| `scenario_full` | 3 | 7 (mixed) | 5 | 2 | 3 | 5 | Badge maintenance, complex |

**Quick Access:**
```python
async def test_example(hass, scenario_minimal, mock_hass_users):
    config_entry, name_to_id_map = scenario_minimal
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Clean room!"]
```

---

## Troubleshooting (3-Attempt Rule)

**If issue persists after 3 attempts, consult [TESTING_GUIDE.md](TESTING_GUIDE.md):**

- **[§ Debugging](TESTING_GUIDE.md#debugging)** - Full troubleshooting guide
- **[§ Lessons Learned](TESTING_GUIDE.md#lessons-learned)** - Common pitfalls and solutions
- **[§ Testing Patterns](TESTING_GUIDE.md#testing-patterns)** - Detailed code patterns
- **[§ Data Loading Methods](TESTING_GUIDE.md#data-loading-methods)** - When to use each approach
- **[§ Dashboard Template Testing](TESTING_GUIDE.md#dashboard-template-testing)** - Jinja2 validation patterns

---

## Code Quality Requirements

### During Development (Optional - Quick Iteration)

```bash
# Run specific test file while working
python -m pytest tests/test_coordinator.py -v

# Lint single file
python utils/lint_check.py --integration custom_components/kidschores/sensor.py

# Quick syntax check
python -m py_compile custom_components/kidschores/sensor.py
```

### Before Completion - MANDATORY REQUIREMENTS ✅

**Work is NOT complete until BOTH commands pass:**

```bash
# 1. FULL LINT CHECK (~22 seconds - BATCHED for speed)
./utils/quick_lint.sh --fix

# This verifies:
# ✅ Pylint errors (critical severity 4+) across ALL files
# ✅ Trailing whitespace (auto-fixes)
# ✅ Line length compliance
# ✅ No import errors or syntax issues
# Type checking DISABLED by default for speed

# 2. FULL TEST SUITE (~7 seconds - 150 tests)
python -m pytest tests/ -v --tb=line

# This verifies:
# ✅ All 150 tests pass (allows intentional skips)
# ✅ No regressions introduced
# ✅ Integration behavior correct end-to-end
```

**NEVER declare work complete without running both commands above.**

### Optional: Full Type Checking (slower, ~1-2 minutes)

```bash
python utils/lint_check.py --types

# For detailed checks on specific files:
python utils/lint_check.py --file path/to/file.py
```

**See [utils/README_LINTING.md](../utils/README_LINTING.md) for complete linting guide.**

### Severity 4 Errors/Warnings - MUST FIX OR SUPPRESS

- ❌ **W0612**: Unused variables → Remove or use underscore `_`
- ❌ **W0613**: Unused arguments → Add `# pylint: disable=unused-argument`
- ❌ **W0611/F401**: Unused imports → Remove them
- ❌ **W0404**: Reimports → Don't import same module twice
- ❌ **W0621**: Redefined names → Suppress for pytest fixtures (module-level)
- ❌ **W0212**: Protected access → Suppress at module level for test files
- ❌ **F841**: Unused local variables → Remove them
- ❌ **F541**: F-strings without placeholders → Convert to regular strings

### Module-Level Suppressions (Critical Pattern)

**ALWAYS use module-level suppressions** for warnings appearing 3+ times in a file:

```python
"""Test module docstring."""

# pylint: disable=protected-access  # Accessing _context/_persist for testing
# pylint: disable=redefined-outer-name  # Pytest fixtures redefine names
# pylint: disable=unused-argument  # Fixtures needed for test setup

from unittest.mock import AsyncMock
```

**Place immediately after docstring, before imports**

### Acceptable Warnings (Severity 2)

- ✅ **C0301**: Line too long (acceptable for readability)
- ✅ **C0415**: Import outside toplevel (acceptable in fixtures)
- ✅ **C0302**: Too many lines (acceptable for conftest.py)
- ✅ **R0914/R0912/R0915**: Too many locals/branches/statements (acceptable in complex tests)

### Test File Checklist

- ✅ Type hints on all test functions
- ✅ Docstrings explain what test validates
- ✅ No debug code (print, pdb, f-strings without interpolation)
- ✅ Descriptive test names: `test_<feature>_<action>_<expected>`
- ✅ Module-level suppressions for repeated patterns
- ✅ Zero severity 4+ warnings (`pylint tests/*.py 2>&1 | grep -E "^[WE][0-9]{4}:" | wc -l` returns 0)

---

**Last Updated**: December 20, 2024
