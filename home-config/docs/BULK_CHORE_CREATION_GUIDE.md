# Bulk Chore Creation Guide - Avoid 15-20 Hours of UI Work

**Problem:** KidsChores has NO service/API for creating chores - you must use the UI options flow.
**Solution:** 4 methods to bulk-import chores, from safest to fastest.

---

## TL;DR - Recommended Approach

**Use Option 2: Python Script** (15 minutes vs 15 hours)
1. Define chores in YAML
2. Run Python script to convert and inject into storage
3. Restart Home Assistant
4. Done!

---

## Understanding KidsChores Storage

### Storage Location
```
/config/.storage/kidschores_data
```

This is a JSON file managed by Home Assistant's Storage helper.

### Chore Structure (from coordinator.py lines 914-952)

```json
{
  "chores": {
    "uuid-here": {
      "name": "Scoop Litter",
      "state": "pending",
      "default_points": 3,
      "allow_multiple_claims_per_day": false,
      "partial_allowed": false,
      "description": "Scoop cat litter box daily",
      "chore_labels": ["Required", "Pets"],
      "icon": "mdi:cat",
      "shared_chore": false,
      "assigned_kids": ["kid-uuid-1"],
      "recurring_frequency": "daily",
      "custom_interval": null,
      "custom_interval_unit": null,
      "due_date": "2025-01-15T23:59:00+00:00",
      "last_completed": null,
      "last_claimed": null,
      "applicable_days": [],
      "notify_on_claim": true,
      "notify_on_approval": true,
      "notify_on_disapproval": true,
      "internal_id": "uuid-here"
    }
  }
}
```

### Required Fields
- `name` (string)
- `internal_id` (UUID - must match dictionary key)
- `assigned_kids` (array of kid UUIDs, NOT names)

### Frequency Options
- `"none"` - One-time chore
- `"daily"` - Recurs every day
- `"weekly"` - Recurs every week
- `"biweekly"` - Every 2 weeks
- `"monthly"` - Once per month
- `"custom"` - Custom interval (requires `custom_interval` and `custom_interval_unit`)

### Applicable Days
Empty array `[]` = all days. Otherwise: `["mon", "tue", "wed", "thu", "fri", "sat", "sun"]`

---

## Option 1: Manual JSON Editing (HIGH RISK - NOT RECOMMENDED)

**Time:** 2-3 hours
**Risk:** HIGH - One syntax error corrupts entire storage
**Skill:** Expert JSON editing, understanding UUIDs

### Steps

1. **BACKUP FIRST**
   ```bash
   cp /config/.storage/kidschores_data /config/.storage/kidschores_data.backup
   ```

2. **Stop Home Assistant**
   ```bash
   # From supervisor CLI or use UI
   ha core stop
   ```

3. **Edit `/config/.storage/kidschores_data`**
   - Get kid UUIDs from existing `kids` section
   - Add chores to `chores` section
   - Generate UUIDs for each (use `uuidgen` or online generator)
   - Ensure valid JSON syntax

4. **Validate JSON**
   ```bash
   python3 -m json.tool /config/.storage/kidschores_data > /dev/null
   echo $?  # Should return 0
   ```

5. **Start Home Assistant**
   ```bash
   ha core start
   ```

**Why NOT recommended:**
- Tedious UUID management
- High error potential
- No validation until restart
- If corrupted, lose ALL kidschores data

---

## Option 2: Python Bulk Import Script ⭐ RECOMMENDED

**Time:** 15-30 minutes
**Risk:** LOW - Script validates and backs up automatically
**Skill:** Basic Python + YAML

### Complete Solution

#### Step 1: Create Chore Definition YAML

Create: `/config/kidschores_import.yaml`

