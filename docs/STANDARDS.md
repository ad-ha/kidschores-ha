## 🏛️ KidsChores Repository Standards

### 1. Git & Workflow Standards

To maintain a clean history and stable environment use a **Traffic Controller** workflow.

- **Branching Strategy**: Use feature branches for all development.
- **The L10n-Staging Bridge**: All feature branches must be merged into `l10n-staging` to trigger translation syncs. Note l10n is shorthand for localization / translations.
- **Sync Protocol**: Regularly merge `l10n-staging` back into your active feature branches to receive the latest translations from Crowdin.
- **Commit Style**: Use **Conventional Commits** (e.g., `feat:`, `fix:`, `refactor:`, `chore(l10n):`) to ensure a readable, professional history.

---

### 2. Localization & Translation Standards

We strictly separate English "source" files from "localized" output to avoid manual editing conflicts.

- **Master Files**: Only the English master files (`en.json`, `en_notifications.json`, `en_dashboard.json`) are edited in the repository.
- **Crowdin-Managed**: All non-English files are read-only and sourced exclusively via the Crowdin GitHub Action.
- **Standard Integration Translations** (`en.json`): Must strictly nest under Home Assistant-approved keys (e.g., `exceptions`, `issues`, `entity`) for core integration features.
- **Custom Translations** (`translations_custom/`): Flexible files (`en_notifications.json`, `en_dashboard.json`) for dashboards and notifications. These mimic the HA JSON structure but handle features not natively supported by Home Assistant.
- **Template Pattern**: Use the **Template Translation System** for errors to reduce redundant work.
- **Logic**: Use one template (e.g., `not_authorized_action`) and pass the specific action as a placeholder (e.g., `approve_chores`).

---

### 3. Constant Naming Standards

With over 1,000 constants, we follow strict naming patterns to ensure the code remains self-documenting.

#### Primary Prefix Patterns

| Prefix               | Plurality    | Usage                               | Example                           |
| -------------------- | ------------ | ----------------------------------- | --------------------------------- |
| `DATA_*`             | **Singular** | Storage keys for specific entities  | `DATA_KID_NAME`                   |
| `CFOF_*`             | **Plural**   | Config/Options flow input fields    | `CFOF_KIDS_INPUT_NAME`            |
| `CFOP_ERROR_*`       | **Singular** | Flow validation error keys          | `CFOP_ERROR_KID_NAME`             |
| `TRANS_KEY_*`        | **N/A**      | Stable identifiers for translations | `TRANS_KEY_CFOF_DUPLICATE_KID`    |
| `CONFIG_FLOW_STEP_*` | **Action**   | Config flow step identifiers        | `CONFIG_FLOW_STEP_COLLECT_CHORES` |
| `OPTIONS_FLOW_*`     | **Action**   | Options flow identifiers            | `OPTIONS_FLOW_STEP_EDIT_CHORE`    |
| `DEFAULT_*`          | **N/A**      | Default configuration values        | `DEFAULT_POINTS_LABEL`            |
| `LABEL_*`            | **N/A**      | Consistent UI text labels           | `LABEL_CHORE`                     |

#### Entity State & Actions

- **`ATTR_*`**: Entity state attributes (100+ constants). e.g., `ATTR_KID_NAME`, `ATTR_CHORE_POINTS`.
- **`SERVICE_*`**: Service action names. e.g., `SERVICE_CLAIM_CHORE`.

#### Specialized Logic Patterns

- **`CHORE_STATE_*`**: Lifecycle states for chores (e.g., `CHORE_STATE_CLAIMED`, `CHORE_STATE_OVERDUE`).
- **`BADGE_*`**: Constants for badge logic, including `BADGE_TYPE_*`, `BADGE_STATE_*`, and `BADGE_RESET_SCHEDULE_*`.
- **`FREQUENCY_*`**: Recurrence options (e.g., `FREQUENCY_DAILY`, `FREQUENCY_CUSTOM`).
- **`PERIOD_*`**: Time period definitions (e.g., `PERIOD_DAY_END`, `PERIOD_ALL_TIME`).
- **`POINTS_SOURCE_*`**: Tracks point origins (e.g., `POINTS_SOURCE_CHORES`, `POINTS_SOURCE_BADGES`).
- **`ACTION_*`**: Notification action button titles.
- **`AWARD_ITEMS_*`**: Badge award composition (e.g., `AWARD_ITEMS_KEY_POINTS`).

#### Entity ID Generation (Dual-Variant System)

All entity platforms MUST provide both human-readable (`*_EID_*`) and machine-readable (`*_UID_*`) variants:

- **Sensors**: `SENSOR_KC_EID_*` / `SENSOR_KC_UID_*` (e.g., `kc_sarah_points` vs `kc_{uuid}_points`)
- **Buttons**: `BUTTON_KC_EID_*` / `BUTTON_KC_UID_*` (e.g., `kc_sarah_claim_chore` vs `kc_{uuid}_claim`)
- **Selects**: `SELECT_KC_EID_*` / `SELECT_KC_UID_*` (e.g., `kc_sarah_chore_list` vs `kc_{uuid}_chore_select`)
- **Calendars**: `CALENDAR_KC_*` (Standardized prefixes/suffixes)

