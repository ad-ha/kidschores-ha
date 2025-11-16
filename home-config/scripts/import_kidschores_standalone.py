#!/usr/bin/env python3
"""
KidsChores Bulk Import - Standalone Version
Includes YAML data inline - no external files needed

Usage:
    python3 import_kidschores_standalone.py /config/.storage/kidschores_data
"""

import json
import uuid
import shutil
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Default values
DEFAULT_POINTS = 5
DEFAULT_ICON = "mdi:star-outline"
FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_BIWEEKLY = "biweekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_NONE = "none"
CHORE_STATE_PENDING = "pending"

# YAML data embedded directly
CHORES_DATA = {
    "kids": [
        {"name": "Bella"},
        {"name": "Lilly"}
    ],
    "chores": [
        # ========== DAILY CHORES ==========
        {
            "name": "Open Blinds (Morning)",
            "assigned_kids": ["Bella", "Lilly"],
            "points": 1,
            "frequency": "daily",
            "due_time": "09:00",
            "description": "Open all blinds in common areas",
            "icon": "mdi:blinds-open",
            "labels": ["Required", "Daily"]
        },
        {
            "name": "Close Blinds (Evening)",
            "assigned_kids": ["Bella", "Lilly"],
            "points": 1,
            "frequency": "daily",
            "due_time": "18:00",
            "description": "Close all blinds after 5pm",
            "icon": "mdi:blinds",
            "labels": ["Required", "Daily"]
        },
        {
            "name": "Plant Lights - On",
            "assigned_kids": ["Bella", "Lilly"],
            "points": 1,
            "frequency": "daily",
            "due_time": "09:00",
            "description": "Turn on grow lights in morning",
            "icon": "mdi:lightbulb-on",
            "labels": ["Required", "Daily", "Plants"]
        },
        {
            "name": "Plant Lights - Off",
            "assigned_kids": ["Bella", "Lilly"],
            "points": 1,
            "frequency": "daily",
            "due_time": "18:00",
            "description": "Turn off grow lights in evening",
            "icon": "mdi:lightbulb-off",
            "labels": ["Required", "Daily", "Plants"]
        },
        {
            "name": "Scoop Litter - Bella",
            "assigned_kids": ["Bella"],
            "points": 3,
            "frequency": "daily",
            "due_time": "17:00",
            "description": "Scoop cat litter box",
            "icon": "mdi:cat",
            "labels": ["Required", "Daily", "Pets"],
            "applicable_days": ["mon", "wed", "fri", "sun"]
        },
        {
            "name": "Scoop Litter - Lilly",
            "assigned_kids": ["Lilly"],
            "points": 3,
            "frequency": "daily",
            "due_time": "17:00",
            "description": "Scoop cat litter box",
            "icon": "mdi:cat",
            "labels": ["Required", "Daily", "Pets"],
            "applicable_days": ["tue", "thu", "sat"]
        },
        {
            "name": "Dog Out After School - Bella",
            "assigned_kids": ["Bella"],
            "points": 2,
            "frequency": "daily",
            "due_time": "16:00",
            "description": "Let dog out when home from school",
            "icon": "mdi:dog",
            "labels": ["Required", "Daily", "Pets"],
            "applicable_days": ["mon", "tue", "thu", "fri"]
        },
        {
            "name": "Dog Out After School - Lilly",
            "assigned_kids": ["Lilly"],
            "points": 2,
            "frequency": "daily",
            "due_time": "16:00",
            "description": "Let dog out when home from school",
            "icon": "mdi:dog",
            "labels": ["Required", "Daily", "Pets"],
            "applicable_days": ["mon", "tue", "thu", "fri"]
        },

        # ========== WEEKLY CHORES ==========
        {
            "name": "Laundry - Bella",
            "assigned_kids": ["Bella"],
            "points": 4,
            "frequency": "weekly",
            "due_time": "18:00",
            "applicable_days": ["sun"],
            "description": "Wash, dry, fold, and put away laundry",
            "icon": "mdi:washing-machine",
            "labels": ["Required", "Weekly", "Laundry"]
        },
        {
            "name": "Laundry - Lilly",
            "assigned_kids": ["Lilly"],
            "points": 4,
            "frequency": "weekly",
            "due_time": "18:00",
            "applicable_days": ["tue"],
            "description": "Wash, dry, fold, and put away laundry",
            "icon": "mdi:washing-machine",
            "labels": ["Required", "Weekly", "Laundry"]
        },
        {
            "name": "Room Reset - Bella",
            "assigned_kids": ["Bella"],
            "points": 5,
            "frequency": "weekly",
            "due_time": "20:00",
            "applicable_days": ["wed"],
            "description": "Full room clean - floor, trash, surfaces",
            "icon": "mdi:home-floor-1",
            "labels": ["Required", "Weekly", "Bedroom"]
        },
        {
            "name": "Room Reset - Lilly",
            "assigned_kids": ["Lilly"],
            "points": 5,
            "frequency": "weekly",
            "due_time": "20:00",
            "applicable_days": ["wed"],
            "description": "Full room clean - floor, trash, surfaces",
            "icon": "mdi:home-floor-1",
            "labels": ["Required", "Weekly", "Bedroom"]
        },
        {
            "name": "Sweep Kitchen",
            "assigned_kids": ["Bella", "Lilly"],
            "points": 3,
            "frequency": "weekly",
            "due_time": "18:00",
            "applicable_days": ["mon", "wed", "fri"],
            "description": "Sweep kitchen and entry areas",
            "icon": "mdi:broom",
            "labels": ["Bonus", "Weekly", "Floors"]
        },

        # Add more chores here...
    ]
}