```yaml
# Chore import configuration
kids:
  - name: Bella
    # UUID will be looked up from existing storage
  - name: Lilly

chores:
  # Daily chores
  - name: "Scoop Litter"
    assigned_kids: ["Bella"]  # Use names, script converts to UUIDs
    points: 3
    frequency: daily
    due_time: "17:00"
    description: "Scoop cat litter box"
    icon: "mdi:cat"
    labels: ["Required", "Pets"]
    applicable_days: []  # All days

  - name: "Open Blinds"
    assigned_kids: ["Bella", "Lilly"]
    points: 1
    frequency: daily
    due_time: "09:00"
    description: "Open all blinds in morning"
    icon: "mdi:blinds-open"
    labels: ["Required"]

  - name: "Close Blinds"
    assigned_kids: ["Bella", "Lilly"]
    points: 1
    frequency: daily
    due_time: "18:00"
    description: "Close all blinds in evening"
    icon: "mdi:blinds"
    labels: ["Required"]

  # Weekly chores
  - name: "Laundry - Bella"
    assigned_kids: ["Bella"]
    points: 4
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["sun"]
    description: "Wash, dry, fold, and put away laundry"
    icon: "mdi:washing-machine"
    labels: ["Required", "Laundry"]

  - name: "Room Reset - Bella"
    assigned_kids: ["Bella"]
    points: 5
    frequency: weekly
    due_time: "20:00"
    applicable_days: ["wed"]
    description: "Full room clean - floor, trash, surfaces"
    icon: "mdi:home-floor-1"
    labels: ["Required", "Bedroom"]

  - name: "Bathroom Sink Clean - Bella"
    assigned_kids: ["Bella"]
    points: 3
    frequency: biweekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Clean faucet, handles, sink bowl"
    icon: "mdi:faucet"
    labels: ["Required", "Bathroom"]

  # Add more chores here...
```

#### Step 2: Create Import Script

Create: `/config/scripts/import_kidschores.py`