#### Lifecycle Suffixes (Internal Development Tools)

- **`_DEPRECATED`**: Current keys actively used in production but slated for a future refactor.
- **`_LEGACY`**: Used **only** during migration functions to read old data.
- **`_UNUSED`**: Abandoned constants with no code references; safe to delete immediately.

---

### 4. Code Quality & Performance Standards

We aim for **Silver** quality standards to prepare for official Home Assistant integration.

- **No Hardcoded Strings**: All user-facing text (errors, logs, UI) **must** use constants and translation keys.
- **Lazy Logging**: Never use f-strings in logging. Use lazy formatting (`_LOGGER.info("Message: %s", variable)`) for performance.
- **Type Hinting**: 100% type hint coverage for all function arguments and return types.
- **Entity Lookup Pattern**: Always use the `get_*_id_or_raise()` helper functions in `kc_helpers.py` for service handlers to eliminate code duplication.
- **Coordinator Persistence**: All entity modifications must follow the **Modify → Persist (`_persist()`) → Notify (`async_update_listeners()`)** pattern.
- **Header Documentation**: Every entity file MUST include a header listing total count, categorized list (Kid-Specific vs System-Level), and legacy imports with clear numbering.

---

### 5. Entity Standards

We enforce strict naming patterns for both **Entity IDs** (runtime identifiers) and **Class Names** (codebase structure) to ensure persistence, readability, and immediate scope identification.

#### Entity ID Construction (Dual-Variant System)

Entities must support two identifiers to balance human readability with registry persistence:

1.  **UNIQUE_ID** (`unique_id`): Internal, stable registry identifier.
    - **Format**: `entry_id + [_kid_id] + [_entity_id] + SUFFIX` (e.g., `..._kid123_points`)
    - **Why Required**: Ensures history and settings persist even if users rename kids or chores.
2.  **ENTITY_ID** (`entity_id`): User-visible UI identifier.
    - **Format**: `domain.kc_[name] + [MIDFIX] + [name2] + [SUFFIX]` (e.g., `sensor.kc_sarah_points`)
    - **Why Required**: Provides descriptive, readable IDs for automations and dashboards.

**Pattern Components**:

- **SUFFIX** (`_points`): Appended to end. Used in both UID and EID. Defined in `const.py`.
- **MIDFIX** (`_chore_claim_`): Embedded between names (EID only) for semantic clarity in multi-part entities.

#### Entity Class Naming

All classes must follow the `[Scope][Entity][Property]EntityType` pattern (e.g., `KidPointsSensor`, `ParentChoreApproveButton`).

**1. Scope (Required)**
Indicates data ownership and initiation source. **Rule**: No blank scopes allowed.

- **`Kid`**: Per-kid data/actions initiated by the kid (e.g., `KidChoreClaimButton`).
- **`Parent`**: Per-kid actions initiated by a parent (e.g., `ParentChoreApproveButton`).
- **`System`**: Global aggregates shared across all kids (e.g., `SystemChoresPendingApprovalSensor`).

**2. Entity & Property**

- **Entity**: The subject (`Chore`, `Badge`, `Points`). Use **Plural** for collections (`SystemChores...`), **Singular** for items (`KidChore...`).
- **Property**: The aspect (`Status`, `Approvals`, `Claim`). **Rule**: Property must follow Entity (`KidBadgeHighest`, never `KidHighestBadge`).

**3. Platform Consistency**
This pattern applies to **all** platforms.

- **Sensor**: `KidPointsSensor` (State: Balance)
- **Button**: `KidChoreClaimButton` (Action: Claim)
- **Select**: `SystemRewardsSelect` (List: All Shared Rewards)
- **Calendar**: `KidScheduleCalendar` (View: Kid's timeline)

---

### 6. Error Handling Standards

We strictly enforce Home Assistant's exception handling patterns to ensure errors are translatable, actionable, and properly categorized.

- **Translation Keys Required**: All exceptions MUST use `translation_key` and `translation_placeholders`. **Never** raise exceptions with hardcoded strings.
- **Specific Exception Types**:
  - `ServiceValidationError`: For invalid user input (e.g., entity not found, invalid date).
  - `HomeAssistantError`: For system/runtime failures (e.g., API error, calculation failure).
  - `UpdateFailed`: Exclusive to Coordinator update failures.
  - `ConfigEntryAuthFailed`: For authentication expiration/invalid credentials.
- **Exception Chaining**: Always use `from err` when re-raising to preserve stack traces.
- **Input Validation**: Validate inputs _before_ processing action logic. Use `get_*_or_raise` helpers.

#### Correct Pattern (Gold Standard)

```python
try:
    kid_id = kh.get_kid_id_or_raise(coordinator, kid_name, "Approve Chore")
except ValueError as err:
    # ✅ Specific exception, translation key, and chaining
    raise ServiceValidationError(
        translation_domain=const.DOMAIN,
        translation_key=const.TRANS_KEY_ERROR_INVALID_INPUT,
        translation_placeholders={"details": str(err)}
    ) from err
```

#### Wrong Pattern (Do Not Use)

```python
# ❌ Hardcoded string, undefined exception type, no chaining
if not kid_id:
    raise Exception(f"Kid {kid_name} not found!")
```
