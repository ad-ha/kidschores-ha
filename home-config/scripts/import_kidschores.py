#!/usr/bin/env python3
"""
KidsChores Bulk Import Script
Reads chore definitions from YAML and injects into storage JSON

Usage:
    python3 import_kidschores.py <import_file.yaml> <storage_file.json>

Example:
    python3 import_kidschores.py ../config/chores_bella_lilly.yaml ~/.homeassistant/.storage/kidschores_data
"""

import json
import yaml
import uuid
import shutil
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Default values (from const.py)
DEFAULT_POINTS = 5
DEFAULT_ICON = "mdi:star-outline"
FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_BIWEEKLY = "biweekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_NONE = "none"
CHORE_STATE_PENDING = "pending"

def backup_storage(storage_file):
    """Create timestamped backup of storage file"""
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

def load_chore_definitions(import_file):
    """Load chore definitions from YAML"""
    with open(import_file, 'r') as f:
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
    parser = argparse.ArgumentParser(
        description='Bulk import chores into KidsChores Home Assistant integration'
    )
    parser.add_argument('import_file', type=Path, help='YAML file with chore definitions')
    parser.add_argument('storage_file', type=Path, help='KidsChores storage JSON file')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation (not recommended)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without modifying storage')

    args = parser.parse_args()

    print("=" * 60)
    print("KidsChores Bulk Import Script")
    print("=" * 60)

    # Validate files exist
    if not args.storage_file.exists():
        print(f"❌ Error: Storage file not found: {args.storage_file}")
        print("   Make sure KidsChores integration is installed and configured")
        return 1

    if not args.import_file.exists():
        print(f"❌ Error: Import file not found: {args.import_file}")
        print(f"   Create {args.import_file} with your chore definitions")
        return 1

    # Backup
    if not args.skip_backup and not args.dry_run:
        print("\n📁 Creating backup...")
        backup_file = backup_storage(args.storage_file)

    # Load data
    print("\n📖 Loading existing storage...")
    storage = load_storage(args.storage_file)

    print("📖 Loading chore definitions...")
    definitions = load_chore_definitions(args.import_file)

    # Build kid name -> UUID map
    kid_uuid_map = {}
    for kid_id, kid_data in storage.get('kids', {}).items():
        kid_name = kid_data.get('name')
        if kid_name:
            kid_uuid_map[kid_name] = kid_id

    print(f"   Found {len(kid_uuid_map)} existing kids: {', '.join(kid_uuid_map.keys())}")

    # Process chores
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

        # Check if chore already exists
        if chore_name in existing_chore_names:
            print(f"   ⏭️  Skipping '{chore_name}' (already exists)")
            chores_skipped += 1
            continue

        # Create chore
        chore_id, chore = create_chore(chore_def, kid_uuid_map)
        new_chores[chore_id] = chore

        print(f"   ✅ {'[DRY RUN] Would create' if args.dry_run else 'Created'} '{chore_name}' (ID: {chore_id[:8]}...)")
        chores_added += 1

    # Save
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
        print("   1. Restart Home Assistant")
        print("   2. Check Developer Tools > States for new sensor entities")
        print("   3. If issues, restore backup:")
        print(f"      cp {backup_file} {args.storage_file}")
        print("      (then restart HA)")
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