```python
#!/usr/bin/env python3
"""
KidsChores Bulk Import Script
Reads chore definitions from YAML and injects into storage JSON
"""

import json
import yaml
import uuid
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Configuration
STORAGE_FILE = Path("/config/.storage/kidschores_data")
IMPORT_FILE = Path("/config/kidschores_import.yaml")
BACKUP_DIR = Path("/config/backups")

# Default values (from const.py)
DEFAULT_POINTS = 5
DEFAULT_ICON = "mdi:star-outline"
FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_BIWEEKLY = "biweekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_NONE = "none"
CHORE_STATE_PENDING = "pending"

def backup_storage():
    """Create timestamped backup of storage file"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"kidschores_data.backup.{timestamp}"
    shutil.copy2(STORAGE_FILE, backup_file)
    print(f"✅ Backup created: {backup_file}")
    return backup_file

def load_storage():
    """Load existing KidsChores storage"""
    with open(STORAGE_FILE, 'r') as f:
        return json.load(f)

def save_storage(data):
    """Save updated storage (atomic write)"""
    temp_file = STORAGE_FILE.with_suffix('.tmp')
    with open(temp_file, 'w') as f:
        json.dump(data, f, indent=2)
    temp_file.replace(STORAGE_FILE)
    print(f"✅ Storage updated: {STORAGE_FILE}")

def load_chore_definitions():
    """Load chore definitions from YAML"""
    with open(IMPORT_FILE, 'r') as f:
        return yaml.safe_load(f)

def get_kid_uuid_by_name(storage, kid_name):
    """Find kid UUID by name"""
    for kid_id, kid_data in storage.get('kids', {}).items():
        if kid_data.get('name') == kid_name:
            return kid_id
    raise ValueError(f"Kid not found: {kid_name}")

def get_next_due_date(frequency, due_time="23:59", applicable_days=None):
    """Calculate next due date based on frequency"""
    # Get local timezone
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone()

    # Parse time
    hour, minute = map(int, due_time.split(':'))

    # Set time on today
    due_dt = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If time already passed, move to tomorrow
    if due_dt <= now_local:
        due_dt += timedelta(days=1)

    # Handle applicable_days for weekly/daily
    if applicable_days and frequency in [FREQUENCY_DAILY, FREQUENCY_WEEKLY]:
        day_map = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        current_weekday = due_dt.weekday()
        target_days = [day_map[d] for d in applicable_days]

        # Find next applicable day
        days_ahead = 0
        while (current_weekday + days_ahead) % 7 not in target_days:
            days_ahead += 1
            if days_ahead > 7:
                break  # Safety

        due_dt += timedelta(days=days_ahead)

    return due_dt.isoformat()

def create_chore(chore_def, kid_uuid_map):
    """Convert chore definition to storage format"""
    chore_id = str(uuid.uuid4())

    # Convert kid names to UUIDs
    assigned_kids = []
    for kid_name in chore_def.get('assigned_kids', []):
        if kid_name in kid_uuid_map:
            assigned_kids.append(kid_uuid_map[kid_name])
        else:
            print(f"⚠️  Warning: Kid '{kid_name}' not found for chore '{chore_def['name']}'")

    # Get frequency
    frequency = chore_def.get('frequency', FREQUENCY_NONE)

    # Calculate due date
    due_date = None
    if frequency != FREQUENCY_NONE:
        due_date = get_next_due_date(
            frequency,
            chore_def.get('due_time', '23:59'),
            chore_def.get('applicable_days', [])
        )

    # Convert applicable_days
    applicable_days_str = chore_def.get('applicable_days', [])

    chore = {
        "name": chore_def['name'],
        "state": CHORE_STATE_PENDING,
        "default_points": chore_def.get('points', DEFAULT_POINTS),
        "allow_multiple_claims_per_day": chore_def.get('allow_multiple_per_day', False),
        "partial_allowed": chore_def.get('partial_allowed', False),
        "description": chore_def.get('description', ''),
        "chore_labels": chore_def.get('labels', []),
        "icon": chore_def.get('icon', DEFAULT_ICON),
        "shared_chore": len(assigned_kids) > 1,
        "assigned_kids": assigned_kids,
        "recurring_frequency": frequency,
        "custom_interval": chore_def.get('custom_interval'),
        "custom_interval_unit": chore_def.get('custom_interval_unit'),
        "due_date": due_date,
        "last_completed": None,
        "last_claimed": None,
        "applicable_days": applicable_days_str,
        "notify_on_claim": chore_def.get('notify_on_claim', True),
        "notify_on_approval": chore_def.get('notify_on_approval', True),
        "notify_on_disapproval": chore_def.get('notify_on_disapproval', True),
        "internal_id": chore_id
    }

    return chore_id, chore

def main():
    print("=" * 60)
    print("KidsChores Bulk Import Script")
    print("=" * 60)

    # Validate files exist
    if not STORAGE_FILE.exists():
        print(f"❌ Error: Storage file not found: {STORAGE_FILE}")
        print("   Make sure KidsChores integration is installed and configured")
        return 1

    if not IMPORT_FILE.exists():
        print(f"❌ Error: Import file not found: {IMPORT_FILE}")
        print(f"   Create {IMPORT_FILE} with your chore definitions")
        return 1

    # Backup
    print("\n📁 Creating backup...")
    backup_file = backup_storage()

    # Load data
    print("\n📖 Loading existing storage...")
    storage = load_storage()

    print("📖 Loading chore definitions...")
    definitions = load_chore_definitions()

    # Build kid name -> UUID map
    kid_uuid_map = {}
    for kid_id, kid_data in storage.get('kids', {}).items():
        kid_name = kid_data.get('name')
        if kid_name:
            kid_uuid_map[kid_name] = kid_id

    print(f"   Found {len(kid_uuid_map)} existing kids: {', '.join(kid_uuid_map.keys())}")

    # Process chores
    print(f"\n🔨 Creating chores...")
    chores_added = 0
    chores_skipped = 0

    existing_chore_names = {
        chore_data.get('name'): chore_id
        for chore_id, chore_data in storage.get('chores', {}).items()
    }

    for chore_def in definitions.get('chores', []):
        chore_name = chore_def.get('name')

        # Check if chore already exists
        if chore_name in existing_chore_names:
            print(f"   ⏭️  Skipping '{chore_name}' (already exists)")
            chores_skipped += 1
            continue

        # Create chore
        chore_id, chore = create_chore(chore_def, kid_uuid_map)

        # Add to storage
        if 'chores' not in storage:
            storage['chores'] = {}
        storage['chores'][chore_id] = chore

        print(f"   ✅ Created '{chore_name}' (ID: {chore_id[:8]}...)")
        chores_added += 1

    # Save
    if chores_added > 0:
        print(f"\n💾 Saving {chores_added} new chores...")
        save_storage(storage)
        print("\n" + "=" * 60)
        print(f"✅ SUCCESS! Added {chores_added} chores")
        if chores_skipped > 0:
            print(f"   (Skipped {chores_skipped} existing chores)")
        print("=" * 60)
        print("\n📋 Next steps:")
        print("   1. Restart Home Assistant")
        print("   2. Check Developer Tools > States for new sensor entities")
        print("   3. If issues, restore backup:")
        print(f"      cp {backup_file} {STORAGE_FILE}")
        print("      (then restart HA)")
    else:
        print("\n⚠️  No new chores to add")

    return 0

if __name__ == "__main__":
    exit(main())
```

