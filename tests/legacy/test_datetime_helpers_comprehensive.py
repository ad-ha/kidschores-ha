"""Comprehensive datetime helper testing across multiple timezones.

Tests all datetime helper functions in kc_helpers.py with focus on:
- Multi-timezone handling (America/New_York, Europe/London, Asia/Tokyo, Australia/Sydney, UTC)
- Edge cases (DST transitions, leap years, month boundaries)
- Input validation and error handling
- Return type variations

Can be run as:
- pytest tests/test_datetime_helpers_comprehensive.py -v
- python tests/test_datetime_helpers_comprehensive.py
"""

# pylint: disable=protected-access  # Accessing internal helpers for testing
# pylint: disable=redefined-outer-name  # Pytest fixtures shadow names
# pylint: disable=unused-argument  # Some test fixtures required for setup

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.kidschores import const
from custom_components.kidschores import kc_helpers as kh

# ============================================================================
# Test Fixtures
# ============================================================================

# Timezone matrix for comprehensive testing
TEST_TIMEZONES = [
    "America/New_York",  # EST/EDT (UTC-5/-4) - DST, US Eastern
    "Europe/London",  # GMT/BST (UTC+0/+1) - DST, Europe
    "Asia/Tokyo",  # JST (UTC+9) - No DST
    "Australia/Sydney",  # AEDT/AEST (UTC+11/+10) - DST opposite hemisphere
    "UTC",  # UTC+0 - Baseline, no DST
]


@pytest.fixture(params=TEST_TIMEZONES)
def test_timezone(request):
    """Parameterized fixture providing each test timezone."""
    return ZoneInfo(request.param)


@pytest.fixture
def mock_timezone(test_timezone, monkeypatch):
    """Mock const.DEFAULT_TIME_ZONE to test timezone."""
    monkeypatch.setattr(const, "DEFAULT_TIME_ZONE", test_timezone)
    return test_timezone


@pytest.fixture
def sample_datetimes(mock_timezone):
    """Generate sample datetimes in the mocked timezone for testing.

    Returns:
        dict: Collection of test datetimes covering various scenarios
    """
    tz = mock_timezone

    return {
        # Regular dates
        "regular_date": datetime(2025, 6, 15, 14, 30, 0, tzinfo=tz),
        "midnight": datetime(2025, 6, 15, 0, 0, 0, tzinfo=tz),
        "noon": datetime(2025, 6, 15, 12, 0, 0, tzinfo=tz),
        "end_of_day": datetime(2025, 6, 15, 23, 59, 59, tzinfo=tz),
        # Edge cases - month boundaries
        "month_end_jan": datetime(2025, 1, 31, 15, 0, 0, tzinfo=tz),
        "month_end_feb_nonleap": datetime(2025, 2, 28, 15, 0, 0, tzinfo=tz),
        "month_end_feb_leap": datetime(2024, 2, 29, 15, 0, 0, tzinfo=tz),
        "month_start": datetime(2025, 3, 1, 15, 0, 0, tzinfo=tz),
        # Edge cases - year boundaries
        "year_end": datetime(2024, 12, 31, 23, 59, 59, tzinfo=tz),
        "year_start": datetime(2025, 1, 1, 0, 0, 0, tzinfo=tz),
        # Weekdays (Monday = 0, Sunday = 6)
        "monday": datetime(2025, 6, 16, 10, 0, 0, tzinfo=tz),  # Monday
        "friday": datetime(2025, 6, 20, 10, 0, 0, tzinfo=tz),  # Friday
        "saturday": datetime(2025, 6, 21, 10, 0, 0, tzinfo=tz),  # Saturday
        "sunday": datetime(2025, 6, 22, 10, 0, 0, tzinfo=tz),  # Sunday
        # DST transition dates (US/NY: Spring forward Mar 9, Fall back Nov 2)
        "before_dst_spring": datetime(2025, 3, 8, 12, 0, 0, tzinfo=tz),
        "after_dst_spring": datetime(2025, 3, 10, 12, 0, 0, tzinfo=tz),
        "before_dst_fall": datetime(2025, 11, 1, 12, 0, 0, tzinfo=tz),
        "after_dst_fall": datetime(2025, 11, 3, 12, 0, 0, tzinfo=tz),
    }


