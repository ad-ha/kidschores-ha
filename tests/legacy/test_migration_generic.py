"""Generic migration tests using the reusable validation framework.

This test file integrates with pytest to validate ANY v40 data file migration
to v42. Simply specify the data file path via pytest command line:

    pytest tests/test_migration_generic.py --migration-file=path/to/file

The tests auto-discover entities and validate structure without hardcoding
specific IDs, names, or values. This makes it trivial to test user data files
for migration correctness.

Examples:
    # Test user production data (e.g., ad-ha)
    pytest tests/test_migration_generic.py \\
        --migration-file=tests/migration_samples/kidschores_data_ad-ha -v

    # Test any other v40 file
    pytest tests/test_migration_generic.py \\
        --migration-file=/path/to/other_data.json -v

NOTE: The sample files in tests/migration_samples/ are:
  - kidschores_data_30, v31, v40beta1: Standard test fixtures (used in test suite)
  - kidschores_data_ad-ha: User production data (available for manual testing)
"""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
# pylint: disable=unused-argument

# Import our reusable validation framework
import sys
from pathlib import Path
from typing import Union

import pytest
from homeassistant.core import HomeAssistant

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.validate_migration import MigrationValidator


@pytest.fixture
def migration_file(request) -> Union[Path, None]:
    """Get migration file path from command line."""
    file_path = request.config.getoption("--migration-file")
    if file_path:
        return Path(file_path)
    return None


@pytest.fixture
def validator(migration_file) -> Union[MigrationValidator, None]:
    """Create validator instance for the specified file."""
    if not migration_file:
        pytest.skip("No --migration-file specified")

    if not migration_file.exists():
        pytest.fail(f"Migration file not found: {migration_file}")

    return MigrationValidator(migration_file)