def backup_storage(storage_file):
    """Create timestamped backup"""
    backup_dir = storage_file.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{storage_file.name}.backup.{timestamp}"
    shutil.copy2(storage_file, backup_file)
    print(f"✅ Backup created: {backup_file}")
    return backup_file

def load_storage(storage_file):
    """Load existing KidsChores storage"""
    with open(storage_file, 'r') as f:
        return json.load(f)

def save_storage(storage_file, data):
    """Save updated storage (atomic write)"""
    temp_file = storage_file.with_suffix('.tmp')
    with open(temp_file, 'w') as f:
        json.dump(data, f, indent=2)
    temp_file.replace(storage_file)
    print(f"✅ Storage updated: {storage_file}")

def get_next_due_date(frequency, due_time="23:59", applicable_days=None):
    """Calculate next due date based on frequency"""
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone()

    hour, minute = map(int, due_time.split(':'))
    due_dt = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if due_dt <= now_local:
        due_dt += timedelta(days=1)

    if applicable_days and frequency in [FREQUENCY_DAILY, FREQUENCY_WEEKLY]:
        day_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
        current_weekday = due_dt.weekday()
        target_days = [day_map[d] for d in applicable_days]

        days_ahead = 0
        while (current_weekday + days_ahead) % 7 not in target_days:
            days_ahead += 1
            if days_ahead > 7:
                break

        due_dt += timedelta(days=days_ahead)

    return due_dt.isoformat()

def create_chore(chore_def, kid_uuid_map):
    """Convert chore definition to storage format"""
    chore_id = str(uuid.uuid4())

    assigned_kids = []
    for kid_name in chore_def.get('assigned_kids', []):
        if kid_name in kid_uuid_map:
            assigned_kids.append(kid_uuid_map[kid_name])
        else:
            print(f"⚠️  Warning: Kid '{kid_name}' not found for chore '{chore_def['name']}'")

    frequency = chore_def.get('frequency', FREQUENCY_NONE)

    due_date = None
    if frequency != FREQUENCY_NONE:
        due_date = get_next_due_date(
            frequency,
            chore_def.get('due_time', '23:59'),
            chore_def.get('applicable_days', [])
        )

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
        "applicable_days": chore_def.get('applicable_days', []),
        "notify_on_claim": chore_def.get('notify_on_claim', True),
        "notify_on_approval": chore_def.get('notify_on_approval', True),
        "notify_on_disapproval": chore_def.get('notify_on_disapproval', True),
        "internal_id": chore_id
    }

    return chore_id, chore

def main():
    parser = argparse.ArgumentParser(description='Bulk import chores into KidsChores')
    parser.add_argument('storage_file', type=Path, help='KidsChores storage JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported')

    args = parser.parse_args()

    print("=" * 60)
    print("KidsChores Bulk Import Script (Standalone)")
    print("=" * 60)

    if not args.storage_file.exists():
        print(f"❌ Error: Storage file not found: {args.storage_file}")
        return 1

    if not args.dry_run:
        print("\n📁 Creating backup...")
        backup_file = backup_storage(args.storage_file)

    print("\n📖 Loading existing storage...")
    storage = load_storage(args.storage_file)

    print("📖 Loading chore definitions (embedded)...")
    definitions = CHORES_DATA

    kid_uuid_map = {}
    for kid_id, kid_data in storage.get('kids', {}).items():
        kid_name = kid_data.get('name')
        if kid_name:
            kid_uuid_map[kid_name] = kid_id

    print(f"   Found {len(kid_uuid_map)} existing kids: {', '.join(kid_uuid_map.keys())}")

    print(f"\n🔨 Processing chores...")
    chores_added = 0
    chores_skipped = 0

    existing_chore_names = {
        chore_data.get('name'): chore_id
        for chore_id, chore_data in storage.get('chores', {}).items()
    }

    new_chores = {}

    for chore_def in definitions.get('chores', []):
        chore_name = chore_def.get('name')

        if chore_name in existing_chore_names:
            print(f"   ⏭️  Skipping '{chore_name}' (already exists)")
            chores_skipped += 1
            continue

        chore_id, chore = create_chore(chore_def, kid_uuid_map)
        new_chores[chore_id] = chore

        print(f"   ✅ {'[DRY RUN] Would create' if args.dry_run else 'Created'} '{chore_name}' (ID: {chore_id[:8]}...)")
        chores_added += 1

    if chores_added > 0 and not args.dry_run:
        print(f"\n💾 Saving {chores_added} new chores...")
        if 'chores' not in storage:
            storage['chores'] = {}
        storage['chores'].update(new_chores)
        save_storage(args.storage_file, storage)

        print("\n" + "=" * 60)
        print(f"✅ SUCCESS! Added {chores_added} chores")
        if chores_skipped > 0:
            print(f"   (Skipped {chores_skipped} existing chores)")
        print("=" * 60)
        print("\n📋 Next steps:")
        print("   1. Restart Home Assistant: ha core restart")
        print("   2. Check Developer Tools > States for new entities")
        print("   3. If issues, restore backup:")
        print(f"      cp {backup_file} {args.storage_file}")
    elif args.dry_run:
        print("\n" + "=" * 60)
        print(f"🔍 DRY RUN: Would add {chores_added} chores")
        if chores_skipped > 0:
            print(f"   (Would skip {chores_skipped} existing chores)")
        print("=" * 60)
        print("\nRun without --dry-run to actually import")
    else:
        print("\n⚠️  No new chores to add")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