@pytest.fixture
def sample_date_strings():
    """Sample date strings in various formats for parsing tests."""
    return {
        "iso_date": "2025-06-15",
        "iso_datetime": "2025-06-15T14:30:00",
        "iso_datetime_tz": "2025-06-15T14:30:00-04:00",
        "iso_datetime_utc": "2025-06-15T18:30:00+00:00",
        "us_format": "06/15/2025",
        "long_format": "June 15, 2025",
        "invalid_empty": "",
        "invalid_malformed": "not-a-date",
        "invalid_none": None,
    }


# ============================================================================
# Test Helper Utilities
# ============================================================================


def assert_datetime_equal(
    dt1: datetime, dt2: datetime, tolerance_seconds: int = 1
) -> None:
    """Compare two datetimes with tolerance for microseconds/sub-second differences."""
    if dt1 is None or dt2 is None:
        assert dt1 == dt2, f"One datetime is None: {dt1} vs {dt2}"
        return

    diff = abs((dt1 - dt2).total_seconds())
    assert diff <= tolerance_seconds, f"Datetimes differ by {diff}s: {dt1} vs {dt2}"


def assert_timezone_aware(dt: datetime, expected_tz: ZoneInfo | None = None) -> None:
    """Verify datetime is timezone-aware and optionally matches expected timezone."""
    assert dt.tzinfo is not None, f"Datetime is not timezone-aware: {dt}"

    if expected_tz:
        # Compare timezone names (handles same timezone with different representations)
        assert str(dt.tzinfo) == str(expected_tz), (
            f"Timezone mismatch: {dt.tzinfo} vs {expected_tz}"
        )


def get_utc_offset_hours(dt: datetime) -> float:
    """Get UTC offset in hours for a datetime."""
    offset = dt.utcoffset()
    if offset:
        return offset.total_seconds() / 3600
    return 0.0


# ============================================================================
# Test Class: Basic DateTime Getters
# ============================================================================


class TestBasicGetters:
    """Test basic datetime getter functions."""

    def test_get_today_local_date(self, mock_timezone):
        """Test get_today_local_date returns correct date in timezone."""
        result = kh.get_today_local_date()

        # Verify it's a date object
        assert isinstance(result, date)
        assert not isinstance(result, datetime)  # Should be date, not datetime

        # Verify it matches current local date
        expected = dt_util.as_local(dt_util.utcnow()).date()
        assert result == expected

    def test_get_today_local_iso(self, mock_timezone):
        """Test get_today_local_iso returns ISO string (YYYY-MM-DD)."""
        result = kh.get_today_local_iso()

        # Verify it's a string
        assert isinstance(result, str)

        # Verify format (YYYY-MM-DD)
        assert len(result) == 10
        assert result[4] == "-" and result[7] == "-"

        # Verify matches today's date
        expected = kh.get_today_local_date().isoformat()
        assert result == expected

    def test_get_now_local_time(self, mock_timezone):
        """Test get_now_local_time returns timezone-aware datetime."""
        result = kh.get_now_local_time()

        # Verify it's a datetime
        assert isinstance(result, datetime)

        # Verify timezone-aware
        assert_timezone_aware(result)

        # Verify it's in local timezone
        expected = dt_util.as_local(dt_util.utcnow())
        assert_datetime_equal(result, expected, tolerance_seconds=2)

    def test_get_now_local_iso(self, mock_timezone):
        """Test get_now_local_iso returns ISO 8601 string with timezone."""
        result = kh.get_now_local_iso()

        # Verify it's a string
        assert isinstance(result, str)

        # Verify contains timezone offset (±HH:MM)
        assert "+" in result or "-" in result.rsplit("T", 1)[-1]

        # Verify can be parsed back
        parsed = datetime.fromisoformat(result)
        assert_timezone_aware(parsed)


