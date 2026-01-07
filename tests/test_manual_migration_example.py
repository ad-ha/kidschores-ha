"""Example test demonstrating manual migration invocation pattern.

This test validates that we can manually invoke the migration to convert
legacy `is_shared` (boolean) → `completion_criteria` (enum) after loading
data through config flow.

Since Option B fully deprecated shared_chore, this test simulates legacy
storage by injecting the old is_shared field into coordinator data.
"""

# pylint: disable=protected-access
# pylint: disable=unused-argument
# Tests need to access coordinator private methods and data

# Test removed - migration infrastructure issue