#### Step 3: Run the Script

```bash
# Make executable
chmod +x /config/scripts/import_kidschores.py

# Run
python3 /config/scripts/import_kidschores.py
```

**Output:**
```
============================================================
KidsChores Bulk Import Script
============================================================

📁 Creating backup...
✅ Backup created: /config/backups/kidschores_data.backup.20250116_143022

📖 Loading existing storage...
📖 Loading chore definitions...
   Found 2 existing kids: Bella, Lilly

🔨 Creating chores...
   ✅ Created 'Scoop Litter' (ID: a1b2c3d4...)
   ✅ Created 'Open Blinds' (ID: e5f6g7h8...)
   ✅ Created 'Close Blinds' (ID: i9j0k1l2...)
   ...

💾 Saving 15 new chores...
✅ Storage updated: /config/.storage/kidschores_data

============================================================
✅ SUCCESS! Added 15 chores
============================================================

📋 Next steps:
   1. Restart Home Assistant
   2. Check Developer Tools > States for new sensor entities
```

#### Step 4: Restart Home Assistant

```bash
ha core restart
```

Or use UI: **Settings > System > Restart**

---

## Option 3: REST API Service (If Available)

**Status:** ❌ Not supported by KidsChores
**Why:** Integration doesn't expose REST endpoints for chore creation

---

## Option 4: Custom Service Creation (Advanced)

**Time:** 2-3 hours initial setup
**Benefit:** Reusable service for future bulk imports
**Skill:** Python development, HA custom component modification

### Add Custom Service to KidsChores

**File:** `/config/custom_components/kidschores/services.py`

Add this service definition (around line 370):

```python
async def async_bulk_create_chores(call):
    """Service to bulk create chores from data"""
    coordinator = hass.data[DOMAIN][entry_id]["coordinator"]

    chores_data = call.data.get("chores", [])
    created_count = 0

    for chore_def in chores_data:
        chore_id = str(uuid.uuid4())
        coordinator._create_chore(chore_id, chore_def)
        created_count += 1

    await coordinator.async_save()
    LOGGER.info(f"Bulk created {created_count} chores")
```

**File:** `/config/custom_components/kidschores/services.yaml`

Add:

```yaml
bulk_create_chores:
  name: "Bulk Create Chores"
  description: "Create multiple chores at once from YAML"
  fields:
    chores:
      name: "Chores Data"
      description: "List of chore definitions"
      required: true
      selector:
        object:
```

Then call via service:

```yaml
service: kidschores.bulk_create_chores
data:
  chores:
    - name: "Scoop Litter"
      assigned_kids: ["Bella"]
      default_points: 3
      recurring_frequency: "daily"
      # ... etc
```

**Downsides:**
- Requires modifying the integration code
- Updates may overwrite your changes
- Still verbose service calls

---

## Full Chore Template for Your System

Based on your design doc, here's a ready-to-use import file:

**File:** `/config/kidschores_import_full.yaml`