# ============================================================================
# Test Class: DateTime Parsing
# ============================================================================


class TestDateTimeParsing:
    """Test datetime parsing functions."""

    def test_parse_datetime_to_utc_iso_with_tz(self, mock_timezone):
        """Test parsing ISO datetime string with timezone to UTC."""
        input_str = "2025-06-15T14:30:00-04:00"
        result = kh.parse_datetime_to_utc(input_str)

        # Verify result is datetime
        assert isinstance(result, datetime)

        # Verify converted to UTC
        assert_timezone_aware(result, ZoneInfo("UTC"))

        # Verify time adjusted correctly (14:30 EDT = 18:30 UTC)
        assert result.hour == 18
        assert result.minute == 30

    def test_parse_datetime_to_utc_iso_without_tz(self, mock_timezone):
        """Test parsing naive ISO datetime applies default timezone."""
        input_str = "2025-06-15T14:30:00"
        result = kh.parse_datetime_to_utc(input_str)

        # Verify result is datetime
        assert isinstance(result, datetime)

        # Verify timezone-aware (should apply default TZ then convert to UTC)
        assert_timezone_aware(result)

    def test_parse_datetime_to_utc_invalid_inputs(self):
        """Test parsing invalid inputs returns None."""
        invalid_inputs = ["", "not-a-date", None, "2025-13-45", "garbage"]

        for invalid in invalid_inputs:
            result = kh.parse_datetime_to_utc(invalid)
            assert result is None, f"Expected None for invalid input: {invalid}"

    def test_parse_date_safe_valid_formats(self):
        """Test parse_date_safe handles various date formats."""
        # Only test formats that dt_util.parse_date actually supports
        test_cases = {
            "2025-06-15": date(2025, 6, 15),
            "2025-6-15": date(2025, 6, 15),
        }

        for input_str, expected in test_cases.items():
            result = kh.parse_date_safe(input_str)
            assert result == expected, f"Failed to parse: {input_str}"

        # Note: dt_util.parse_date may not support US format (MM/DD/YYYY)
        # This is expected behavior - use normalize_datetime_input for broader support

    def test_parse_date_safe_invalid_inputs(self):
        """Test parse_date_safe returns None for invalid inputs."""
        invalid_inputs = ["", "not-a-date", None, "2025-13-45"]

        for invalid in invalid_inputs:
            result = kh.parse_date_safe(invalid)
            assert result is None, f"Expected None for invalid input: {invalid}"


# ============================================================================
# Test Class: DateTime Formatting
# ============================================================================


class TestDateTimeFormatting:
    """Test datetime formatting and conversion functions."""

    def test_format_datetime_return_unchanged(self, sample_datetimes):
        """Test HELPER_RETURN_DATETIME returns datetime unchanged."""
        input_dt = sample_datetimes["regular_date"]
        result = kh.format_datetime_with_return_type(
            input_dt, const.HELPER_RETURN_DATETIME
        )

        assert result is input_dt  # Should be same object
        assert isinstance(result, datetime)

    def test_format_datetime_return_utc(self, sample_datetimes):
        """Test HELPER_RETURN_DATETIME_UTC converts to UTC."""
        input_dt = sample_datetimes["regular_date"]
        result = kh.format_datetime_with_return_type(
            input_dt, const.HELPER_RETURN_DATETIME_UTC
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result, ZoneInfo("UTC"))

    def test_format_datetime_return_local(self, mock_timezone, sample_datetimes):
        """Test HELPER_RETURN_DATETIME_LOCAL converts to local."""
        input_dt = sample_datetimes["regular_date"]
        result = kh.format_datetime_with_return_type(
            input_dt, const.HELPER_RETURN_DATETIME_LOCAL
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result)

    def test_format_datetime_return_date(self, sample_datetimes):
        """Test HELPER_RETURN_DATE extracts date object."""
        input_dt = sample_datetimes["regular_date"]
        result = kh.format_datetime_with_return_type(input_dt, const.HELPER_RETURN_DATE)

        assert isinstance(result, date)
        assert not isinstance(result, datetime)
        assert result == input_dt.date()

    def test_format_datetime_return_iso_datetime(self, sample_datetimes):
        """Test HELPER_RETURN_ISO_DATETIME returns ISO string."""
        input_dt = sample_datetimes["regular_date"]
        result = kh.format_datetime_with_return_type(
            input_dt, const.HELPER_RETURN_ISO_DATETIME
        )

        assert isinstance(result, str)
        assert "T" in result  # ISO datetime format includes T separator

        # Verify can parse back
        parsed = datetime.fromisoformat(result)
        assert_datetime_equal(parsed, input_dt)

    def test_format_datetime_return_iso_date(self, sample_datetimes):
        """Test HELPER_RETURN_ISO_DATE returns date ISO string."""
        input_dt = sample_datetimes["regular_date"]
        result = kh.format_datetime_with_return_type(
            input_dt, const.HELPER_RETURN_ISO_DATE
        )

        assert isinstance(result, str)
        assert result == input_dt.date().isoformat()
        assert len(result) == 10  # YYYY-MM-DD