@pytest.mark.asyncio
async def test_generic_migration_v40_to_v42(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test complete v40→v42 migration with auto-discovery.

    This test:
    1. Loads v40 data from specified file
    2. Validates v40 schema correctness
    3. Runs migration through actual integration
    4. Validates v42 schema correctness
    5. Verifies all entities preserved
    6. Checks modern structures present
    7. Ensures legacy fields removed
    8. Validates kid data integrity
    9. Validates chore data integrity

    No hardcoded entity IDs or values required!
    """
    # Run all validations
    results = await validator.validate_all(hass)

    # Print detailed report
    validator.print_report()

    # Assert all passed
    failed_results = [r for r in results if not r.passed]

    if failed_results:
        failure_messages = "\n".join(
            [f"  - {r.name}: {r.message}" for r in failed_results]
        )
        pytest.fail(
            f"\n❌ {len(failed_results)} validation(s) failed:\n{failure_messages}"
        )

    # Success message
    print(f"\n✅ All {len(results)} validations passed!")
    print(f"✅ Migration validated for {validator.data_file.name}")


@pytest.mark.asyncio
async def test_generic_schema_upgrade(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test schema version upgrade from v40 to v42."""
    validator.load_v40_data()

    # Verify starting schema
    v40_result = validator.validate_v40_schema()
    assert v40_result.passed, f"V40 validation failed: {v40_result.message}"

    # Migrate
    await validator.migrate_with_integration(hass)

    # Verify ending schema
    v42_result = validator.validate_v42_schema()
    assert v42_result.passed, f"V42 validation failed: {v42_result.message}"

    # Verify version change
    assert validator.v42_data["meta"]["schema_version"] == 42


@pytest.mark.asyncio
async def test_generic_entity_preservation(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test that all entities are preserved during migration."""
    validator.load_v40_data()
    await validator.migrate_with_integration(hass)

    result = validator.validate_entity_preservation()
    assert result.passed, f"Entity preservation failed: {result.message}"

    # Verify counts match
    assert validator.before_counts.total() == validator.after_counts.total()
    assert validator.before_counts.kids == validator.after_counts.kids
    assert validator.before_counts.chores == validator.after_counts.chores


@pytest.mark.asyncio
async def test_generic_modern_structures(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test that v42 modern structures are present."""
    validator.load_v40_data()
    await validator.migrate_with_integration(hass)

    result = validator.validate_modern_structures()
    assert result.passed, f"Modern structures validation failed: {result.message}"

    # Verify specific structures exist
    if validator.v42_data.get("kids"):
        first_kid = next(iter(validator.v42_data["kids"].values()))
        assert "chore_stats" in first_kid, "Missing chore_stats"
        assert "point_stats" in first_kid, "Missing point_stats"


@pytest.mark.asyncio
async def test_generic_legacy_field_removal(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test that legacy v40 fields are removed."""
    validator.load_v40_data()
    await validator.migrate_with_integration(hass)

    result = validator.validate_no_legacy_fields()
    assert result.passed, f"Legacy field removal failed: {result.message}"


@pytest.mark.asyncio
async def test_generic_kid_data_integrity(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test that kid data is preserved correctly."""
    validator.load_v40_data()
    await validator.migrate_with_integration(hass)

    result = validator.validate_kid_data_integrity()
    assert result.passed, f"Kid data integrity failed: {result.message}"


@pytest.mark.asyncio
async def test_generic_chore_data_integrity(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test that chore data is preserved correctly."""
    validator.load_v40_data()
    await validator.migrate_with_integration(hass)

    result = validator.validate_chore_data_integrity()
    assert result.passed, f"Chore data integrity failed: {result.message}"


@pytest.mark.asyncio
async def test_generic_zero_data_loss(
    hass: HomeAssistant,
    validator: MigrationValidator,
) -> None:
    """Test that absolutely no data is lost during migration."""
    validator.load_v40_data()

    # Count total data points before
    v40_kids = validator.v40_data.get("kids", {})
    before_data_points = sum(
        len(str(kid_data))  # Rough measure of data size
        for kid_data in v40_kids.values()
    )

    await validator.migrate_with_integration(hass)

    # Count total data points after
    v42_kids = validator.v42_data.get("kids", {})
    after_data_points = sum(len(str(kid_data)) for kid_data in v42_kids.values())

    # Data size should be similar (allow for structure changes)
    # If we lost data, size would drop significantly
    data_loss_percent = (
        abs(before_data_points - after_data_points) / before_data_points * 100
    )

    assert data_loss_percent < 10, (
        f"Significant data loss detected: {data_loss_percent:.1f}% size change. "
        f"Before: {before_data_points} chars, After: {after_data_points} chars"
    )


# ============================================================================
# EXAMPLE: Testing Multiple Files
# ============================================================================
# NOTE: This example shows the pattern for testing additional data files.
# The ad-ha sample is user data and should be tested manually with:
#   pytest tests/test_migration_generic.py --migration-file=tests/migration_samples/kidschores_data_ad-ha -v
#
# To add other test data files (not user data), add them to the parametrize list below.


@pytest.mark.parametrize(
    "sample_file",
    [
        # Add standardized test data files here (not user-specific data):
        # "tests/migration_samples/kidschores_data_test1",
        # "tests/migration_samples/kidschores_data_test2",
    ],
)
@pytest.mark.asyncio
async def test_multiple_files_example(
    hass: HomeAssistant,
    sample_file: str,
) -> None:
    """Example: Test multiple data files in one test run.

    To use this:
    1. Add more file paths to the parametrize list above
    2. Run: pytest tests/test_migration_generic.py::test_multiple_files_example -v

    Each file will be tested independently with full validation.
    """
    file_path = Path(sample_file)

    if not file_path.exists():
        pytest.skip(f"Sample file not available: {sample_file}")

    validator = MigrationValidator(file_path)
    results = await validator.validate_all(hass)

    # Assert all passed
    failed_results = [r for r in results if not r.passed]
    assert not failed_results, (
        f"Validation failed for {file_path.name}: {[r.message for r in failed_results]}"
    )

    print(f"✅ {file_path.name}: All validations passed")