```yaml
kids:
  - name: Bella
  - name: Lilly

chores:
  # ========== DAILY CHORES ==========

  - name: "Open Blinds (Morning)"
    assigned_kids: ["Bella", "Lilly"]
    points: 1
    frequency: daily
    due_time: "09:00"
    description: "Open all blinds in common areas"
    icon: "mdi:blinds-open"
    labels: ["Required", "Daily"]

  - name: "Close Blinds (Evening)"
    assigned_kids: ["Bella", "Lilly"]
    points: 1
    frequency: daily
    due_time: "18:00"
    description: "Close all blinds after 5pm"
    icon: "mdi:blinds"
    labels: ["Required", "Daily"]

  - name: "Plant Lights - On"
    assigned_kids: ["Bella", "Lilly"]
    points: 1
    frequency: daily
    due_time: "09:00"
    description: "Turn on grow lights in morning"
    icon: "mdi:lightbulb-on"
    labels: ["Required", "Daily", "Plants"]

  - name: "Plant Lights - Off"
    assigned_kids: ["Bella", "Lilly"]
    points: 1
    frequency: daily
    due_time: "18:00"
    description: "Turn off grow lights in evening"
    icon: "mdi:lightbulb-off"
    labels: ["Required", "Daily", "Plants"]

  - name: "Scoop Litter - Bella"
    assigned_kids: ["Bella"]
    points: 3
    frequency: daily
    due_time: "17:00"
    description: "Scoop cat litter box"
    icon: "mdi:cat"
    labels: ["Required", "Daily", "Pets"]
    applicable_days: ["mon", "wed", "fri", "sun"]

  - name: "Scoop Litter - Lilly"
    assigned_kids: ["Lilly"]
    points: 3
    frequency: daily
    due_time: "17:00"
    description: "Scoop cat litter box"
    icon: "mdi:cat"
    labels: ["Required", "Daily", "Pets"]
    applicable_days: ["tue", "thu", "sat"]

  - name: "Dog - After School (Bella)"
    assigned_kids: ["Bella"]
    points: 2
    frequency: daily
    due_time: "16:00"
    description: "Let dog out when home from school"
    icon: "mdi:dog"
    labels: ["Required", "Daily", "Pets"]
    applicable_days: ["mon", "tue", "thu", "fri"]  # Not Wed when gone

  - name: "Dog - After School (Lilly)"
    assigned_kids: ["Lilly"]
    points: 2
    frequency: daily
    due_time: "16:00"
    description: "Let dog out when home from school"
    icon: "mdi:dog"
    labels: ["Required", "Daily", "Pets"]
    applicable_days: ["mon", "tue", "thu", "fri"]

  # ========== WEEKLY CHORES ==========

  - name: "Laundry - Bella"
    assigned_kids: ["Bella"]
    points: 4
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["sun"]
    description: "Wash, dry, fold, and put away laundry"
    icon: "mdi:washing-machine"
    labels: ["Required", "Weekly", "Laundry"]

  - name: "Laundry - Lilly"
    assigned_kids: ["Lilly"]
    points: 4
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["tue"]
    description: "Wash, dry, fold, and put away laundry"
    icon: "mdi:washing-machine"
    labels: ["Required", "Weekly", "Laundry"]

  - name: "Towels - Lilly"
    assigned_kids: ["Lilly"]
    points: 3
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["wed"]
    description: "Wash bathroom towels and bathmat"
    icon: "mdi:towel"
    labels: ["Required", "Weekly", "Laundry"]

  - name: "Delicates - Bella"
    assigned_kids: ["Bella"]
    points: 3
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Wash delicate items"
    icon: "mdi:hanger"
    labels: ["Required", "Weekly", "Laundry"]

  - name: "Room Reset - Bella"
    assigned_kids: ["Bella"]
    points: 5
    frequency: weekly
    due_time: "20:00"
    applicable_days: ["wed"]
    description: "Full room clean - floor clear, trash out, surfaces clean"
    icon: "mdi:home-floor-1"
    labels: ["Required", "Weekly", "Bedroom"]

  - name: "Room Reset - Lilly"
    assigned_kids: ["Lilly"]
    points: 5
    frequency: weekly
    due_time: "20:00"
    applicable_days: ["wed"]
    description: "Full room clean - floor clear, trash out, surfaces clean"
    icon: "mdi:home-floor-1"
    labels: ["Required", "Weekly", "Bedroom"]

  - name: "Bathroom Trash"
    assigned_kids: ["Bella"]  # Manual rotation via automation
    points: 2
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Empty bathroom trash can"
    icon: "mdi:delete-empty"
    labels: ["Required", "Weekly", "Bathroom"]

  - name: "Sweep Kitchen"
    assigned_kids: ["Bella", "Lilly"]
    points: 3
    frequency: weekly
    due_time: "18:00"
    applicable_days: ["mon", "wed", "fri"]
    description: "Sweep kitchen and entry areas"
    icon: "mdi:broom"
    labels: ["Bonus", "Weekly", "Floors"]

  - name: "Pip Feeding - Lilly"
    assigned_kids: ["Lilly"]
    points: 3
    frequency: weekly
    due_time: "17:00"
    applicable_days: ["wed"]
    description: "Feed Pip worms and handle for exercise"
    icon: "mdi:snake"
    labels: ["Required", "Weekly", "Pets"]

  # ========== BI-WEEKLY CHORES ==========

  - name: "Bathroom Sink Clean - Bella"
    assigned_kids: ["Bella"]
    points: 3
    frequency: biweekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Clean faucet, handles, and sink bowl"
    icon: "mdi:faucet"
    labels: ["Required", "Bathroom"]

  - name: "Bathroom Sink Clean - Lilly"
    assigned_kids: ["Lilly"]
    points: 3
    frequency: biweekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Clean faucet, handles, and sink bowl"
    icon: "mdi:faucet"
    labels: ["Required", "Bathroom"]

  - name: "Toilet Scrub - Bella"
    assigned_kids: ["Bella"]
    points: 4
    frequency: biweekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Scrub toilet bowl and seat"
    icon: "mdi:toilet"
    labels: ["Required", "Bathroom"]

  - name: "Toilet Scrub - Lilly"
    assigned_kids: ["Lilly"]
    points: 4
    frequency: biweekly
    due_time: "18:00"
    applicable_days: ["thu"]
    description: "Scrub toilet bowl and seat"
    icon: "mdi:toilet"
    labels: ["Required", "Bathroom"]

  # ========== MONTHLY CHORES ==========

  - name: "Bathroom Floor - Mop"
    assigned_kids: ["Bella"]  # Rotates via automation
    points: 4
    frequency: monthly
    due_time: "14:00"
    description: "Mop bathroom floor"
    icon: "mdi:water"
    labels: ["Required", "Monthly", "Bathroom"]

  - name: "Bathroom Tub/Shower Scrub"
    assigned_kids: ["Bella"]
    points: 5
    frequency: monthly
    due_time: "14:00"
    description: "Scrub tub/shower walls and floor"
    icon: "mdi:shower"
    labels: ["Required", "Monthly", "Bathroom"]

  - name: "Bathroom Mirror"
    assigned_kids: ["Bella"]
    points: 2
    frequency: monthly
    due_time: "14:00"
    description: "Clean bathroom mirror"
    icon: "mdi:mirror"
    labels: ["Required", "Monthly", "Bathroom"]

  - name: "Bathroom Dusting"
    assigned_kids: ["Bella"]
    points: 3
    frequency: monthly
    due_time: "14:00"
    description: "Dust ceiling, corners, and vents"
    icon: "mdi:spider-web"
    labels: ["Required", "Monthly", "Bathroom"]

  - name: "Bathroom Baseboards"
    assigned_kids: ["Bella"]
    points: 3
    frequency: monthly
    due_time: "14:00"
    description: "Wipe baseboards and trim"
    icon: "mdi:border-all"
    labels: ["Required", "Monthly", "Bathroom"]

  - name: "Bathroom Countertop"
    assigned_kids: ["Bella"]
    points: 3
    frequency: monthly
    due_time: "14:00"
    description: "Clean countertop and backsplash edges"
    icon: "mdi:counter"
    labels: ["Required", "Monthly", "Bathroom"]

  # Add more as needed...
```