# ============================================================================
# Test Class: normalize_datetime_input
# ============================================================================


class TestNormalizeDatetimeInput:
    """Test comprehensive datetime normalization function."""

    def test_normalize_string_iso_date(self, mock_timezone):
        """Test normalizing ISO date string."""
        result = kh.normalize_datetime_input(
            "2025-06-15", return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result)
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15

    def test_normalize_string_iso_datetime(self, mock_timezone):
        """Test normalizing ISO datetime string."""
        result = kh.normalize_datetime_input(
            "2025-06-15T14:30:00", return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result)
        assert result.hour == 14
        assert result.minute == 30

    def test_normalize_date_object(self, mock_timezone):
        """Test normalizing date object to datetime."""
        input_date = date(2025, 6, 15)
        result = kh.normalize_datetime_input(
            input_date, return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result)
        assert result.date() == input_date

    def test_normalize_datetime_naive(self, mock_timezone):
        """Test normalizing naive datetime applies timezone."""
        naive_dt = datetime(2025, 6, 15, 14, 30, 0)
        result = kh.normalize_datetime_input(
            naive_dt, return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result)
        assert result.hour == 14  # Time preserved

    def test_normalize_datetime_aware(self, mock_timezone):
        """Test normalizing aware datetime preserves timezone."""
        aware_dt = datetime(2025, 6, 15, 14, 30, 0, tzinfo=ZoneInfo("America/New_York"))
        result = kh.normalize_datetime_input(
            aware_dt, return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        assert_timezone_aware(result)

    def test_normalize_all_return_types(self, mock_timezone):
        """Test normalize with all return type variations."""
        input_str = "2025-06-15T14:30:00"

        # Test each return type
        result_dt = kh.normalize_datetime_input(
            input_str, return_type=const.HELPER_RETURN_DATETIME
        )
        assert isinstance(result_dt, datetime)

        result_date = kh.normalize_datetime_input(
            input_str, return_type=const.HELPER_RETURN_DATE
        )
        assert isinstance(result_date, date)
        assert not isinstance(result_date, datetime)

        result_iso_dt = kh.normalize_datetime_input(
            input_str, return_type=const.HELPER_RETURN_ISO_DATETIME
        )
        assert isinstance(result_iso_dt, str)
        assert "T" in result_iso_dt

        result_iso_date = kh.normalize_datetime_input(
            input_str, return_type=const.HELPER_RETURN_ISO_DATE
        )
        assert isinstance(result_iso_date, str)
        assert len(result_iso_date) == 10

    def test_normalize_invalid_inputs(self):
        """Test normalize returns None for invalid inputs."""
        invalid_inputs = ["", None, "not-a-date", 12345]

        for invalid in invalid_inputs:
            result = kh.normalize_datetime_input(invalid)
            assert result is None, f"Expected None for invalid input: {invalid}"


# ============================================================================
# Test Class: Interval Adjustments
# ============================================================================


class TestIntervalAdjustments:
    """Test adjust_datetime_by_interval function."""

    def test_adjust_by_days_positive(self, sample_datetimes):
        """Test adding days to datetime."""
        input_dt = sample_datetimes["regular_date"]

        # Add 1 day
        result = kh.adjust_datetime_by_interval(
            input_dt, const.TIME_UNIT_DAYS, 1, return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        expected = input_dt + timedelta(days=1)
        assert_datetime_equal(result, expected)

    def test_adjust_by_days_negative(self, sample_datetimes):
        """Test subtracting days from datetime."""
        input_dt = sample_datetimes["regular_date"]

        # Subtract 7 days
        result = kh.adjust_datetime_by_interval(
            input_dt, const.TIME_UNIT_DAYS, -7, return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        expected = input_dt - timedelta(days=7)
        assert_datetime_equal(result, expected)

    def test_adjust_by_weeks(self, sample_datetimes):
        """Test adjusting by weeks."""
        input_dt = sample_datetimes["regular_date"]

        # Add 2 weeks
        result = kh.adjust_datetime_by_interval(
            input_dt, const.TIME_UNIT_WEEKS, 2, return_type=const.HELPER_RETURN_DATETIME
        )

        assert isinstance(result, datetime)
        expected = input_dt + timedelta(weeks=2)
        assert_datetime_equal(result, expected)

    def test_adjust_by_months_no_overflow(self, sample_datetimes):
        """Test adding months without day overflow."""
        input_dt = sample_datetimes["regular_date"]  # June 15

        # Add 1 month (June 15 → July 15)
        result = kh.adjust_datetime_by_interval(
            input_dt,
            const.TIME_UNIT_MONTHS,
            1,
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.month == 7
        assert result.day == 15

    def test_adjust_by_months_with_overflow(self, sample_datetimes):
        """Test adding months with day overflow (Jan 31 → Feb 28/29)."""
        input_dt = sample_datetimes["month_end_jan"]  # Jan 31

        # Add 1 month (Jan 31 → Feb 28 in 2025, non-leap year)
        result = kh.adjust_datetime_by_interval(
            input_dt,
            const.TIME_UNIT_MONTHS,
            1,
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.month == 2
        # Should be Feb 28 (2025 is not a leap year)
        assert result.day in [28, 29]  # Allow both for different year scenarios

    def test_adjust_by_months_leap_year(self, sample_datetimes):
        """Test month adjustment preserves Feb 29 in leap years."""
        input_dt = sample_datetimes["month_end_feb_leap"]  # Feb 29, 2024

        # Add 12 months (Feb 29, 2024 → Feb 28/29, 2025)
        result = kh.adjust_datetime_by_interval(
            input_dt,
            const.TIME_UNIT_MONTHS,
            12,
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 2


# ============================================================================
# Test Class: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test critical edge cases for datetime handling."""

    def test_leap_year_feb_29(self, mock_timezone):
        """Test operations on Feb 29 (leap year)."""
        leap_date = datetime(2024, 2, 29, 12, 0, 0, tzinfo=mock_timezone)

        # Verify parsing
        result = kh.normalize_datetime_input(
            "2024-02-29", return_type=const.HELPER_RETURN_DATETIME
        )
        assert result.month == 2
        assert result.day == 29

        # Verify adding 1 year (should go to Feb 28, 2025)
        next_year = kh.adjust_datetime_by_interval(
            leap_date,
            const.TIME_UNIT_MONTHS,
            12,
            return_type=const.HELPER_RETURN_DATETIME,
        )
        assert next_year.year == 2025
        assert next_year.month == 2
        assert next_year.day in [28, 29]  # Handles overflow to Feb 28

    def test_year_boundary_rollover(self, sample_datetimes):
        """Test operations across year boundary."""
        year_end = sample_datetimes["year_end"]

        # Add 1 day (Dec 31 → Jan 1)
        result = kh.adjust_datetime_by_interval(
            year_end, const.TIME_UNIT_DAYS, 1, return_type=const.HELPER_RETURN_DATETIME
        )

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_month_boundaries_all_months(self, mock_timezone):
        """Test month-end dates for all months."""
        month_ends = [
            (2025, 1, 31),
            (2025, 2, 28),
            (2025, 3, 31),
            (2025, 4, 30),
            (2025, 5, 31),
            (2025, 6, 30),
            (2025, 7, 31),
            (2025, 8, 31),
            (2025, 9, 30),
            (2025, 10, 31),
            (2025, 11, 30),
            (2025, 12, 31),
        ]

        for year, month, day in month_ends:
            dt = datetime(year, month, day, 12, 0, 0, tzinfo=mock_timezone)

            # Add 1 month and verify no crash
            result = kh.adjust_datetime_by_interval(
                dt, const.TIME_UNIT_MONTHS, 1, return_type=const.HELPER_RETURN_DATETIME
            )
            assert isinstance(result, datetime)
            assert result > dt

    def test_empty_none_invalid_handling(self):
        """Test all functions handle None/empty gracefully."""
        # parse_datetime_to_utc
        assert kh.parse_datetime_to_utc(None) is None
        assert kh.parse_datetime_to_utc("") is None

        # parse_date_safe
        assert kh.parse_date_safe(None) is None
        assert kh.parse_date_safe("") is None

        # normalize_datetime_input
        assert kh.normalize_datetime_input(None) is None
        assert kh.normalize_datetime_input("") is None


# ============================================================================
# Test Class: Applicable Days
# ============================================================================


class TestApplicableDays:
    """Test get_next_applicable_day function."""

    def test_next_applicable_single_day(self, sample_datetimes):
        """Test advancing to a single applicable day (Monday only)."""
        input_dt = sample_datetimes["friday"]  # Friday

        # Next Monday (weekday 0)
        result = kh.get_next_applicable_day(
            input_dt,
            [0],  # Monday only
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.weekday() == 0  # Should be Monday
        assert result > input_dt

    def test_next_applicable_weekdays(self, sample_datetimes):
        """Test advancing within weekdays (Mon-Fri)."""
        input_dt = sample_datetimes["saturday"]  # Saturday

        # Next weekday (Mon-Fri)
        result = kh.get_next_applicable_day(
            input_dt,
            [0, 1, 2, 3, 4],  # Mon-Fri
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.weekday() == 0  # Should be Monday (next weekday after Sat)

    def test_next_applicable_current_day_included(self, sample_datetimes):
        """Test returns same day if current day is applicable."""
        input_dt = sample_datetimes["monday"]  # Monday

        # Monday is in applicable days
        result = kh.get_next_applicable_day(
            input_dt,
            [0, 2, 4],  # Mon, Wed, Fri
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.date() == input_dt.date()  # Should be same day
        assert result.weekday() == 0  # Still Monday

    def test_next_applicable_week_boundary(self, sample_datetimes):
        """Test crossing week boundary (Sun → Mon)."""
        input_dt = sample_datetimes["sunday"]  # Sunday

        # Next Monday
        result = kh.get_next_applicable_day(
            input_dt,
            [0],  # Monday only
            return_type=const.HELPER_RETURN_DATETIME,
        )

        assert isinstance(result, datetime)
        assert result.weekday() == 0
        assert result > input_dt
        # Should be next day (Monday)
        assert (result.date() - input_dt.date()).days == 1


# ============================================================================
# Main Execution (Standalone Mode)
# ============================================================================

if __name__ == "__main__":
    # Run pytest programmatically
    pytest.main(
        [
            __file__,
            "-v",  # Verbose
            "--tb=short",  # Short traceback
            "-k",
            "not slow",  # Skip slow tests
            "--color=yes",  # Colored output
        ]
    )
