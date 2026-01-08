# KidsChores Code Review Guide

**Purpose**: Systematic code review checklist for maintaining quality, consistency, and performance across the KidsChores integration.

**Version**: 1.1
**Last Updated**: January 4, 2026
**Target**: KidsChores v0.5.0+ (Storage-Only Architecture)

---

## Table of Contents

1. [Phase 0: Repeatable Audit Framework](#phase-0-repeatable-audit-framework) ⭐ **REQUIRED FIRST STEP**
2. [General Code Quality](#general-code-quality)
3. [Entity Review Checklist](#entity-review-checklist)
4. [Performance Review](#performance-review)
5. [Standards Compliance](#standards-compliance)
6. [Platform-Specific Reviews](#platform-specific-reviews)
7. [Review Process](#review-process)

---

## Phase 0: Repeatable Audit Framework

**CRITICAL**: All new files must be audited using this framework BEFORE code review. This ensures consistent identification of user-facing strings, data constants, logging patterns, and translation requirements.

**When to use**: Auditing any new Python file for integration into the KidsChores codebase (entity platforms, helper modules, coordinator changes, etc.)

**Output**: Standardized audit report (JSON format) documenting findings and required constants.

### Step 1: Logging Audit

```bash
# Search for all logging statements in file
grep -n "const\.LOGGER\.\(debug\|info\|warning\|error\)" file.py
```

**Checklist**:

- [ ] Search for all `const.LOGGER.*` calls in file
- [ ] Verify each uses lazy logging (not f-strings): `logger.debug("Message: %s", var)` ✓
- [ ] Count by severity: DEBUG, INFO, WARNING, ERROR
- [ ] Document any hardcoded strings in log messages
- [ ] Verify no f-strings in lazy logging (should use `%s`, `%d` placeholders)

**Documentation**:

- Total log statements: **N**
- Debug: **X**, Info: **Y**, Warning: **Z**, Error: **W**
- Compliance: **100%** (or list issues found)
- Example: "22 log statements reviewed; 100% compliant; all use correct lazy logging patterns"

### Step 2: User-Facing String Identification

**Checklist**:

- [ ] Identify all user-facing validation error messages (config flow, options flow)
- [ ] Identify all field labels and descriptions (schema builders)
- [ ] Identify all entity names, descriptions used in UI
- [ ] Identify all error messages returned to user
- [ ] **Identify all notification titles and messages** (coordinator notification calls) ⭐ NEW
- [ ] Search for hardcoded strings in error dicts: `errors['field'] = 'hardcoded_string'`
- [ ] Search for strings in field builders: `vol.Optional("name", description="...")`
- [ ] **Search for hardcoded notification strings**: `title="..."`, `message=...` ⭐ NEW

**Search patterns**:

```python
errors["field"] = "hardcoded"  # ❌ Identify these
vol.Optional("field", description="Hardcoded text")  # ❌ Identify these
return vol.Schema({...})  # Check for embedded strings
```

**Notification-specific patterns** ⭐ NEW:

```bash
# Find hardcoded notification titles
grep -n 'title="[A-Z]' file.py

# Find hardcoded notification messages (often with f-strings)
grep -n 'message=.*f"' file.py

# Find notification function calls
grep -n '_notify_kid\|_notify_parents\|async_send_notification' file.py
```

**Documentation**:

- Total user-facing strings found: **N**
- Error messages: **X**
- Field labels: **Y**
- Descriptions: **Z**
- **Notification titles/messages**: **W** ⭐ NEW
- Other UI text: **V**
- Hardcoded (non-constant) strings: **List with line numbers**

### Step 3: Data/Lookup Constant Identification

**Checklist**:

- [ ] Search for repeated string literals (use `grep` with frequency count)
- [ ] Identify dictionary keys used 2+ times: `dict['key']`, `dict.get('key')`
- [ ] Identify enum-like strings: status values, type names, tag names
- [ ] Identify format strings: date formats, filename patterns, templates
- [ ] Identify magic numbers and delimiters: hardcoded lengths, delimiters

**Search patterns**:

```bash
# Find most-repeated string literals (potential constants)
grep -oE "'[^']+'|\"[^\"]+\"" file.py | sort | uniq -c | sort -rn | head -20

# Find dictionary access patterns
grep -E "\[.?['\"][^'\"]+['\"]" file.py

# Find hardcoded delimiters or formats
grep -E "(split|join|format|strftime)" file.py
```

**Documentation**:

- Total data constants needed: **N**
- Dictionary keys: **X** items
- Entity type/enum values: **Y** items
- Format strings: **Z** items
- Magic strings: **W** items
- **Breakdown by priority**:
  - HIGH (>5 occurrences): **X** items
  - MEDIUM (2-4 occurrences): **Y** items
  - LOW (1 occurrence): **Z** items

### Step 4: Pattern Analysis

**Checklist**:

- [ ] Verify error messages follow `CFOP_ERROR_*` → `TRANS_KEY_CFOF_*` pattern
- [ ] Verify field labels use appropriate `CFOF_*` or `LABEL_*` constants
- [ ] Verify data structure access is consistent (dict keys vs. const references)
- [ ] Verify logging compliance (no f-strings, lazy evaluation)
- [ ] Search for `const.` usage to understand naming patterns in file

**Documentation**:

- Pattern compliance: **X%** (Y errors, Z warnings)
- Naming patterns identified: (e.g., "BACKUP*KEY*_", "ENTITY*KEY*_", etc.)
- Issues found: (list any inconsistencies)

### Step 5: Translation Key Verification

**Checklist**:

- [ ] Extract all unique `TRANS_KEY_*` and `CFOP_ERROR_*` constants found in file
- [ ] Cross-reference against `en.json` → verify English translations exist
- [ ] Identify missing translation keys (constants defined but no en.json entry)
- [ ] Document gaps for Phase 4 remediation
- [ ] Note: No strings.json required (KidsChores uses en.json as master, storage-only architecture)

**Search patterns**:

```bash
# Find all TRANS_KEY_ and CFOP_ERROR_ references
grep -n "TRANS_KEY_\|CFOP_ERROR_" file.py

# Verify in en.json (master file)
grep -c "TRANS_KEY_\|CFOP_ERROR_" custom_components/kidschores/translations/en.json
```

**Documentation**:

- Translation keys found: **N**
- In en.json: **Y** ✓
- Missing translations: **List with keys**
- Translation coverage: **X%** (en.json is master, 100% expected)

### Step 5b: Translation Rationalization (Conditional)

**When to perform**: If Step 5 identified new translation keys OR new user-facing strings without existing translation templates.

**Checklist**:

- [ ] Review extracted user-facing strings from Step 2
- [ ] For each string without a translation template, check if similar patterns exist in en.json
- [ ] Document existing translation templates that could be reused
- [ ] If pattern doesn't exist, draft new translation template following KidsChores naming conventions
- [ ] Flag ambiguous strings for confirmation with domain expert

**Search for existing patterns**:

```bash
# Check for similar translation patterns
grep -i "error\|invalid\|required\|duplicate" custom_components/kidschores/translations/en.json | head -20

# Look for UI text patterns
grep -i "button\|confirm\|cancel\|success" custom_components/kidschores/translations/en.json | head -20
```

**Documentation**:

- Strings requiring new translations: **X**
- Reusable existing templates found: **Y** (list patterns)
- New translation templates drafted: **Z**
- Ambiguous items flagged for review: **List with rationale**

### Step 6: Audit Documentation

**Generate standardized audit report** (JSON format):

```json
{
  "file": "custom_components/kidschores/flow_helpers.py",
  "audit_date": "2025-12-19",
  "loc_total": 3316,
  "sections": {
    "logging": {
      "total_statements": 22,
      "debug": 17,
      "info": 2,
      "warning": 3,
      "error": 0,
      "compliance_percent": 100,
      "issues": []
    },
    "user_facing_strings": {
      "total": 62,
      "error_messages": 32,
      "field_labels": 15,
      "descriptions": 8,
      "other": 7,
      "hardcoded": 6,
      "compliance_percent": 90
    },
    "data_constants": {
      "total": 47,
      "dict_keys": 12,
      "entity_keys": 9,
      "enum_values": 15,
      "format_strings": 9,
      "magic_strings": 3,
      "high_priority": 21,
      "medium_priority": 21,
      "low_priority": 5
    },
    "translation_keys": {
      "found": 28,
      "in_en_json": 28,
      "missing_en_json": 0,
      "coverage_percent": 100
    }
  },
  "summary": "109 total hardcoded strings; 90% user-facing compliance; 53+ constants needed",
  "constants_needed": [
    {
      "string": "tag",
      "occurrences": 9,
      "suggested_constant": "BACKUP_KEY_TAG = 'tag'",
      "priority": "HIGH"
    }
  ],
  "next_phase": "Constant definition and code remediation"
}
```

**Documentation checklist**:

- [ ] All file sections read (line ranges documented)
- [ ] Logging audit completed and verified
- [ ] User-facing strings 100% identified
- [ ] Data constants categorized by priority
- [ ] Translation keys cross-referenced with en.json (master file)
- [ ] Audit report generated (JSON format)
- [ ] Estimated LOC changes calculated
- [ ] Summary statement written

### Audit Completion Checklist

**Before proceeding to code review**, verify:

- [ ] All 6 steps completed for the file
- [ ] Audit report generated and reviewed
- [ ] No identified user-facing strings missing constants
- [ ] All data constants categorized by priority
- [ ] Translation gaps documented
- [ ] **Notification strings audited** (if file contains notification code) ⭐ NEW
- [ ] Estimated constants needed: **N** new constants
- [ ] Estimated code locations to update: **M** locations
- [ ] File is ready for Phase 2+ remediation OR full code review

---

### Step 6b: Notification-Specific Audit (Conditional) ⭐ NEW

**When to perform**: If Step 2 identified notification-related code (calls to `_notify_kid`, `_notify_parents`, or `async_send_notification`).

**Why this is needed**: Phase 3/3b focused on exception messages. Notification strings use a different pattern (direct function parameters) and require separate auditing to ensure complete standardization.

**Checklist**:

- [ ] Locate all notification function calls in file
- [ ] For each notification call, identify:
  - [ ] `title=` parameter value (hardcoded string or constant?)
  - [ ] `message=` parameter value (hardcoded string/f-string or constant?)
  - [ ] Any embedded entity names or dynamic data (should use message_data dict)
- [ ] Document required TRANS*KEY_NOTIF_TITLE*\* constants
- [ ] Document required TRANS*KEY_NOTIF_MESSAGE*\* constants
- [ ] Flag f-strings in notification messages (should use placeholder substitution)

**Search patterns**:

```bash
# Find all notification calls
grep -n '_notify_kid\|_notify_parents\|async_send_notification' file.py

# For each call found, extract title/message
grep -A 5 '_notify_kid(' file.py | grep 'title=\|message='

# Find hardcoded notification titles
grep -n 'title="[A-Z]' file.py

# Find f-string notification messages (need conversion)
grep -n 'message=.*f"' file.py
```

**Documentation**:

```json
{
  "notification_audit": {
    "notification_calls_found": 15,
    "hardcoded_titles": 15,
    "hardcoded_messages": 15,
    "f_strings_in_messages": 15,
    "required_title_constants": [
      "TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED",
      "TRANS_KEY_NOTIF_TITLE_CHORE_DISAPPROVED",
      ...
    ],
    "required_message_constants": [
      "TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED",
      "TRANS_KEY_NOTIF_MESSAGE_CHORE_DISAPPROVED",
      ...
    ],
    "estimated_effort": "4-6 hours for full notification refactor"
  }
}
```

**Example Finding**:

```python
# ❌ FOUND (Line 3257):
self.hass.async_create_task(
    self._notify_kid(
        kid_id,
        title="KidsChores: Chore Approved",  # ❌ Hardcoded
        message=f"Your chore '{chore_info[const.DATA_CHORE_NAME]}' was approved.",  # ❌ f-string
    )
)

# ✅ TARGET PATTERN:
self.hass.async_create_task(
    self._notify_kid(
        kid_id,
        title=const.TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED,  # ✅ Constant
        message=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED,  # ✅ Constant
        message_data={"chore_name": chore_info[const.DATA_CHORE_NAME]},  # ✅ Data dict
    )
)
```

**Notification Audit Completion**:

- [ ] All notification calls documented
- [ ] Required constants identified and counted
- [ ] Translation entries planned (for en.json)
- [ ] Effort estimate calculated
- [ ] Findings documented in `/docs/in-process/PHASE3C_NOTIFICATION_REFACTOR_FINDING.md` (or similar)

---

### Step 7: Reverse Translation Audit (Phase 4b)

**When to perform**: After completing Phase 3/3b/3c code remediation and Phase 4 forward translation validation. This step finds **unused translation keys** in en.json that are no longer referenced in code.

**Why this matters**:

- Prevents translation bloat (fewer strings = easier maintenance)
- Reduces future translation burden when adding new languages
- Keeps en.json clean and understandable
- Establishes clean baseline for future work

**Checklist**:

- [ ] Extract all translation keys from en.json structure
- [ ] For each key, search codebase for references (const.py, all \*.py files)
- [ ] Categorize findings: actively used, legacy/deprecated, reserved for future, truly orphaned
- [ ] Distinguish between different translation sections (exceptions, config.error, config.abort, entity, etc.)
- [ ] Document why certain "unused" keys should be kept (future use, external references)

**Search patterns**:

```bash
# Extract exception keys from en.json
jq -r '.exceptions | keys[]' custom_components/kidschores/translations/en.json

# Search for each key in codebase
for key in $(jq -r '.exceptions | keys[]' custom_components/kidschores/translations/en.json); do
  if ! grep -r "\"$key\"" custom_components/kidschores/*.py > /dev/null; then
    echo "Potentially unused: exceptions.$key"
  fi
done

# Check if key exists as TRANS_KEY constant
grep "TRANS_KEY.*=.*\"$key\"" custom_components/kidschores/const.py
```

**Automated script approach**:

```python
# Phase 4b reverse audit script (see implementation below)
python3 << 'EOF'
import json
import re
from pathlib import Path

# Read en.json and extract all keys from all sections
with open("custom_components/kidschores/translations/en.json") as f:
    translations = json.load(f)

# Check exceptions section
exceptions = translations.get("exceptions", {})
for key in exceptions.keys():
    # Search in const.py for constant definition
    # Search in all *.py for direct usage
    # Report if orphaned

# Repeat for config.error, config.abort, entity.*, etc.
EOF
```

**Documentation**:

```json
{
  "reverse_translation_audit": {
    "en_json_sections_audited": [
      "exceptions",
      "config.error",
      "config.abort",
      "entity",
      "display"
    ],
    "total_keys_found": 150,
    "actively_used": 120,
    "potentially_unused": 30,
    "findings": [
      {
        "section": "exceptions",
        "key": "entity_not_found",
        "status": "unused",
        "recommendation": "Remove (duplicate of 'not_found')",
        "rationale": "Not referenced in const.py or any *.py files"
      },
      {
        "section": "exceptions",
        "key": "configuration_error",
        "status": "reserved",
        "recommendation": "Keep (future use)",
        "rationale": "Generic template for future configuration errors"
      }
    ],
    "summary": {
      "remove": 10,
      "keep_reserved": 15,
      "keep_legacy": 5
    }
  }
}
```

**Review criteria for "unused" keys**:

- **Remove**: True orphans with no purpose (typos, renamed keys, obsolete features)
- **Keep (Reserved)**: Generic templates for future features (document in comments)
- **Keep (Legacy)**: May be used by external tools, dashboards, or migration logic
- **Keep (External)**: Referenced in YAML dashboards or automations
- **Investigate**: Ambiguous cases requiring domain expert review

**Completion criteria**:

- [ ] All en.json sections audited (exceptions, config, entity, display)
- [ ] Each "unused" key categorized with recommendation
- [ ] Removal candidates listed with rationale
- [ ] "Keep" decisions documented with reason
- [ ] Update en.json if removing orphaned keys
- [ ] Run full test suite to verify no breakage (510/510 expected)
- [ ] Generate report: `/docs/completed/PHASE4B_REVERSE_TRANSLATION_AUDIT.md`

---

- [ ] All data constants categorized by priority
- [ ] Translation gaps documented
- [ ] Estimated constants needed: **N** new constants
- [ ] Estimated code locations to update: **M** locations
- [ ] File is ready for Phase 2+ remediation OR full code review

---

## General Code Quality

### Documentation Standards

**✅ File-Level Docstrings**

```python
"""Platform for KidsChores sensor entities.

Provides 26 sensor types across 3 scopes:
- Kid Scope: Per-kid sensors (points, chores completed, badges)
- Parent Scope: Parent-specific sensors (N/A for sensors)
- System Scope: Global aggregation sensors (pending approvals)
"""
```

- [ ] Module docstring exists and describes purpose
- [ ] Module docstring lists key entity types/counts
- [ ] Module docstring mentions scope categories
- [ ] Copyright/license present if required

**✅ Class Docstrings**

```python
class KidPointsSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking a kid's current point balance.

    Updates whenever points change via:
    - Chore approvals (adds default_points)
    - Reward redemptions (subtracts cost)
    - Bonus applications (adds bonus_points)
    - Penalty applications (subtracts penalty_points)
    - Direct point adjustments (adds/subtracts adjustment)

    Attributes:
        native_value: Current point balance (float)
        state_class: measurement
        device_class: None
    """
```

- [ ] Class docstring explains entity purpose
- [ ] Class docstring documents when entity updates
- [ ] Class docstring lists key attributes
- [ ] Class docstring includes example if complex

**✅ Method Docstrings**

```python
def _handle_coordinator_update(self) -> None:
    """Handle updated data from coordinator.

    Recalculates point balance from:
    - Base points in kid data
    - Applied badge multipliers
    """
```

- [ ] All public methods have docstrings
- [ ] Docstring describes what method does
- [ ] Docstring documents parameters if not obvious
- [ ] Docstring documents return value if not obvious

### Code Comments

**✅ Inline Comments**

```python
# Calculate net points for today (chores - rewards - penalties + bonuses)
net_points = (
    chore_points
    - reward_points
    - penalty_points
    + bonus_points
)
```

- [ ] Comments explain "why" not "what"
- [ ] Comments describe complex logic
- [ ] No commented-out code
- [ ] No TODO/FIXME comments (create issues instead)

### Type Hints

**✅ Type Annotations**

```python
def _calculate_chore_attributes(
    self,
    chore_id: str,
    chore_info: dict[str, Any],
    kid_info: dict[str, Any],
    chore_eid: str | None,
) -> dict[str, Any]:
    """Calculate chore attributes for dashboard display."""
```

- [ ] All parameters have type hints
- [ ] Return type specified
- [ ] Properties have return type hints
- [ ] Use `str | None` not `Optional[str]` (Python 3.10+)
- [ ] Use `dict[str, Any]` not `Dict[str, Any]`

---

## Entity Review Checklist

### Naming Consistency

**✅ Entity Class Names**

- [ ] Follows `[Scope][EntityType][Property]` pattern
- [ ] Kid scope: `Kid*` (e.g., `KidPointsSensor`)
- [ ] Parent scope: `Parent*` (e.g., `ParentChoreApproveButton`)
- [ ] System scope: `System*` for legacy, `Kid*` for modern helpers

**✅ Unique ID Construction**

```python
self._attr_unique_id = (
    f"{self._entry.entry_id}_{self._kid_id}"
    f"{const.SENSOR_KC_UID_SUFFIX_POINTS}"
)
```

- [ ] Uses `entry_id` as prefix
- [ ] Includes scope-appropriate identifier (`kid_id`, `entry_id`)
- [ ] Uses constant suffix from `const.py`
- [ ] Unique across all platform instances

**✅ Entity ID Pattern**

```python
# Kid scope: kc_<kid_slug>_<purpose>
# System scope: kc_<purpose> or kc_all_<purpose>
```

- [ ] Entity ID automatically generated from name
- [ ] Name follows Home Assistant conventions
- [ ] `has_entity_name = True` set
- [ ] Device info attached correctly

### Entity Attributes

**✅ Required Attributes**

```python
_attr_has_entity_name = True
_attr_device_class = SensorDeviceClass.ENUM
_attr_state_class = SensorStateClass.MEASUREMENT
_attr_native_unit_of_measurement = "Points"
```

- [ ] `_attr_has_entity_name` always `True`
- [ ] Device class set if applicable
- [ ] State class set for numeric sensors
- [ ] Unit of measurement uses config option if applicable
- [ ] Icon uses config option or appropriate MDI icon

**✅ Translation Keys**

```python
_attr_translation_key = "kid_points"
# Corresponds to en.json (master translation file):
# { "kid_points": "Points" }
```

- [ ] Translation key set for all entities
- [ ] Corresponding entry exists in `en.json` (master file)
- [ ] Translation follows naming pattern
- [ ] No hardcoded user-facing strings

### Entity Properties

**✅ Native Value**

```python
@property
def native_value(self) -> float:
    """Return current point balance."""
    kid_info = self.coordinator.kids_data.get(self._kid_id, {})
    return kid_info.get(const.DATA_KID_POINTS, 0.0)
```

- [ ] Returns appropriate type (float, int, str, datetime)
- [ ] Returns `None` for unknown values (not "unknown")
- [ ] No complex calculations (move to coordinator)
- [ ] Efficient data access (no loops if avoidable)

**✅ Extra State Attributes**

```python
@property
def extra_state_attributes(self) -> dict[str, Any]:
    """Return additional sensor attributes."""
    kid_info = self.coordinator.kids_data.get(self._kid_id, {})
    return {
        "lifetime_points": kid_info.get(const.DATA_KID_LIFETIME_POINTS, 0.0),
        "points_multiplier": kid_info.get(const.DATA_KID_POINTS_MULTIPLIER, 1.0),
        "max_points_ever": kid_info.get(const.DATA_KID_MAX_POINTS_EVER, 0.0),
    }
```

- [ ] All keys always present (use `None` for missing values)
- [ ] Attribute names descriptive and snake_case
- [ ] No redundant data (already in native_value)
- [ ] No heavy computation (pre-compute in coordinator)

### Device Registry

**✅ Device Info**

```python
_attr_device_info = DeviceInfo(
    identifiers={(const.DOMAIN, self._kid_id)},
    name=self._kid_name,
    entry_type=DeviceEntryType.SERVICE,
)
```

- [ ] Device identifiers use internal ID
- [ ] Device name uses human-readable name
- [ ] Entry type set appropriately
- [ ] Device shared across related entities

---

## Performance Review

### Coordinator Access Patterns

**✅ Efficient Data Access**

```python
# ✅ Good: Single coordinator access
kid_info = self.coordinator.kids_data.get(self._kid_id, {})
points = kid_info.get(const.DATA_KID_POINTS, 0.0)
name = kid_info.get(const.DATA_KID_NAME, "")

# ❌ Bad: Multiple coordinator accesses
points = self.coordinator.kids_data.get(self._kid_id, {}).get(const.DATA_KID_POINTS, 0.0)
name = self.coordinator.kids_data.get(self._kid_id, {}).get(const.DATA_KID_NAME, "")
```

- [ ] Minimize coordinator data access calls
- [ ] Cache coordinator data in local variable
- [ ] Use `.get()` with defaults for safety
- [ ] No nested dictionary traversals

**✅ Avoid Expensive Operations**

```python
# ❌ Bad: Expensive loop in property
@property
def native_value(self) -> int:
    count = 0
    for chore_id in self.coordinator.chores_data:
        if chore_id in self.coordinator.kids_data[kid_id]["claimed_chores"]:
            count += 1
    return count

# ✅ Good: Pre-computed in coordinator
@property
def native_value(self) -> int:
    kid_info = self.coordinator.kids_data.get(self._kid_id, {})
    return len(kid_info.get(const.DATA_KID_CLAIMED_CHORES, []))
```

- [ ] No loops in properties/native_value
- [ ] No complex calculations in properties
- [ ] Pre-compute aggregations in coordinator
- [ ] Cache expensive lookups

### Memory Efficiency

**✅ Attribute Size Management**

```python
# ❌ Bad: Large list in attributes
@property
def extra_state_attributes(self) -> dict[str, Any]:
    return {
        "all_chore_history": self._get_complete_history()  # 1000+ items
    }

# ✅ Good: Summarized/limited data
@property
def extra_state_attributes(self) -> dict[str, Any]:
    return {
        "recent_history": self._get_recent_history(limit=10)
    }
```

- [ ] Attributes contain reasonable data sizes
- [ ] Large lists paginated or limited
- [ ] Historical data summarized not raw
- [ ] Consider entity registry size limits

### Update Patterns

**✅ Coordinator Updates**

```python
def _handle_coordinator_update(self) -> None:
    """Handle updated data from the coordinator."""
    # Only do work if necessary
    if self._requires_update():
        self._update_internal_state()
    super()._handle_coordinator_update()
```

- [ ] Only updates when data changes
- [ ] Uses `CoordinatorEntity` base class
- [ ] `should_poll = False` when using coordinator
- [ ] No redundant state writes

---

## Standards Compliance

### Home Assistant Best Practices

**✅ Async Programming**

```python
# ✅ All I/O is async
async def async_press(self) -> None:
    """Handle button press."""
    await self.coordinator.async_claim_chore(self._kid_id, self._chore_id)

# ❌ No blocking calls
def _sync_operation(self):
    time.sleep(1)  # ❌ Blocks event loop
```

- [ ] All I/O operations are async
- [ ] No `time.sleep()` (use `asyncio.sleep()`)
- [ ] No blocking file operations
- [ ] Use `@callback` for event loop safe functions

**✅ Error Handling**

```python
try:
    data = await self.coordinator.fetch_data()
except ApiException as err:
    raise UpdateFailed(f"API error: {err}") from err
```

- [ ] Specific exceptions caught
- [ ] Errors logged appropriately
- [ ] User-facing errors use `ServiceValidationError`
- [ ] Coordinator errors use `UpdateFailed`

**✅ State Management**

```python
# ✅ Use None for unknown
@property
def native_value(self) -> float | None:
    kid_info = self.coordinator.kids_data.get(self._kid_id)
    if not kid_info:
        return None
    return kid_info.get(const.DATA_KID_POINTS, 0.0)

# ❌ Don't use "unknown" string
@property
def native_value(self) -> str:
    return "unknown"  # ❌ Bad
```

- [ ] Unknown values return `None`
- [ ] Availability via `available` property
- [ ] No "unknown" or "unavailable" strings

### Integration Quality Scale

**✅ Bronze Requirements (Mandatory)**

- [ ] Config flow implemented
- [ ] All entities have unique IDs
- [ ] Action setup (services) implemented
- [ ] Branding (name, icon) correct

**✅ Silver Requirements**

- [ ] Entity unavailability handled
- [ ] Parallel updates specified
- [ ] Reauthentication flow (N/A for local)

**✅ Gold Requirements**

- [ ] Device registry used
- [ ] Diagnostics implemented
- [ ] Entity/action translations

**✅ Platinum Requirements**

- [ ] Strict typing (all hints present)
- [ ] Async dependencies (no blocking libs)
- [ ] WebSession injection (N/A for local)

---

### Notification Standards ⭐ NEW

**✅ Notification Title/Message Patterns**

```python
# ✅ GOOD: Use translation constants
self.hass.async_create_task(
    self._notify_kid(
        kid_id,
        title=const.TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED,  # ✅ Constant
        message=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED,  # ✅ Constant
        message_data={  # ✅ Separate data dict for placeholders
            "chore_name": chore_info[const.DATA_CHORE_NAME],
            "points": points_earned,
        },
        extra_data=extra_data,
    )
)

# ❌ BAD: Hardcoded strings
self.hass.async_create_task(
    self._notify_kid(
        kid_id,
        title="KidsChores: Chore Approved",  # ❌ Hardcoded
        message=f"Your chore '{chore_name}' was approved.",  # ❌ f-string
    )
)
```

**Checklist**:

- [ ] **No hardcoded notification titles** - all use `TRANS_KEY_NOTIF_TITLE_*` constants
- [ ] **No hardcoded notification messages** - all use `TRANS_KEY_NOTIF_MESSAGE_*` constants
- [ ] **No f-strings in notification messages** - use `message_data` dict for placeholder substitution
- [ ] **All notification constants exist in const.py**
- [ ] **All notification translations exist in en.json** with proper placeholders
- [ ] Action strings properly encode context (e.g., `f"{ACTION_APPROVE}|{kid_id}|{chore_id}"`)

**Why This Matters**:

- **Translation Support**: Hardcoded strings prevent localization
- **Maintainability**: Constants centralize notification text
- **Consistency**: Standard pattern across all notifications
- **Testing**: Mock notifications easier with constants

**Common Notification Patterns to Audit**:

```bash
# Find all notification calls
grep -n '_notify_kid\|_notify_parents\|async_send_notification' coordinator.py

# Find hardcoded titles (should use constants)
grep -n 'title="[A-Z]' coordinator.py

# Find f-string messages (should use message_data)
grep -n 'message=.*f"' coordinator.py
```

**Reference**: See `/docs/in-process/PHASE3C_NOTIFICATION_REFACTOR_FINDING.md` for comprehensive notification audit findings.

---

### Language Selection Standards ⭐ NEW

**✅ Language Selection Pattern**

```python
# flow_helpers.py - Building schema with language selector
async def build_kid_schema(hass, ...):
    """Build kid schema with language selection."""
    # Get available languages (returns language codes only)
    language_options = await kh.get_available_dashboard_languages(hass)

    return vol.Schema({
        # ... other fields ...
        vol.Optional(
            const.CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE,  # ✅ Use CFOF_* for schema fields
            default=default_dashboard_language or const.DEFAULT_DASHBOARD_LANGUAGE,
        ): selector.LanguageSelector(
            selector.LanguageSelectorConfig(
                languages=language_options,
                native_name=True,  # Frontend provides native language names
            )
        ),
        # ... more fields ...
    })
```

**Checklist**:

- [ ] **Use LanguageSelector, not SelectSelector** - HA standard component for language selection
- [ ] **Set native_name=True** - Frontend automatically provides native language names (e.g., "Español" for "es")
- [ ] **Language options are codes only** - `get_available_dashboard_languages()` returns `["en", "es", "de", ...]`
- [ ] **No hardcoded language names** - Names come from HA's `LANGUAGES` set via frontend
- [ ] **Dynamic language detection** - Adding translation file auto-detects new language (no code changes needed)
- [ ] **Filter against HA LANGUAGES** - Only valid language codes exposed to users

**Why This Matters**:

- **HA Standard**: Uses core's language infrastructure, not custom patterns
- **Crowdin-Safe**: No metadata to translate = no corruption risk
- **Scalable**: Add language file, system auto-detects; no hardcoding needed
- **User Experience**: Frontend provides correct native language names automatically
- **Maintainability**: Single source of truth (filesystem + HA's master list)

**Common Language Selection Patterns to Audit**:

```bash
# Verify LanguageSelector is used, not SelectSelector
grep -n 'LanguageSelector\|SelectSelector' flow_helpers.py

# Check that language_options is passed directly to LanguageSelector
grep -n 'languages=language_options' flow_helpers.py

# Verify native_name=True is set
grep -n 'native_name=True' flow_helpers.py

# Confirm get_available_dashboard_languages returns list[str] not dicts
grep -n 'async def get_available_dashboard_languages' kc_helpers.py
```

**Reference**: See [ARCHITECTURE.md § Language Selection Architecture](ARCHITECTURE.md#language-selection-architecture) for complete design rationale and implementation details.

---

## Platform-Specific Reviews

### Sensor Platform (`sensor.py`)

**✅ Sensor-Specific Checks**

- [ ] State class appropriate (`measurement`, `total`, `total_increasing`)
- [ ] Device class set if applicable
- [ ] Unit of measurement correct
- [ ] Icon appropriate for state
- [ ] Options populated for enum sensors
- [ ] Last reset tracked for total sensors

**✅ Dashboard Helper Sensor**

```python
class KidDashboardHelperSensor(CoordinatorEntity, SensorEntity):
    """Aggregates all kid data for dashboard consumption."""
```

- [ ] All entity ID references use entity registry lookups
- [ ] Button entity IDs included for actions
- [ ] Lists pre-sorted by appropriate criteria
- [ ] Translations loaded from coordinator
- [ ] Change flags reset after attribute build

### Button Platform (`button.py`)

**✅ Button-Specific Checks**

```python
async def async_press(self) -> None:
    """Handle button press."""
    # Validate authorization
    if not await self._async_validate_authorization():
        raise ServiceValidationError("Unauthorized")

    # Execute action
    self.coordinator.apply_bonus(self._kid_id, self._bonus_id, self._user_id)
```

- [ ] Authorization checked before action
- [ ] User context available (`self._context`)
- [ ] Appropriate exceptions raised
- [ ] Coordinator method called (not direct state change)
- [ ] No return value (buttons don't return data)

### Select Platform (`select.py`)

**✅ Select-Specific Checks**

```python
@property
def options(self) -> list[str]:
    """Return list of available options."""
    return [chore["name"] for chore in self.coordinator.chores_data.values()]

async def async_select_option(self, option: str) -> None:
    """Handle option selection."""
    # No action needed - display only
```

- [ ] Options list always populated
- [ ] Options list kept current with coordinator
- [ ] Legacy selects wrapped with `show_legacy_entities` flag
- [ ] Modern selects always instantiated

### Calendar Platform (`calendar.py`)

**✅ Calendar-Specific Checks**

```python
async def async_get_events(
    self,
    hass: HomeAssistant,
    start_date: datetime,
    end_date: datetime,
) -> list[CalendarEvent]:
    """Return calendar events within date range."""
```

- [ ] Events generated from chore due dates
- [ ] Date range respected
- [ ] All-day events handled correctly
- [ ] Recurring chores processed

### Datetime Platform (`datetime.py`)

**✅ Datetime-Specific Checks**

```python
async def async_set_value(self, value: datetime) -> None:
    """Set new datetime value."""
    self.coordinator.set_chore_due_date(self._chore_id, value)
```

- [ ] Timezone handling correct
- [ ] Min/max values set appropriately
- [ ] Updates propagate to coordinator
- [ ] Date formatting consistent

---

## Review Process

### Phase 0 (Required): Audit Framework

**⭐ BEFORE ANY CODE REVIEW**, complete Phase 0 audit using steps above:

1. **Logging Audit** – Verify lazy logging patterns (100% compliance expected)
2. **User-facing Strings** – Identify all hardcoded UI text requiring constants
3. **Data/Lookup Constants** – Identify all repeated string literals
4. **Pattern Analysis** – Verify naming consistency (CFOP*ERROR*\_, CFOF\_\_, DATA\_\*, etc.)
5. **Translation Verification** – Check en.json (master file) coverage
6. **Audit Documentation** – Generate standardized report (JSON)

**Deliverable**: Audit report documenting:

- Total hardcoded strings and breakdown
- Constants needed (with priority: HIGH/MEDIUM/LOW)
- Translation gaps (missing en.json entries)
- Estimated code locations to update
- Ready for Phase 2 remediation

**Gate**: Phase 0 must be **100% complete** before proceeding to code review.

---

### Crowdin Translation Workflow

**When to use**: After Phase 0 audit confirms new user-facing strings need translations.

**Process**:

1. **Edit English Master Files** (in repository):

   - `translations/en.json` - Integration translations
   - `translations_custom/en_dashboard.json` - Dashboard UI translations
   - `translations_custom/en_notifications.json` - Notification messages
   - Only modify English masters; never edit other language files

2. **Push to `l10n-staging` Branch**:

   - Creates pull request with English translation changes
   - Triggers automated `.github/workflows/translation-sync.yaml` workflow

3. **Automated Crowdin Sync** (Workflow steps):

   - Uploads English sources to Crowdin project
   - Triggers Google Translate machine translation engine
   - Pre-translates to all configured languages (10+ languages)
   - Workflow commits translated files back to repository

4. **Alternative: Manual Download**:
   - If automated workflow fails or you need immediate translations
   - Download directly from Crowdin project via web interface
   - Follow same file structure and naming conventions

**Key Principles**:

- ✅ **Only English in Repository**: Developers edit English master files only
- ✅ **All Other Languages from Crowdin**: Never commit non-English translations manually
- ✅ **Automated Sync**: Workflow handles uploads and downloads automatically
- ✅ **Single Source of Truth**: Crowdin prevents translation sync conflicts
- ✅ **Machine Translation Bootstrap**: Google Translate MT pre-translates new strings

**Translation Key Validation**:

After updating English master files, verify:

```bash
# Verify all TRANS_KEY_* constants have en.json entries
grep 'const.TRANS_KEY_' custom_components/kidschores/*.py | \
  while read line; do
    key=$(echo "$line" | grep -oP 'TRANS_KEY_\K[A-Z_]+')
    grep -q "\"${key,,}\"" custom_components/kidschores/translations/en.json || \
      echo "Missing: $key"
  done
```

**Troubleshooting**:

- **Crowdin workflow doesn't trigger**: Ensure you pushed to `l10n-staging` branch, not `master`
- **Machine translation looks odd**: Review in Crowdin project, make corrections in en.json and re-push
- **Missing language**: Check Crowdin project settings for language availability

**Reference**: [ARCHITECTURE.md § Translation Architecture](ARCHITECTURE.md#translation-architecture-complete-reference)

---

### Step 1: Pre-Review Validation

**Run Automated Checks**

```bash
# Full lint check
./utils/quick_lint.sh --fix

# Full test suite
python -m pytest tests/ -v --tb=line

# Type checking (if enabled)
mypy custom_components/kidschores/
```

- [ ] All linting passes (9.5+/10)
- [ ] All tests pass (150+ tests)
- [ ] No type errors
- [ ] No trailing whitespace

### Step 2: File-by-File Review

**For Each Platform File:**

1. **Open file and scan structure**

   - [ ] File docstring complete
   - [ ] Imports organized (stdlib, third-party, local)
   - [ ] Constants defined at top
   - [ ] Helper functions before classes

2. **Review each entity class**

   - [ ] Use entity checklist above
   - [ ] Check all properties
   - [ ] Verify all attributes
   - [ ] Test method logic

3. **Check platform setup**
   - [ ] `async_setup_entry` correct
   - [ ] Entity instantiation matches patterns
   - [ ] Platform constants used correctly

### Step 3: Cross-File Validation

**Coordinator Integration**

- [ ] All entity data accessed through coordinator
- [ ] No direct storage manager access
- [ ] Coordinator methods called for state changes
- [ ] Update listeners registered correctly

**Constant Usage**

- [ ] All constants from `const.py`
- [ ] No magic strings
- [ ] Naming patterns followed
- [ ] No duplicate definitions

**Translation Coverage**

- [ ] All translation keys exist in `en.json` (master file)
- [ ] All user-facing strings translated
- [ ] No hardcoded English text
- [ ] Error messages translatable

### Step 4: Performance Profiling

**Hot Path Identification**

```python
# Frequently called properties (check performance):
# - native_value (called every state change)
# - extra_state_attributes (called every state change)
# - _handle_coordinator_update (called every coordinator update)
```

- [ ] Profile hot paths with realistic data
- [ ] Measure coordinator update time
- [ ] Check entity state write frequency
- [ ] Identify optimization opportunities

**Memory Profiling**

- [ ] Check entity attribute sizes
- [ ] Monitor coordinator data growth
- [ ] Verify cleanup routines work
- [ ] Test with large datasets (50+ kids, 200+ chores)

### Step 5: Documentation Review

**Code Comments**

- [ ] All complex logic explained
- [ ] Edge cases documented
- [ ] Algorithm choices justified

**External Documentation**

- [ ] ARCHITECTURE.md accurate
- [ ] README.md up to date
- [ ] Breaking changes documented
- [ ] Migration guides provided

### Step 6: Standards Audit

**Naming Conventions**

- [ ] Entity names follow scope pattern
- [ ] Method names descriptive
- [ ] Variable names clear
- [ ] Constants appropriately named

**Code Organization**

- [ ] Related code grouped together
- [ ] Separation of concerns maintained
- [ ] DRY principle followed
- [ ] SOLID principles applied

---

## Review Checklist Summary

### Quick Reference

**Per Entity Review** (5-10 minutes per entity)

- [ ] Documentation complete
- [ ] Type hints present
- [ ] Naming consistent
- [ ] Performance acceptable
- [ ] Standards compliant
- [ ] Tests exist

**Per Platform Review** (30-45 minutes per platform)

- [ ] All entities reviewed
- [ ] Platform setup correct
- [ ] Integration tests pass
- [ ] Performance profiled
- [ ] Documentation updated

**Full Integration Review** (2-3 hours)

- [ ] All platforms reviewed
- [ ] Cross-file validation done
- [ ] Performance acceptable
- [ ] Standards audit complete
- [ ] Documentation current

---

## Common Issues & Fixes

### Issue: Slow Entity Updates

**Problem**: Entity state updates lag behind coordinator updates

**Check**:

- [ ] Entity inherits from `CoordinatorEntity`
- [ ] `should_poll = False` set
- [ ] No blocking operations in properties

**Fix**: Ensure proper coordinator integration

### Issue: Missing Translations

**Problem**: Entity names show as "entity not found" in UI

**Check**:

- [ ] `translation_key` set correctly
- [ ] Entry exists in `en.json` (master file)
- [ ] Translation file format valid

**Fix**: Add missing translations to en.json

### Issue: Entity Not Appearing

**Problem**: Entity doesn't show up in entity registry

**Check**:

- [ ] `unique_id` set correctly
- [ ] Platform registered in `PLATFORMS`
- [ ] Entity added in `async_setup_entry`
- [ ] No exceptions during entity creation

**Fix**: Debug entity instantiation

### Issue: Performance Degradation

**Problem**: Integration slows down with many entities

**Check**:

- [ ] Properties don't have expensive calculations
- [ ] Coordinator data accessed efficiently
- [ ] No redundant entity updates
- [ ] Entity attribute sizes reasonable

**Fix**: Profile and optimize hot paths

---

## Tools & Resources

### Linting Tools

```bash
# Quick lint (comprehensive)
./utils/quick_lint.sh --fix

# Individual checks
pylint custom_components/kidschores/sensor.py
mypy custom_components/kidschores/sensor.py
```

### Testing Tools

```bash
# Run specific platform tests
pytest tests/test_sensor_values.py -v

# Run with coverage
pytest tests/ --cov=custom_components.kidschores --cov-report=term-missing

# Run specific test
pytest tests/test_sensor_values.py::test_kid_points_sensor_attributes -v
```

### Performance Tools

```python
# Profile coordinator updates
import cProfile
cProfile.run('coordinator.async_refresh()')

# Memory profiling
import tracemalloc
tracemalloc.start()
# ... run code ...
snapshot = tracemalloc.take_snapshot()
```

### Reference Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) - Integration architecture and patterns
- [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index/)
- [Home Assistant Entity Development](https://developers.home-assistant.io/docs/core/entity/)
- [TESTING_GUIDE.md](../tests/TESTING_GUIDE.md) - Testing patterns and troubleshooting

---

**Review Guide Version**: 1.2
**Last Updated**: January 4, 2026
**Maintainer**: KidsChores Development Team

---

## Phase 0: Audit Framework – Required Deliverables

**This section confirms Phase 0 audit outputs as REQUIRED for all code reviews.**

### Deliverable 1: Audit Report (JSON)

**Filename**: `audit_report_<filename>_<date>.json`

**Contents**:

```json
{
  "file": "path/to/file.py",
  "audit_date": "YYYY-MM-DD",
  "loc_total": 1234,
  "sections": {
    "logging": { ... },
    "user_facing_strings": { ... },
    "data_constants": { ... },
    "translation_keys": { ... }
  },
  "summary": "...",
  "constants_needed": [ ... ]
}
```

**When**: Generated during Phase 0 step 6

**Where**: Attached to PR description or referenced in code review comment

### Deliverable 2: Constants List

**Format**: Table or JSON array

**Columns**:

- String value
- Suggested constant name
- Priority (HIGH/MEDIUM/LOW)
- Occurrence count
- Line numbers

**Example**:
| String | Suggested Constant | Priority | Count | Lines |
|--------|-------------------|----------|-------|-------|
| `"base"` | `KEY_BASE = 'base'` | HIGH | 9 | 124, 1039, 2251, ... |
| `"tag"` | `BACKUP_KEY_TAG = 'tag'` | HIGH | 9 | 2933, 3024, ... |

### Deliverable 3: Translation Gaps Report

**Format**: List of missing entries in en.json (master file)

**Contents**:

- TRANS*KEY*\* constants found in code but missing in en.json
- CFOP*ERROR*\* constants found in code but missing in en.json
- Suggested English translations for each gap
- **Note**: KidsChores uses en.json only; no strings.json required (storage-only architecture)

**Example**:

```markdown
## Missing en.json Entries (4 total)

1. `CFOP_ERROR_DUPLICATE_CHORE_NAME`

   - Location: flow_helpers.py:1082
   - Suggested text: "Chore name already exists"

2. `TRANS_KEY_CFOF_INVALID_DATE_FORMAT`
   - Location: flow_helpers.py:2175
   - Suggested text: "Invalid date format (YYYY-MM-DD)"
```

### Deliverable 4: Code Remediation Plan

**Format**: Checklist or table

**Contents**:

- HIGH priority: Constant definitions needed first
- MEDIUM priority: Secondary constant definitions
- LOW priority: Nice-to-have constants

**Estimated effort**:

- X new constants to add to const.py
- Y code locations to update (with line numbers)
- Z translation entries to add to en.json only
- Estimated LOC changes: W

### Acceptance Gate: Phase 0 Completion

**All of the following must be true before PR approval**:

- [ ] **Audit report generated** – JSON document with complete findings
- [ ] **Constants list created** – All hardcoded strings categorized
- [ ] **Translation gaps identified** – Missing en.json entries documented
- [ ] **Code remediation plan ready** – Estimate of constants + code changes calculated
- [ ] **Phase 0 checklist** – All 6 steps completed with documentation
- [ ] **Sign-off** – Lead developer confirms audit is complete and accurate

**If Phase 0 is incomplete**, PR should not proceed past code review. Return to Phase 0 for completion.

---

**Phase 0 Audit Framework Integration**: Complete ✅
**Last Updated**: January 4, 2026

---

## Lessons Learned: Coordinator Remediation 2025

### Overview

This section documents key insights from the December 2025 comprehensive remediation of coordinator.py (9,183 lines), which achieved 100% code quality compliance through systematic pattern standardization.

### Pattern Compliance Achievements

#### 1. Exception Message Standardization (100% Compliance)

**Challenge**: 59 `HomeAssistantError` instances throughout coordinator, 6 using non-compliant f-string patterns.

**Solution**:

- All exceptions now use `translation_domain + translation_key + translation_placeholders` pattern
- Translation keys: `TRANS_KEY_ERROR_INSUFFICIENT_POINTS`, `TRANS_KEY_ERROR_MISSING_FIELD`, `TRANS_KEY_ERROR_INVALID_FREQUENCY`, `TRANS_KEY_ERROR_NOT_ASSIGNED`
- Zero hardcoded error messages remain in code

**Example Pattern**:

```python
# ❌ Before (non-compliant)
raise HomeAssistantError(f"Insufficient points for {kid_name}")

# ✅ After (compliant)
raise HomeAssistantError(
    translation_domain=const.DOMAIN,
    translation_key=const.TRANS_KEY_ERROR_INSUFFICIENT_POINTS,
    translation_placeholders={"kid_name": kid_name}
)
```

**Validation**: All exceptions verified through automated audits and manual review.

#### 2. Notification System Translation (31 Strings)

**Challenge**: All notification messages were hardcoded strings, preventing internationalization.

**Solution**:

- Implemented Home Assistant standard `async_get_translations()` API
- Created translation wrapper methods: `_notify_kid()`, `_notify_reminder()`
- Added test mode detection for faster test execution (5s vs 1800s reminder delay)
- 36 notification translation keys in `en.json` (title + message for each notification type)

**Key Constants Pattern**:

```python
# Notification titles
TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED = "notif_title_chore_approved"
TRANS_KEY_NOTIF_TITLE_OVERDUE = "notif_title_overdue_reminder"

# Notification messages
TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED = "notif_message_chore_approved"
TRANS_KEY_NOTIF_MESSAGE_OVERDUE = "notif_message_overdue_reminder"
```

**Translation Loading Pattern**:

```python
translations = await async_get_translations(
    self.hass,
    self.hass.config.language,
    "entity_component",
    {const.DOMAIN}
)
```

#### 3. Lazy Logging Enforcement (100% Compliance)

**Challenge**: Preventing f-strings in logging calls to avoid unnecessary string formatting overhead.

**Finding**: Zero violations found across 9,183 lines.

**Correct Pattern**:

```python
# ✅ Always use lazy logging with %s placeholders
const.LOGGER.debug("Processing chore for kid: %s", kid_name)
const.LOGGER.info("Approval completed for: %s at %s", chore_name, timestamp)
const.LOGGER.warning("Invalid frequency: %s", frequency)
```

**Enforcement Tools**:

```bash
# Audit command used during validation
grep -n 'LOGGER\.(debug|info|warning|error).*f["\']' coordinator.py
# Result: 0 matches = 100% compliance
```

#### 4. Data Constants Usage (1000+ References)

**Challenge**: Ensuring all dictionary key access uses `const.DATA_*` or `const.CONF_*` constants instead of string literals.

**Finding**: Comprehensive compliance throughout coordinator.

**Pattern Examples**:

```python
# ✅ Using constants for dictionary access
kid_data = kid.get(const.DATA_NAME, "")
points = kid.get(const.DATA_POINTS, 0)
assigned_kids = chore.get(const.DATA_ASSIGNED_KIDS, [])

# ✅ Using constants for config entry options
update_interval = self.config_entry.options.get(
    const.CONF_UPDATE_INTERVAL,
    const.DEFAULT_UPDATE_INTERVAL
)
```

### Validation Framework

#### Automated Audit Scripts

Three key validation scripts developed and proven effective:

**1. F-String Logging Audit**:

```bash
grep -n 'LOGGER\.(debug|info|warning|error).*f["\']' coordinator.py
```

**2. Dictionary Key Pattern Analysis**:

```python
# Regex to find literal dictionary keys
pattern = r'\[["\']([a-z_]+)["\']\]|\\.get\\(["\']([a-z_]+)["\']'
# Expected: Should only find const.DATA_* or const.CONF_* usage
```

**3. Translation Key Coverage**:

```python
# Verify all TRANS_KEY_* constants have corresponding en.json entries
trans_key_refs = re.findall(r'const\\.TRANS_KEY_[A-Z_]+', coordinator_code)
json_keys = load_translations('en.json')
# Compare and report missing keys
```

#### Test Suite Validation

**Coverage Requirements**:

- 526 passing tests (100% of non-skipped)
- 95%+ code coverage required
- All entity types tested (kids, parents, chores, rewards, badges, challenges, achievements)

**Key Test Categories**:

1. Config/Options flows (UI interactions)
2. Coordinator business logic (direct method testing)
3. Workflow scenarios (end-to-end state changes)
4. Migration/backward compatibility
5. Datetime handling (timezone-aware operations)
6. Dashboard template rendering

### Recommendations for Future Work

#### 1. Maintain 100% Pattern Compliance

**New Code Checklist**:

- [ ] All exceptions use `translation_domain + translation_key + translation_placeholders`
- [ ] No hardcoded user-facing strings
- [ ] Lazy logging only (`const.LOGGER.*()` with `%s` placeholders)
- [ ] Dictionary access via `const.DATA_*` or `const.CONF_*`

#### 2. Translation System Best Practices

**When Adding New Notifications**:

1. Define constants in `const.py`:
   - `TRANS_KEY_NOTIF_TITLE_<event>` (title key)
   - `TRANS_KEY_NOTIF_MESSAGE_<event>` (message key)
2. Add entries to `translations/en.json`
3. Use wrapper methods: `_notify_kid()` or `_notify_reminder()`
4. Test with `pytest -k notification` to verify

**When Adding New Exceptions**:

1. Define constant: `TRANS_KEY_ERROR_<condition>`
2. Add entry to `translations/en.json` under `exceptions` section
3. Use full pattern with placeholders
4. Test error paths explicitly

#### 3. Avoid Common Pitfalls

**Pitfall #1**: Using f-strings in `HomeAssistantError`

```python
# ❌ WRONG - Not translatable, not testable
raise HomeAssistantError(f"Kid {kid_name} not found")

# ✅ RIGHT - Translatable, testable
raise HomeAssistantError(
    translation_domain=const.DOMAIN,
    translation_key=const.TRANS_KEY_ERROR_KID_NOT_FOUND,
    translation_placeholders={"kid_name": kid_name}
)
```

**Pitfall #2**: Hardcoding dictionary keys

```python
# ❌ WRONG - Magic strings
name = kid["name"]
points = kid.get("points", 0)

# ✅ RIGHT - Using constants
name = kid[const.DATA_NAME]
points = kid.get(const.DATA_POINTS, 0)
```

**Pitfall #3**: Inconsistent notification patterns

```python
# ❌ WRONG - Hardcoded string
await self.notify("Chore approved!")

# ✅ RIGHT - Translation system
await self._notify_kid(
    kid,
    title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED,
    message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED,
    placeholders={"chore_name": chore_name}
)
```

### Metrics Summary

**Remediation Results (Phase 3 Complete)**:

| Metric                   | Target              | Achieved             | Status |
| ------------------------ | ------------------- | -------------------- | ------ |
| Exception compliance     | 100%                | 59/59 (100%)         | ✅     |
| Notification translation | All strings         | 31 strings converted | ✅     |
| Lazy logging compliance  | Zero f-strings      | 0 violations         | ✅     |
| Translation key coverage | All keys in en.json | 44/44 keys           | ✅     |
| Test pass rate           | 95%+                | 526/526 (100%)       | ✅     |
| Code quality score       | 9.5+                | 9.64/10              | ✅     |

**Effort Investment**:

- Phase 1 (Notification Constants): ~4 hours
- Phase 2 (Translation System): ~6 hours
- Phase 3 (Validation & Testing): ~8 hours
- **Total**: ~18 hours for 100% compliance

### Integration with Phase 0 Framework

These remediation achievements demonstrate the effectiveness of the Phase 0 Audit Framework:

1. **Systematic pattern identification** - All 59 exceptions cataloged
2. **Translation gap analysis** - 44 translation keys properly mapped
3. **Automated validation** - Scripts proven effective for auditing
4. **Documentation** - Comprehensive guide for future code quality work

**Next Steps for Future Files**: Apply Phase 0 framework BEFORE code review to prevent quality debt.

---

**Last Updated**: January 4, 2026 (v0.5.0 Pre-Release Review)