---

## Comparison of Methods

| Method | Time | Risk | Flexibility | Reusable |
|--------|------|------|-------------|----------|
| Manual UI | 15-20 hrs | Low | High | No |
| Manual JSON | 2-3 hrs | **HIGH** | Medium | No |
| **Python Script** | **15-30 min** | **Low** | **High** | **Yes** |
| Custom Service | 2-3 hrs setup | Medium | High | Yes |

---

## Troubleshooting

### Error: "Kid 'Bella' not found"
- Make sure kid exists in KidsChores UI first
- Check spelling matches exactly

### Chores don't appear after restart
- Check HA logs: `Settings > System > Logs`
- Verify JSON syntax: `python3 -m json.tool /config/.storage/kidschores_data`
- Restore backup and try again

### Due dates are wrong
- Script calculates based on server timezone
- Adjust `due_time` in YAML
- For specific dates, manually set after import

### UUIDs collide
- Extremely unlikely (UUID v4 = 122-bit random)
- Script generates new UUID for each chore

---

## Next Steps After Bulk Import

1. **Verify in UI**
   - Settings > Devices & Services > KidsChores > Configure
   - Check all chores appear

2. **Assign to correct weeks**
   - Some bi-weekly/monthly may need manual first due date
   - Use `kidschores.set_chore_due_date` service

3. **Set up automations**
   - Rotation logic (bathroom)
   - Custody-aware assignments
   - See `SCALE_UP_PLAN.md`

4. **Test the system**
   - Claim a chore
   - Approve via notification
   - Verify points update

---

**Recommendation:** Use Option 2 (Python Script). Takes 15-30 minutes vs 15-20 hours of UI clicking, with automatic backups and validation.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-16
**Dependencies:** Python 3.7+, PyYAML (`pip install pyyaml`)
