# File: coordinator.py
"""Coordinator for the KidsChores integration.

Handles data synchronization, chore claiming and approval, badge tracking,
reward redemption, penalty application, and recurring chore handling.
Manages entities primarily using internal_id for consistency.
"""

import asyncio
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Optional

from homeassistant.auth.models import User
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh
from .notification_helper import async_send_notification
from .storage_manager import KidsChoresStorageManager


class KidsChoresDataCoordinator(DataUpdateCoordinator):
    """Coordinator for KidsChores integration.

    Manages data primarily using internal_id for entities.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        storage_manager: KidsChoresStorageManager,
    ):
        """Initialize the KidsChoresDataCoordinator."""
        update_interval_minutes = config_entry.options.get(
            const.CONF_UPDATE_INTERVAL, const.DEFAULT_UPDATE_INTERVAL
        )

        super().__init__(
            hass,
            const.LOGGER,
            name=f"{const.DOMAIN}{const.COORDINATOR_SUFFIX}",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.config_entry = config_entry
        self.storage_manager = storage_manager
        self._data: dict[str, Any] = {}

    # -------------------------------------------------------------------------------------
    # Migrate Data and Converters
    # -------------------------------------------------------------------------------------

    def _migrate_datetime(self, dt_str: str) -> str:
        """Convert a datetime string to a UTC-aware ISO string."""
        if not isinstance(dt_str, str):
            return dt_str

        try:
            dt_obj_utc = kh.parse_datetime_to_utc(dt_str)
            if dt_obj_utc:
                return dt_obj_utc.isoformat()
            else:
                raise ValueError("Parsed datetime is None")
        except Exception as err:
            const.LOGGER.warning(
                "WARNING: Migrate DateTime - Error migrating datetime '%s': %s",
                dt_str,
                err,
            )
            return dt_str

    def _migrate_stored_datetimes(self):
        """Walk through stored data and convert known datetime fields to UTC-aware ISO strings."""
        # For each chore, migrate due_date, last_completed, and last_claimed
        for chore_info in self._data.get(const.DATA_CHORES, {}).values():
            if chore_info.get(const.DATA_CHORE_DUE_DATE):
                chore_info[const.DATA_CHORE_DUE_DATE] = self._migrate_datetime(
                    chore_info[const.DATA_CHORE_DUE_DATE]
                )
            if chore_info.get(const.DATA_CHORE_LAST_COMPLETED):
                chore_info[const.DATA_CHORE_LAST_COMPLETED] = self._migrate_datetime(
                    chore_info[const.DATA_CHORE_LAST_COMPLETED]
                )
            if chore_info.get(const.DATA_CHORE_LAST_CLAIMED):
                chore_info[const.DATA_CHORE_LAST_CLAIMED] = self._migrate_datetime(
                    chore_info[const.DATA_CHORE_LAST_CLAIMED]
                )
        # Also, migrate timestamps in pending approvals
        for approval in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, []):
            if approval.get(const.DATA_CHORE_TIMESTAMP):
                approval[const.DATA_CHORE_TIMESTAMP] = self._migrate_datetime(
                    approval[const.DATA_CHORE_TIMESTAMP]
                )
        for approval in self._data.get(const.DATA_PENDING_REWARD_APPROVALS, []):
            if approval.get(const.DATA_CHORE_TIMESTAMP):
                approval[const.DATA_CHORE_TIMESTAMP] = self._migrate_datetime(
                    approval[const.DATA_CHORE_TIMESTAMP]
                )

        # Migrate datetime on Challenges
        for challenge_info in self._data.get(const.DATA_CHALLENGES, {}).values():
            start_date = challenge_info.get(const.DATA_CHALLENGE_START_DATE)
            if not isinstance(start_date, str) or not start_date.strip():
                challenge_info[const.DATA_CHALLENGE_START_DATE] = None
            else:
                challenge_info[const.DATA_CHALLENGE_START_DATE] = (
                    self._migrate_datetime(start_date)
                )

            end_date = challenge_info.get(const.DATA_CHALLENGE_END_DATE)
            if not isinstance(end_date, str) or not end_date.strip():
                challenge_info[const.DATA_CHALLENGE_END_DATE] = None
            else:
                challenge_info[const.DATA_CHALLENGE_END_DATE] = self._migrate_datetime(
                    end_date
                )

    def _migrate_chore_data(self):
        """Migrate each chore's data to include new fields if missing."""
        chores = self._data.get(const.DATA_CHORES, {})
        for chore_info in chores.values():
            chore_info.setdefault(
                const.CONF_APPLICABLE_DAYS, const.DEFAULT_APPLICABLE_DAYS
            )
            chore_info.setdefault(
                const.CONF_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
            )
            chore_info.setdefault(
                const.CONF_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
            )
            chore_info.setdefault(
                const.CONF_NOTIFY_ON_DISAPPROVAL, const.DEFAULT_NOTIFY_ON_DISAPPROVAL
            )
        const.LOGGER.info("INFO: Chore data migration complete.")

    def _migrate_legacy_kid_chore_data_and_streaks(self):
        """Migrate legacy streak and stats data to the new kid chores structure (period-based).

        This function will automatically run through all kids and all assigned chores.
        Data that only needs to be migrated once per kid is handled separately from per-chore data.
        """
        from datetime import datetime

        for kid_id, kid_info in self.kids_data.items():
            # --- Per-kid migration (run once per kid) ---
            # Only migrate these once per kid, not per chore
            chore_stats = kid_info.setdefault(const.DATA_KID_CHORE_STATS, {})
            legacy_streaks = kid_info.get(const.DATA_KID_CHORE_STREAKS_LEGACY, {})
            legacy_max = 0
            last_longest_streak_date = None

            # Find the max streak and last date across all chores for this kid
            for chore_id, legacy_streak in legacy_streaks.items():
                max_streak = legacy_streak.get(const.DATA_KID_MAX_STREAK, 0)
                if max_streak > legacy_max:
                    legacy_max = max_streak
                    last_longest_streak_date = legacy_streak.get(
                        const.DATA_KID_LAST_STREAK_DATE
                    )

            if legacy_max > chore_stats.get(
                const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME, 0
            ):
                chore_stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME] = (
                    legacy_max
                )
                # Store the date on any one chore (will be set per-chore below as well)
                if last_longest_streak_date:
                    for chore_data in kid_info.get(
                        const.DATA_KID_CHORE_DATA, {}
                    ).values():
                        chore_data[
                            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME
                        ] = last_longest_streak_date

            # Migrate all-time and yearly completed counts from legacy (once per kid)
            chore_stats[const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME] = kid_info.get(
                const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, 0
            )
            chore_stats[const.DATA_KID_CHORE_STATS_APPROVED_YEAR] = kid_info.get(
                const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, 0
            )

            # Migrate all-time claimed count from legacy (use max of any chore's claims or completed_chores_total)
            all_claims = [
                kid_info.get(const.DATA_KID_CHORE_CLAIMS_LEGACY, {}).get(chore_id, 0)
                for chore_id in self.chores_data.keys()
            ]
            chore_stats[const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME] = max(
                max(all_claims, default=0),
                kid_info.get(const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, 0),
            )

            # --- Per-chore migration (run for each assigned chore) ---
            for chore_id, chore_info in self.chores_data.items():
                assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
                if assigned_kids and kid_id not in assigned_kids:
                    continue

                # Ensure new structure exists
                if const.DATA_KID_CHORE_DATA not in kid_info:
                    kid_info[const.DATA_KID_CHORE_DATA] = {}

                if chore_id not in kid_info[const.DATA_KID_CHORE_DATA]:
                    chore_name = chore_info.get(const.DATA_CHORE_NAME, chore_id)
                    kid_info[const.DATA_KID_CHORE_DATA][chore_id] = {
                        const.DATA_KID_CHORE_DATA_NAME: chore_name,
                        const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
                        const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
                        const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
                        const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
                        const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
                        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
                        const.DATA_KID_CHORE_DATA_PERIODS: {
                            const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                            const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                            const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                            const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                            const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
                        },
                        const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
                    }

                kid_chore_data = kid_info[const.DATA_KID_CHORE_DATA][chore_id]
                periods = kid_chore_data[const.DATA_KID_CHORE_DATA_PERIODS]

                # --- Migrate legacy current streaks for this chore ---
                legacy_streak = legacy_streaks.get(chore_id, {})
                last_date = legacy_streak.get(const.DATA_KID_LAST_STREAK_DATE)
                if last_date:
                    # Daily
                    daily_data = periods[
                        const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                    ].setdefault(
                        last_date,
                        {
                            const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                            const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                            const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                            const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                            const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                        },
                    )
                    daily_data[const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK] = (
                        legacy_streak.get(const.DATA_KID_CURRENT_STREAK, 0)
                    )

                for period_key, period_fmt in [
                    (const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, "%Y-W%V"),
                    (const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, "%Y-%m"),
                    (const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, "%Y"),
                    (const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME, const.PERIOD_ALL_TIME),
                ]:
                    if last_date:
                        try:
                            dt = datetime.fromisoformat(last_date)
                            period_id = dt.strftime(period_fmt)
                        except Exception:
                            period_id = None
                    else:
                        period_id = None

                    if period_id:
                        period_data_dict = periods[period_key].setdefault(
                            period_id,
                            {
                                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                                const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                                const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                            },
                        )
                        period_data_dict[
                            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK
                        ] = legacy_streak.get(const.DATA_KID_MAX_STREAK, 0)

                # --- Migrate claim/approval counts for this chore ---
                claims = kid_info.get(const.DATA_KID_CHORE_CLAIMS_LEGACY, {}).get(
                    chore_id, 0
                )
                approvals = kid_info.get(const.DATA_KID_CHORE_APPROVALS_LEGACY, {}).get(
                    chore_id, 0
                )

                # --- Migrate period completion and claim counts for this chore ---
                now_local = kh.get_now_local_time()
                today_iso = now_local.date().isoformat()
                week_iso = now_local.strftime("%Y-W%V")
                month_iso = now_local.strftime("%Y-%m")
                year_iso = now_local.strftime("%Y")

                # Daily
                daily_data = periods[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(
                    today_iso,
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                        const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                    },
                )
                # No per chore data available for daily period

                # Weekly
                weekly_stats = periods[
                    const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY
                ].setdefault(
                    week_iso,
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                        const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                    },
                )
                # No per chore data available for weekly period

                # Monthly
                monthly_stats = periods[
                    const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY
                ].setdefault(
                    month_iso,
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                        const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                    },
                )
                # No per chore data available for monthly period

                # Yearly
                yearly_stats = periods[
                    const.DATA_KID_CHORE_DATA_PERIODS_YEARLY
                ].setdefault(
                    year_iso,
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                        const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                    },
                )
                # Mapping legacy totals to yearly stats
                yearly_stats[const.DATA_KID_CHORE_DATA_PERIOD_APPROVED] = approvals
                yearly_stats[const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED] = claims

                # --- Migrate legacy all-time stats into the new all_time period for this chore ---
                all_time_data = periods[
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME
                ].setdefault(
                    const.PERIOD_ALL_TIME,
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
                        const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
                    },
                )

                # Map legacy totals to all time data
                all_time_data[const.DATA_KID_CHORE_DATA_PERIOD_APPROVED] = approvals
                all_time_data[const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED] = claims

        # Optionally, remove legacy data after migration
        # for kid_info in self.kids_data.values():
        #     kid_info.pop(const.DATA_KID_CHORE_STREAKS_LEGACY, None)

    def _migrate_badges(self):
        """Migrate legacy badges into cumulative badges and ensure all required fields exist.

        For badges whose threshold_type is set to the legacy value (e.g. BADGE_THRESHOLD_TYPE_CHORE_COUNT),
        compute the new threshold as the legacy count multiplied by the average default points across all chores.
        Also, set reset fields to empty and disable periodic resets.
        For any badge, ensure all required fields and nested structures exist using constants.
        """
        badges_dict = self._data.get(const.DATA_BADGES, {})
        chores_dict = self._data.get(const.DATA_CHORES, {})

        # Calculate the average default points over all chores.
        total_points = 0.0
        count = 0
        for chore_info in chores_dict.values():
            try:
                default_points = float(
                    chore_info.get(
                        const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
                    )
                )
                total_points += default_points
                count += 1
            except Exception:
                continue

        # If there are no chores, we fallback to DEFAULT_POINTS.
        average_points = (total_points / count) if count > 0 else const.DEFAULT_POINTS

        # Process each badge.
        for badge_id, badge_info in badges_dict.items():
            # --- Legacy migration logic ---
            if badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE:
                # If the badge is already moved to cumulative, skip legacy migration.
                pass
            else:
                # Check if the badge uses the legacy "chore_count" threshold type if so estimate points and assign.
                if (
                    badge_info.get(const.DATA_BADGE_THRESHOLD_TYPE_LEGACY)
                    == const.BADGE_THRESHOLD_TYPE_CHORE_COUNT
                ):
                    old_threshold = badge_info.get(
                        const.DATA_BADGE_THRESHOLD_VALUE_LEGACY,
                        const.DEFAULT_BADGE_THRESHOLD_VALUE_LEGACY,
                    )
                    try:
                        # Multiply the legacy count by the average default points.
                        new_threshold = float(old_threshold) * average_points
                    except Exception:
                        new_threshold = old_threshold

                    # Force to points type and set new value
                    badge_info[const.DATA_BADGE_THRESHOLD_TYPE_LEGACY] = (
                        const.CONF_POINTS
                    )
                    badge_info[const.DATA_BADGE_THRESHOLD_VALUE_LEGACY] = new_threshold

                    # Also update the target structure immediately
                    badge_info.setdefault(const.DATA_BADGE_TARGET, {})
                    badge_info[const.DATA_BADGE_TARGET][
                        const.DATA_BADGE_TARGET_TYPE
                    ] = const.CONF_POINTS
                    badge_info[const.DATA_BADGE_TARGET][
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE
                    ] = new_threshold

                    const.LOGGER.info(
                        "INFO: Legacy Chore Count Badge '%s' migrated: Old threshold %s -> New threshold %s (average_points=%.2f)",
                        badge_info.get(const.DATA_BADGE_NAME),
                        old_threshold,
                        new_threshold,
                        average_points,
                    )

                    # Remove legacy fields now so they can't overwrite later
                    badge_info.pop(const.DATA_BADGE_THRESHOLD_TYPE_LEGACY, None)
                    badge_info.pop(const.DATA_BADGE_THRESHOLD_VALUE_LEGACY, None)

                # Set badge type to cumulative if not already set
                if const.DATA_BADGE_TYPE not in badge_info:
                    badge_info[const.DATA_BADGE_TYPE] = const.BADGE_TYPE_CUMULATIVE

            # --- Ensure all required fields and nested structures exist using constants ---

            # assigned_to
            if const.DATA_BADGE_ASSIGNED_TO not in badge_info:
                badge_info[const.DATA_BADGE_ASSIGNED_TO] = []

            # reset_schedule
            if const.DATA_BADGE_RESET_SCHEDULE not in badge_info:
                badge_info[const.DATA_BADGE_RESET_SCHEDULE] = {
                    const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY: const.FREQUENCY_NONE,
                    const.DATA_BADGE_RESET_SCHEDULE_START_DATE: None,
                    const.DATA_BADGE_RESET_SCHEDULE_END_DATE: None,
                    const.DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS: 0,
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL: None,
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: None,
                }

            # awards
            if const.DATA_BADGE_AWARDS not in badge_info or not isinstance(
                badge_info[const.DATA_BADGE_AWARDS], dict
            ):
                badge_info[const.DATA_BADGE_AWARDS] = {}
            # Force award items to be multiplier since the was the only award type in the original badges
            badge_info[const.DATA_BADGE_AWARDS][const.DATA_BADGE_AWARDS_AWARD_ITEMS] = [
                const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            ]
            badge_info[const.DATA_BADGE_AWARDS].setdefault(
                const.DATA_BADGE_AWARDS_AWARD_POINTS, 0
            )
            badge_info[const.DATA_BADGE_AWARDS].setdefault(
                const.DATA_BADGE_AWARDS_AWARD_REWARD, ""
            )
            badge_info[const.DATA_BADGE_AWARDS].setdefault(
                const.DATA_BADGE_AWARDS_POINT_MULTIPLIER,
                badge_info.get(
                    const.DATA_BADGE_POINTS_MULTIPLIER_LEGACY,
                    const.DEFAULT_POINTS_MULTIPLIER,
                ),
            )

            # target
            if const.DATA_BADGE_TARGET not in badge_info or not isinstance(
                badge_info[const.DATA_BADGE_TARGET], dict
            ):
                badge_info[const.DATA_BADGE_TARGET] = {}
            badge_info[const.DATA_BADGE_TARGET].setdefault(
                const.DATA_BADGE_TARGET_TYPE,
                badge_info.get(
                    const.DATA_BADGE_THRESHOLD_TYPE_LEGACY,
                    const.BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                ),
            )
            badge_info[const.DATA_BADGE_TARGET].setdefault(
                const.DATA_BADGE_TARGET_THRESHOLD_VALUE,
                badge_info.get(const.DATA_BADGE_THRESHOLD_VALUE_LEGACY, 0),
            )
            badge_info[const.DATA_BADGE_TARGET].setdefault(
                const.DATA_BADGE_MAINTENANCE_RULES, 0
            )

            # --- Migrate threshold_type/value to target if not already done ---
            if const.DATA_BADGE_THRESHOLD_TYPE_LEGACY in badge_info:
                badge_info[const.DATA_BADGE_TARGET][const.DATA_BADGE_TARGET_TYPE] = (
                    badge_info.get(const.DATA_BADGE_THRESHOLD_TYPE_LEGACY)
                )
            if const.DATA_BADGE_THRESHOLD_VALUE_LEGACY in badge_info:
                badge_info[const.DATA_BADGE_TARGET][
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE
                ] = badge_info.get(const.DATA_BADGE_THRESHOLD_VALUE_LEGACY)

            # Migrate points_multiplier to awards.points_multiplier if not already done
            if const.DATA_BADGE_POINTS_MULTIPLIER_LEGACY in badge_info:
                badge_info[const.DATA_BADGE_AWARDS][
                    const.DATA_BADGE_AWARDS_POINT_MULTIPLIER
                ] = float(
                    badge_info.get(
                        const.DATA_BADGE_POINTS_MULTIPLIER_LEGACY,
                        const.DEFAULT_POINTS_MULTIPLIER,
                    )
                )

            # --- Clean up any legacy fields that might exist outside the new nested structure ---
            legacy_fields = [
                const.DATA_BADGE_THRESHOLD_TYPE_LEGACY,
                const.DATA_BADGE_THRESHOLD_VALUE_LEGACY,
                const.DATA_BADGE_CHORE_COUNT_TYPE_LEGACY,
                const.DATA_BADGE_POINTS_MULTIPLIER_LEGACY,
            ]
            for field in legacy_fields:
                if field in badge_info:
                    temp = "#####################********* DISABLED DELETE WHILE DEVELOPING *********#####################"
                    del badge_info[field]

        self._persist()
        self.async_set_updated_data(self._data)

        # --- Update config_entry.options so the UI sees the migrated badges ---
        updated_options = dict(self.config_entry.options)
        updated_options[const.CONF_BADGES] = self._data.get(const.DATA_BADGES, {})
        self.hass.config_entries.async_update_entry(
            self.config_entry, options=updated_options
        )

        const.LOGGER.info(
            "INFO: Badge Migration - Completed migration of legacy badges to new structure"
        )

    def _migrate_kid_legacy_badges_to_cumulative_progress(self):
        """
        For each kid, set their current cumulative badge to the highest-value badge
        (by points threshold) from their legacy earned badges list.
        Also set their cumulative cycle points to their current points balance to avoid losing progress.
        """
        for kid_id, kid_info in self.kids_data.items():
            legacy_badge_names = kid_info.get(const.DATA_KID_BADGES_LEGACY, [])
            if not legacy_badge_names:
                continue

            # Find the highest-value cumulative badge earned by this kid
            highest_badge = None
            highest_points = -1
            for badge_name in legacy_badge_names:
                # Find badge_id by name and ensure it's cumulative
                badge_id = None
                for b_id, b_info in self.badges_data.items():
                    if (
                        b_info.get(const.DATA_BADGE_NAME) == badge_name
                        and b_info.get(const.DATA_BADGE_TYPE)
                        == const.BADGE_TYPE_CUMULATIVE
                    ):
                        badge_id = b_id
                        break
                if not badge_id:
                    continue
                badge_info = self.badges_data[badge_id]
                points = float(
                    badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                    )
                )
                if points > highest_points:
                    highest_points = points
                    highest_badge = badge_info

            # Set the current cumulative badge progress for this kid
            if highest_badge:
                progress = kid_info.setdefault(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
                )
                progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID] = (
                    highest_badge.get(const.DATA_BADGE_INTERNAL_ID)
                )
                progress[
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME
                ] = highest_badge.get(const.DATA_BADGE_NAME)
                progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD] = (
                    highest_badge.get(const.DATA_BADGE_TARGET, {}).get(
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                    )
                )
                # Set cycle points to current points balance to avoid losing progress
                progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] = (
                    kid_info.get(const.DATA_KID_POINTS, 0.0)
                )

    def _migrate_kid_legacy_badges_to_badges_earned(self):
        """One-time migration from legacy 'badges' list to structured 'badges_earned' dict for each kid."""
        import random

        today_local_iso = kh.get_today_local_iso()

        for kid_id, kid_info in self.kids_data.items():
            legacy_badge_names = kid_info.get(const.DATA_KID_BADGES_LEGACY, [])
            badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})

            for badge_name in legacy_badge_names:
                badge_id = kh.get_badge_id_by_name(self, badge_name)

                if not badge_id:
                    badge_id = f"{const.MIGRATION_DATA_LEGACY_ORPHAN}_{random.randint(100000, 999999)}"
                    const.LOGGER.warning(
                        "WARNING: Migrate - Badge '%s' not found in badge data. Assigning legacy orphan ID '%s' for kid '%s'.",
                        badge_name,
                        badge_id,
                        kid_info.get(const.DATA_KID_NAME, kid_id),
                    )

                if badge_id in badges_earned:
                    const.LOGGER.debug(
                        "DEBUG: Migration - Badge '%s' (%s) already in badges_earned for kid '%s', skipping.",
                        badge_name,
                        badge_id,
                        kid_id,
                    )
                    continue

                badges_earned[badge_id] = {
                    const.DATA_KID_BADGES_EARNED_NAME: badge_name,
                    const.DATA_KID_BADGES_EARNED_LAST_AWARDED: today_local_iso,
                    const.DATA_KID_BADGES_EARNED_AWARD_COUNT: 1,
                }

                const.LOGGER.info(
                    "INFO: Migration - Migrated badge '%s' (%s) to badges_earned for kid '%s'.",
                    badge_name,
                    badge_id,
                    kid_info.get(const.DATA_KID_NAME, kid_id),
                )

            # Cleanup: remove the legacy badges list after migration
            if const.DATA_KID_BADGES_LEGACY in kid_info:
                del kid_info[const.DATA_KID_BADGES_LEGACY]

        self._persist()
        self.async_set_updated_data(self._data)

    def _migrate_legacy_point_stats(self):
        """Migrate legacy rolling point stats into the new point_data period structure for each kid."""
        for kid_id, kid_info in self.kids_data.items():
            # Legacy values
            legacy_today = round(
                kid_info.get(const.DATA_KID_POINTS_EARNED_TODAY_LEGACY, 0.0), 1
            )
            legacy_week = round(
                kid_info.get(const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY, 0.0), 1
            )
            legacy_month = round(
                kid_info.get(const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY, 0.0), 1
            )
            legacy_max = round(kid_info.get(const.DATA_KID_MAX_POINTS_EVER, 0.0), 1)

            # Get or create point_data periods
            point_data = kid_info.setdefault(const.DATA_KID_POINT_DATA, {})
            periods = point_data.setdefault(const.DATA_KID_POINT_DATA_PERIODS, {})

            # Get period keys
            today_local_iso = kh.get_today_local_date().isoformat()
            now_local = kh.get_now_local_time()
            week_local_iso = now_local.strftime("%Y-W%V")
            month_local_iso = now_local.strftime("%Y-%m")
            year_local_iso = now_local.strftime("%Y")

            # Helper to migrate if legacy > 0 and period is missing or zero
            def migrate_period(period_key, period_id, legacy_value):
                if legacy_value > 0:
                    bucket = periods.setdefault(period_key, {})
                    entry = bucket.setdefault(
                        period_id,
                        {
                            const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL: 0.0,
                            const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE: {},
                        },
                    )
                    if entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] == 0.0:
                        entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] = (
                            legacy_value
                        )
                        # Use a point source of other
                        entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE][
                            const.POINTS_SOURCE_OTHER
                        ] = legacy_value

            migrate_period(
                const.DATA_KID_POINT_DATA_PERIODS_DAILY, today_local_iso, legacy_today
            )
            migrate_period(
                const.DATA_KID_POINT_DATA_PERIODS_WEEKLY, week_local_iso, legacy_week
            )
            migrate_period(
                const.DATA_KID_POINT_DATA_PERIODS_MONTHLY, month_local_iso, legacy_month
            )

            # Set yearly period points to legacy_max if > 0
            if legacy_max > 0:
                yearly_bucket = periods.setdefault(
                    const.DATA_KID_POINT_DATA_PERIODS_YEARLY, {}
                )
                yearly_entry = yearly_bucket.setdefault(
                    year_local_iso,
                    {
                        const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL: 0.0,
                        const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE: {},
                    },
                )
                yearly_entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] = legacy_max
                yearly_entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE][
                    const.POINTS_SOURCE_OTHER
                ] = legacy_max

            # Migrate legacy max points ever to point_stats highest balance if needed
            point_stats = kid_info.setdefault(const.DATA_KID_POINT_STATS, {})
            if legacy_max > 0 and legacy_max > point_stats.get(
                const.DATA_KID_POINT_STATS_HIGHEST_BALANCE, 0.0
            ):
                point_stats[const.DATA_KID_POINT_STATS_HIGHEST_BALANCE] = legacy_max

            # Set points_earned_all_time to legacy_max if > 0
            if legacy_max > 0:
                point_stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME] = legacy_max

            # --- Migrate all-time points by source ---
            if legacy_max > 0:
                point_stats[const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME] = {
                    const.POINTS_SOURCE_OTHER: legacy_max
                }

            # Optionally, remove legacy fields after migration
            # kid_info.pop(const.DATA_KID_POINTS_EARNED_TODAY_LEGACY, None)
            # kid_info.pop(const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY, None)
            # kid_info.pop(const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY, None)
            # kid_info.pop(const.DATA_KID_MAX_POINTS_EVER, None)

        const.LOGGER.info("INFO: Legacy point stats migration complete.")

    # -------------------------------------------------------------------------------------
    # Normalize Lists
    # -------------------------------------------------------------------------------------

    def _normalize_kid_lists(self, kid_info: dict[str, Any]) -> None:
        "Normalize lists and ensuring they are not dict"
        for key in [
            const.DATA_KID_CLAIMED_CHORES,
            const.DATA_KID_APPROVED_CHORES,
            const.DATA_KID_PENDING_REWARDS,
            const.DATA_KID_REDEEMED_REWARDS,
        ]:
            if not isinstance(kid_info.get(key), list):
                kid_info[key] = []

    # -------------------------------------------------------------------------------------
    # Periodic + First Refresh
    # -------------------------------------------------------------------------------------

    async def _async_update_data(self):
        """Periodic update."""
        try:
            # Check overdue chores
            await self._check_overdue_chores()

            # Notify entities of changes
            self.async_update_listeners()

            return self._data
        except Exception as err:
            raise UpdateFailed(f"Error updating KidsChores data: {err}") from err

    async def async_config_entry_first_refresh(self):
        """Load from storage and merge config options."""
        stored_data = self.storage_manager.get_data()
        if stored_data:
            self._data = stored_data

            # Run migrations only if not done before
            current_version = const.MIGRATION_KEY_VERSION_NUMBER
            stored_version = self._data.get(
                const.MIGRATION_KEY_VERSION, const.DEFAULT_ZERO
            )
            if (not self._data.get(const.MIGRATION_PERFORMED, False)) or (
                stored_version < current_version
            ):
                # Migrate any datetime fields in stored data to UTC-aware strings
                self._migrate_stored_datetimes()

                # Migrate chore data and add new fields
                self._migrate_chore_data()

                #  Migrate Badge Data for Legacy Badges
                self._migrate_badges()

                # Migrate legacy badges to cumulative progress
                self._migrate_kid_legacy_badges_to_cumulative_progress()

                # Migrate legacy badges to badges_earned
                self._migrate_kid_legacy_badges_to_badges_earned()

                # Migrate legacy point stats to new structure
                self._migrate_legacy_point_stats()

                # Migrate legacy chore streaks and stats to new structure
                self._migrate_legacy_kid_chore_data_and_streaks()

                # Flag migrations as done
                self._data[const.MIGRATION_PERFORMED] = True
                self._data[const.MIGRATION_KEY_VERSION] = current_version

            else:
                const.LOGGER.debug(
                    "DEBUG: Data migration to version '%s' already performed. Skipping migration.",
                    current_version,
                )

        else:
            self._data = {
                const.DATA_KIDS: {},
                const.DATA_CHORES: {},
                const.DATA_BADGES: {},
                const.DATA_REWARDS: {},
                const.DATA_PARENTS: {},
                const.DATA_PENALTIES: {},
                const.DATA_BONUSES: {},
                const.DATA_ACHIEVEMENTS: {},
                const.DATA_CHALLENGES: {},
                const.DATA_PENDING_CHORE_APPROVALS: [],
                const.DATA_PENDING_REWARD_APPROVALS: [],
            }
            self._data[const.MIGRATION_PERFORMED] = True

        if not isinstance(self._data.get(const.DATA_PENDING_CHORE_APPROVALS), list):
            self._data[const.DATA_PENDING_CHORE_APPROVALS] = []
        if not isinstance(self._data.get(const.DATA_PENDING_REWARD_APPROVALS), list):
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = []

        # Register daily/weekly/monthly resets
        async_track_time_change(
            self.hass, self._reset_all_chore_counts, **const.DEFAULT_DAILY_RESET_TIME
        )

        # Merge config entry data (options) into the stored data
        self._initialize_data_from_config()

        # Normalize all kids list fields
        for kid in self._data.get(const.DATA_KIDS, {}).values():
            self._normalize_kid_lists(kid)

        # Initialize badge references in kid chore tracking
        self._update_chore_badge_references_for_kid()

        # Initialize chore and point stats
        for kid_id, kid_info in self.kids_data.items():
            self._recalculate_chore_stats_for_kid(kid_id)
            self._recalculate_point_stats_for_kid(kid_id)

        self._persist()
        await super().async_config_entry_first_refresh()

    # -------------------------------------------------------------------------------------
    # Data Initialization from Config
    # -------------------------------------------------------------------------------------

    def _initialize_data_from_config(self):
        """Merge config_entry options with stored data structures using internal_id."""
        options = self.config_entry.options

        # Retrieve configuration dictionaries from config entry options
        config_sections = {
            const.DATA_KIDS: options.get(const.CONF_KIDS, {}),
            const.DATA_PARENTS: options.get(const.CONF_PARENTS, {}),
            const.DATA_CHORES: options.get(const.CONF_CHORES, {}),
            const.DATA_BADGES: options.get(const.CONF_BADGES, {}),
            const.DATA_REWARDS: options.get(const.CONF_REWARDS, {}),
            const.DATA_PENALTIES: options.get(const.CONF_PENALTIES, {}),
            const.DATA_BONUSES: options.get(const.CONF_BONUSES, {}),
            const.DATA_ACHIEVEMENTS: options.get(const.CONF_ACHIEVEMENTS, {}),
            const.DATA_CHALLENGES: options.get(const.CONF_CHALLENGES, {}),
        }

        # Ensure minimal structure
        self._ensure_minimal_structure()

        # Initialize each section using private helper
        for section_key, data_dict in config_sections.items():
            init_func = getattr(self, f"_initialize_{section_key}", None)
            if init_func:
                init_func(data_dict)
            else:
                self._data.setdefault(section_key, data_dict)
                const.LOGGER.warning(
                    "WARNING: No initializer found for section '%s'", section_key
                )

        # Recalculate Badges on reload
        self._recalculate_all_badges()

    def _ensure_minimal_structure(self):
        """Ensure that all necessary data sections are present."""
        for key in [
            const.DATA_KIDS,
            const.DATA_PARENTS,
            const.DATA_CHORES,
            const.DATA_BADGES,
            const.DATA_REWARDS,
            const.DATA_PENALTIES,
            const.DATA_BONUSES,
            const.DATA_ACHIEVEMENTS,
            const.DATA_CHALLENGES,
        ]:
            self._data.setdefault(key, {})

        for key in [
            const.DATA_PENDING_CHORE_APPROVALS,
            const.DATA_PENDING_REWARD_APPROVALS,
        ]:
            if not isinstance(self._data.get(key), list):
                self._data[key] = []

    # -------------------------------------------------------------------------------------
    # Helpers to Sync Entities from config
    # -------------------------------------------------------------------------------------

    def _initialize_kids(self, kids_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_KIDS, kids_dict, self._create_kid, self._update_kid
        )

    def _initialize_parents(self, parents_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_PARENTS, parents_dict, self._create_parent, self._update_parent
        )

    def _initialize_chores(self, chores_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_CHORES, chores_dict, self._create_chore, self._update_chore
        )

    def _initialize_badges(self, badges_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_BADGES, badges_dict, self._create_badge, self._update_badge
        )

    def _initialize_rewards(self, rewards_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_REWARDS, rewards_dict, self._create_reward, self._update_reward
        )

    def _initialize_penalties(self, penalties_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_PENALTIES,
            penalties_dict,
            self._create_penalty,
            self._update_penalty,
        )

    def _initialize_achievements(self, achievements_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_ACHIEVEMENTS,
            achievements_dict,
            self._create_achievement,
            self._update_achievement,
        )

    def _initialize_challenges(self, challenges_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_CHALLENGES,
            challenges_dict,
            self._create_challenge,
            self._update_challenge,
        )

    def _initialize_bonuses(self, bonuses_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_BONUSES, bonuses_dict, self._create_bonus, self._update_bonus
        )

    def _sync_entities(
        self,
        section: str,
        config_data: dict[str, Any],
        create_method,
        update_method,
    ):
        """Synchronize entities in a given data section based on config_data."""
        existing_ids = set(self._data[section].keys())
        config_ids = set(config_data.keys())

        # Identify entities to remove
        entities_to_remove = existing_ids - config_ids
        for entity_id in entities_to_remove:
            # Remove entity from data
            del self._data[section][entity_id]

            # Remove entity from HA registry
            self._remove_entities_in_ha(section, entity_id)
            if section == const.DATA_CHORES:
                for kid_id in self.kids_data.keys():
                    self._remove_kid_chore_entities(kid_id, entity_id)

            # Perform general clean-up
            self._cleanup_all_links()

            # Remove deleted kids from parents list
            self._cleanup_parent_assignments()

            # Remove chore approvals on chore delete
            self._cleanup_pending_chore_approvals()

            # Remove reward approvals on reward delete
            if section == const.DATA_REWARDS:
                self._cleanup_pending_reward_approvals()

        # Add or update entities
        for entity_id, entity_body in config_data.items():
            if entity_id not in self._data[section]:
                create_method(entity_id, entity_body)
            else:
                update_method(entity_id, entity_body)

        # Remove orphaned shared chore sensors.
        if section == const.DATA_CHORES:
            self.hass.async_create_task(self._remove_orphaned_shared_chore_sensors())

        # Remove orphaned achievement and challenges sensors
        self.hass.async_create_task(self._remove_orphaned_achievement_entities())
        self.hass.async_create_task(self._remove_orphaned_challenge_entities())

        # Remove deprecated sensors
        self.hass.async_create_task(
            self.remove_deprecated_entities(self.hass, self.config_entry)
        )

        # Remove deprecated buttons
        self.remove_deprecated_button_entities()

    def _cleanup_all_links(self) -> None:
        """Run all cross-entity cleanup routines."""
        self._cleanup_deleted_kid_references()
        self._cleanup_deleted_chore_references()
        self._cleanup_deleted_chore_in_achievements()
        self._cleanup_deleted_chore_in_challenges()

    def _remove_entities_in_ha(self, section: str, item_id: str):
        """Remove all platform entities whose unique_id references the given item_id."""
        ent_reg = er.async_get(self.hass)
        for entity_entry in list(ent_reg.entities.values()):
            if str(item_id) in str(entity_entry.unique_id):
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "DEBUG: Auto-removed entity '%s' with UID '%s'",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                )

    async def _remove_orphaned_shared_chore_sensors(self):
        """Remove SharedChoreGlobalStateSensor entities for chores no longer marked as shared."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = const.DATA_GLOBAL_STATE_SUFFIX
        for entity_entry in list(ent_reg.entities.values()):
            unique_id = str(entity_entry.unique_id)
            if (
                entity_entry.domain == const.Platform.SENSOR
                and unique_id.startswith(prefix)
                and unique_id.endswith(suffix)
            ):
                chore_id = unique_id[len(prefix) : -len(suffix)]
                chore_info = self.chores_data.get(chore_id)
                if not chore_info or not chore_info.get(
                    const.DATA_CHORE_SHARED_CHORE, False
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "DEBUG: Removed orphaned Shared Chore Global State Sensor: %s",
                        entity_entry.entity_id,
                    )

    async def _remove_orphaned_achievement_entities(self) -> None:
        """Remove achievement progress entities for kids that are no longer assigned."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = const.DATA_ACHIEVEMENT_PROGRESS_SUFFIX
        for entity_entry in list(ent_reg.entities.values()):
            unique_id = str(entity_entry.unique_id)
            if (
                entity_entry.domain == const.Platform.SENSOR
                and unique_id.startswith(prefix)
                and unique_id.endswith(suffix)
            ):
                core_id = unique_id[len(prefix) : -len(suffix)]
                parts = core_id.split("_", 1)
                if len(parts) != 2:
                    continue

                kid_id, achievement_id = parts
                achievement_info = self._data.get(const.DATA_ACHIEVEMENTS, {}).get(
                    achievement_id
                )
                if not achievement_info or kid_id not in achievement_info.get(
                    const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "DEBUG: Removed orphaned Achievement Progress sensor '%s'. Kid ID '%s' is not assigned to Achievement '%s'",
                        entity_entry.entity_id,
                        kid_id,
                        achievement_id,
                    )

    async def _remove_orphaned_challenge_entities(self) -> None:
        """Remove challenge progress sensor entities for kids no longer assigned."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = const.DATA_CHALLENGE_PROGRESS_SUFFIX
        for entity_entry in list(ent_reg.entities.values()):
            unique_id = str(entity_entry.unique_id)
            if (
                entity_entry.domain == const.Platform.SENSOR
                and unique_id.startswith(prefix)
                and unique_id.endswith(suffix)
            ):
                core_id = unique_id[len(prefix) : -len(suffix)]
                parts = core_id.split("_", 1)
                if len(parts) != 2:
                    continue

                kid_id, challenge_id = parts
                challenge_info = self._data.get(const.DATA_CHALLENGES, {}).get(
                    challenge_id
                )
                if not challenge_info or kid_id not in challenge_info.get(
                    const.DATA_CHALLENGE_ASSIGNED_KIDS, []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "DEBUG: Removed orphaned Challenge Progress sensor '%s'. Kid ID '%s' is not assigned to Challenge '%s'",
                        entity_entry.entity_id,
                        kid_id,
                        challenge_id,
                    )

    def _remove_kid_chore_entities(self, kid_id: str, chore_id: str) -> None:
        """Remove all kid-specific chore entities for a given kid and chore."""
        ent_reg = er.async_get(self.hass)
        for entity_entry in list(ent_reg.entities.values()):
            if (kid_id in entity_entry.unique_id) and (
                chore_id in entity_entry.unique_id
            ):
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "DEBUG: Removed kid-specific entity '%s' for Kid ID '%s' and Chore '%s'",
                    entity_entry.entity_id,
                    kid_id,
                    chore_id,
                )

    def _cleanup_chore_from_kid(self, kid_id: str, chore_id: str) -> None:
        """Remove references to a specific chore from a kid's data."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Remove from lists if present
        for key in [const.DATA_KID_CLAIMED_CHORES, const.DATA_KID_APPROVED_CHORES]:
            if chore_id in kid_info.get(key, []):
                kid_info[key] = [c for c in kid_info[key] if c != chore_id]
                const.LOGGER.debug(
                    "DEBUG: Removed Chore '%s' from Kid ID '%s' list '%s'",
                    chore_id,
                    kid_id,
                    key,
                )

        # Remove from dictionary fields if present
        for dict_key in [
            const.DATA_KID_CHORE_CLAIMS_LEGACY,
            const.DATA_KID_CHORE_APPROVALS_LEGACY,
        ]:
            if chore_id in kid_info.get(dict_key, {}):
                kid_info[dict_key].pop(chore_id)
                const.LOGGER.debug(
                    "DEBUG: Removed Chore '%s' from Kid ID '%s' dict '%s'",
                    chore_id,
                    kid_id,
                    dict_key,
                )

        # Remove from chore streaks if present
        if (
            const.DATA_KID_CHORE_STREAKS_LEGACY in kid_info
            and chore_id in kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY]
        ):
            kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY].pop(chore_id)
            const.LOGGER.debug(
                "DEBUG: Removed Chore Streak for Chore '%s' from Kid ID '%s'",
                chore_id,
                kid_id,
            )

        # Remove any pending chore approvals for this kid and chore
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
            if not (
                ap.get(const.DATA_KID_ID) == kid_id
                and ap.get(const.DATA_CHORE_ID) == chore_id
            )
        ]

    def _cleanup_pending_chore_approvals(self) -> None:
        """Remove any pending chore approvals for chore IDs that no longer exist."""
        valid_chore_ids = set(self._data.get(const.DATA_CHORES, {}).keys())
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
            if ap.get(const.DATA_CHORE_ID) in valid_chore_ids
        ]

    def _cleanup_pending_reward_approvals(self) -> None:
        """Remove any pending reward approvals for reward IDs that no longer exist."""
        valid_reward_ids = set(self._data.get(const.DATA_REWARDS, {}).keys())
        self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
            approval
            for approval in self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
            if approval.get(const.DATA_REWARD_ID) in valid_reward_ids
        ]

    def _cleanup_deleted_kid_references(self) -> None:
        """Remove references to kids that no longer exist from other sections."""
        valid_kid_ids = set(self.kids_data.keys())

        # Remove deleted kid IDs from all chore assignments
        for chore_info in self._data.get(const.DATA_CHORES, {}).values():
            if const.DATA_CHORE_ASSIGNED_KIDS in chore_info:
                original = chore_info[const.DATA_CHORE_ASSIGNED_KIDS]
                filtered = [kid for kid in original if kid in valid_kid_ids]
                if filtered != original:
                    chore_info[const.DATA_CHORE_ASSIGNED_KIDS] = filtered
                    const.LOGGER.debug(
                        "DEBUG: Removed Assigned Kids in Chore '%s'",
                        chore_info.get(const.DATA_CHORE_NAME),
                    )

        # Remove progress in achievements and challenges
        for section in [const.DATA_ACHIEVEMENTS, const.DATA_CHALLENGES]:
            for entity in self._data.get(section, {}).values():
                progress = entity.get(const.DATA_PROGRESS, {})
                keys_to_remove = [kid for kid in progress if kid not in valid_kid_ids]
                for kid in keys_to_remove:
                    del progress[kid]
                    const.LOGGER.debug(
                        "DEBUG: Removed Progress for deleted Kid ID '%s' in '%s'",
                        kid,
                        section,
                    )
                if const.DATA_ASSIGNED_KIDS in entity:
                    original_assigned = entity[const.DATA_ASSIGNED_KIDS]
                    filtered_assigned = [
                        kid for kid in original_assigned if kid in valid_kid_ids
                    ]
                    if filtered_assigned != original_assigned:
                        entity[const.DATA_ASSIGNED_KIDS] = filtered_assigned
                        const.LOGGER.debug(
                            "DEBUG: Removed Assigned Kids in '%s', '%s'",
                            section,
                            entity.get(const.DATA_NAME),
                        )

    def _cleanup_deleted_chore_references(self) -> None:
        """Remove references to chores that no longer exist from kid data."""
        valid_chore_ids = set(self.chores_data.keys())
        for kid_info in self.kids_data.values():
            # Clean up list fields
            for key in [const.DATA_KID_CLAIMED_CHORES, const.DATA_KID_APPROVED_CHORES]:
                if key in kid_info:
                    original = kid_info[key]
                    filtered = [chore for chore in original if chore in valid_chore_ids]
                    if filtered != original:
                        kid_info[key] = filtered

            # Clean up dictionary fields
            for dict_key in [
                const.DATA_KID_CHORE_CLAIMS_LEGACY,
                const.DATA_KID_CHORE_APPROVALS_LEGACY,
            ]:
                if dict_key in kid_info:
                    kid_info[dict_key] = {
                        chore: count
                        for chore, count in kid_info[dict_key].items()
                        if chore in valid_chore_ids
                    }

            # Clean up chore streaks
            if const.DATA_KID_CHORE_STREAKS_LEGACY in kid_info:
                for chore in list(kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY].keys()):
                    if chore not in valid_chore_ids:
                        del kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY][chore]
                        const.LOGGER.debug(
                            "DEBUG: Removed Chore Streak for deleted Chore '%s'", chore
                        )

    def _cleanup_parent_assignments(self) -> None:
        """Remove any kid IDs from parent's 'associated_kids' that no longer exist."""
        valid_kid_ids = set(self.kids_data.keys())
        for parent_info in self._data.get(const.DATA_PARENTS, {}).values():
            original = parent_info.get(const.DATA_PARENT_ASSOCIATED_KIDS, [])
            filtered = [kid_id for kid_id in original if kid_id in valid_kid_ids]
            if filtered != original:
                parent_info[const.DATA_PARENT_ASSOCIATED_KIDS] = filtered
                const.LOGGER.debug(
                    "DEBUG: Removed Associated Kids for Parent '%s'. Current Associated Kids: %s",
                    parent_info.get(const.DATA_PARENT_NAME),
                    filtered,
                )

    def _cleanup_deleted_chore_in_achievements(self) -> None:
        """Clear selected_chore_id in achievements if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for achievement_info in self._data.get(const.DATA_ACHIEVEMENTS, {}).values():
            selected = achievement_info.get(const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID)
            if selected and selected not in valid_chore_ids:
                achievement_info[const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID] = ""
                const.LOGGER.debug(
                    "DEBUG: Removed Selected Chore ID in Achievement '%s'",
                    achievement_info.get(const.DATA_ACHIEVEMENT_NAME),
                )

    def _cleanup_deleted_chore_in_challenges(self) -> None:
        """Clear selected_chore_id in challenges if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for challenge_info in self._data.get(const.DATA_CHALLENGES, {}).values():
            selected = challenge_info.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
            if selected and selected not in valid_chore_ids:
                challenge_info[const.DATA_CHALLENGE_SELECTED_CHORE_ID] = (
                    const.CONF_EMPTY
                )
                const.LOGGER.debug(
                    "DEBUG: Removed Selected Chore ID in Challenge '%s'",
                    challenge_info.get(const.DATA_CHALLENGE_NAME),
                )

    async def remove_deprecated_entities(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Remove old/deprecated sensor entities from the entity registry that are no longer used."""

        ent_reg = er.async_get(hass)
        old_suffixes = [
            "_badges",
            "_reward_claims",
            "_reward_approvals",
            "_chore_claims",
            "_chore_approvals",
            "_streak",
        ]

        for entity_id, entity_entry in list(ent_reg.entities.items()):
            if not entity_entry.unique_id.startswith(f"{entry.entry_id}_"):
                continue
            if any(entity_entry.unique_id.endswith(suffix) for suffix in old_suffixes):
                ent_reg.async_remove(entity_id)
                const.LOGGER.debug(
                    "DEBUG: Removed deprecated Entity '%s', UID '%s'",
                    entity_id,
                    entity_entry.unique_id,
                )

    def remove_deprecated_button_entities(self) -> None:
        """Remove dynamic button entities that are not present in the current configuration."""
        ent_reg = er.async_get(self.hass)
        entry_prefix = f"{self.config_entry.entry_id}_"

        # Build the set of expected unique_ids ("whitelist")
        allowed_uids = set()

        # --- Chore Buttons ---
        # For each chore, create expected unique IDs for claim, approve, and disapprove buttons
        for chore_id, chore_info in self.chores_data.items():
            for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                # Expected unique_id formats:
                uid_claim = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_CLAIM}"
                uid_approve = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_APPROVE}"
                uid_disapprove = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_DISAPPROVE}"
                allowed_uids.update({uid_claim, uid_approve, uid_disapprove})

        # --- Reward Buttons ---
        # For each kid and reward, add expected unique IDs for reward claim, approve, and disapprove buttons.
        for kid_id in self.kids_data.keys():
            for reward_id in self.rewards_data.keys():
                # The reward claim button might be built with a dedicated prefix:
                uid_claim = f"{self.config_entry.entry_id}_{const.BUTTON_REWARD_PREFIX}{kid_id}_{reward_id}"
                uid_approve = f"{self.config_entry.entry_id}_{kid_id}_{reward_id}{const.BUTTON_KC_UID_SUFFIX_APPROVE_REWARD}"
                uid_disapprove = f"{self.config_entry.entry_id}_{kid_id}_{reward_id}{const.BUTTON_KC_UID_SUFFIX_DISAPPROVE_REWARD}"
                allowed_uids.update({uid_claim, uid_approve, uid_disapprove})

        # --- Penalty Buttons ---
        for kid_id in self.kids_data.keys():
            for penalty_id in self.penalties_data.keys():
                uid = f"{self.config_entry.entry_id}_{const.BUTTON_PENALTY_PREFIX}{kid_id}_{penalty_id}"
                allowed_uids.add(uid)

        # --- Bonus Buttons ---
        for kid_id in self.kids_data.keys():
            for bonus_id in self.bonuses_data.keys():
                uid = f"{self.config_entry.entry_id}_{const.BUTTON_BONUS_PREFIX}{kid_id}_{bonus_id}"
                allowed_uids.add(uid)

        # --- Points Adjust Buttons ---
        # Determine the list of adjustment delta values from configuration or defaults.
        raw_values = self.config_entry.options.get(const.CONF_POINTS_ADJUST_VALUES)
        if not raw_values:
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        elif isinstance(raw_values, str):
            points_adjust_values = kh.parse_points_adjust_values(raw_values)
            if not points_adjust_values:
                points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        elif isinstance(raw_values, list):
            try:
                points_adjust_values = [float(v) for v in raw_values]
            except (ValueError, TypeError):
                points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        else:
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES

        for kid_id in self.kids_data.keys():
            for delta in points_adjust_values:
                uid = f"{self.config_entry.entry_id}_{kid_id}{const.BUTTON_KC_UID_MIDFIX_ADJUST_POINTS}{delta}"
                allowed_uids.add(uid)

        # --- Now remove any button entity whose unique_id is not in allowed_uids ---
        for entity_entry in list(ent_reg.entities.values()):
            if entity_entry.domain != "button" or not entity_entry.unique_id.startswith(
                entry_prefix
            ):
                continue
            if entity_entry.unique_id not in allowed_uids:
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "DEBUG: Removed deprecated Button '%s'", entity_entry.entity_id
                )

    # -------------------------------------------------------------------------------------
    # Create/Update Entities
    # (Kids, Parents, Chores, Badges, Rewards, Penalties, Bonus, Achievements and Challenges)
    # -------------------------------------------------------------------------------------

    # -- Kids
    def _create_kid(self, kid_id: str, kid_data: dict[str, Any]):
        self._data[const.DATA_KIDS][kid_id] = {
            const.DATA_KID_NAME: kid_data.get(const.DATA_KID_NAME, const.CONF_EMPTY),
            const.DATA_KID_POINTS: kid_data.get(
                const.DATA_KID_POINTS, const.DEFAULT_ZERO
            ),
            const.DATA_KID_BADGES_EARNED: kid_data.get(
                const.DATA_KID_BADGES_EARNED, {}
            ),
            const.DATA_KID_CLAIMED_CHORES: kid_data.get(
                const.DATA_KID_CLAIMED_CHORES, []
            ),
            const.DATA_KID_APPROVED_CHORES: kid_data.get(
                const.DATA_KID_APPROVED_CHORES, []
            ),
            const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_COMPLETED_CHORES_WEEKLY_LEGACY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_WEEKLY_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_COMPLETED_CHORES_MONTHLY_LEGACY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_MONTHLY_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_HA_USER_ID: kid_data.get(const.DATA_KID_HA_USER_ID),
            const.DATA_KID_INTERNAL_ID: kid_id,
            const.DATA_KID_POINTS_MULTIPLIER: kid_data.get(
                const.DATA_KID_POINTS_MULTIPLIER, const.DEFAULT_KID_POINTS_MULTIPLIER
            ),
            const.DATA_KID_REWARD_CLAIMS: kid_data.get(
                const.DATA_KID_REWARD_CLAIMS, {}
            ),
            const.DATA_KID_REWARD_APPROVALS: kid_data.get(
                const.DATA_KID_REWARD_APPROVALS, {}
            ),
            const.DATA_KID_CHORE_CLAIMS_LEGACY: kid_data.get(
                const.DATA_KID_CHORE_CLAIMS_LEGACY, {}
            ),
            const.DATA_KID_CHORE_APPROVALS_LEGACY: kid_data.get(
                const.DATA_KID_CHORE_APPROVALS_LEGACY, {}
            ),
            const.DATA_KID_PENALTY_APPLIES: kid_data.get(
                const.DATA_KID_PENALTY_APPLIES, {}
            ),
            const.DATA_KID_BONUS_APPLIES: kid_data.get(
                const.DATA_KID_BONUS_APPLIES, {}
            ),
            const.DATA_KID_PENDING_REWARDS: kid_data.get(
                const.DATA_KID_PENDING_REWARDS, []
            ),
            const.DATA_KID_REDEEMED_REWARDS: kid_data.get(
                const.DATA_KID_REDEEMED_REWARDS, []
            ),
            const.DATA_KID_POINTS_EARNED_TODAY_LEGACY: kid_data.get(
                const.DATA_KID_POINTS_EARNED_TODAY_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY: kid_data.get(
                const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY: kid_data.get(
                const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_MAX_POINTS_EVER: kid_data.get(
                const.DATA_KID_MAX_POINTS_EVER, const.DEFAULT_ZERO
            ),
            const.DATA_KID_ENABLE_NOTIFICATIONS: kid_data.get(
                const.DATA_KID_ENABLE_NOTIFICATIONS, True
            ),
            const.DATA_KID_MOBILE_NOTIFY_SERVICE: kid_data.get(
                const.DATA_KID_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
            ),
            const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: kid_data.get(
                const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            const.DATA_KID_CHORE_STREAKS_LEGACY: {},
            const.DATA_KID_OVERDUE_CHORES: [],
            const.DATA_KID_OVERDUE_NOTIFICATIONS: {},
        }

        self._normalize_kid_lists(self._data[const.DATA_KIDS][kid_id])

        const.LOGGER.debug(
            "DEBUG: Kid Added - '%s', ID '%s'",
            self._data[const.DATA_KIDS][kid_id][const.DATA_KID_NAME],
            kid_id,
        )

    def _update_kid(self, kid_id: str, kid_data: dict[str, Any]):
        """Update an existing kid entity, only updating fields present in kid_data."""

        kids = self._data.setdefault(const.DATA_KIDS, {})
        existing = kids.get(kid_id, {})
        # Only update fields present in kid_data, preserving all others
        existing.update(kid_data)
        kids[kid_id] = existing

        kid_name = existing.get(const.DATA_KID_NAME, const.CONF_EMPTY)
        const.LOGGER.debug(
            "DEBUG: Kid Updated - '%s', ID '%s'",
            kid_name,
            kid_id,
        )

    # -- Parents
    def _create_parent(self, parent_id: str, parent_data: dict[str, Any]):
        associated_kids_ids = []
        for kid_id in parent_data.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
            if kid_id in self.kids_data:
                associated_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "WARNING: Parent '%s': Kid ID '%s' not found. Skipping assignment to parent",
                    parent_data.get(const.DATA_PARENT_NAME, parent_id),
                    kid_id,
                )

        self._data[const.DATA_PARENTS][parent_id] = {
            const.DATA_PARENT_NAME: parent_data.get(
                const.DATA_PARENT_NAME, const.CONF_EMPTY
            ),
            const.DATA_PARENT_HA_USER_ID: parent_data.get(
                const.DATA_PARENT_HA_USER_ID, const.CONF_EMPTY
            ),
            const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids_ids,
            const.DATA_PARENT_ENABLE_NOTIFICATIONS: parent_data.get(
                const.DATA_PARENT_ENABLE_NOTIFICATIONS, True
            ),
            const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: parent_data.get(
                const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
            ),
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: parent_data.get(
                const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            const.DATA_PARENT_INTERNAL_ID: parent_id,
        }
        const.LOGGER.debug(
            "DEBUG: Parent Added - '%s', ID '%s'",
            self._data[const.DATA_PARENTS][parent_id][const.DATA_PARENT_NAME],
            parent_id,
        )

    def _update_parent(self, parent_id: str, parent_data: dict[str, Any]):
        parent_info = self._data[const.DATA_PARENTS][parent_id]
        parent_info[const.DATA_PARENT_NAME] = parent_data.get(
            const.DATA_PARENT_NAME, parent_info[const.DATA_PARENT_NAME]
        )
        parent_info[const.DATA_PARENT_HA_USER_ID] = parent_data.get(
            const.DATA_PARENT_HA_USER_ID, parent_info[const.DATA_PARENT_HA_USER_ID]
        )

        # Update associated_kids
        updated_kids = []
        for kid_id in parent_data.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
            if kid_id in self.kids_data:
                updated_kids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "WARNING: Parent '%s': Kid ID '%s' not found. Skipping assignment to parent",
                    parent_info[const.DATA_PARENT_NAME],
                    kid_id,
                )
        parent_info[const.DATA_PARENT_ASSOCIATED_KIDS] = updated_kids
        parent_info[const.DATA_PARENT_ENABLE_NOTIFICATIONS] = parent_data.get(
            const.DATA_PARENT_ENABLE_NOTIFICATIONS,
            parent_info.get(const.DATA_PARENT_ENABLE_NOTIFICATIONS, True),
        )
        parent_info[const.DATA_PARENT_MOBILE_NOTIFY_SERVICE] = parent_data.get(
            const.DATA_PARENT_MOBILE_NOTIFY_SERVICE,
            parent_info.get(const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY),
        )
        parent_info[const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS] = parent_data.get(
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS,
            parent_info.get(const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True),
        )

        const.LOGGER.debug(
            "DEBUG: Parent Updated - '%s', ID '%s'",
            parent_info[const.DATA_PARENT_NAME],
            parent_id,
        )

    # -- Chores
    def _create_chore(self, chore_id: str, chore_data: dict[str, Any]):
        assigned_kids_ids = []
        for kid_name in chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            kid_id = kh.get_kid_id_by_name(self, kid_name)
            if kid_id:
                assigned_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "WARNING: Chore '%s': Kid ID '%s' not found. Skipping assignment",
                    chore_data.get(const.DATA_CHORE_NAME, chore_id),
                    kid_name,
                )

        # If chore is recurring, set due_date to creation date if not set
        # CLS 20251110 Due date no longer required for recurring
        # freq = chore_data.get(
        #    const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        # )
        # if freq != const.FREQUENCY_NONE and not chore_data.get(
        #    const.DATA_CHORE_DUE_DATE
        # ):
        #    now_local = kh.get_now_local_time()
        # Force the time to 23:59:00 (and zero microseconds)
        #    default_due = now_local.replace(**const.DEFAULT_DUE_TIME)
        #    chore_data[const.DATA_CHORE_DUE_DATE] = default_due.isoformat()
        #    const.LOGGER.debug(
        #        "DEBUG: Chore '%s' has frequency set to '%s' but no due date. Defaulting to 23:59 local time: %s",
        #        chore_data.get(const.DATA_CHORE_NAME, chore_id),
        #        freq,
        #        chore_data[const.DATA_CHORE_DUE_DATE],
        #    )

        self._data[const.DATA_CHORES][chore_id] = {
            const.DATA_CHORE_NAME: chore_data.get(
                const.DATA_CHORE_NAME, const.CONF_EMPTY
            ),
            const.DATA_CHORE_STATE: chore_data.get(
                const.DATA_CHORE_STATE, const.CHORE_STATE_PENDING
            ),
            const.DATA_CHORE_DEFAULT_POINTS: chore_data.get(
                const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
            ),
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_data.get(
                const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY,
                const.DEFAULT_MULTIPLE_CLAIMS_PER_DAY,
            ),
            const.DATA_CHORE_PARTIAL_ALLOWED: chore_data.get(
                const.DATA_CHORE_PARTIAL_ALLOWED, const.DEFAULT_PARTIAL_ALLOWED
            ),
            const.DATA_CHORE_DESCRIPTION: chore_data.get(
                const.DATA_CHORE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_CHORE_LABELS: chore_data.get(const.DATA_CHORE_LABELS, []),
            const.DATA_CHORE_ICON: chore_data.get(
                const.DATA_CHORE_ICON, const.DEFAULT_ICON
            ),
            const.DATA_CHORE_SHARED_CHORE: chore_data.get(
                const.DATA_CHORE_SHARED_CHORE, False
            ),
            const.DATA_CHORE_ASSIGNED_KIDS: assigned_kids_ids,
            const.DATA_CHORE_RECURRING_FREQUENCY: chore_data.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
            ),
            const.DATA_CHORE_CUSTOM_INTERVAL: chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL
            )
            if chore_data.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            == const.FREQUENCY_CUSTOM
            else None,
            const.DATA_CHORE_CUSTOM_INTERVAL_UNIT: chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
            )
            if chore_data.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            == const.FREQUENCY_CUSTOM
            else None,
            const.DATA_CHORE_DUE_DATE: chore_data.get(const.DATA_CHORE_DUE_DATE),
            const.DATA_CHORE_LAST_COMPLETED: chore_data.get(
                const.DATA_CHORE_LAST_COMPLETED
            ),
            const.DATA_CHORE_LAST_CLAIMED: chore_data.get(
                const.DATA_CHORE_LAST_CLAIMED
            ),
            const.DATA_CHORE_APPLICABLE_DAYS: chore_data.get(
                const.DATA_CHORE_APPLICABLE_DAYS, []
            ),
            const.DATA_CHORE_NOTIFY_ON_CLAIM: chore_data.get(
                const.DATA_CHORE_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
            ),
            const.DATA_CHORE_NOTIFY_ON_APPROVAL: chore_data.get(
                const.DATA_CHORE_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
            ),
            const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL: chore_data.get(
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
                const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
            ),
            const.DATA_CHORE_INTERNAL_ID: chore_id,
        }
        const.LOGGER.debug(
            "DEBUG: Chore Added - '%s', ID '%s'",
            self._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NAME],
            chore_id,
        )

        # Notify Kids of new chore
        new_name = self._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NAME]
        due_date = self._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_DUE_DATE]
        for kid_id in assigned_kids_ids:
            due_str = due_date if due_date else const.TRANS_KEY_NO_DUE_DATE
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: New Chore",
                    message=f"New chore '{new_name}' was assigned to you! Due: {due_str}",
                    extra_data=extra_data,
                )
            )

    def _update_chore(self, chore_id: str, chore_data: dict[str, Any]):
        chore_info = self._data[const.DATA_CHORES][chore_id]
        chore_info[const.DATA_CHORE_NAME] = chore_data.get(
            const.DATA_CHORE_NAME, chore_info[const.DATA_CHORE_NAME]
        )
        chore_info[const.DATA_CHORE_STATE] = chore_data.get(
            const.DATA_CHORE_STATE, chore_info[const.DATA_CHORE_STATE]
        )
        chore_info[const.DATA_CHORE_DEFAULT_POINTS] = chore_data.get(
            const.DATA_CHORE_DEFAULT_POINTS, chore_info[const.DATA_CHORE_DEFAULT_POINTS]
        )
        chore_info[const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY] = chore_data.get(
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY,
            chore_info[const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY],
        )
        chore_info[const.DATA_CHORE_PARTIAL_ALLOWED] = chore_data.get(
            const.DATA_CHORE_PARTIAL_ALLOWED,
            chore_info[const.DATA_CHORE_PARTIAL_ALLOWED],
        )
        chore_info[const.DATA_CHORE_DESCRIPTION] = chore_data.get(
            const.DATA_CHORE_DESCRIPTION, chore_info[const.DATA_CHORE_DESCRIPTION]
        )
        chore_info[const.DATA_CHORE_LABELS] = chore_data.get(
            const.DATA_CHORE_LABELS,
            chore_info.get(const.DATA_CHORE_LABELS, []),
        )
        chore_info[const.DATA_CHORE_ICON] = chore_data.get(
            const.DATA_CHORE_ICON, chore_info[const.DATA_CHORE_ICON]
        )
        chore_info[const.DATA_CHORE_SHARED_CHORE] = chore_data.get(
            const.DATA_CHORE_SHARED_CHORE, chore_info[const.DATA_CHORE_SHARED_CHORE]
        )

        assigned_kids_ids = []
        for kid_name in chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            kid_id = kh.get_kid_id_by_name(self, kid_name)
            if kid_id:
                assigned_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "WARNING: Chore '%s': Kid ID '%s' not found. Skipping assignment",
                    chore_data.get(const.DATA_CHORE_NAME, chore_id),
                    kid_name,
                )
        old_assigned = set(chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []))
        new_assigned = set(assigned_kids_ids)
        removed_kids = old_assigned - new_assigned
        for kid in removed_kids:
            self._remove_kid_chore_entities(kid, chore_id)
            self._cleanup_chore_from_kid(kid, chore_id)

        # Update the chore's assigned kids list with the new assignments
        chore_info[const.DATA_CHORE_ASSIGNED_KIDS] = list(new_assigned)
        chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] = chore_data.get(
            const.DATA_CHORE_RECURRING_FREQUENCY,
            chore_info[const.DATA_CHORE_RECURRING_FREQUENCY],
        )
        chore_info[const.DATA_CHORE_DUE_DATE] = chore_data.get(
            const.DATA_CHORE_DUE_DATE, chore_info[const.DATA_CHORE_DUE_DATE]
        )
        chore_info[const.DATA_CHORE_LAST_COMPLETED] = chore_data.get(
            const.DATA_CHORE_LAST_COMPLETED,
            chore_info.get(const.DATA_CHORE_LAST_COMPLETED),
        )
        chore_info[const.DATA_CHORE_LAST_CLAIMED] = chore_data.get(
            const.DATA_CHORE_LAST_CLAIMED, chore_info.get(const.DATA_CHORE_LAST_CLAIMED)
        )
        chore_info[const.DATA_CHORE_APPLICABLE_DAYS] = chore_data.get(
            const.DATA_CHORE_APPLICABLE_DAYS,
            chore_info.get(const.DATA_CHORE_APPLICABLE_DAYS, []),
        )
        chore_info[const.DATA_CHORE_NOTIFY_ON_CLAIM] = chore_data.get(
            const.DATA_CHORE_NOTIFY_ON_CLAIM,
            chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
            ),
        )
        chore_info[const.DATA_CHORE_NOTIFY_ON_APPROVAL] = chore_data.get(
            const.DATA_CHORE_NOTIFY_ON_APPROVAL,
            chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
            ),
        )
        chore_info[const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL] = chore_data.get(
            const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
            chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
                const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
            ),
        )

        if chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] == const.FREQUENCY_CUSTOM:
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL] = chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL
            )
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
            )
        else:
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL] = None
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = None

        const.LOGGER.debug(
            "DEBUG: Chore Updated - '%s', ID '%s'",
            chore_info[const.DATA_CHORE_NAME],
            chore_id,
        )

        self.hass.async_create_task(self._check_overdue_chores())

    # -- Badges
    def _create_badge(self, badge_id: str, badge_data: dict[str, Any]):
        """Create a new badge entity."""

        # --- Simplified Logic ---
        # Directly assign badge_data to badge_info.
        # This assumes badge_data is already validated and contains all necessary fields.
        self._data.setdefault(const.DATA_BADGES, {})[badge_id] = badge_data

        badge_info = self._data[const.DATA_BADGES][badge_id]
        badge_name = badge_info.get(const.DATA_BADGE_NAME, const.CONF_EMPTY)

        const.LOGGER.debug(
            "DEBUG: Badge Updated - '%s', ID '%s'",
            badge_name,
            badge_id,
        )

    def _update_badge(self, badge_id: str, badge_data: dict[str, Any]):
        """Update an existing badge entity, only updating fields present in badge_data."""

        badges = self._data.setdefault(const.DATA_BADGES, {})
        existing = badges.get(badge_id, {})
        # Only update fields present in badge_data, preserving all others
        existing.update(badge_data)
        badges[badge_id] = existing

        badge_name = existing.get(const.DATA_BADGE_NAME, const.CONF_EMPTY)
        const.LOGGER.debug(
            "DEBUG: Badge Updated - '%s', ID '%s'",
            badge_name,
            badge_id,
        )

    # -- Rewards
    def _create_reward(self, reward_id: str, reward_data: dict[str, Any]):
        self._data[const.DATA_REWARDS][reward_id] = {
            const.DATA_REWARD_NAME: reward_data.get(
                const.DATA_REWARD_NAME, const.CONF_EMPTY
            ),
            const.DATA_REWARD_COST: reward_data.get(
                const.DATA_REWARD_COST, const.DEFAULT_REWARD_COST
            ),
            const.DATA_REWARD_DESCRIPTION: reward_data.get(
                const.DATA_REWARD_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_REWARD_LABELS: reward_data.get(const.DATA_REWARD_LABELS, []),
            const.DATA_REWARD_ICON: reward_data.get(
                const.DATA_REWARD_ICON, const.DEFAULT_REWARD_ICON
            ),
            const.DATA_REWARD_INTERNAL_ID: reward_id,
        }
        const.LOGGER.debug(
            "DEBUG: Reward Added - '%s', ID '%s'",
            self._data[const.DATA_REWARDS][reward_id][const.DATA_REWARD_NAME],
            reward_id,
        )

    def _update_reward(self, reward_id: str, reward_data: dict[str, Any]):
        reward_info = self._data[const.DATA_REWARDS][reward_id]

        reward_info[const.DATA_REWARD_NAME] = reward_data.get(
            const.DATA_REWARD_NAME, reward_info[const.DATA_REWARD_NAME]
        )
        reward_info[const.DATA_REWARD_COST] = reward_data.get(
            const.DATA_REWARD_COST, reward_info[const.DATA_REWARD_COST]
        )
        reward_info[const.DATA_REWARD_DESCRIPTION] = reward_data.get(
            const.DATA_REWARD_DESCRIPTION, reward_info[const.DATA_REWARD_DESCRIPTION]
        )
        reward_info[const.DATA_REWARD_LABELS] = reward_data.get(
            const.DATA_REWARD_LABELS, reward_info.get(const.DATA_REWARD_LABELS, [])
        )
        reward_info[const.DATA_REWARD_ICON] = reward_data.get(
            const.DATA_REWARD_ICON, reward_info[const.DATA_REWARD_ICON]
        )
        const.LOGGER.debug(
            "DEBUG: Reward Updated - '%s', ID '%s'",
            reward_info[const.DATA_REWARD_NAME],
            reward_id,
        )

    # -- Bonuses
    def _create_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        self._data[const.DATA_BONUSES][bonus_id] = {
            const.DATA_BONUS_NAME: bonus_data.get(
                const.DATA_BONUS_NAME, const.CONF_EMPTY
            ),
            const.DATA_BONUS_POINTS: bonus_data.get(
                const.DATA_BONUS_POINTS, const.DEFAULT_BONUS_POINTS
            ),
            const.DATA_BONUS_DESCRIPTION: bonus_data.get(
                const.DATA_BONUS_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_BONUS_LABELS: bonus_data.get(const.DATA_BONUS_LABELS, []),
            const.DATA_BONUS_ICON: bonus_data.get(
                const.DATA_BONUS_ICON, const.DEFAULT_BONUS_ICON
            ),
            const.DATA_BONUS_INTERNAL_ID: bonus_id,
        }
        const.LOGGER.debug(
            "DEBUG: Bonus Added - '%s', ID '%s'",
            self._data[const.DATA_BONUSES][bonus_id][const.DATA_BONUS_NAME],
            bonus_id,
        )

    def _update_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        bonus_info = self._data[const.DATA_BONUSES][bonus_id]
        bonus_info[const.DATA_BONUS_NAME] = bonus_data.get(
            const.DATA_BONUS_NAME, bonus_info[const.DATA_BONUS_NAME]
        )
        bonus_info[const.DATA_BONUS_POINTS] = bonus_data.get(
            const.DATA_BONUS_POINTS, bonus_info[const.DATA_BONUS_POINTS]
        )
        bonus_info[const.DATA_BONUS_DESCRIPTION] = bonus_data.get(
            const.DATA_BONUS_DESCRIPTION, bonus_info[const.DATA_BONUS_DESCRIPTION]
        )
        bonus_info[const.DATA_BONUS_LABELS] = bonus_data.get(
            const.DATA_BONUS_LABELS, bonus_info.get(const.DATA_BONUS_LABELS, [])
        )
        bonus_info[const.DATA_BONUS_ICON] = bonus_data.get(
            const.DATA_BONUS_ICON, bonus_info[const.DATA_BONUS_ICON]
        )
        const.LOGGER.debug(
            "DEBUG: Bonus Updated - '%s', ID '%s'",
            bonus_info[const.DATA_BONUS_NAME],
            bonus_id,
        )

    # -- Penalties
    def _create_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        self._data[const.DATA_PENALTIES][penalty_id] = {
            const.DATA_PENALTY_NAME: penalty_data.get(
                const.DATA_PENALTY_NAME, const.CONF_EMPTY
            ),
            const.DATA_PENALTY_POINTS: penalty_data.get(
                const.DATA_PENALTY_POINTS, -const.DEFAULT_PENALTY_POINTS
            ),
            const.DATA_PENALTY_DESCRIPTION: penalty_data.get(
                const.DATA_PENALTY_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_PENALTY_LABELS: penalty_data.get(const.DATA_PENALTY_LABELS, []),
            const.DATA_PENALTY_ICON: penalty_data.get(
                const.DATA_PENALTY_ICON, const.DEFAULT_PENALTY_ICON
            ),
            const.DATA_PENALTY_INTERNAL_ID: penalty_id,
        }
        const.LOGGER.debug(
            "DEBUG: Penalty Added - '%s', ID '%s'",
            self._data[const.DATA_PENALTIES][penalty_id][const.DATA_PENALTY_NAME],
            penalty_id,
        )

    def _update_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        penalty_info = self._data[const.DATA_PENALTIES][penalty_id]
        penalty_info[const.DATA_PENALTY_NAME] = penalty_data.get(
            const.DATA_PENALTY_NAME, penalty_info[const.DATA_PENALTY_NAME]
        )
        penalty_info[const.DATA_PENALTY_POINTS] = penalty_data.get(
            const.DATA_PENALTY_POINTS, penalty_info[const.DATA_PENALTY_POINTS]
        )
        penalty_info[const.DATA_PENALTY_DESCRIPTION] = penalty_data.get(
            const.DATA_PENALTY_DESCRIPTION, penalty_info[const.DATA_PENALTY_DESCRIPTION]
        )
        penalty_info[const.DATA_PENALTY_LABELS] = penalty_data.get(
            const.DATA_PENALTY_LABELS, penalty_info.get(const.DATA_PENALTY_LABELS, [])
        )
        penalty_info[const.DATA_PENALTY_ICON] = penalty_data.get(
            const.DATA_PENALTY_ICON, penalty_info[const.DATA_PENALTY_ICON]
        )
        const.LOGGER.debug(
            "DEBUG: Penalty Updated - '%s', ID '%s'",
            penalty_info[const.DATA_PENALTY_NAME],
            penalty_id,
        )

    # -- Achievements
    def _create_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        self._data[const.DATA_ACHIEVEMENTS][achievement_id] = {
            const.DATA_ACHIEVEMENT_NAME: achievement_data.get(
                const.DATA_ACHIEVEMENT_NAME, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_DESCRIPTION: achievement_data.get(
                const.DATA_ACHIEVEMENT_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_LABELS: achievement_data.get(
                const.DATA_ACHIEVEMENT_LABELS, []
            ),
            const.DATA_ACHIEVEMENT_ICON: achievement_data.get(
                const.DATA_ACHIEVEMENT_ICON, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: achievement_data.get(
                const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
            ),
            const.DATA_ACHIEVEMENT_TYPE: achievement_data.get(
                const.DATA_ACHIEVEMENT_TYPE, const.ACHIEVEMENT_TYPE_STREAK
            ),
            const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID: achievement_data.get(
                const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_CRITERIA: achievement_data.get(
                const.DATA_ACHIEVEMENT_CRITERIA, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_TARGET_VALUE: achievement_data.get(
                const.DATA_ACHIEVEMENT_TARGET_VALUE, const.DEFAULT_ACHIEVEMENT_TARGET
            ),
            const.DATA_ACHIEVEMENT_REWARD_POINTS: achievement_data.get(
                const.DATA_ACHIEVEMENT_REWARD_POINTS,
                const.DEFAULT_ACHIEVEMENT_REWARD_POINTS,
            ),
            const.DATA_ACHIEVEMENT_PROGRESS: achievement_data.get(
                const.DATA_ACHIEVEMENT_PROGRESS, {}
            ),
            const.DATA_ACHIEVEMENT_INTERNAL_ID: achievement_id,
        }
        const.LOGGER.debug(
            "DEBUG: Achievement Added - '%s', ID '%s'",
            self._data[const.DATA_ACHIEVEMENTS][achievement_id][
                const.DATA_ACHIEVEMENT_NAME
            ],
            achievement_id,
        )

    def _update_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        achievement_info = self._data[const.DATA_ACHIEVEMENTS][achievement_id]
        achievement_info[const.DATA_ACHIEVEMENT_NAME] = achievement_data.get(
            const.DATA_ACHIEVEMENT_NAME, achievement_info[const.DATA_ACHIEVEMENT_NAME]
        )
        achievement_info[const.DATA_ACHIEVEMENT_DESCRIPTION] = achievement_data.get(
            const.DATA_ACHIEVEMENT_DESCRIPTION,
            achievement_info[const.DATA_ACHIEVEMENT_DESCRIPTION],
        )
        achievement_info[const.DATA_ACHIEVEMENT_LABELS] = achievement_data.get(
            const.DATA_ACHIEVEMENT_LABELS,
            achievement_info.get(const.DATA_ACHIEVEMENT_LABELS, []),
        )
        achievement_info[const.DATA_ACHIEVEMENT_ICON] = achievement_data.get(
            const.DATA_ACHIEVEMENT_ICON, achievement_info[const.DATA_ACHIEVEMENT_ICON]
        )
        achievement_info[const.DATA_ACHIEVEMENT_ASSIGNED_KIDS] = achievement_data.get(
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS,
            achievement_info[const.DATA_ACHIEVEMENT_ASSIGNED_KIDS],
        )
        achievement_info[const.DATA_ACHIEVEMENT_TYPE] = achievement_data.get(
            const.DATA_ACHIEVEMENT_TYPE, achievement_info[const.DATA_ACHIEVEMENT_TYPE]
        )
        achievement_info[const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID] = (
            achievement_data.get(
                const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID,
                achievement_info.get(
                    const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID, const.CONF_EMPTY
                ),
            )
        )
        achievement_info[const.DATA_ACHIEVEMENT_CRITERIA] = achievement_data.get(
            const.DATA_ACHIEVEMENT_CRITERIA,
            achievement_info[const.DATA_ACHIEVEMENT_CRITERIA],
        )
        achievement_info[const.DATA_ACHIEVEMENT_TARGET_VALUE] = achievement_data.get(
            const.DATA_ACHIEVEMENT_TARGET_VALUE,
            achievement_info[const.DATA_ACHIEVEMENT_TARGET_VALUE],
        )
        achievement_info[const.DATA_ACHIEVEMENT_REWARD_POINTS] = achievement_data.get(
            const.DATA_ACHIEVEMENT_REWARD_POINTS,
            achievement_info[const.DATA_ACHIEVEMENT_REWARD_POINTS],
        )
        const.LOGGER.debug(
            "DEBUG: Achievement Updated - '%s', ID '%s'",
            achievement_info[const.DATA_ACHIEVEMENT_NAME],
            achievement_id,
        )

    # -- Challenges
    def _create_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        self._data[const.DATA_CHALLENGES][challenge_id] = {
            const.DATA_CHALLENGE_NAME: challenge_data.get(
                const.DATA_CHALLENGE_NAME, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_DESCRIPTION: challenge_data.get(
                const.DATA_CHALLENGE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_LABELS: challenge_data.get(
                const.DATA_CHALLENGE_LABELS, []
            ),
            const.DATA_CHALLENGE_ICON: challenge_data.get(
                const.DATA_CHALLENGE_ICON, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_ASSIGNED_KIDS: challenge_data.get(
                const.DATA_CHALLENGE_ASSIGNED_KIDS, []
            ),
            const.DATA_CHALLENGE_TYPE: challenge_data.get(
                const.DATA_CHALLENGE_TYPE, const.CHALLENGE_TYPE_DAILY_MIN
            ),
            const.DATA_CHALLENGE_SELECTED_CHORE_ID: challenge_data.get(
                const.DATA_CHALLENGE_SELECTED_CHORE_ID, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_CRITERIA: challenge_data.get(
                const.DATA_CHALLENGE_CRITERIA, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_TARGET_VALUE: challenge_data.get(
                const.DATA_CHALLENGE_TARGET_VALUE, const.DEFAULT_CHALLENGE_TARGET
            ),
            const.DATA_CHALLENGE_REWARD_POINTS: challenge_data.get(
                const.DATA_CHALLENGE_REWARD_POINTS,
                const.DEFAULT_CHALLENGE_REWARD_POINTS,
            ),
            const.DATA_CHALLENGE_START_DATE: (
                challenge_data.get(const.DATA_CHALLENGE_START_DATE)
                if challenge_data.get(const.DATA_CHALLENGE_START_DATE) not in [None, {}]
                else None
            ),
            const.DATA_CHALLENGE_END_DATE: (
                challenge_data.get(const.DATA_CHALLENGE_END_DATE)
                if challenge_data.get(const.DATA_CHALLENGE_END_DATE) not in [None, {}]
                else None
            ),
            const.DATA_CHALLENGE_PROGRESS: challenge_data.get(
                const.DATA_CHALLENGE_PROGRESS, {}
            ),
            const.DATA_CHALLENGE_INTERNAL_ID: challenge_id,
        }
        const.LOGGER.debug(
            "DEBUG: Challenge Added - '%s', ID '%s'",
            self._data[const.DATA_CHALLENGES][challenge_id][const.DATA_CHALLENGE_NAME],
            challenge_id,
        )

    def _update_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        challenge_info = self._data[const.DATA_CHALLENGES][challenge_id]
        challenge_info[const.DATA_CHALLENGE_NAME] = challenge_data.get(
            const.DATA_CHALLENGE_NAME, challenge_info[const.DATA_CHALLENGE_NAME]
        )
        challenge_info[const.DATA_CHALLENGE_DESCRIPTION] = challenge_data.get(
            const.DATA_CHALLENGE_DESCRIPTION,
            challenge_info[const.DATA_CHALLENGE_DESCRIPTION],
        )
        challenge_info[const.DATA_CHALLENGE_LABELS] = challenge_data.get(
            const.DATA_CHALLENGE_LABELS,
            challenge_info.get(const.DATA_CHALLENGE_LABELS, []),
        )
        challenge_info[const.DATA_CHALLENGE_ICON] = challenge_data.get(
            const.DATA_CHALLENGE_ICON, challenge_info[const.DATA_CHALLENGE_ICON]
        )
        challenge_info[const.DATA_CHALLENGE_ASSIGNED_KIDS] = challenge_data.get(
            const.DATA_CHALLENGE_ASSIGNED_KIDS,
            challenge_info[const.DATA_CHALLENGE_ASSIGNED_KIDS],
        )
        challenge_info[const.DATA_CHALLENGE_TYPE] = challenge_data.get(
            const.DATA_CHALLENGE_TYPE, challenge_info[const.DATA_CHALLENGE_TYPE]
        )
        challenge_info[const.DATA_CHALLENGE_SELECTED_CHORE_ID] = challenge_data.get(
            const.DATA_CHALLENGE_SELECTED_CHORE_ID,
            challenge_info.get(
                const.DATA_CHALLENGE_SELECTED_CHORE_ID, const.CONF_EMPTY
            ),
        )
        challenge_info[const.DATA_CHALLENGE_CRITERIA] = challenge_data.get(
            const.DATA_CHALLENGE_CRITERIA, challenge_info[const.DATA_CHALLENGE_CRITERIA]
        )
        challenge_info[const.DATA_CHALLENGE_TARGET_VALUE] = challenge_data.get(
            const.DATA_CHALLENGE_TARGET_VALUE,
            challenge_info[const.DATA_CHALLENGE_TARGET_VALUE],
        )
        challenge_info[const.DATA_CHALLENGE_REWARD_POINTS] = challenge_data.get(
            const.DATA_CHALLENGE_REWARD_POINTS,
            challenge_info[const.DATA_CHALLENGE_REWARD_POINTS],
        )
        challenge_info[const.DATA_CHALLENGE_START_DATE] = (
            challenge_data.get(const.DATA_CHALLENGE_START_DATE)
            if challenge_data.get(const.DATA_CHALLENGE_START_DATE) not in [None, {}]
            else None
        )
        challenge_info[const.DATA_CHALLENGE_END_DATE] = (
            challenge_data.get(const.DATA_CHALLENGE_END_DATE)
            if challenge_data.get(const.DATA_CHALLENGE_END_DATE) not in [None, {}]
            else None
        )
        const.LOGGER.debug(
            "DEBUG: Challenge Updated - '%s', ID '%s'",
            challenge_info[const.DATA_CHALLENGE_NAME],
            challenge_id,
        )

    # -------------------------------------------------------------------------------------
    # Properties for Easy Access
    # -------------------------------------------------------------------------------------

    @property
    def kids_data(self) -> dict[str, Any]:
        """Return the kids data."""
        return self._data.get(const.DATA_KIDS, {})

    @property
    def parents_data(self) -> dict[str, Any]:
        """Return the parents data."""
        return self._data.get(const.DATA_PARENTS, {})

    @property
    def chores_data(self) -> dict[str, Any]:
        """Return the chores data."""
        return self._data.get(const.DATA_CHORES, {})

    @property
    def badges_data(self) -> dict[str, Any]:
        """Return the badges data."""
        return self._data.get(const.DATA_BADGES, {})

    @property
    def rewards_data(self) -> dict[str, Any]:
        """Return the rewards data."""
        return self._data.get(const.DATA_REWARDS, {})

    @property
    def penalties_data(self) -> dict[str, Any]:
        """Return the penalties data."""
        return self._data.get(const.DATA_PENALTIES, {})

    @property
    def achievements_data(self) -> dict[str, Any]:
        """Return the achievements data."""
        return self._data.get(const.DATA_ACHIEVEMENTS, {})

    @property
    def challenges_data(self) -> dict[str, Any]:
        """Return the challenges data."""
        return self._data.get(const.DATA_CHALLENGES, {})

    @property
    def bonuses_data(self) -> dict[str, Any]:
        """Return the bonuses data."""
        return self._data.get(const.DATA_BONUSES, {})

    # -------------------------------------------------------------------------------------
    # Chores: Claim, Approve, Disapprove, Compute Global State for Shared Chores
    # -------------------------------------------------------------------------------------

    def claim_chore(self, kid_id: str, chore_id: str, user_name: str):
        """Kid claims chore => state=claimed; parent must then approve."""
        if chore_id not in self.chores_data:
            const.LOGGER.warning(
                "WARNING: Claim Chore - Chore ID '%s' not found", chore_id
            )
            raise HomeAssistantError(f"Chore ID '{chore_id}' not found.")

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            const.LOGGER.warning(
                "WARNING: Claim Chore - Chore ID '%s' not assigned to kid ID '%s'",
                chore_id,
                kid_id,
            )
            raise HomeAssistantError(
                f"Chore '{chore_info.get(const.DATA_CHORE_NAME)}' is not assigned to kid '{self.kids_data[kid_id][const.DATA_KID_NAME]}'."
            )

        if kid_id not in self.kids_data:
            const.LOGGER.warning("WARNING: Kid ID '%s' not found", kid_id)
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        kid_info = self.kids_data.get(kid_id)

        self._normalize_kid_lists(kid_info)

        allow_multiple = chore_info.get(
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False
        )
        if allow_multiple:
            # If already approved, remove it so the new claim can trigger a new approval flow
            kid_info[const.DATA_KID_APPROVED_CHORES] = [
                item
                for item in kid_info.get(const.DATA_KID_APPROVED_CHORES, [])
                if item != chore_id
            ]

        if not allow_multiple:
            if chore_id in kid_info.get(
                const.DATA_KID_CLAIMED_CHORES, []
            ) or chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                error_message = f"WARNING: Claim Chore - Chore '{chore_info[const.DATA_CHORE_NAME]}' has already been claimed today. Multiple claims not allowed."
                const.LOGGER.warning(error_message)
                raise HomeAssistantError(error_message)

        self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_CLAIMED)

        # Send a notification to the parents that a kid claimed a chore
        if chore_info.get(const.CONF_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM):
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                },
            ]
            # Pass extra context so the event handler can route the action.
            extra_data = {
                const.DATA_KID_ID: kid_id,
                const.DATA_CHORE_ID: chore_id,
            }
            self.hass.async_create_task(
                self._notify_parents(
                    kid_id,
                    title="KidsChores: Chore Claimed",
                    message=f"'{self.kids_data[kid_id][const.DATA_KID_NAME]}' claimed chore '{self.chores_data[chore_id][const.DATA_CHORE_NAME]}'",
                    actions=actions,
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def approve_chore(
        self,
        parent_name: str,
        kid_id: str,
        chore_id: str,
        points_awarded: Optional[float] = None,
    ):
        """Approve a chore for kid_id if assigned."""
        if chore_id not in self.chores_data:
            raise HomeAssistantError(f"Chore ID '{chore_id}' not found.")

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            raise HomeAssistantError(
                f"Chore '{chore_info.get(const.DATA_CHORE_NAME)}' is not assigned to kid '{self.kids_data[kid_id][const.DATA_KID_NAME]}'."
            )

        if kid_id not in self.kids_data:
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        kid_info = self.kids_data.get(kid_id)

        allow_multiple = chore_info.get(
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False
        )
        if not allow_multiple:
            if chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                error_message = f"WARNING: Claim Chore - Chore '{chore_info[const.DATA_CHORE_NAME]}' has already been approved today. Multiple approvals not allowed."
                const.LOGGER.warning(error_message)
                raise HomeAssistantError(error_message)

        default_points = chore_info.get(
            const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
        )

        # Note - multiplier will be added in the _update_kid_points method called from _process_chore_state
        self._process_chore_state(
            kid_id, chore_id, const.CHORE_STATE_APPROVED, points_awarded=default_points
        )

        # Manage Achievements
        today_local = kh.get_today_local_date()
        for achievement_id, achievement_info in self.achievements_data.items():
            if (
                achievement_info.get(const.DATA_ACHIEVEMENT_TYPE)
                == const.ACHIEVEMENT_TYPE_STREAK
            ):
                selected_chore_id = achievement_info.get(
                    const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID
                )
                if selected_chore_id == chore_id:
                    # Get or create the progress dict for this kid
                    progress = achievement_info.setdefault(
                        const.DATA_ACHIEVEMENT_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_KID_CURRENT_STREAK: const.DEFAULT_ZERO,
                            const.DATA_KID_LAST_STREAK_DATE: None,
                            const.DATA_ACHIEVEMENT_AWARDED: False,
                        },
                    )
                    self._update_streak_progress(progress, today_local)

        # Manage Challenges
        today_local_iso = kh.get_today_local_iso()
        for challenge_id, challenge_info in self.challenges_data.items():
            challenge_type = challenge_info.get(const.DATA_CHALLENGE_TYPE)

            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                selected_chore = challenge_info.get(
                    const.DATA_CHALLENGE_SELECTED_CHORE_ID
                )
                if selected_chore and selected_chore != chore_id:
                    continue

                start_date_utc = kh.parse_datetime_to_utc(
                    challenge_info.get(const.DATA_CHALLENGE_START_DATE)
                )

                end_date_utc = kh.parse_datetime_to_utc(
                    challenge_info.get(const.DATA_CHALLENGE_END_DATE)
                )

                now_utc = dt_util.utcnow()

                if (
                    start_date_utc
                    and end_date_utc
                    and start_date_utc <= now_utc <= end_date_utc
                ):
                    progress = challenge_info.setdefault(
                        const.DATA_CHALLENGE_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_CHALLENGE_COUNT: const.DEFAULT_ZERO,
                            const.DATA_CHALLENGE_AWARDED: False,
                        },
                    )
                    progress[const.DATA_CHALLENGE_COUNT] += 1

            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                selected_chore = challenge_info.get(
                    const.DATA_CHALLENGE_SELECTED_CHORE_ID
                )
                if not selected_chore:
                    const.LOGGER.warning(
                        "WARNING: Challenge '%s' of type daily minimum has no selected chore id. Skipping progress update.",
                        challenge_info.get(const.DATA_CHALLENGE_NAME),
                    )
                    continue

                if selected_chore != chore_id:
                    continue

                if kid_id in challenge_info.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                    progress = challenge_info.setdefault(
                        const.DATA_CHALLENGE_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_CHALLENGE_DAILY_COUNTS: {},
                            const.DATA_CHALLENGE_AWARDED: False,
                        },
                    )
                    progress[const.DATA_CHALLENGE_DAILY_COUNTS][today_local_iso] = (
                        progress[const.DATA_CHALLENGE_DAILY_COUNTS].get(
                            today_local_iso, const.DEFAULT_ZERO
                        )
                        + 1
                    )

        # Send a notification to the kid that chore was approved
        if chore_info.get(
            const.CONF_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
        ):
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Chore Approved",
                    message=f"Your chore '{chore_info[const.DATA_CHORE_NAME]}' was approved. You earned {default_points} points plus multiplier.",
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def disapprove_chore(self, parent_name: str, kid_id: str, chore_id: str):
        """Disapprove a chore for kid_id."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            raise HomeAssistantError(f"Chore ID '{chore_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        # Send a notification to the kid that chore was disapproved
        if chore_info.get(
            const.CONF_NOTIFY_ON_DISAPPROVAL, const.DEFAULT_NOTIFY_ON_DISAPPROVAL
        ):
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Chore Disapproved",
                    message=f"Your chore '{chore_info[const.DATA_CHORE_NAME]}' was disapproved.",
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def update_chore_state(self, chore_id: str, state: str):
        """Manually override a chore's state."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            const.LOGGER.warning(
                "WARNING: Update Chore State -  Chore ID '%s' not found", chore_id
            )
            return
        # Set state for all kids assigned to the chore:
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, state)
        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.debug(
            "DEBUG: Chore ID '%s' manually updated to '%s'", chore_id, state
        )

    # -------------------------------------------------------------------------------------
    # Chore State Processing: Centralized Function
    # The most critical thing to understand when working on this function is that
    # chore_info[const.DATA_CHORE_STATE] is actually the global state of the chore. The individual chore
    # state per kid is always calculated based on whether they have any claimed, approved, or
    # overdue chores listed for them.
    #
    # Global state will only match if a single kid is assigned to the chore, or all kids
    # assigned are in the same state.
    # -------------------------------------------------------------------------------------

    def _process_chore_state(
        self,
        kid_id: str,
        chore_id: str,
        new_state: str,
        *,
        points_awarded: Optional[float] = None,
    ) -> None:
        """Centralized function to update a chore’s state for a given kid."""

        # Add a flag to control debug messages
        debug_enabled = False

        if debug_enabled:
            const.LOGGER.debug(
                "DEBUG: Chore State - Processing - Kid ID '%s', Chore ID '%s', State '%s', Points Awarded '%s'",
                kid_id,
                chore_id,
                new_state,
                points_awarded,
            )

        kid_info = self.kids_data.get(kid_id)
        chore_info = self.chores_data.get(chore_id)

        if not kid_info or not chore_info:
            const.LOGGER.warning(
                "WARNING: Chore State - Change skipped. Kid ID '%s' or Chore ID '%s' not found",
                kid_id,
                chore_id,
            )
            return

        # Update kid chore tracking data
        # Pass 0 for points_awarded if None and not in APPROVED state
        actual_points = points_awarded if points_awarded is not None else 0.0

        # Get due date from chore info to pass to kid chore data
        due_date = chore_info.get(const.DATA_CHORE_DUE_DATE)

        # Update the kid's chore history
        self._update_chore_data_for_kid(
            kid_id=kid_id,
            chore_id=chore_id,
            points_awarded=actual_points,
            state=new_state,
            due_date=due_date,
        )

        # Clear any overdue tracking.
        kid_info.setdefault(const.DATA_KID_OVERDUE_CHORES, [])
        # kid_info.setdefault(const.DATA_KID_OVERDUE_NOTIFICATIONS, {})

        # Remove all instances of the chore from overdue lists.
        kid_info[const.DATA_KID_OVERDUE_CHORES] = [
            entry
            for entry in kid_info.get(const.DATA_KID_OVERDUE_CHORES, [])
            if entry != chore_id
        ]

        # Clear any overdue tracking *only* when not processing an overdue state.
        if new_state != const.CHORE_STATE_OVERDUE:
            kid_info.setdefault(const.DATA_KID_OVERDUE_NOTIFICATIONS, {})
            if chore_id in kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS]:
                kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS].pop(chore_id)

        if new_state == const.CHORE_STATE_CLAIMED:
            # Remove all previous approvals in case of duplicate, add to claimed.
            kid_info[const.DATA_KID_APPROVED_CHORES] = [
                item
                for item in kid_info.get(const.DATA_KID_APPROVED_CHORES, [])
                if item != chore_id
            ]

            kid_info.setdefault(const.DATA_KID_CLAIMED_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_CLAIMED_CHORES]:
                kid_info[const.DATA_KID_CLAIMED_CHORES].append(chore_id)

            chore_info[const.DATA_CHORE_LAST_CLAIMED] = dt_util.utcnow().isoformat()

            self._data.setdefault(const.DATA_PENDING_CHORE_APPROVALS, []).append(
                {
                    const.DATA_KID_ID: kid_id,
                    const.DATA_CHORE_ID: chore_id,
                    const.DATA_CHORE_TIMESTAMP: dt_util.utcnow().isoformat(),
                }
            )

        elif new_state == const.CHORE_STATE_APPROVED:
            # Remove all claims for chores in case of duplicates, add to approvals.
            kid_info[const.DATA_KID_CLAIMED_CHORES] = [
                item
                for item in kid_info.get(const.DATA_KID_CLAIMED_CHORES, [])
                if item != chore_id
            ]

            kid_info.setdefault(const.DATA_KID_APPROVED_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_APPROVED_CHORES]:
                kid_info[const.DATA_KID_APPROVED_CHORES].append(chore_id)

            # Increment Chore Approvals
            if chore_id in kid_info[const.DATA_KID_CHORE_APPROVALS_LEGACY]:
                kid_info[const.DATA_KID_CHORE_APPROVALS_LEGACY][chore_id] += 1
            else:
                kid_info[const.DATA_KID_CHORE_APPROVALS_LEGACY][chore_id] = 1

            chore_info[const.DATA_CHORE_LAST_COMPLETED] = dt_util.utcnow().isoformat()

            if points_awarded is not None:
                self.update_kid_points(
                    kid_id, delta=points_awarded, source=const.POINTS_SOURCE_CHORES
                )

            self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
                ap
                for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
                if not (
                    ap.get(const.DATA_KID_ID) == kid_id
                    and ap.get(const.DATA_CHORE_ID) == chore_id
                )
            ]

        elif new_state == const.CHORE_STATE_PENDING:
            # Remove the chore from both claimed and approved lists.
            for field in [
                const.DATA_KID_CLAIMED_CHORES,
                const.DATA_KID_APPROVED_CHORES,
            ]:
                if chore_id in kid_info.get(field, []):
                    kid_info[field] = [c for c in kid_info[field] if c != chore_id]

            # Remove from pending approvals.
            self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
                ap
                for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
                if not (
                    ap.get(const.DATA_KID_ID) == kid_id
                    and ap.get(const.DATA_CHORE_ID) == chore_id
                )
            ]

        elif new_state == const.CHORE_STATE_OVERDUE:
            # Mark as overdue.
            kid_info.setdefault(const.DATA_KID_OVERDUE_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_OVERDUE_CHORES]:
                kid_info[const.DATA_KID_OVERDUE_CHORES].append(chore_id)

        # Compute and update the chore's global state.
        # Given the process above is handling everything properly for each kid, computing the global state straightforward.
        # This process needs run every time a chore state changes, so it no longer warrants a separate function.
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        if len(assigned_kids) == 1:
            # if only one kid is assigned to the chore, update the chore state to new state 1:1
            chore_info[const.DATA_CHORE_STATE] = new_state
        elif len(assigned_kids) > 1:
            # For chores assigned to multiple kids, you have to figure out the global state
            count_pending = count_claimed = count_approved = count_overdue = (
                const.DEFAULT_ZERO
            )
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})
                if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                    count_overdue += 1
                elif chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                    count_approved += 1
                elif chore_id in kid_info.get(const.DATA_KID_CLAIMED_CHORES, []):
                    count_claimed += 1
                else:
                    count_pending += 1
            total = len(assigned_kids)

            # If all kids are in the same state, update the chore state to new state 1:1
            if (
                count_pending == total
                or count_claimed == total
                or count_approved == total
                or count_overdue == total
            ):
                chore_info[const.DATA_CHORE_STATE] = new_state

            # For shared chores, recompute global state of a partial if they aren't all in the same state as checked above
            elif chore_info.get(const.DATA_CHORE_SHARED_CHORE, False):
                if count_overdue > const.DEFAULT_ZERO:
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_OVERDUE
                elif count_approved > const.DEFAULT_ZERO:
                    chore_info[const.DATA_CHORE_STATE] = (
                        const.CHORE_STATE_APPROVED_IN_PART
                    )
                elif count_claimed > const.DEFAULT_ZERO:
                    chore_info[const.DATA_CHORE_STATE] = (
                        const.CHORE_STATE_CLAIMED_IN_PART
                    )
                else:
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_UNKNOWN

            # For non-shared chores multiple assign it will be independent if they aren't all in the same state as checked above.
            elif chore_info.get(const.DATA_CHORE_SHARED_CHORE, False) is False:
                chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_INDEPENDENT

        else:
            chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_UNKNOWN

        if debug_enabled:
            const.LOGGER.debug(
                "DEBUG: Chore State - Chore ID '%s' Global State changed to '%s'",
                chore_id,
                chore_info[const.DATA_CHORE_STATE],
            )

    def _update_chore_data_for_kid(
        self,
        kid_id: str,
        chore_id: str,
        points_awarded: float,
        state: Optional[str] = None,
        due_date: Optional[str] = None,
    ):
        """
        Update a kid's chore data when a state change or completion occurs.

        Args:
            kid_id: The ID of the kid
            chore_id: The ID of the chore
            points_awarded: Points awarded for this chore
            state: New chore state (if state is changing)
            due_date: New due date (if due date is changing)
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Get chore name for reference
        chore_info = self.chores_data.get(chore_id, {})
        chore_name = chore_info.get(const.DATA_CHORE_NAME, chore_id)

        # Initialize chore data structure if needed
        kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})

        # Initialize this chore's data if it doesn't exist yet
        kid_chore_data = kid_chores_data.setdefault(
            chore_id,
            {
                const.DATA_KID_CHORE_DATA_NAME: chore_name,
                const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
                const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
                const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
                const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
                const.DATA_KID_CHORE_DATA_PERIODS: {
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
                },
                const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
            },
        )

        # --- Use a consistent default dict for all period stats ---
        period_default = {
            const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
            const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
        }

        # Get period keys using constants
        now_utc = dt_util.utcnow()
        now_iso = now_utc.isoformat()
        now_local = kh.get_now_local_time()
        today_local = kh.get_today_local_date()
        today_local_iso = today_local.isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        # For updating period stats
        periods_data = kid_chore_data[const.DATA_KID_CHORE_DATA_PERIODS]
        period_keys = [
            (const.DATA_KID_CHORE_DATA_PERIODS_DAILY, today_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, week_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, month_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, year_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME, const.PERIOD_ALL_TIME),
        ]

        previous_state = kid_chore_data.get(const.DATA_KID_CHORE_DATA_STATE)
        points_awarded = round(points_awarded, 1) if points_awarded is not None else 0.0

        # --- All-time stats update helpers ---
        chore_stats = kid_info.setdefault(const.DATA_KID_CHORE_STATS, {})

        def inc_stat(key, amount):
            chore_stats[key] = chore_stats.get(key, 0) + amount

        # Helper to update period stats safely for all periods
        def update_periods(increments: dict, periods: list):
            for period_key, period_id in periods:
                period_data_dict = periods_data[period_key].setdefault(
                    period_id, period_default.copy()
                )
                for key, val in period_default.items():
                    period_data_dict.setdefault(key, val)
                for inc_key, inc_val in increments.items():
                    period_data_dict[inc_key] += inc_val

        if state is not None:
            kid_chore_data[const.DATA_KID_CHORE_DATA_STATE] = state

            # --- Handle CLAIMED state ---
            if state == const.CHORE_STATE_CLAIMED:
                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = now_iso
                update_periods(
                    {const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 1},
                    period_keys,
                )
                # Increment all-time claimed count
                inc_stat(const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME, 1)

            # --- Handle APPROVED state ---
            elif state == const.CHORE_STATE_APPROVED:
                # LEGACY: Deprecate in the future
                kid_info[const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY] += 1
                kid_info[const.DATA_KID_COMPLETED_CHORES_WEEKLY_LEGACY] += 1
                kid_info[const.DATA_KID_COMPLETED_CHORES_MONTHLY_LEGACY] += 1
                kid_info[const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY] += 1

                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_APPROVED] = now_iso

                inc_stat(const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, 1)
                inc_stat(
                    const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME,
                    points_awarded,
                )

                # Update period stats for count and points
                update_periods(
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 1,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: points_awarded,
                    },
                    period_keys,
                )

                # Calculate today's streak based on yesterday's daily period data
                yesterday_local_iso = kh.adjust_datetime_by_interval(
                    today_local_iso,
                    interval_unit=const.CONF_DAYS,
                    delta=-1,
                    require_future=False,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )
                yesterday_chore_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].get(yesterday_local_iso, {})
                yesterday_streak = yesterday_chore_data.get(
                    const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
                )
                today_streak = yesterday_streak + 1 if yesterday_streak > 0 else 1

                # Store today's streak as the daily longest streak
                daily_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(today_local_iso, period_default.copy())
                daily_data[const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK] = (
                    today_streak
                )

                # --- All-time longest streak update (per-chore and per-kid) ---
                all_time_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME
                ].setdefault(const.PERIOD_ALL_TIME, period_default.copy())
                prev_all_time_streak = all_time_data.get(
                    const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
                )
                if today_streak > prev_all_time_streak:
                    all_time_data[const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK] = (
                        today_streak
                    )
                    kid_chore_data[
                        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME
                    ] = today_local_iso

                # Update streak for higher periods if needed (excluding all_time, already handled above)
                for period_key, period_id in [
                    (const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, week_local_iso),
                    (const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, month_local_iso),
                    (const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, year_local_iso),
                ]:
                    period_data_dict = periods_data[period_key].setdefault(
                        period_id, period_default.copy()
                    )
                    if today_streak > period_data_dict.get(
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
                    ):
                        period_data_dict[
                            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK
                        ] = today_streak

                # Still update the kid's global all-time longest streak if this is a new record
                longest_streak_all_time = chore_stats.get(
                    const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME, 0
                )
                if today_streak > longest_streak_all_time:
                    chore_stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME] = (
                        today_streak
                    )

            # --- Handle OVERDUE state ---
            elif state == const.CHORE_STATE_OVERDUE:
                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_OVERDUE] = now_iso
                daily_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(today_local_iso, period_default.copy())
                for key, val in period_default.items():
                    daily_data.setdefault(key, val)
                first_overdue_today = (
                    daily_data.get(const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0) < 1
                )
                if first_overdue_today:
                    daily_data[const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE] = 1
                    # Only increment higher periods if this is the first overdue for today
                    update_periods(
                        {const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 1},
                        period_keys[1:],  # skip daily
                    )
                    inc_stat(const.DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME, 1)

            # --- Handle DISAPPROVED (claimed -> pending) state ---
            elif (
                state == const.CHORE_STATE_PENDING
                and previous_state == const.CHORE_STATE_CLAIMED
            ):
                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED] = now_iso
                daily_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(today_local_iso, period_default.copy())
                for key, val in period_default.items():
                    daily_data.setdefault(key, val)
                first_disapproved_today = (
                    daily_data.get(const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0) < 1
                )
                if first_disapproved_today:
                    daily_data[const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED] = 1
                    update_periods(
                        {const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 1},
                        period_keys[1:],  # skip daily
                    )
                    inc_stat(const.DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME, 1)

        # Update due date if provided
        if due_date is not None:
            kid_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = due_date

        # Clean up old period data to keep storage manageable
        kh.cleanup_period_data(
            self,
            periods_data=periods_data,
            period_keys={
                const.CONF_DAILY: const.DATA_KID_CHORE_DATA_PERIODS_DAILY,
                const.CONF_WEEKLY: const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY,
                const.CONF_MONTHLY: const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY,
                const.CONF_YEARLY: const.DATA_KID_CHORE_DATA_PERIODS_YEARLY,
            },
        )

        # --- Update kid_chore_stats after all per-chore updates ---
        self._recalculate_chore_stats_for_kid(kid_id)

    def _recalculate_chore_stats_for_kid(self, kid_id: str):
        """Aggregate and update all kid_chore_stats for a given kid.

        This function always resets all stat keys to zero/default and then
        aggregates from the current state of all chore data. This ensures
        stats are never double-counted, even if this function is called
        multiple times per state change.

        Note: All-time stats (completed_all_time, total_points_all_time, longest_streak_all_time)
        must be stored incrementally and not reset here, since old period data may be pruned.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # --- Reset all stat keys (prevents double counting) Exception for All-time stats which are always kept and updated as necessary---
        # --- All-time stats could be calculated from individual chore all-time stats, but then deleted chore data would also need to be stored.
        stats = {
            const.DATA_KID_CHORE_STATS_APPROVED_TODAY: 0,
            const.DATA_KID_CHORE_STATS_APPROVED_WEEK: 0,
            const.DATA_KID_CHORE_STATS_APPROVED_MONTH: 0,
            const.DATA_KID_CHORE_STATS_APPROVED_YEAR: 0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, 0),
            # --- Claimed counts ---
            const.DATA_KID_CHORE_STATS_CLAIMED_TODAY: 0,
            const.DATA_KID_CHORE_STATS_CLAIMED_WEEK: 0,
            const.DATA_KID_CHORE_STATS_CLAIMED_MONTH: 0,
            const.DATA_KID_CHORE_STATS_CLAIMED_YEAR: 0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME, 0),
            # --- Overdue counts ---
            const.DATA_KID_CHORE_STATS_OVERDUE_TODAY: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_WEEK: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_MONTH: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_YEAR: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME, 0),
            # --- Disapproved counts ---
            const.DATA_KID_CHORE_STATS_DISAPPROVED_TODAY: 0,
            const.DATA_KID_CHORE_STATS_DISAPPROVED_WEEK: 0,
            const.DATA_KID_CHORE_STATS_DISAPPROVED_MONTH: 0,
            const.DATA_KID_CHORE_STATS_DISAPPROVED_YEAR: 0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME, 0),
            # --- Longest streaks ---
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_WEEK: 0,
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_MONTH: 0,
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_YEAR: 0,
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME, 0),
            # --- Most completed chore ---
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE: None,
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_WEEK: None,
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_MONTH: None,
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_YEAR: None,
            # --- Total points from chores ---
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_TODAY: 0.0,
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_WEEK: 0.0,
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_MONTH: 0.0,
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_YEAR: 0.0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME, 0.0),
            # --- Average points per day ---
            const.DATA_KID_CHORE_STATS_AVG_PER_DAY_WEEK: 0.0,
            const.DATA_KID_CHORE_STATS_AVG_PER_DAY_MONTH: 0.0,
            # --- Current status stats ---
            const.DATA_KID_CHORE_STATS_CURRENT_DUE_TODAY: 0,
            const.DATA_KID_CHORE_STATS_CURRENT_OVERDUE: 0,
            const.DATA_KID_CHORE_STATS_CURRENT_CLAIMED: 0,
            const.DATA_KID_CHORE_STATS_CURRENT_APPROVED: 0,
        }

        # Get current period keys
        now_local = kh.get_now_local_time()
        today_local_iso = kh.get_today_local_date().isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        # For most completed chore
        most_completed = {}
        most_completed_week = {}
        most_completed_month = {}
        most_completed_year = {}

        # For longest streaks
        max_streak_week = 0
        max_streak_month = 0
        max_streak_year = 0

        # --- Aggregate stats from all chores (no double counting) ---
        for chore_id, chore_data in kid_info.get(const.DATA_KID_CHORE_DATA, {}).items():
            # All-time stats are incremented at event time, not recalculated here

            # Period stats
            periods = chore_data.get(const.DATA_KID_CHORE_DATA_PERIODS, {})

            # Most completed chore (all time)
            all_time = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME, {})
            total_count = all_time.get(const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0)
            most_completed[chore_id] = total_count

            # Daily
            daily = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_DAILY, {})
            today_stats = daily.get(today_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_TODAY] += (
                today_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )

            # Weekly
            weekly = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, {})
            week_stats = weekly.get(week_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_WEEK] += (
                week_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )
            most_completed_week[chore_id] = week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            max_streak_week = max(
                max_streak_week,
                week_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0),
            )

            # Monthly
            monthly = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, {})
            month_stats = monthly.get(month_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_MONTH] += (
                month_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )
            most_completed_month[chore_id] = month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            max_streak_month = max(
                max_streak_month,
                month_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0),
            )

            # Yearly
            yearly = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, {})
            year_stats = yearly.get(year_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_YEAR] += (
                year_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )
            most_completed_year[chore_id] = year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            max_streak_year = max(
                max_streak_year,
                year_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0),
            )

            # --- Current status counts ---
            state = chore_data.get(const.DATA_KID_CHORE_DATA_STATE)
            due_datetime_iso = chore_data.get(
                const.DATA_KID_CHORE_DATA_DUE_DATE
            ) or self.chores_data.get(chore_id, {}).get(const.DATA_CHORE_DUE_DATE)
            due_date_local = kh.normalize_datetime_input(
                due_datetime_iso, return_type=const.HELPER_RETURN_DATETIME_LOCAL
            )
            if due_date_local:
                try:
                    today_local = kh.get_today_local_date()
                    if due_date_local and due_date_local.date() == today_local:
                        stats[const.DATA_KID_CHORE_STATS_CURRENT_DUE_TODAY] += 1
                except Exception:
                    pass
            if state == const.CHORE_STATE_OVERDUE:
                stats[const.DATA_KID_CHORE_STATS_CURRENT_OVERDUE] += 1
            elif state == const.CHORE_STATE_CLAIMED:
                stats[const.DATA_KID_CHORE_STATS_CURRENT_CLAIMED] += 1
            elif state in (
                const.CHORE_STATE_APPROVED,
                const.CHORE_STATE_APPROVED_IN_PART,
            ):
                stats[const.DATA_KID_CHORE_STATS_CURRENT_APPROVED] += 1

        # --- Derived stats (no double counting, just pick max or calculate) ---
        if most_completed:
            most_completed_chore_id = max(most_completed, key=most_completed.get)
            chore_name = self.chores_data.get(most_completed_chore_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_chore_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE] = chore_name
        if most_completed_week:
            most_completed_week_id = max(
                most_completed_week, key=most_completed_week.get
            )
            chore_name = self.chores_data.get(most_completed_week_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_week_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_WEEK] = chore_name
        if most_completed_month:
            most_completed_month_id = max(
                most_completed_month, key=most_completed_month.get
            )
            chore_name = self.chores_data.get(most_completed_month_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_month_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_MONTH] = chore_name
        if most_completed_year:
            most_completed_year_id = max(
                most_completed_year, key=most_completed_year.get
            )
            chore_name = self.chores_data.get(most_completed_year_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_year_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_YEAR] = chore_name

        stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_WEEK] = max_streak_week
        stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_MONTH] = max_streak_month
        stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_YEAR] = max_streak_year

        # Averages (no double counting, just divide)
        stats[const.DATA_KID_CHORE_STATS_AVG_PER_DAY_WEEK] = round(
            (
                stats[const.DATA_KID_CHORE_STATS_APPROVED_WEEK] / 7.0
                if stats[const.DATA_KID_CHORE_STATS_APPROVED_WEEK]
                else 0.0
            ),
            2,
        )
        now = kh.get_now_local_time()
        days_in_month = monthrange(now.year, now.month)[1]
        stats[const.DATA_KID_CHORE_STATS_AVG_PER_DAY_MONTH] = round(
            (
                stats[const.DATA_KID_CHORE_STATS_APPROVED_MONTH] / days_in_month
                if stats[const.DATA_KID_CHORE_STATS_APPROVED_MONTH]
                else 0.0
            ),
            2,
        )

        # --- Save back to kid_info ---
        kid_info[const.DATA_KID_CHORE_STATS] = stats

    # -------------------------------------------------------------------------------------
    # Kids: Update Points
    # -------------------------------------------------------------------------------------

    def update_kid_points(
        self, kid_id: str, delta: float, *, source: str = const.POINTS_SOURCE_OTHER
    ):
        """
        Adjust a kid's points by delta (±), track by-source, update legacy stats,
        record into new point_data history, then recheck badges/achievements/challenges.
        Also updates all-time and highest balance stats using constants.
        If the source is chores, applies the kid's multiplier.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.warning(
                "WARNING: Update Kid Points - Kid ID '%s' not found", kid_id
            )
            return

        # 1) Sanitize delta
        try:
            delta_value = round(float(delta), 1)
        except (ValueError, TypeError):
            const.LOGGER.warning(
                "WARNING: Update Kid Points - Invalid delta '%s' for Kid ID '%s'.",
                delta,
                kid_id,
            )
            return
        if delta_value == 0:
            const.LOGGER.debug(
                "DEBUG: Update Kid Points - No change (delta=0) for Kid ID '%s'", kid_id
            )
            return

        # If source is chores, apply multiplier
        if source == const.POINTS_SOURCE_CHORES:
            multiplier = kid_info.get(const.DATA_KID_POINTS_MULTIPLIER, 1.0)
            delta_value = round(delta_value * float(multiplier), 1)

        # 2) Compute new balance
        try:
            old = round(float(kid_info.get(const.DATA_KID_POINTS, 0.0)), 1)
        except (ValueError, TypeError):
            const.LOGGER.warning(
                "WARNING: Update Kid Points - Invalid old_points for Kid ID '%s'. Defaulting to 0.0.",
                kid_id,
            )
            old = 0.0
        new = old + delta_value
        kid_info[const.DATA_KID_POINTS] = new

        # 3) Update legacy rolling stats
        kid_info.setdefault(const.DATA_KID_POINTS_EARNED_TODAY_LEGACY, 0.0)
        kid_info.setdefault(const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY, 0.0)
        kid_info.setdefault(const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY, 0.0)
        kid_info[const.DATA_KID_POINTS_EARNED_TODAY_LEGACY] += delta_value
        kid_info[const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY] += delta_value
        kid_info[const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY] += delta_value
        kid_info[const.DATA_KID_MAX_POINTS_EVER] += delta_value

        # 4) Legacy cumulative badge logic
        progress = kid_info.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {})
        if delta_value > 0:
            progress.setdefault(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0.0
            )
            progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] += (
                delta_value
            )

        # 5) All-time and highest balance stats (handled incrementally)
        point_stats = kid_info.setdefault(const.DATA_KID_POINT_STATS, {})
        point_stats.setdefault(const.DATA_KID_POINT_STATS_EARNED_ALL_TIME, 0.0)
        point_stats.setdefault(const.DATA_KID_POINT_STATS_SPENT_ALL_TIME, 0.0)
        point_stats.setdefault(const.DATA_KID_POINT_STATS_NET_ALL_TIME, 0.0)
        point_stats.setdefault(const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME, {})
        point_stats.setdefault(const.DATA_KID_POINT_STATS_HIGHEST_BALANCE, 0.0)

        if delta_value > 0:
            point_stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME] += delta_value
        elif delta_value < 0:
            point_stats[const.DATA_KID_POINT_STATS_SPENT_ALL_TIME] += delta_value
        point_stats[const.DATA_KID_POINT_STATS_NET_ALL_TIME] += delta_value

        by_source_all_time = point_stats[const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME]
        by_source_all_time.setdefault(source, 0.0)
        by_source_all_time[source] += delta_value

        if new > point_stats[const.DATA_KID_POINT_STATS_HIGHEST_BALANCE]:
            point_stats[const.DATA_KID_POINT_STATS_HIGHEST_BALANCE] = new

        # 6) Record into new point_data history (use same date logic as chore_data)
        periods_data = kid_info.setdefault(const.DATA_KID_POINT_DATA, {}).setdefault(
            const.DATA_KID_POINT_DATA_PERIODS, {}
        )

        now_local = kh.get_now_local_time()
        today_local_iso = kh.get_today_local_date().isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        period_default = {
            const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL: 0.0,
            const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE: {},
        }

        for period_key, period_id in [
            (const.DATA_KID_POINT_DATA_PERIODS_DAILY, today_local_iso),
            (const.DATA_KID_POINT_DATA_PERIODS_WEEKLY, week_local_iso),
            (const.DATA_KID_POINT_DATA_PERIODS_MONTHLY, month_local_iso),
            (const.DATA_KID_POINT_DATA_PERIODS_YEARLY, year_local_iso),
        ]:
            bucket = periods_data.setdefault(period_key, {})
            entry = bucket.setdefault(period_id, {})
            # Safely initialize fields if missing
            if const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL not in entry:
                entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] = 0.0
            if (
                const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE not in entry
                or not isinstance(
                    entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE], dict
                )
            ):
                entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE] = {}
            entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] += delta_value
            entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE].setdefault(source, 0.0)
            entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE][source] += delta_value

        # 7) Re‑evaluate everything and persist
        self._recalculate_point_stats_for_kid(kid_id)
        kh.cleanup_period_data(
            self,
            periods_data=periods_data,
            period_keys={
                "daily": const.DATA_KID_POINT_DATA_PERIODS_DAILY,
                "weekly": const.DATA_KID_POINT_DATA_PERIODS_WEEKLY,
                "monthly": const.DATA_KID_POINT_DATA_PERIODS_MONTHLY,
                "yearly": const.DATA_KID_POINT_DATA_PERIODS_YEARLY,
            },
        )
        self._check_badges_for_kid(kid_id)
        self._check_achievements_for_kid(kid_id)
        self._check_challenges_for_kid(kid_id)

        self._persist()
        self.async_set_updated_data(self._data)

        const.LOGGER.debug(
            "DEBUG: Update Kid Points - Kid ID '%s': delta=%.2f, old=%.2f, new=%.2f, source=%s",
            kid_id,
            delta_value,
            old,
            new,
            source,
        )

    def _recalculate_point_stats_for_kid(self, kid_id: str):
        """Aggregate and update all kid_point_stats for a given kid.

        This function always resets all stat keys to zero/default and then
        aggregates from the current state of all point data. This ensures
        stats are never double-counted, even if this function is called
        multiple times per state change.

        Note: All-time stats (earned_all_time, spent_all_time, net_all_time, by_source_all_time, highest_balance)
        must be stored incrementally and not reset here, since old period data may be pruned.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})

        stats = {
            # Per-period stats
            const.DATA_KID_POINT_STATS_EARNED_TODAY: 0.0,
            const.DATA_KID_POINT_STATS_EARNED_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_EARNED_MONTH: 0.0,
            const.DATA_KID_POINT_STATS_EARNED_YEAR: 0.0,
            # All-time stats (handled incrementally in update_kid_points, not recalculated here)
            const.DATA_KID_POINT_STATS_EARNED_ALL_TIME: point_stats.get(
                const.DATA_KID_POINT_STATS_EARNED_ALL_TIME, 0.0
            ),
            # By-source breakdowns
            const.DATA_KID_POINT_STATS_BY_SOURCE_TODAY: {},
            const.DATA_KID_POINT_STATS_BY_SOURCE_WEEK: {},
            const.DATA_KID_POINT_STATS_BY_SOURCE_MONTH: {},
            const.DATA_KID_POINT_STATS_BY_SOURCE_YEAR: {},
            # All-time by-source (handled incrementally)
            const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME: point_stats.get(
                const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME, {}
            ).copy(),
            # Spent (negative deltas)
            const.DATA_KID_POINT_STATS_SPENT_TODAY: 0.0,
            const.DATA_KID_POINT_STATS_SPENT_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_SPENT_MONTH: 0.0,
            const.DATA_KID_POINT_STATS_SPENT_YEAR: 0.0,
            # All-time spent (handled incrementally)
            const.DATA_KID_POINT_STATS_SPENT_ALL_TIME: point_stats.get(
                const.DATA_KID_POINT_STATS_SPENT_ALL_TIME, 0.0
            ),
            # Net (earned - spent)
            const.DATA_KID_POINT_STATS_NET_TODAY: 0.0,
            const.DATA_KID_POINT_STATS_NET_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_NET_MONTH: 0.0,
            const.DATA_KID_POINT_STATS_NET_YEAR: 0.0,
            # All-time net (This is calculated even though it is an all time stat)
            const.DATA_KID_POINT_STATS_NET_ALL_TIME: 0.0,
            # Highest balance ever (handled incrementally)
            const.DATA_KID_POINT_STATS_HIGHEST_BALANCE: point_stats.get(
                const.DATA_KID_POINT_STATS_HIGHEST_BALANCE, 0.0
            ),
            # Averages (calculated below)
            const.DATA_KID_POINT_STATS_AVG_PER_DAY_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_AVG_PER_DAY_MONTH: 0.0,
            # Streaks and avg per chore are optional, not implemented here
            # const.DATA_KID_POINT_STATS_EARNING_STREAK_CURRENT: 0,
            # const.DATA_KID_POINT_STATS_EARNING_STREAK_LONGEST: 0,
            # const.DATA_KID_POINT_STATS_AVG_PER_CHORE: 0.0,
        }

        pts_periods = kid_info.get(const.DATA_KID_POINT_DATA, {}).get(
            const.DATA_KID_POINT_DATA_PERIODS, {}
        )

        now_local = kh.get_now_local_time()
        today_local_iso = kh.get_today_local_date().isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        def get_period(period_key, period_id):
            period = pts_periods.get(period_key, {})
            entry = period.get(period_id, {})
            by_source = entry.get(const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE, {})
            earned = sum(v for v in by_source.values() if v > 0)
            spent = sum(v for v in by_source.values() if v < 0)
            net = entry.get(const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL, 0.0)
            return earned, spent, net, by_source.copy()

        # Daily
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_DAILY, today_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_TODAY] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_TODAY] = spent
        stats[const.DATA_KID_POINT_STATS_NET_TODAY] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_TODAY] = by_source

        # Weekly
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_WEEKLY, week_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_WEEK] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_WEEK] = spent
        stats[const.DATA_KID_POINT_STATS_NET_WEEK] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_WEEK] = by_source

        # Monthly
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_MONTHLY, month_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_MONTH] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_MONTH] = spent
        stats[const.DATA_KID_POINT_STATS_NET_MONTH] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_MONTH] = by_source

        # Yearly
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_YEARLY, year_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_YEAR] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_YEAR] = spent
        stats[const.DATA_KID_POINT_STATS_NET_YEAR] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_YEAR] = by_source

        # --- All-time Net stats ---
        stats[const.DATA_KID_POINT_STATS_NET_ALL_TIME] = (
            stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME]
            + stats[const.DATA_KID_POINT_STATS_SPENT_ALL_TIME]
        )

        # --- Averages ---
        stats[const.DATA_KID_POINT_STATS_AVG_PER_DAY_WEEK] = (
            round(stats[const.DATA_KID_POINT_STATS_EARNED_WEEK] / 7.0, 2)
            if stats[const.DATA_KID_POINT_STATS_EARNED_WEEK]
            else 0.0
        )
        now = kh.get_now_local_time()
        days_in_month = monthrange(now.year, now.month)[1]
        stats[const.DATA_KID_POINT_STATS_AVG_PER_DAY_MONTH] = (
            round(stats[const.DATA_KID_POINT_STATS_EARNED_MONTH] / days_in_month, 2)
            if stats[const.DATA_KID_POINT_STATS_EARNED_MONTH]
            else 0.0
        )

        # --- Save back to kid_info ---
        kid_info[const.DATA_KID_POINT_STATS] = stats

    # -------------------------------------------------------------------------------------
    # Rewards: Redeem, Approve, Disapprove
    # -------------------------------------------------------------------------------------

    def redeem_reward(self, parent_name: str, kid_id: str, reward_id: str):
        """Kid claims a reward => mark as pending approval (no deduction yet)."""
        reward_info = self.rewards_data.get(reward_id)
        if not reward_info:
            raise HomeAssistantError(f"Reward ID '{reward_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        cost = reward_info.get(const.DATA_REWARD_COST, const.DEFAULT_ZERO)
        if kid_info[const.DATA_KID_POINTS] < cost:
            raise HomeAssistantError(
                f"'{kid_info[const.DATA_KID_NAME]}' does not have enough points ({cost} needed)."
            )

        kid_info.setdefault(const.DATA_KID_PENDING_REWARDS, []).append(reward_id)
        kid_info.setdefault(const.DATA_KID_REDEEMED_REWARDS, [])

        # Generate a unique notification ID for this claim.
        notif_id = uuid.uuid4().hex

        # Add to pending approvals
        self._data[const.DATA_PENDING_REWARD_APPROVALS].append(
            {
                const.DATA_KID_ID: kid_id,
                const.DATA_REWARD_ID: reward_id,
                const.DATA_REWARD_TIMESTAMP: dt_util.utcnow().isoformat(),
                const.DATA_REWARD_NOTIFICATION_ID: notif_id,
            }
        )

        # increment reward_claims counter
        if reward_id in kid_info[const.DATA_KID_REWARD_CLAIMS]:
            kid_info[const.DATA_KID_REWARD_CLAIMS][reward_id] += 1
        else:
            kid_info[const.DATA_KID_REWARD_CLAIMS][reward_id] = 1

        # Send a notification to the parents that a kid claimed a reward
        actions = [
            {
                const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
            },
            {
                const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
            },
            {
                const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
            },
        ]
        extra_data = {
            const.DATA_KID_ID: kid_id,
            const.DATA_REWARD_ID: reward_id,
            const.DATA_REWARD_NOTIFICATION_ID: notif_id,
        }
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Reward Claimed",
                message=f"'{kid_info[const.DATA_KID_NAME]}' claimed reward '{reward_info[const.DATA_REWARD_NAME]}'",
                actions=actions,
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def approve_reward(
        self,
        parent_name: str,
        kid_id: str,
        reward_id: str,
        notif_id: Optional[str] = None,
    ):
        """Parent approves the reward => deduct points."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        reward_info = self.rewards_data.get(reward_id)
        if not reward_info:
            raise HomeAssistantError(f"Reward ID '{reward_id}' not found.")

        cost = reward_info.get(const.DATA_REWARD_COST, const.DEFAULT_ZERO)

        pending_count = kid_info.get(const.DATA_KID_PENDING_REWARDS, []).count(
            reward_id
        )
        if pending_count > 0:
            if kid_info[const.DATA_KID_POINTS] < cost:
                raise HomeAssistantError(
                    f"'{kid_info[const.DATA_KID_NAME]}' does not have enough points to redeem '{reward_info[const.DATA_REWARD_NAME]}'."
                )

            # Deduct points for one claim.
            if cost is not None:
                self.update_kid_points(
                    kid_id, delta=-cost, source=const.POINTS_SOURCE_REWARDS
                )

            # Remove one occurrence from the kid's pending rewards list and add to redeemed.
            kid_info[const.DATA_KID_PENDING_REWARDS].remove(reward_id)
            kid_info.setdefault(const.DATA_KID_REDEEMED_REWARDS, []).append(reward_id)

        else:
            # Direct approval (no pending claim present).
            if kid_info[const.DATA_KID_POINTS] < cost:
                raise HomeAssistantError(
                    f"'{kid_info[const.DATA_KID_NAME]}' does not have enough points to redeem '{reward_info[const.DATA_REWARD_NAME]}'."
                )
            kid_info[const.DATA_KID_POINTS] -= cost
            kid_info[const.DATA_KID_REDEEMED_REWARDS].append(reward_id)

        # Remove only one matching pending reward approval from global approvals.
        approvals = self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        for i, ap in enumerate(approvals):
            if (
                ap.get(const.DATA_KID_ID) == kid_id
                and ap.get(const.DATA_REWARD_ID) == reward_id
            ):
                # If a notification ID was passed, only remove the matching one.
                if notif_id is not None:
                    if ap.get(const.DATA_REWARD_NOTIFICATION_ID) == notif_id:
                        del approvals[i]
                        break
                else:
                    del approvals[i]
                    break

        # Increment reward approval counter for the kid.
        if reward_id in kid_info[const.DATA_KID_REWARD_APPROVALS]:
            kid_info[const.DATA_KID_REWARD_APPROVALS][reward_id] += 1
        else:
            kid_info[const.DATA_KID_REWARD_APPROVALS][reward_id] = 1

        # Check badges
        self._check_badges_for_kid(kid_id)

        # Notify the kid that the reward has been approved
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Reward Approved",
                message=f"Your reward '{reward_info[const.DATA_REWARD_NAME]}' was approved.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def disapprove_reward(self, parent_name: str, kid_id: str, reward_id: str):
        """Disapprove a reward for kid_id."""

        reward_info = self.rewards_data.get(reward_id)
        if not reward_info:
            raise HomeAssistantError(f"Reward ID '{reward_id}' not found.")

        # Remove only one entry of each reward claim from pending approvals
        approvals = self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        for i, ap in enumerate(approvals):
            if (
                ap.get(const.DATA_KID_ID) == kid_id
                and ap.get(const.DATA_REWARD_ID) == reward_id
            ):
                del approvals[i]
                break
        self._data[const.DATA_PENDING_REWARD_APPROVALS] = approvals

        kid_info = self.kids_data.get(kid_id)
        if kid_info and reward_id in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
            kid_info[const.DATA_KID_PENDING_REWARDS].remove(reward_id)

        # Send a notification to the kid that reward was disapproved
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Reward Disapproved",
                message=f"Your reward '{reward_info[const.DATA_REWARD_NAME]}' was disapproved.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Badges: Check, Award
    # -------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    # Badge Data vs. Kid Badge Progress Data
    # -----------------------------------------------------------------------------
    # Badge data (badge_info): stores static configuration for each badge (name, type,
    # thresholds, tracked chores, reset schedule, etc.).
    # Kid badge progress data (progress): stores per-kid, per-badge progress (state,
    # cycle counts, points, start/end dates, etc.).
    # Always use badge data for config lookups and kid progress data for runtime state.
    # This separation ensures config changes are reflected and progress is tracked per kid.
    # -----------------------------------------------------------------------------

    def _check_badges_for_kid(self, kid_id: str):
        """Evaluate all badge thresholds for kid and update progress.

        This function:
        - Respects badge start/end dates.
        - Tracks daily progress and rolls it into the cycle count on day change.
        - Updates an overall progress field (DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS) for UI/logic.
        - Awards badges if criteria are met.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Maintenance cycles to ensure badge progress is initialized and up-to-date
        self._manage_badge_maintenance(kid_id)
        self._manage_cumulative_badge_maintenance(kid_id)

        # Mapping of target_type to handler and parameters
        target_type_handlers = {
            const.BADGE_TARGET_THRESHOLD_TYPE_POINTS: (
                self._handle_badge_target_points,
                {},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES: (
                self._handle_badge_target_points,
                {const.BADGE_HANDLER_PARAM_FROM_CHORES_ONLY: True},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT: (
                self._handle_badge_target_chore_count,
                {},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_MIN_COUNT: 3},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_MIN_COUNT: 5},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_MIN_COUNT: 7},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES: (
                self._handle_badge_target_streak,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES: (
                self._handle_badge_target_streak,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE: (
                self._handle_badge_target_streak,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES: (
                self._handle_badge_target_streak,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE: (
                self._handle_badge_target_streak,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
        }

        for badge_id, badge_info in self.badges_data.items():
            badge_name = badge_info.get(const.DATA_BADGE_NAME)
            badge_type = badge_info.get(const.DATA_BADGE_TYPE)

            # Determine if this badge is assigned to the kid
            is_assigned_to = bool(
                not badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                or kid_id in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            )
            if not is_assigned_to:
                continue

            # Note this process will only award a cumulative badge the first time.  Once
            # the badge is awarded, any future maintenance and awards associated with
            # maintenance periods will be handled by the _manage_cumulative_badge_maintenance
            # function.
            if badge_type == const.BADGE_TYPE_CUMULATIVE:
                if kid_id in badge_info.get(const.DATA_BADGE_EARNED_BY, []):
                    # This badge has already been awarded, so skip it
                    continue

                cumulative_badge_progress = self._get_cumulative_badge_progress(kid_id)
                if cumulative_badge_progress:
                    stored_cumulative_badge_progress = self.kids_data[kid_id].get(
                        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
                    )
                    stored_cumulative_badge_progress.update(cumulative_badge_progress)
                    self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
                        stored_cumulative_badge_progress
                    )
                effective_badge_id = cumulative_badge_progress.get(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID, None
                )
                if effective_badge_id and effective_badge_id == badge_id:
                    # This badge matches with the calculated effective badge ID, so it should be awarded
                    progress = kid_info.get(
                        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
                    )
                    try:
                        baseline_points = float(
                            progress.get(
                                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE,
                                const.DEFAULT_ZERO,
                            )
                        )
                        cycle_points = float(
                            progress.get(
                                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS,
                                const.DEFAULT_ZERO,
                            )
                        )
                    except (ValueError, TypeError) as err:
                        const.LOGGER.error(
                            "ERROR: Award Badge - Non-numeric values for cumulative points for kid '%s': %s",
                            kid_info.get(const.DATA_KID_NAME, kid_id),
                            err,
                        )
                        return
                    progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE] = (
                        baseline_points + cycle_points
                    )
                    progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] = (
                        const.DEFAULT_ZERO
                    )

                    self._award_badge(kid_id, badge_id)

                self._persist()
                self.async_set_updated_data(self._data)
                continue

            # Respect badge start/end dates
            badge_progress = kid_info.get(const.DATA_KID_BADGE_PROGRESS, {}).get(
                badge_id, {}
            )
            start_date_iso = badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_START_DATE
            )
            end_date_iso = badge_progress.get(const.DATA_KID_BADGE_PROGRESS_END_DATE)
            today_local_iso = kh.get_today_local_iso()
            in_effect = (not start_date_iso or today_local_iso >= start_date_iso) and (
                not end_date_iso or today_local_iso <= end_date_iso
            )
            const.LOGGER.debug(
                "DEBUG: Badge Progress - Badge '%s' for kid '%s': today_local_iso=%s, start_date_iso=%s, end_date_iso=%s, in_effect=%s",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, "Unknown Kid"),
                today_local_iso,
                start_date_iso,
                end_date_iso,
                in_effect,
            )

            if not in_effect:
                continue

            # Get chores tracked by this badge
            tracked_chores = self._get_badge_in_scope_chores_list(badge_info, kid_id)
            target_type = badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                const.DATA_BADGE_TARGET_TYPE
            )
            threshold_value = float(
                badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )

            # Copy progress dict for updates
            progress = badge_progress.copy() if badge_progress else {}

            handler_tuple = target_type_handlers.get(target_type)
            if handler_tuple:
                handler, handler_kwargs = handler_tuple
                progress = handler(
                    kid_info,
                    badge_info,
                    badge_id,
                    tracked_chores,
                    progress,
                    today_local_iso,
                    threshold_value,
                    **handler_kwargs,
                )
            else:
                # Fallback for unknown types (could log or skip)
                continue

            # Store the updated progress data for this badge
            kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id] = progress

            # Award the badge if criteria are met and not already earned
            if progress.get(const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET, False):
                current_state = progress.get(
                    const.DATA_KID_BADGE_PROGRESS_STATUS,
                    const.BADGE_STATE_IN_PROGRESS,
                )
                if current_state != const.BADGE_STATE_EARNED:
                    kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id][
                        const.DATA_KID_BADGE_PROGRESS_STATUS
                    ] = const.BADGE_STATE_EARNED
                    kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id][
                        const.DATA_KID_BADGE_PROGRESS_LAST_AWARDED
                    ] = kh.get_today_local_iso()
                    self._award_badge(kid_id, badge_id)

        # Update badge references to reflect current badge tracking settings
        self._update_chore_badge_references_for_kid()

        self._persist()
        self.async_set_updated_data(self._data)

    def _get_badge_in_scope_chores_list(self, badge_info: dict, kid_id: str) -> list:
        """
        Get the list of chore IDs that are in-scope for this badge evaluation.

        For badges with tracked chores:
        - Returns only those specific chore IDs that are also assigned to the kid
        For badges without tracked chores:
        - Returns all chore IDs assigned to the kid
        """

        badge_type = badge_info.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)
        include_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES

        kid_assigned_chores = []

        # If badge does not include tracked chores, return empty list
        if include_tracked_chores:
            tracked_chores = badge_info.get(const.DATA_BADGE_TRACKED_CHORES, {})
            tracked_chore_ids = tracked_chores.get(
                const.DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES, []
            )

            # Get all chores assigned to this kid
            for chore_id, chore_info in self.chores_data.items():
                chore_assigned_to = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
                if not chore_assigned_to or kid_id in chore_assigned_to:
                    kid_assigned_chores.append(chore_id)

            if tracked_chore_ids:
                # Badge has specific tracked chores, return only those that are also assigned to the kid
                return [
                    chore_id
                    for chore_id in tracked_chore_ids
                    if chore_id in kid_assigned_chores
                ]
            else:
                # Badge considers all chores, return all chores assigned to the kid
                return kid_assigned_chores
        else:
            # Badge does not include tracked chores component, return the empty list
            return kid_assigned_chores

    def _handle_badge_target_points(
        self,
        kid_info,
        badge_info,
        badge_id,
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        from_chores_only=False,
    ):
        """Handle points-based badge targets (all points or from chores only)."""
        total_points_all_sources, total_points_chores, _, _, points_map, _, _ = (
            kh.get_today_chore_and_point_progress(self, kid_info, tracked_chores)
        )
        points_today = (
            total_points_chores if from_chores_only else total_points_all_sources
        )
        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        points_cycle_count = progress.get(
            const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT, 0
        )

        if last_update_day and last_update_day != today_local_iso:
            points_cycle_count += progress.get(
                const.DATA_KID_BADGE_PROGRESS_POINTS_TODAY, 0
            )
            progress[const.DATA_KID_BADGE_PROGRESS_POINTS_TODAY] = 0

        progress[const.DATA_KID_BADGE_PROGRESS_POINTS_TODAY] = points_today
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso
        progress[const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT] = points_cycle_count
        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED] = points_map
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                (points_cycle_count + points_today) / threshold_value
                if threshold_value
                else 0,
                1.0,
            ),
            2,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = (
            points_cycle_count + points_today
        ) >= threshold_value
        return progress

    def _handle_badge_target_chore_count(
        self,
        kid_info,
        badge_info,
        badge_id,
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        min_count=None,
    ):
        """Handle chore count-based badge targets (optionally with a minimum count per day)."""
        _, _, chore_count_today, _, _, count_map, _ = (
            kh.get_today_chore_and_point_progress(self, kid_info, tracked_chores)
        )
        if min_count is not None and chore_count_today < min_count:
            chore_count_today = 0  # Only count days meeting the minimum

        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        chores_cycle_count = progress.get(
            const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT, 0
        )

        if last_update_day and last_update_day != today_local_iso:
            chores_cycle_count += progress.get(
                const.DATA_KID_BADGE_PROGRESS_CHORES_TODAY, 0
            )
            progress[const.DATA_KID_BADGE_PROGRESS_CHORES_TODAY] = 0

        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_TODAY] = chore_count_today
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso
        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT] = chores_cycle_count
        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED] = count_map
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                (chores_cycle_count + chore_count_today) / threshold_value
                if threshold_value
                else 0,
                1.0,
            ),
            2,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = (
            chores_cycle_count + chore_count_today
        ) >= threshold_value
        return progress

    def _handle_badge_target_daily_completion(
        self,
        kid_info,
        badge_info,
        badge_id,
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        percent_required=1.0,
        only_due_today=False,
        require_no_overdue=False,
        min_count=None,
    ):
        """Handle daily completion-based badge targets (all, percent, due, no overdue, min N)."""
        criteria_met, approved_count, total_count = (
            kh.get_today_chore_completion_progress(
                self,
                kid_info,
                tracked_chores,
                percent_required=percent_required,
                require_no_overdue=require_no_overdue,
                only_due_today=only_due_today,
                count_required=min_count,
            )
        )
        days_completed = progress.get(const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {})
        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        days_cycle_count = progress.get(
            const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0
        )

        if last_update_day and last_update_day != today_local_iso:
            if progress.get(const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED, False):
                days_cycle_count += 1
            progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = False

        progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = criteria_met
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso

        if criteria_met:
            days_completed[today_local_iso] = True
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED] = days_completed
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT] = days_cycle_count
        progress[const.DATA_KID_BADGE_PROGRESS_APPROVED_COUNT] = approved_count
        progress[const.DATA_KID_BADGE_PROGRESS_TOTAL_COUNT] = total_count
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                (days_cycle_count + (1 if criteria_met else 0)) / threshold_value
                if threshold_value
                else 0,
                1.0,
            ),
            2,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = (
            days_cycle_count + (1 if criteria_met else 0)
        ) >= threshold_value
        return progress

    def _handle_badge_target_streak(
        self,
        kid_info,
        badge_info,
        badge_id,
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        percent_required=1.0,
        only_due_today=False,
        require_no_overdue=False,
        min_count=None,
    ):
        """Handle streak-based badge targets (consecutive days meeting criteria).

        Uses the same fields as daily completion, but interprets DAYS_CYCLE_COUNT as the current streak.
        """
        criteria_met, approved_count, total_count = (
            kh.get_today_chore_completion_progress(
                self,
                kid_info,
                tracked_chores,
                percent_required=percent_required,
                require_no_overdue=require_no_overdue,
                only_due_today=only_due_today,
                count_required=min_count,
            )
        )
        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        streak = progress.get(const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0)
        days_completed = progress.get(const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {})

        if last_update_day and last_update_day != today_local_iso:
            if progress.get(const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED, False):
                # Only increment streak if yesterday was completed
                yesterday_iso = kh.adjust_datetime_by_interval(
                    today_local_iso,
                    interval_unit=const.CONF_DAYS,
                    delta=-1,
                    require_future=False,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )
                if days_completed.get(yesterday_iso):
                    streak += 1
                else:
                    streak = 1 if criteria_met else 0
            else:
                streak = 0
            progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = False

        # Update today's completion status and last_update_day
        progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = criteria_met
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso

        if criteria_met:
            days_completed[today_local_iso] = True
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED] = days_completed
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT] = streak
        progress[const.DATA_KID_BADGE_PROGRESS_APPROVED_COUNT] = approved_count
        progress[const.DATA_KID_BADGE_PROGRESS_TOTAL_COUNT] = total_count
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                streak / threshold_value if threshold_value else 0,
                1.0,
            ),
            2,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = streak >= threshold_value
        return progress

    def _award_badge(self, kid_id: str, badge_id: str):
        """Add the badge to kid's 'earned_by' and kid's 'badges' list."""
        badge_info = self.badges_data.get(badge_id)
        kid_info = self.kids_data.get(kid_id, {})
        if not kid_info:
            const.LOGGER.error("ERROR: Award Badge - Kid ID '%s' not found.", kid_id)
            return
        if not badge_info:
            const.LOGGER.error(
                "ERROR: Award Badge - Badge ID '%s' not found. Cannot be awarded to Kid ID '%s'",
                badge_id,
                kid_id,
            )
            return

        badge_type = badge_info.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)
        badge_name = badge_info.get(const.DATA_BADGE_NAME)
        kid_name = kid_info[const.DATA_KID_NAME]

        # Award the badge (for all types, including special occasion).
        const.LOGGER.info(
            "INFO: Award Badge - Awarding badge '%s' (%s) to kid '%s' (%s).",
            badge_id,
            badge_name,
            kid_id,
            kid_name,
        )
        earned_by_list = badge_info.setdefault(const.DATA_BADGE_EARNED_BY, [])
        if kid_id not in earned_by_list:
            earned_by_list.append(kid_id)
        self._update_badges_earned_for_kid(kid_id, badge_id)

        # --- Unified Award Items Logic ---
        award_data = badge_info.get(const.DATA_BADGE_AWARDS, {})
        award_items = award_data.get(const.DATA_BADGE_AWARDS_AWARD_ITEMS, [])
        points_awarded = award_data.get(
            const.DATA_BADGE_AWARDS_AWARD_POINTS, const.DEFAULT_ZERO
        )
        multiplier = award_data.get(
            const.DATA_BADGE_AWARDS_POINT_MULTIPLIER,
            const.DEFAULT_KID_POINTS_MULTIPLIER,
        )

        # Process award_items using helper
        to_award, _ = self.process_award_items(
            award_items,
            self.rewards_data,
            self.bonuses_data,
            self.penalties_data,
        )

        # 1. Points
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS)
            for item in award_items
        ):
            if points_awarded > const.DEFAULT_ZERO:
                const.LOGGER.info(
                    "INFO: Award Badge - Awarding points: %s for kid '%s'.",
                    points_awarded,
                    kid_name,
                )
                self.update_kid_points(
                    kid_id,
                    delta=points_awarded,
                    source=const.POINTS_SOURCE_BADGES,
                )

        # 2. Multiplier (only for cumulative badges)
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER)
            for item in award_items
        ):
            if multiplier > const.DEFAULT_ZERO:
                kid_info[const.DATA_KID_POINTS_MULTIPLIER] = multiplier
                const.LOGGER.info(
                    "INFO: Award Badge - Set points multiplier to %.2f for kid '%s'.",
                    multiplier,
                    kid_name,
                )
            else:
                kid_info[const.DATA_KID_POINTS_MULTIPLIER] = (
                    const.DEFAULT_POINTS_MULTIPLIER
                )

        # 3. Rewards (multiple)
        for reward_id in to_award.get(const.AWARD_ITEMS_KEY_REWARDS, []):
            if reward_id in self.rewards_data:
                if reward_id not in kid_info.get(const.DATA_KID_REDEEMED_REWARDS, []):
                    kid_info.setdefault(const.DATA_KID_REDEEMED_REWARDS, []).append(
                        reward_id
                    )
                    const.LOGGER.info(
                        "INFO: Award Badge - Added reward '%s' to redeemed rewards for kid '%s'.",
                        self.rewards_data[reward_id].get(
                            const.DATA_REWARD_NAME, reward_id
                        ),
                        kid_name,
                    )
                kid_info.setdefault(const.DATA_KID_REWARD_APPROVALS, {})
                kid_info[const.DATA_KID_REWARD_APPROVALS][reward_id] = (
                    kid_info[const.DATA_KID_REWARD_APPROVALS].get(reward_id, 0) + 1
                )
                if reward_id in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
                    kid_info[const.DATA_KID_PENDING_REWARDS].remove(reward_id)

        # 4. Bonuses (multiple)
        for bonus_id in to_award.get(const.AWARD_ITEMS_KEY_BONUSES, []):
            if bonus_id in self.bonuses_data:
                self.apply_bonus(kid_name, kid_id, bonus_id)

        # --- Notification ---
        message = f"You earned a new badge: '{badge_name}'!"
        if to_award.get(const.AWARD_ITEMS_KEY_REWARDS):
            reward_names = [
                self.rewards_data[rid].get(const.DATA_REWARD_NAME, rid)
                for rid in to_award[const.AWARD_ITEMS_KEY_REWARDS]
            ]
            message += f" Rewards: {', '.join(reward_names)}."
        if to_award.get(const.AWARD_ITEMS_KEY_BONUSES):
            bonus_names = [
                self.bonuses_data[bid].get(const.DATA_BONUS_NAME, bid)
                for bid in to_award[const.AWARD_ITEMS_KEY_BONUSES]
            ]
            message += f" Bonuses: {', '.join(bonus_names)}."
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS)
            for item in award_items
        ):
            message += f" Points: {points_awarded}."
        if badge_type == const.BADGE_TYPE_CUMULATIVE and any(
            item == const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER)
            for item in award_items
        ):
            message += f" Multiplier: {multiplier}x."

        parent_message = f"'{kid_name}' earned a new badge: '{badge_name}'."
        if to_award.get(const.AWARD_ITEMS_KEY_REWARDS):
            reward_names = [
                self.rewards_data[rid].get(const.DATA_REWARD_NAME, rid)
                for rid in to_award[const.AWARD_ITEMS_KEY_REWARDS]
            ]
            parent_message += f" Rewards: {', '.join(reward_names)}."
        if to_award.get(const.AWARD_ITEMS_KEY_BONUSES):
            bonus_names = [
                self.bonuses_data[bid].get(const.DATA_BONUS_NAME, bid)
                for bid in to_award[const.AWARD_ITEMS_KEY_BONUSES]
            ]
            parent_message += f" Bonuses: {', '.join(bonus_names)}."
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS)
            for item in award_items
        ):
            parent_message += f" Points: {points_awarded}."
        if badge_type == const.BADGE_TYPE_CUMULATIVE and any(
            item == const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER)
            for item in award_items
        ):
            parent_message += f" Multiplier: {multiplier}x."

        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_BADGE_ID: badge_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Badge Earned",
                message=message,
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Badge Earned",
                message=parent_message,
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)
        self._check_badges_for_kid(kid_id)

    def process_award_items(
        self, award_items, rewards_dict, bonuses_dict, penalties_dict
    ):
        """Process award_items and return dicts of items to award or penalize."""
        to_award = {
            const.AWARD_ITEMS_KEY_REWARDS: [],
            const.AWARD_ITEMS_KEY_BONUSES: [],
        }
        to_penalize = []
        for item in award_items:
            if item.startswith(const.AWARD_ITEMS_PREFIX_REWARD):
                reward_id = item.split(":", 1)[1]
                if reward_id in rewards_dict:
                    to_award[const.AWARD_ITEMS_KEY_REWARDS].append(reward_id)
            elif item.startswith(const.AWARD_ITEMS_PREFIX_BONUS):
                bonus_id = item.split(":", 1)[1]
                if bonus_id in bonuses_dict:
                    to_award[const.AWARD_ITEMS_KEY_BONUSES].append(bonus_id)
            elif item.startswith(const.AWARD_ITEMS_PREFIX_PENALTY):
                penalty_id = item.split(":", 1)[1]
                if penalty_id in penalties_dict:
                    to_penalize.append(penalty_id)
        return to_award, to_penalize

    def _update_point_multiplier_for_kid(self, kid_id: str):
        """Update the kid's points multiplier based on the current (effective) cumulative badge only."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        progress = kid_info.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {})
        current_badge_id = progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID
        )

        if current_badge_id:
            current_badge_info = self.badges_data.get(current_badge_id, {})
            badge_awards = current_badge_info.get(const.DATA_BADGE_AWARDS, {})
            multiplier = badge_awards.get(
                const.DATA_BADGE_AWARDS_POINT_MULTIPLIER,
                const.DEFAULT_KID_POINTS_MULTIPLIER,
            )
        else:
            multiplier = const.DEFAULT_KID_POINTS_MULTIPLIER

        kid_info[const.DATA_KID_POINTS_MULTIPLIER] = multiplier

    def _update_badges_earned_for_kid(self, kid_id: str, badge_id: str) -> None:
        """Update the kid's badges-earned tracking for the given badge, including period stats."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.error(
                "ERROR: Update Kid Badges Earned - Kid ID '%s' not found.", kid_id
            )
            return

        badge_info = self.badges_data.get(badge_id)
        if not badge_info:
            const.LOGGER.error(
                "ERROR: Update Kid Badges Earned - Badge ID '%s' not found.", badge_id
            )
            return

        today_local_iso = kh.get_today_local_iso()
        now = kh.get_now_local_time()
        week = now.strftime("%Y-W%V")
        month = now.strftime("%Y-%m")
        year = now.strftime("%Y")

        badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})

        # Use new constants for periods
        PERIODS_KEY = const.DATA_KID_BADGES_EARNED_PERIODS
        PERIOD_DAILY = const.DATA_KID_BADGES_EARNED_PERIODS_DAILY
        PERIOD_WEEKLY = const.DATA_KID_BADGES_EARNED_PERIODS_WEEKLY
        PERIOD_MONTHLY = const.DATA_KID_BADGES_EARNED_PERIODS_MONTHLY
        PERIOD_YEARLY = const.DATA_KID_BADGES_EARNED_PERIODS_YEARLY

        if badge_id not in badges_earned:
            badges_earned[badge_id] = {
                const.DATA_KID_BADGES_EARNED_NAME: badge_info.get(
                    const.DATA_BADGE_NAME
                ),
                const.DATA_KID_BADGES_EARNED_LAST_AWARDED: today_local_iso,
                const.DATA_KID_BADGES_EARNED_AWARD_COUNT: 1,
                PERIODS_KEY: {
                    PERIOD_DAILY: {today_local_iso: 1},
                    PERIOD_WEEKLY: {week: 1},
                    PERIOD_MONTHLY: {month: 1},
                    PERIOD_YEARLY: {year: 1},
                },
            }
            const.LOGGER.info(
                "INFO: Update Kid Badges Earned - Created new tracking for badge '%s' for kid '%s'.",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
            )
        else:
            tracking_entry = badges_earned[badge_id]
            tracking_entry[const.DATA_KID_BADGES_EARNED_NAME] = badge_info.get(
                const.DATA_BADGE_NAME
            )
            tracking_entry[const.DATA_KID_BADGES_EARNED_LAST_AWARDED] = today_local_iso
            tracking_entry[const.DATA_KID_BADGES_EARNED_AWARD_COUNT] = (
                tracking_entry.get(const.DATA_KID_BADGES_EARNED_AWARD_COUNT, 0) + 1
            )
            # Ensure periods and sub-dicts exist
            periods = tracking_entry.setdefault(PERIODS_KEY, {})
            periods.setdefault(PERIOD_DAILY, {})
            periods.setdefault(PERIOD_WEEKLY, {})
            periods.setdefault(PERIOD_MONTHLY, {})
            periods.setdefault(PERIOD_YEARLY, {})
            periods[PERIOD_DAILY][today_local_iso] = (
                periods[PERIOD_DAILY].get(today_local_iso, 0) + 1
            )
            periods[PERIOD_WEEKLY][week] = periods[PERIOD_WEEKLY].get(week, 0) + 1
            periods[PERIOD_MONTHLY][month] = periods[PERIOD_MONTHLY].get(month, 0) + 1
            periods[PERIOD_YEARLY][year] = periods[PERIOD_YEARLY].get(year, 0) + 1

            const.LOGGER.info(
                "INFO: Update Kid Badges Earned - Updated tracking for badge '%s' for kid '%s'.",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
            )
            # Cleanup old period data
            self._cleanup_badge_period_data_for_kid(periods)

        self._persist()
        self.async_set_updated_data(self._data)

    def _update_chore_badge_references_for_kid(
        self, include_cumulative_badges: bool = False
    ):
        """Update badge reference lists in kid chore data.

        This maintains a list of which badges reference each chore,
        useful for quick lookups when evaluating badges.

        Args:
            include_cumulative_badges: Whether to include cumulative badges in the references.
                                    Default is False which excludes them since they are currently points only
        """
        # Clear existing badge references
        for kid_id, kid_info in self.kids_data.items():
            if const.DATA_KID_CHORE_DATA not in kid_info:
                continue

            for chore_data in kid_info[const.DATA_KID_CHORE_DATA].values():
                chore_data[const.DATA_KID_CHORE_DATA_BADGE_REFS] = []

        # Add badge references to relevant chores
        for badge_id, badge_info in self.badges_data.items():
            # Skip cumulative badges if not explicitly included
            if (
                not include_cumulative_badges
                and badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE
            ):
                continue

            # For each kid this badge is assigned to
            assigned_to = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            for kid_id in (
                assigned_to or self.kids_data.keys()
            ):  # If empty, apply to all kids
                kid_info = self.kids_data.get(kid_id)
                if not kid_info or const.DATA_KID_CHORE_DATA not in kid_info:
                    continue

                # Use the helper function to get the correct in-scope chores for this badge and kid
                in_scope_chores_list = self._get_badge_in_scope_chores_list(
                    badge_info, kid_id
                )

                # Add badge reference to each tracked chore
                for chore_id in in_scope_chores_list:
                    if chore_id in kid_info[const.DATA_KID_CHORE_DATA]:
                        if (
                            badge_id
                            not in kid_info[const.DATA_KID_CHORE_DATA][chore_id][
                                const.DATA_KID_CHORE_DATA_BADGE_REFS
                            ]
                        ):
                            kid_info[const.DATA_KID_CHORE_DATA][chore_id][
                                const.DATA_KID_CHORE_DATA_BADGE_REFS
                            ].append(badge_id)

    def _cleanup_badge_period_data_for_kid(self, periods_data: dict):
        """Remove old period data for badges to keep storage manageable.

        Retains:
            - 7 days of daily data
            - 5 weeks of weekly data
            - 3 months of monthly data
            - 3 years of yearly data
        """
        today_local = kh.get_today_local_date()

        # Daily: keep 7 days
        cutoff_daily = kh.adjust_datetime_by_interval(
            today_local.isoformat(),
            interval_unit=const.CONF_DAYS,
            delta=-7,
            require_future=False,
            return_type=const.HELPER_RETURN_ISO_DATE,
        )
        daily_data = periods_data.get(const.DATA_KID_BADGES_EARNED_PERIODS_DAILY, {})
        for day in list(daily_data.keys()):
            if day < cutoff_daily:
                del daily_data[day]

        # Weekly: keep 5 weeks
        cutoff_date = kh.adjust_datetime_by_interval(
            today_local.isoformat(),
            interval_unit=const.CONF_WEEKS,
            delta=-5,
            require_future=False,
            return_type=const.HELPER_RETURN_DATETIME,
        )
        cutoff_weekly = cutoff_date.strftime("%Y-W%V")
        weekly_data = periods_data.get(const.DATA_KID_BADGES_EARNED_PERIODS_WEEKLY, {})
        for week in list(weekly_data.keys()):
            if week < cutoff_weekly:
                del weekly_data[week]

        # Monthly: keep 3 months
        cutoff_date = kh.adjust_datetime_by_interval(
            today_local.isoformat(),
            interval_unit=const.CONF_MONTHS,
            delta=-3,
            require_future=False,
            return_type=const.HELPER_RETURN_DATETIME,
        )
        cutoff_monthly = cutoff_date.strftime("%Y-%m")
        monthly_data = periods_data.get(
            const.DATA_KID_BADGES_EARNED_PERIODS_MONTHLY, {}
        )
        for month in list(monthly_data.keys()):
            if month < cutoff_monthly:
                del monthly_data[month]

        # Yearly: keep 3 years
        cutoff_yearly = str(int(today_local.strftime("%Y")) - 3)
        yearly_data = periods_data.get(const.DATA_KID_BADGES_EARNED_PERIODS_YEARLY, {})
        for year in list(yearly_data.keys()):
            if year < cutoff_yearly:
                del yearly_data[year]

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Badges: Remove Awarded Badges
    # Removes awarded badges from kids based on provided kid name and/or badge name.
    # Converts kid name to kid ID and badge name to badge ID for targeted removal using
    # the _remove_awarded_badges_by_id method.
    # If badge_id is not found, it assumes the badge was deleted and removes it from the kid's data.
    # If neither is provided, it globally removes all awarded badges from all kids.
    # -------------------------------------------------------------------------------------
    def remove_awarded_badges(
        self, kid_name: Optional[str] = None, badge_name: Optional[str] = None
    ) -> None:
        """Remove awarded badges based on provided kid_name and badge_name."""
        # Convert kid_name to kid_id if provided.
        kid_id = None
        if kid_name:
            kid_id = next(
                (
                    kid_id
                    for kid_id, kid_info in self.kids_data.items()
                    if kid_info.get(const.DATA_KID_NAME) == kid_name
                ),
                None,
            )
            if kid_id is None:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Kid name '%s' not found.", kid_name
                )
                raise HomeAssistantError(f"Kid name '{kid_name}' not found.")
        else:
            kid_id = None

        # If badge_name is provided, try to find its corresponding badge_id.
        if badge_name:
            badge_id = next(
                (
                    bid
                    for bid, badge_info in self.badges_data.items()
                    if badge_info.get(const.DATA_BADGE_NAME) == badge_name
                ),
                None,
            )
            if not badge_id:
                # If the badge isn't found, assume the actual badge was deleted but still listed in kid data
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Badge name '%s' not found in badges_data. Removing from kid data only.",
                    badge_name,
                )
                # Remove badge name from a specific kid if kid_id is provided,
                # or from all kids if not.
                if kid_id:
                    kid_info = self.kids_data.get(kid_id)
                    if kid_info:
                        # Remove badge from the kid's earned badges
                        badges_earned = kid_info.get(const.DATA_KID_BADGES_EARNED, {})
                        to_remove = [
                            badge_id
                            for badge_id, entry in badges_earned.items()
                            if entry.get(const.DATA_KID_BADGES_EARNED_NAME)
                            == badge_name
                        ]
                        for badge_id in to_remove:
                            del badges_earned[badge_id]
                else:
                    for kid_info in self.kids_data.values():
                        # Remove badge from the kid's earned badges
                        badges_earned = kid_info.get(const.DATA_KID_BADGES_EARNED, {})
                        to_remove = [
                            badge_id
                            for badge_id, entry in badges_earned.items()
                            if entry.get(const.DATA_KID_BADGES_EARNED_NAME)
                            == badge_name
                        ]
                        for badge_id in to_remove:
                            del badges_earned[badge_id]

                self._persist()
                self.async_set_updated_data(self._data)
                return
        else:
            badge_id = None

        self._remove_awarded_badges_by_id(kid_id, badge_id)

    def _remove_awarded_badges_by_id(
        self, kid_id: Optional[str] = None, badge_id: Optional[str] = None
    ) -> None:
        """Removes awarded badges based on provided kid_id and badge_id."""

        const.LOGGER.info("INFO: Remove Awarded Badges - Starting removal process.")
        found = False

        if badge_id and kid_id:
            # Reset a specific badge for a specific kid.
            kid_info = self.kids_data.get(kid_id)
            badge_info = self.badges_data.get(badge_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")
            if not badge_info:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Badge ID '%s' not found.", badge_id
                )
                raise HomeAssistantError(f"Badge ID '{badge_id}' not found.")
            badge_name = badge_info.get(const.DATA_BADGE_NAME, badge_id)
            kid_name = kid_info.get(const.DATA_KID_NAME, kid_id)
            # Remove the badge from the kid's badges_earned.
            badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})
            if badge_id in badges_earned:
                found = True
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                    badge_name,
                    kid_name,
                )
                del badges_earned[badge_id]

            # Remove the kid from the badge earned_by list.
            earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
            if kid_id in earned_by_list:
                earned_by_list.remove(kid_id)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Badge '%s' ('%s') not found in kid '%s' ('%s') data.",
                    badge_id,
                    badge_name,
                    kid_id,
                    kid_name,
                )

        elif badge_id:
            # Remove a specific awarded badge for all kids.
            badge_info = self.badges_data.get(badge_id)
            badge_name = badge_info.get(const.DATA_BADGE_NAME, badge_id)
            for kid_id, kid_info in self.kids_data.items():
                kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown Kid")
                # Remove the badge from the kid's badges_earned.
                badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})
                if badge_id in badges_earned:
                    found = True
                    const.LOGGER.warning(
                        "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                        badge_name,
                        kid_name,
                    )
                    del badges_earned[badge_id]

                # Remove the kid from the badge earned_by list.
                earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
                if kid_id in earned_by_list:
                    earned_by_list.remove(kid_id)

            # All kids should already be removed from the badge earned_by list, but in case of orphans, clear those fields
            if const.DATA_BADGE_EARNED_BY in badge_info:
                badge_info[const.DATA_BADGE_EARNED_BY].clear()

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Badge '%s' ('%s') not found in any kid's data.",
                    badge_id,
                    badge_name,
                )

        elif kid_id:
            # Remove all awarded badges for a specific kid.
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")
            kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown Kid")
            for badge_id, badge_info in self.badges_data.items():
                badge_name = badge_info.get(const.DATA_BADGE_NAME)
                earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
                badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})
                if kid_id in earned_by_list:
                    found = True
                    # Remove kid from badge earned_by list
                    earned_by_list.remove(kid_id)
                    # Remove the badge from the kid's badges_earned.
                    if badge_id in badges_earned:
                        found = True
                        const.LOGGER.warning(
                            "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                            badge_name,
                            kid_name,
                        )
                        del badges_earned[badge_id]

            # All badges should already be removed from the kid's badges list, but in case of orphans, clear those fields
            if const.DATA_KID_BADGES_EARNED in kid_info:
                kid_info[const.DATA_KID_BADGES_EARNED].clear()
            # CLS Should also clear all extra fields for all badge types later

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - No badge found for kid '%s'.",
                    kid_info.get(const.DATA_KID_NAME, kid_id),
                )

        else:
            # Remove Awarded Badges for all kids.
            const.LOGGER.info(
                "INFO: Remove Awarded Badges - Removing all awarded badges for all kids."
            )
            for badge_id, badge_info in self.badges_data.items():
                badge_name = badge_info.get(const.DATA_BADGE_NAME)
                for kid_id, kid_info in self.kids_data.items():
                    kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown Kid")
                    # Remove the badge from the kid's badges_earned.
                    badges_earned = kid_info.setdefault(
                        const.DATA_KID_BADGES_EARNED, {}
                    )
                    if badge_id in badges_earned:
                        found = True
                        const.LOGGER.warning(
                            "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                            badge_name,
                            kid_name,
                        )
                        del badges_earned[badge_id]

                    # Remove the kid from the badge earned_by list.
                    earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
                    if kid_id in earned_by_list:
                        earned_by_list.remove(kid_id)

                    # All badges should already be removed from the kid's badges list, but in case of orphans, clear those fields
                    if const.DATA_KID_BADGES_EARNED in kid_info:
                        kid_info[const.DATA_KID_BADGES_EARNED].clear()
                    # CLS Should also clear all extra fields for all badge types later

                # All kids should already be removed from the badge earned_by list, but in case of orphans, clear those fields
                if const.DATA_BADGE_EARNED_BY in badge_info:
                    badge_info[const.DATA_BADGE_EARNED_BY].clear()

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - No awarded badges found in any kid's data."
                )

        const.LOGGER.info(
            "INFO: Remove Awarded Badges - Badge removal process completed."
        )
        self._persist()
        self.async_set_updated_data(self._data)

    def _recalculate_all_badges(self):
        """Global re-check of all badges for all kids."""
        const.LOGGER.info("INFO: Recalculate All Badges - Starting Recalculation")

        # Re-evaluate badge criteria for each kid.
        for kid_id in self.kids_data.keys():
            self._check_badges_for_kid(kid_id)

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.info("INFO: Recalculate All Badges - Recalculation Complete")

    def _get_cumulative_badge_progress(self, kid_id: str) -> dict[str, Any]:
        """
        Builds and returns the full cumulative badge progress block for a kid.
        Uses badge level logic, progress tracking, and next-tier metadata.
        Does not mutate state.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return {}

        # Make a copy of the existing progress so that we don't modify the stored data.
        stored_progress = kid_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        ).copy()

        # Compute values from badge level logic.
        (highest_earned, next_higher, next_lower, baseline, cycle_points) = (
            self._get_cumulative_badge_levels(kid_id)
        )
        total_points = baseline + cycle_points

        # Determine which badge should be considered current.
        # If the stored status is "demoted", then set current badge to next_lower; otherwise, use highest_earned.
        current_status = stored_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
            const.CUMULATIVE_BADGE_STATE_ACTIVE,
        )
        if current_status == const.CUMULATIVE_BADGE_STATE_DEMOTED:
            current_badge_info = next_lower
        else:
            current_badge_info = highest_earned

        # Build a new dictionary with computed values.
        computed_progress = {
            # Maintenance tracking (we'll merge stored values below)
            # For keys like status we prefer the stored value, or the default.
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: stored_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
                const.CUMULATIVE_BADGE_STATE_ACTIVE,
            ),
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE: baseline,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS: cycle_points,
            # Highest earned badge
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_ID: highest_earned.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if highest_earned
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_NAME: highest_earned.get(
                const.DATA_BADGE_NAME
            )
            if highest_earned
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_THRESHOLD: float(
                highest_earned.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )
            if highest_earned
            else None,
            # Current badge in effect
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: current_badge_info.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if current_badge_info
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: current_badge_info.get(
                const.DATA_BADGE_NAME
            )
            if current_badge_info
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: float(
                current_badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )
            if current_badge_info
            else None,
            # Next higher tier
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_ID: next_higher.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if next_higher
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_NAME: next_higher.get(
                const.DATA_BADGE_NAME
            )
            if next_higher
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_THRESHOLD: float(
                next_higher.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )
            if next_higher
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_POINTS_NEEDED: (
                max(
                    0.0,
                    float(
                        next_higher.get(const.DATA_BADGE_TARGET, {}).get(
                            const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                        )
                    )
                    - total_points,
                )
                if next_higher
                else None
            ),
            # Next lower tier
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_ID: next_lower.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if next_lower
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_NAME: next_lower.get(
                const.DATA_BADGE_NAME
            )
            if next_lower
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_THRESHOLD: float(
                next_lower.get(const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0)
            )
            if next_lower
            else None,
        }

        # Merge the computed values over the stored progress.
        stored_progress.update(computed_progress)

        # Return the merged dictionary without modifying the underlying stored data.
        return stored_progress

    def _manage_badge_maintenance(self, kid_id: str) -> None:
        """
        Manages badge maintenance for a kid:
        - Initializes badge progress data for badges that don't have it yet
        - Checks if badges have reached their end dates
        - Resets progress for badges that have passed their end_date
        - Updates badge states based on the reset
        - Sets up new cycle dates for recurring badges
        - Ensures all required fields exist in badge progress data
        - Synchronizes badge configuration changes with progress data
        """
        # ===============================================================
        # SECTION 1: INITIALIZATION - Basic setup and validation
        # ===============================================================
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # First, ensure all badge progress entries have all required fields
        badge_progress = kid_info.setdefault(const.DATA_KID_BADGE_PROGRESS, {})
        today_local_iso = kh.get_today_local_iso()

        # ===============================================================
        # SECTION 2: BADGE INITIALIZATION & SYNC - Create or update badge progress data
        # ===============================================================
        self._sync_badge_progress_for_kid(kid_id)

        # ===============================================================
        # SECTION 3: BADGE RESET CYCLE - Manage recurring badges that reached end date
        # ===============================================================
        # Now perform badge reset maintenance
        for badge_id, progress in list(badge_progress.items()):
            badge_info = self.badges_data.get(badge_id)
            if not badge_info:
                continue

            recurring_frequency = progress.get(
                const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY
            )

            # ---------------------------------------------------------------
            # Check if badge has reached its end date
            # ---------------------------------------------------------------
            # Kid badge progress end date should always be populated for recurring badges.
            # If the user does not set a date, it will default to today.
            end_date_iso = progress.get(
                const.DATA_KID_BADGE_PROGRESS_END_DATE, today_local_iso
            )
            if not end_date_iso or today_local_iso <= end_date_iso:
                continue

            # --- Apply penalties if badge was NOT earned by end date, and not already applied ---
            if not progress.get(
                const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET, False
            ) and not progress.get(
                const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED, False
            ):
                # Mark the penalty as applied to avoid reapplying it
                progress[const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED] = True
                award_data = badge_info.get(const.DATA_BADGE_AWARDS, {})
                award_items = award_data.get(const.DATA_BADGE_AWARDS_AWARD_ITEMS, [])
                _, to_penalize = self.process_award_items(
                    award_items,
                    self.rewards_data,
                    self.bonuses_data,
                    self.penalties_data,
                )
                for penalty_id in to_penalize:
                    if penalty_id in self.penalties_data:
                        self.apply_penalty("system", kid_id, penalty_id)
                        const.LOGGER.info(
                            "INFO: Penalty Applied - Badge '%s' not earned by kid '%s'. Penalty '%s' applied.",
                            badge_info.get(const.DATA_BADGE_NAME, badge_id),
                            kid_info.get(const.DATA_KID_NAME, kid_id),
                            self.penalties_data[penalty_id].get(
                                const.DATA_PENALTY_NAME, penalty_id
                            ),
                        )

            # Now skip further reset logic if not recurring
            if recurring_frequency == const.FREQUENCY_NONE:
                continue

            # Debug: Log when the reset logic is triggered for this badge
            const.LOGGER.debug(
                "DEBUG: Badge Reset Triggered - Badge '%s' for kid '%s': today_local_iso=%s, end_date_iso=%s (reset logic will run)",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
                today_local_iso,
                end_date_iso,
            )

            # Increment the cycle count for this badge
            progress[const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT] = (
                progress.get(const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT, 0) + 1
            )

            # ---------------------------------------------------------------
            # Calculate new dates for next badge cycle
            # ---------------------------------------------------------------
            # Get reset schedule from badge configuration
            reset_schedule = badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
            badge_type = badge_info.get(const.DATA_BADGE_TYPE)
            # Use the end date from the badge first, but if that isn't available, use the badge progress
            # from kid data which should always be populated for a recurring badge.
            prior_end_date_iso = badge_info.get(
                const.DATA_BADGE_RESET_SCHEDULE_END_DATE, end_date_iso
            )

            # The following require special handling because resets will not happen until after the end date passes
            # Since the scheduling functions will always look for a future date, it would end up with an end date
            # for tomorrow (2 days) instead of just rescheduling the end date by 1 day.
            is_daily = recurring_frequency == const.FREQUENCY_DAILY
            is_custom_1_day = (
                recurring_frequency == const.FREQUENCY_CUSTOM
                and reset_schedule.get(const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL)
                == 1
                and reset_schedule.get(
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                )
                == const.CONF_DAYS
            )

            if is_daily or is_custom_1_day:
                # Use PERIOD_DAY_END to set end date to end of today - See detail above.
                new_end_date_iso = kh.get_next_scheduled_datetime(
                    prior_end_date_iso,
                    interval_type=const.PERIOD_DAY_END,
                    require_future=True,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )

            # Calculate new end date based on recurring frequency
            elif recurring_frequency == const.FREQUENCY_CUSTOM:
                # Handle custom frequency
                custom_interval = reset_schedule.get(
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
                )
                custom_interval_unit = reset_schedule.get(
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                )

                if custom_interval and custom_interval_unit:
                    new_end_date_iso = kh.adjust_datetime_by_interval(
                        prior_end_date_iso,
                        interval_unit=custom_interval_unit,
                        delta=custom_interval,
                        require_future=True,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
                else:
                    # Default fallback to weekly
                    new_end_date_iso = kh.adjust_datetime_by_interval(
                        prior_end_date_iso,
                        interval_unit=const.CONF_WEEKS,
                        delta=1,
                        require_future=True,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
            else:
                # Use standard frequency helper
                new_end_date_iso = kh.get_next_scheduled_datetime(
                    prior_end_date_iso,
                    interval_type=recurring_frequency,
                    require_future=True,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )

            # ---------------------------------------------------------------
            # Calculate new start date based on badge type and previous cycle
            # ---------------------------------------------------------------
            # If there was no previous start date, don't set one (immediately effective)
            # If there was a previous start date, calculate the new one based on the duration
            existing_start_date_iso = progress.get(
                const.DATA_KID_BADGE_PROGRESS_START_DATE
            )

            if existing_start_date_iso:
                try:
                    # Handle special case where start and end dates are the same
                    if existing_start_date_iso == end_date_iso:
                        # For badges where start date equals end date (like special occasions)
                        # set the new start date equal to the new end date
                        new_start_date_iso = new_end_date_iso
                    else:
                        # Convert ISO dates to datetime objects
                        start_dt_utc = kh.parse_datetime_to_utc(existing_start_date_iso)
                        end_dt_utc = kh.parse_datetime_to_utc(end_date_iso)

                        if start_dt_utc and end_dt_utc:
                            # Calculate duration in days
                            duration = (end_dt_utc - start_dt_utc).days

                            # Set new start date by subtracting the same duration from new end date
                            new_start_date_iso = kh.adjust_datetime_by_interval(
                                new_end_date_iso,
                                interval_unit=const.CONF_DAYS,
                                delta=-duration,
                                require_future=False,  # Allow past dates for calculation
                                return_type=const.HELPER_RETURN_ISO_DATE,
                            )

                            # If new start date is in the past, use today
                            if new_start_date_iso < today_local_iso:
                                new_start_date_iso = today_local_iso
                        else:
                            # Fallback to today if date parsing fails
                            new_start_date_iso = today_local_iso
                except Exception:
                    # Fallback to today if calculation fails
                    new_start_date_iso = today_local_iso
            else:
                # No existing start date - keep it unset (None)
                new_start_date_iso = None

            # ---------------------------------------------------------------
            # Reset badge progress for the new cycle
            # ---------------------------------------------------------------
            target_type = progress.get(const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE)

            # Update badge state to active_cycle (working on next iteration)
            progress[const.DATA_KID_BADGE_PROGRESS_STATUS] = (
                const.BADGE_STATE_ACTIVE_CYCLE
            )
            progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = new_start_date_iso
            progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = new_end_date_iso

            # Reset fenalty applied flag
            progress[const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED] = False

            # Reset all known progress tracking fields if present
            reset_fields = [
                (const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT, 0.0),
                (const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT, 0),
                (const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0),
                (const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED, {}),
                (const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {}),
            ]
            for field, default in reset_fields:
                if field in progress:
                    progress[field] = default

            const.LOGGER.debug(
                "DEBUG: Badge Maintenance - Reset badge '%s' for kid '%s'. New cycle: %s to %s",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
                new_start_date_iso if new_start_date_iso else "immediate",
                new_end_date_iso,
            )

            const.LOGGER.debug(
                "DEBUG: Badge Maintenance - Reset badge '%s' for kid '%s'. New cycle: %s to %s",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
                new_start_date_iso if new_start_date_iso else "immediate",
                new_end_date_iso,
            )

        # ===============================================================
        # SECTION 4: FINALIZATION - Save updates back to kid data
        # ===============================================================
        # Save the updated progress back to the kid data
        kid_info[const.DATA_KID_BADGE_PROGRESS] = badge_progress

        self._persist()
        self.async_set_updated_data(self._data)

    def _sync_badge_progress_for_kid(self, kid_id: str) -> None:
        """Sync badge progress for a specific kid."""
        # Initialize badge progress for any badges that don't have progress data yet

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        for badge_id, badge_info in self.badges_data.items():
            # Skip badges that are not assigned to this kid
            is_assigned_to = bool(
                not badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                or kid_id in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            )
            if not is_assigned_to:
                continue

            # Skip cumulative badges (handled separately)
            if badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE:
                continue

            # Initialize progress structure if it doesn't exist
            if const.DATA_KID_BADGE_PROGRESS not in kid_info:
                kid_info[const.DATA_KID_BADGE_PROGRESS] = {}

            badge_type = badge_info.get(const.DATA_BADGE_TYPE)

            # --- Set flags based on badge type ---
            has_target = badge_type in const.INCLUDE_TARGET_BADGE_TYPES
            has_special_occasion = (
                badge_type in const.INCLUDE_SPECIAL_OCCASION_BADGE_TYPES
            )
            has_achievement_linked = (
                badge_type in const.INCLUDE_ACHIEVEMENT_LINKED_BADGE_TYPES
            )
            has_challenge_linked = (
                badge_type in const.INCLUDE_CHALLENGE_LINKED_BADGE_TYPES
            )
            has_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES
            has_assigned_to = badge_type in const.INCLUDE_ASSIGNED_TO_BADGE_TYPES
            has_awards = badge_type in const.INCLUDE_AWARDS_BADGE_TYPES
            has_reset_schedule = badge_type in const.INCLUDE_RESET_SCHEDULE_BADGE_TYPES

            # ===============================================================
            # SECTION 1: NEW BADGE SETUP - Create initial progress structure
            # ===============================================================
            if badge_id not in kid_info[const.DATA_KID_BADGE_PROGRESS]:
                # Get badge details

                # --- Common fields ---
                progress = {
                    const.DATA_KID_BADGE_PROGRESS_NAME: badge_info.get(
                        const.DATA_BADGE_NAME
                    ),
                    const.DATA_KID_BADGE_PROGRESS_TYPE: badge_type,
                    const.DATA_KID_BADGE_PROGRESS_STATUS: const.BADGE_STATE_IN_PROGRESS,
                }

                # --- Target fields ---
                if has_target:
                    target_type = badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                        const.DATA_BADGE_TARGET_TYPE
                    )
                    threshold_value = float(
                        badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                            const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                        )
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE] = target_type
                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE] = (
                        threshold_value
                    )

                    # Initialize all possible progress fields to their defaults if not present
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT, 0.0
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT, 0
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED, {}
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {}
                    )

                # --- Achievement Linked fields ---
                if has_achievement_linked:
                    # Store the associated achievement ID if present
                    achievement_id = badge_info.get(
                        const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT
                    )
                    if achievement_id:
                        progress[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = (
                            achievement_id
                        )

                # --- Challenge Linked fields ---
                if has_challenge_linked:
                    # Store the associated challenge ID if present
                    challenge_id = badge_info.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE)
                    if challenge_id:
                        progress[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = challenge_id

                # --- Tracked Chores fields ---
                if has_tracked_chores and not has_special_occasion:
                    progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = (
                        self._get_badge_in_scope_chores_list(badge_info, kid_id)
                    )

                # --- Assigned To fields ---
                if has_assigned_to:
                    assigned_to = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                    progress[const.DATA_BADGE_ASSIGNED_TO] = assigned_to

                # --- Awards fields --- Not required for now
                # if has_awards:
                #    awards = badge_info.get(const.DATA_BADGE_AWARDS, {})
                #    progress[const.DATA_BADGE_AWARDS] = awards

                # --- Reset Schedule fields ---
                if has_reset_schedule:
                    reset_schedule = badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
                    recurring_frequency = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
                        const.FREQUENCY_NONE,
                    )
                    start_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_START_DATE
                    )
                    end_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_END_DATE
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY] = (
                        recurring_frequency
                    )

                    # Set initial schedule if there is a frequency and no end date
                    if recurring_frequency != const.FREQUENCY_NONE:
                        if end_date_iso:
                            progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = (
                                start_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = (
                                end_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT] = (
                                const.DEFAULT_ZERO
                            )
                        else:
                            # ---------------------------------------------------------------
                            # Calculate initial end date from today since there is no end date
                            # ---------------------------------------------------------------
                            today_local_iso = kh.get_today_local_iso()
                            is_daily = recurring_frequency == const.FREQUENCY_DAILY
                            is_custom_1_day = (
                                recurring_frequency == const.FREQUENCY_CUSTOM
                                and reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
                                )
                                == 1
                                and reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                                )
                                == const.CONF_DAYS
                            )

                            if is_daily or is_custom_1_day:
                                # This is special case where if you set a daily badge, you don't want it to get scheduled with
                                # tomorrow as the end date.
                                new_end_date_iso = today_local_iso
                            elif recurring_frequency == const.FREQUENCY_CUSTOM:
                                # Handle other custom frequencies
                                custom_interval = reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
                                )
                                custom_interval_unit = reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                                )
                                if custom_interval and custom_interval_unit:
                                    new_end_date_iso = kh.adjust_datetime_by_interval(
                                        today_local_iso,
                                        interval_unit=custom_interval_unit,
                                        delta=custom_interval,
                                        require_future=True,
                                        return_type=const.HELPER_RETURN_ISO_DATE,
                                    )
                                else:
                                    # Default fallback to weekly
                                    new_end_date_iso = kh.adjust_datetime_by_interval(
                                        today_local_iso,
                                        interval_unit=const.CONF_WEEKS,
                                        delta=1,
                                        require_future=True,
                                        return_type=const.HELPER_RETURN_ISO_DATE,
                                    )
                            else:
                                # Use standard frequency helper
                                new_end_date_iso = kh.get_next_scheduled_datetime(
                                    today_local_iso,
                                    interval_type=recurring_frequency,
                                    require_future=True,
                                    return_type=const.HELPER_RETURN_ISO_DATE,
                                )

                            progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = (
                                start_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = (
                                new_end_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT] = (
                                const.DEFAULT_ZERO
                            )

                            # Set penalty applied to False
                            # This is to ensure that if the badge is not earned, the penalty will be applied
                            progress[const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED] = (
                                False
                            )

                # --- Special Occasion fields ---
                if has_special_occasion:
                    # Add occasion type if present
                    occasion_type = badge_info.get(const.DATA_BADGE_OCCASION_TYPE)
                    if occasion_type:
                        progress[const.DATA_BADGE_OCCASION_TYPE] = occasion_type

                # Store the progress data
                kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id] = progress

            # ===============================================================
            # SECTION 2: BADGE SYNC - Update existing badge progress data
            # ===============================================================
            else:
                # --- Remove badge progress if badge is no longer available or not assigned to this kid ---
                if badge_id not in self.badges_data or (
                    badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                    and kid_id not in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                ):
                    if badge_id in kid_info[const.DATA_KID_BADGE_PROGRESS]:
                        del kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id]
                        const.LOGGER.info(
                            "INFO: Badge Maintenance - Removed badge progress for badge '%s' from kid '%s' (badge deleted or unassigned).",
                            badge_id,
                            kid_info.get(const.DATA_KID_NAME, kid_id),
                        )
                    continue

                # The badge already exists in progress data - sync configuration fields
                progress = kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id]

                # --- Common fields ---
                progress[const.DATA_KID_BADGE_PROGRESS_NAME] = badge_info.get(
                    const.DATA_BADGE_NAME, "Unknown Badge"
                )
                progress[const.DATA_KID_BADGE_PROGRESS_TYPE] = badge_type

                # --- Target fields ---
                if has_target:
                    target_type = badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                        const.DATA_BADGE_TARGET_TYPE,
                        const.BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE] = target_type

                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE] = (
                        badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                            const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                        )
                    )

                # --- Special Occasion fields ---
                if has_special_occasion:
                    # Add occasion type if present
                    occasion_type = badge_info.get(const.DATA_BADGE_OCCASION_TYPE)
                    if occasion_type:
                        progress[const.DATA_BADGE_OCCASION_TYPE] = occasion_type

                # --- Achievement Linked fields ---
                if has_achievement_linked:
                    achievement_id = badge_info.get(
                        const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT
                    )
                    if achievement_id:
                        progress[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = (
                            achievement_id
                        )

                # --- Challenge Linked fields ---
                if has_challenge_linked:
                    challenge_id = badge_info.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE)
                    if challenge_id:
                        progress[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = challenge_id

                # --- Tracked Chores fields ---
                if has_tracked_chores and not has_special_occasion:
                    progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = (
                        self._get_badge_in_scope_chores_list(badge_info, kid_id)
                    )

                # --- Assigned To fields ---
                if has_assigned_to:
                    assigned_to = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                    progress[const.DATA_BADGE_ASSIGNED_TO] = assigned_to

                # --- Awards fields --- Not required for now
                # if has_awards:
                #    awards = badge_info.get(const.DATA_BADGE_AWARDS, {})
                #    progress[const.DATA_BADGE_AWARDS] = awards

                # --- Reset Schedule fields ---
                if has_reset_schedule:
                    reset_schedule = badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
                    recurring_frequency = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
                        const.FREQUENCY_NONE,
                    )
                    start_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_START_DATE
                    )
                    end_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_END_DATE
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY] = (
                        recurring_frequency
                    )
                    # Only update start and end dates if they have values
                    if start_date_iso:
                        progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = (
                            start_date_iso
                        )
                    if end_date_iso:
                        progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = end_date_iso

        # ===============================================================
        # SECTION 3: CLEANUP - Remove progress for badges that are no longer assigned to this kid
        # ===============================================================
        assigned_badge_ids = {
            badge_id
            for badge_id, badge_info in self.badges_data.items()
            if not badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            or kid_id in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
        }
        progress_badge_ids = set(kid_info[const.DATA_KID_BADGE_PROGRESS].keys())
        for badge_id in progress_badge_ids - assigned_badge_ids:
            del kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id]
            const.LOGGER.info(
                "INFO: Badge Maintenance - Removed badge progress for badge '%s' from kid '%s' (badge unassigned).",
                badge_id,
                kid_info.get(const.DATA_KID_NAME, kid_id),
            )

    def _manage_cumulative_badge_maintenance(self, kid_id: str) -> None:
        """
        Manages cumulative badge maintenance for a kid:
        - Evaluates whether the maintenance or grace period has ended.
        - Updates badge status (active, grace, or demoted) based on cycle points.
        - Resets cycle points and updates maintenance windows if needed.
        - Updates the current badge information based on maintenance outcome.
        """

        # Retrieve kid-specific information from the kids_data dictionary.
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Retrieve the cumulative badge progress data for the kid.
        cumulative_badge_progress = kid_info.setdefault(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )

        # DEBUG: Log starting state for the kid.
        kid_name = kid_info.get(const.DATA_KID_NAME, kid_id)
        const.LOGGER.debug(
            "DEBUG: Manage Cumulative Badge Maintenance - Kid=%s, Initial Status=%s, Cycle Points=%.2f",
            kid_name,
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS, "active"
            ),
            float(
                cumulative_badge_progress.get(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
                )
            ),
        )

        # Extract current maintenance and grace end dates, status, and accumulated cycle points.
        end_date_iso = cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE
        )
        grace_date_iso = cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE
        )
        status = cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
            const.CUMULATIVE_BADGE_STATE_ACTIVE,
        )
        cycle_points = float(
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
            )
        )

        # Get today's date in ISO format using the local timezone.
        today_local_iso = kh.get_today_local_iso()

        # Get badge level information: highest earned badge, next lower badge, baseline, etc.
        highest_earned, _, next_lower, baseline, _ = self._get_cumulative_badge_levels(
            kid_id
        )
        if not highest_earned:
            return

        # Determine the maintenance threshold, reset type, grace period duration, and whether reset is enabled.
        maintenance_required = float(
            highest_earned.get(const.DATA_BADGE_TARGET, {}).get(
                const.DATA_BADGE_MAINTENANCE_RULES, const.DEFAULT_ZERO
            )
        )
        reset_schedule = highest_earned.get(const.DATA_BADGE_RESET_SCHEDULE, {})
        frequency = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY
        )
        grace_days = int(
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS, const.DEFAULT_ZERO
            )
        )
        reset_enabled = frequency is not None and frequency != const.FREQUENCY_NONE

        # DEBUG: Log the key parameters derived from today's date and the highest earned badge.
        const.LOGGER.debug(
            "DEBUG: Manage Cumulative Badge Maintenance - today_local=%s, highest_earned=%s, maintenance_required=%.2f, reset_type=%s, grace_days=%d, reset_enabled=%s",
            today_local_iso,
            highest_earned.get(const.DATA_BADGE_NAME),
            maintenance_required,
            frequency,
            grace_days,
            reset_enabled,
        )

        # If the badge is not recurring (reset not enabled):
        # clear any existing maintenance and grace dates and exit the function.
        if not reset_enabled:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: None,
                }
            )
            self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
                cumulative_badge_progress
            )
            self._persist()
            self.async_set_updated_data(self._data)
            return

        award_success = False
        demotion_required = False

        # Check if the maintenance period (or grace period) has ended based on the current status.
        if (
            status
            in (
                const.CUMULATIVE_BADGE_STATE_ACTIVE,
                const.CUMULATIVE_BADGE_STATE_DEMOTED,
            )
            and end_date_iso
            and today_local_iso >= end_date_iso
        ):
            # If cycle points meet or exceed the required maintenance threshold, the badge is maintained.
            if cycle_points >= maintenance_required:
                award_success = True
            # If it is already past the grace date, then a demotion is required (edge case)
            elif grace_date_iso and today_local_iso >= grace_date_iso:
                demotion_required = True
            # Otherwise, if a grace period is allowed, move the badge status into the grace state.
            elif grace_days > const.DEFAULT_ZERO:
                cumulative_badge_progress[
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS
                ] = const.CUMULATIVE_BADGE_STATE_GRACE
            # If neither condition is met, then a demotion is required.
            else:
                demotion_required = True

        elif status == const.CUMULATIVE_BADGE_STATE_GRACE:
            # While in the grace period, if the required cycle points are met, maintain the badge.
            if cycle_points >= maintenance_required:
                award_success = True
            # If the grace period has expired, then a demotion is required.
            elif grace_date_iso and today_local_iso >= grace_date_iso:
                demotion_required = True

        # Determine the frequency and custom fields before proceeding
        reset_schedule = highest_earned.get(const.DATA_BADGE_RESET_SCHEDULE, {})
        frequency = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )
        custom_interval = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
        )
        custom_interval_unit = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
        )
        # Use reference_dt if available; otherwise, default to today's date
        base_date_iso = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_END_DATE, today_local_iso
        )

        # Fallback to today's date if reference_dt is None
        if not base_date_iso:
            base_date_iso = today_local_iso

        # If the base date is in the future, use it as the reference date so the next schedule is in the future of that date.
        # As an example if on June 5th I create a badge and give it an end date of July 7th and chooose frequency of Period End,
        # then the expectation would be a next scheduled date of Sept 30th, not June 30th.
        reference_datetime_iso = (
            base_date_iso if base_date_iso > today_local_iso else today_local_iso
        )

        # Initialize the variables for the next maintenance end date and grace end date
        next_end = None
        next_grace = None

        # First-Time Assignment:
        # If the badge is reset-enabled but no maintenance end date is set (i.e., first-time award),
        # then calculate and set the maintenance and grace dates.
        is_first_time = reset_enabled and not cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE
        )

        # Check if the maintenance period or grace period has ended
        if award_success or demotion_required or is_first_time:
            if frequency == const.CONF_CUSTOM:
                # If custom interval and unit are valid, calculate next_end make sure it is in the future and past the reference
                if custom_interval and custom_interval_unit:
                    next_end = kh.adjust_datetime_by_interval(
                        base_date=base_date_iso,
                        interval_unit=custom_interval_unit,  # Fix: change from custom_interval_unit to interval_unit
                        delta=custom_interval,  # Fix: change from custom_interval to delta
                        require_future=True,
                        reference_datetime=reference_datetime_iso,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
                else:
                    # Fallback to existing logic if custom interval/unit are invalid
                    next_end = kh.get_next_scheduled_datetime(
                        base_date_iso,
                        interval_type=frequency,
                        require_future=True,
                        reference_datetime=reference_datetime_iso,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
            else:
                # Default behavior for non-custom frequencies
                base_date_iso = today_local_iso
                next_end = kh.get_next_scheduled_datetime(
                    base_date_iso,
                    interval_type=frequency,
                    require_future=True,
                    reference_datetime=reference_datetime_iso,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )

            # Compute the grace period end date by adding the grace period (in days) to the maintenance end date
            next_grace = kh.adjust_datetime_by_interval(
                next_end,
                const.CONF_DAYS,
                grace_days,
                require_future=True,
                return_type=const.HELPER_RETURN_ISO_DATE,
            )

        # If the badge maintenance requirements are met, update the badge as successfully maintained.
        if award_success:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: next_end,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: next_grace,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: const.CUMULATIVE_BADGE_STATE_ACTIVE,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: highest_earned.get(
                        const.DATA_BADGE_INTERNAL_ID
                    ),
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: highest_earned.get(
                        const.DATA_BADGE_NAME
                    ),
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: highest_earned.get(
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE
                    ),
                }
            )
            # Award the badge through the helper function.
            self._award_badge(kid_id, highest_earned.get(const.DATA_BADGE_INTERNAL_ID))

        # If demotion is required due to failure to meet maintenance requirements:
        if demotion_required:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: const.CUMULATIVE_BADGE_STATE_DEMOTED,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: next_lower.get(
                        const.DATA_BADGE_INTERNAL_ID
                    )
                    if next_lower
                    else None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: next_lower.get(
                        const.DATA_BADGE_NAME
                    )
                    if next_lower
                    else None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: next_lower.get(
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE
                    )
                    if next_lower
                    else None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE: baseline
                    + cycle_points,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS: 0,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: next_end,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: next_grace,
                }
            )
            self._update_point_multiplier_for_kid(kid_id)

        # If is first_time, then set the end dates
        if is_first_time:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: next_end,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: next_grace,
                }
            )

        # Simplified final debug: show only key maintenance info.
        const.LOGGER.debug(
            "DEBUG: Manage Cumulative Badge Maintenance - Final (Kid=%s): Status=%s, End=%s, Grace=%s, CyclePts=%.2f",
            kid_name,
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS
            ),
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE
            ),
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE
            ),
            float(
                cumulative_badge_progress.get(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
                )
            ),
        )

        # Save the updated progress and notify any listeners. The extra update here is to do a merge
        # as a precaution ensuring nothing gets lost if other keys have been changed during processign
        existing_progress = self.kids_data[kid_id].get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )
        existing_progress.update(cumulative_badge_progress)
        self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
            existing_progress
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def _get_cumulative_badge_levels(
        self, kid_id: str
    ) -> tuple[Optional[dict], Optional[dict], Optional[dict], float, float]:
        """
        Determines the highest earned cumulative badge for a kid, and the next higher/lower badge tiers.

        Returns:
            - highest_earned_badge_info (dict or None)
            - next_higher_badge_info (dict or None)
            - next_lower_badge_info (dict or None)
            - baseline (float)
            - cycle_points (float)
        """

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return None, None, None, 0.0, 0.0

        progress = kid_info.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {})
        baseline = round(
            float(progress.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE, 0)), 1
        )
        cycle_points = round(
            float(
                progress.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0)
            ),
            1,
        )
        total_points = baseline + cycle_points

        # Get sorted list of cumulative badges (lowest to highest threshold)
        cumulative_badges = sorted(
            (
                (badge_id, badge_info)
                for badge_id, badge_info in self.badges_data.items()
                if badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE
            ),
            key=lambda item: float(
                item[1]
                .get(const.DATA_BADGE_TARGET, {})
                .get(const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0)
            ),
        )

        if not cumulative_badges:
            return None, None, None, baseline, cycle_points

        highest_earned = None
        next_higher = None
        next_lower = None
        previous_badge_info = None

        for badge_id, badge_info in cumulative_badges:
            threshold = float(
                badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )

            # Set the is_assigned_to flag: True if the list is empty or if kid_id is in the assigned list
            is_assigned_to = not badge_info.get(
                const.DATA_BADGE_ASSIGNED_TO, []
            ) or kid_id in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])

            if is_assigned_to:
                if total_points >= threshold:
                    highest_earned = badge_info
                    next_lower = previous_badge_info
                else:
                    next_higher = badge_info
                    break

                previous_badge_info = badge_info

        return highest_earned, next_higher, next_lower, baseline, cycle_points

    # -------------------------------------------------------------------------------------
    # Penalties: Apply
    # -------------------------------------------------------------------------------------

    def apply_penalty(self, parent_name: str, kid_id: str, penalty_id: str):
        """Apply penalty => negative points to reduce kid's points."""
        penalty_info = self.penalties_data.get(penalty_id)
        if not penalty_info:
            raise HomeAssistantError(f"Penalty ID '{penalty_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        penalty_pts = penalty_info.get(const.DATA_PENALTY_POINTS, const.DEFAULT_ZERO)
        self.update_kid_points(
            kid_id, delta=penalty_pts, source=const.POINTS_SOURCE_PENALTIES
        )

        # increment penalty_applies
        if penalty_id in kid_info[const.DATA_KID_PENALTY_APPLIES]:
            kid_info[const.DATA_KID_PENALTY_APPLIES][penalty_id] += 1
        else:
            kid_info[const.DATA_KID_PENALTY_APPLIES][penalty_id] = 1

        # Send a notification to the kid that a penalty was applied
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_PENALTY_ID: penalty_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Penalty Applied",
                message=f"A '{penalty_info[const.DATA_PENALTY_NAME]}' penalty was applied. Your points changed by {penalty_pts}.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Bonuses: Apply
    # -------------------------------------------------------------------------

    def apply_bonus(self, parent_name: str, kid_id: str, bonus_id: str):
        """Apply bonus => positive points to increase kid's points."""
        bonus_info = self.bonuses_data.get(bonus_id)
        if not bonus_info:
            raise HomeAssistantError(f"Bonus ID '{bonus_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

        bonus_pts = bonus_info.get(const.DATA_BONUS_POINTS, const.DEFAULT_ZERO)
        self.update_kid_points(
            kid_id, delta=bonus_pts, source=const.POINTS_SOURCE_BONUSES
        )

        # increment bonus_applies
        if bonus_id in kid_info[const.DATA_KID_BONUS_APPLIES]:
            kid_info[const.DATA_KID_BONUS_APPLIES][bonus_id] += 1
        else:
            kid_info[const.DATA_KID_BONUS_APPLIES][bonus_id] = 1

        # Send a notification to the kid that a bonus was applied
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_BONUS_ID: bonus_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Bonus Applied",
                message=f"A '{bonus_info[const.DATA_BONUS_NAME]}' bonus was applied. Your points changed by {bonus_pts}.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Achievements: Check, Award
    # -------------------------------------------------------------------------
    def _check_achievements_for_kid(self, kid_id: str):
        """Evaluate all achievement criteria for a given kid.

        For each achievement not already awarded, check its type and update progress accordingly.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        today_local = kh.get_today_local_date()

        for achievement_id, achievement_info in self._data[
            const.DATA_ACHIEVEMENTS
        ].items():
            progress = achievement_info.setdefault(const.DATA_ACHIEVEMENT_PROGRESS, {})
            if kid_id in progress and progress[kid_id].get(
                const.DATA_ACHIEVEMENT_AWARDED, False
            ):
                continue

            ach_type = achievement_info.get(const.DATA_ACHIEVEMENT_TYPE)
            target = achievement_info.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)

            # For a streak achievement, update a streak counter:
            if ach_type == const.ACHIEVEMENT_TYPE_STREAK:
                progress = progress.setdefault(
                    kid_id,
                    {
                        const.DATA_KID_CURRENT_STREAK: const.DEFAULT_ZERO,
                        const.DATA_KID_LAST_STREAK_DATE: None,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                self._update_streak_progress(progress, today_local)
                if progress[const.DATA_KID_CURRENT_STREAK] >= target:
                    self._award_achievement(kid_id, achievement_id)

            # For a total achievement, simply compare total completed chores:
            elif ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
                # Get per–kid progress for this achievement.
                progress = achievement_info.setdefault(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).setdefault(
                    kid_id,
                    {
                        const.DATA_ACHIEVEMENT_BASELINE: None,
                        const.DATA_ACHIEVEMENT_CURRENT_VALUE: const.DEFAULT_ZERO,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                # Set the baseline so that we only count chores done after deployment.
                if (
                    const.DATA_ACHIEVEMENT_BASELINE not in progress
                    or progress[const.DATA_ACHIEVEMENT_BASELINE] is None
                ):
                    progress[const.DATA_ACHIEVEMENT_BASELINE] = kid_info.get(
                        const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, const.DEFAULT_ZERO
                    )

                # Calculate progress as (current total minus baseline)
                current_total = kid_info.get(
                    const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, const.DEFAULT_ZERO
                )

                progress[const.DATA_ACHIEVEMENT_CURRENT_VALUE] = current_total

                effective_target = progress[const.DATA_ACHIEVEMENT_BASELINE] + target

                if current_total >= effective_target:
                    self._award_achievement(kid_id, achievement_id)

            # For daily minimum achievement, compare total daily chores:
            elif ach_type == const.ACHIEVEMENT_TYPE_DAILY_MIN:
                # Initialize progress for this achievement if missing.
                progress = achievement_info.setdefault(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).setdefault(
                    kid_id,
                    {
                        const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE: None,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                today_local_iso = kh.get_today_local_iso()

                # Only award bonus if not awarded today AND the kid's daily count meets the threshold.
                if (
                    progress.get(const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE)
                    != today_local_iso
                    and kid_info.get(
                        const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY,
                        const.DEFAULT_ZERO,
                    )
                    >= target
                ):
                    self._award_achievement(kid_id, achievement_id)
                    progress[const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE] = today_local_iso

    def _award_achievement(self, kid_id: str, achievement_id: str):
        """Award the achievement to the kid.

        Update the achievement progress to indicate it is earned,
        and send notifications to both the kid and their parents.
        """
        achievement_info = self.achievements_data.get(achievement_id)
        if not achievement_info:
            const.LOGGER.error(
                "ERROR: Achievement Award - Achievement ID '%s' not found.",
                achievement_id,
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = achievement_info.setdefault(
            const.DATA_ACHIEVEMENT_PROGRESS, {}
        ).get(kid_id)
        if progress_for_kid is None:
            # If it doesn't exist, initialize it with baseline from the kid's current total.
            kid_info = self.kids_data.get(kid_id, {})
            progress_dict = {
                const.DATA_ACHIEVEMENT_BASELINE: kid_info.get(
                    const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, const.DEFAULT_ZERO
                ),
                const.DATA_ACHIEVEMENT_CURRENT_VALUE: const.DEFAULT_ZERO,
                const.DATA_ACHIEVEMENT_AWARDED: False,
            }
            achievement_info[const.DATA_ACHIEVEMENT_PROGRESS][kid_id] = progress_dict
            progress_for_kid = progress_dict

        # Mark achievement as earned for the kid by storing progress (e.g. set to target)
        progress_for_kid[const.DATA_ACHIEVEMENT_AWARDED] = True
        progress_for_kid[const.DATA_ACHIEVEMENT_CURRENT_VALUE] = achievement_info.get(
            const.DATA_ACHIEVEMENT_TARGET_VALUE, 1
        )

        # Award the extra reward points defined in the achievement
        extra_points = achievement_info.get(
            const.DATA_ACHIEVEMENT_REWARD_POINTS, const.DEFAULT_ZERO
        )
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            self.update_kid_points(
                kid_id, delta=extra_points, source=const.POINTS_SOURCE_ACHIEVEMENTS
            )

        # Notify kid and parents
        extra_data = {
            const.DATA_KID_ID: kid_id,
            const.DATA_ACHIEVEMENT_ID: achievement_id,
        }
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Achievement Earned",
                message=f"You have earned the achievement: '{achievement_info.get(const.DATA_ACHIEVEMENT_NAME)}'.",
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Achievement Earned",
                message=f"{self.kids_data[kid_id][const.DATA_KID_NAME]} has earned the achievement: '{achievement_info.get(const.DATA_ACHIEVEMENT_NAME)}'.",
                extra_data=extra_data,
            )
        )
        const.LOGGER.debug(
            "DEBUG: Achievement Award - Achievement ID '%s' to Kid ID '%s'",
            achievement_info.get(const.DATA_ACHIEVEMENT_NAME),
            kid_id,
        )
        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Challenges: Check, Award
    # -------------------------------------------------------------------------
    def _check_challenges_for_kid(self, kid_id: str):
        """Evaluate all challenge criteria for a given kid.

        Checks that the challenge is active and then updates progress.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        now_utc = dt_util.utcnow()
        for challenge_id, challenge_info in self.challenges_data.items():
            progress = challenge_info.setdefault(const.DATA_CHALLENGE_PROGRESS, {})
            if kid_id in progress and progress[kid_id].get(
                const.DATA_CHALLENGE_AWARDED, False
            ):
                continue

            # Check challenge window
            start_date_utc = kh.parse_datetime_to_utc(
                challenge_info.get(const.DATA_CHALLENGE_START_DATE)
            )

            end_date_utc = kh.parse_datetime_to_utc(
                challenge_info.get(const.DATA_CHALLENGE_END_DATE)
            )

            if start_date_utc and now_utc < start_date_utc:
                continue
            if end_date_utc and now_utc > end_date_utc:
                continue

            target = challenge_info.get(const.DATA_CHALLENGE_TARGET_VALUE, 1)
            challenge_type = challenge_info.get(const.DATA_CHALLENGE_TYPE)

            # For a total count challenge:
            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                progress = progress.setdefault(
                    kid_id,
                    {
                        const.DATA_CHALLENGE_COUNT: const.DEFAULT_ZERO,
                        const.DATA_CHALLENGE_AWARDED: False,
                    },
                )

                if progress[const.DATA_CHALLENGE_COUNT] >= target:
                    self._award_challenge(kid_id, challenge_id)
            # For a daily minimum challenge, you might store per-day counts:
            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                progress = progress.setdefault(
                    kid_id,
                    {
                        const.DATA_CHALLENGE_DAILY_COUNTS: {},
                        const.DATA_CHALLENGE_AWARDED: False,
                    },
                )

                required_daily = challenge_info.get(
                    const.DATA_CHALLENGE_REQUIRED_DAILY, 1
                )

                if start_date_utc and end_date_utc:
                    num_days = (end_date_utc - start_date_utc).days + 1
                    # Verify for each day:
                    success = True
                    for n in range(num_days):
                        day = (start_date_utc + timedelta(days=n)).date().isoformat()
                        if (
                            progress[const.DATA_CHALLENGE_DAILY_COUNTS].get(
                                day, const.DEFAULT_ZERO
                            )
                            < required_daily
                        ):
                            success = False
                            break
                    if success:
                        self._award_challenge(kid_id, challenge_id)

    def _award_challenge(self, kid_id: str, challenge_id: str):
        """Award the challenge to the kid.

        Update progress and notify kid/parents.
        """
        challenge_info = self.challenges_data.get(challenge_id)
        if not challenge_info:
            const.LOGGER.error(
                "ERROR: Challenge Award - Challenge ID '%s' not found", challenge_id
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = challenge_info.setdefault(
            const.DATA_CHALLENGE_PROGRESS, {}
        ).setdefault(
            kid_id,
            {
                const.DATA_CHALLENGE_COUNT: const.DEFAULT_ZERO,
                const.DATA_CHALLENGE_AWARDED: False,
            },
        )

        # Mark challenge as earned for the kid by storing progress
        progress_for_kid[const.DATA_CHALLENGE_AWARDED] = True
        progress_for_kid[const.DATA_CHALLENGE_COUNT] = challenge_info.get(
            const.DATA_CHALLENGE_TARGET_VALUE, 1
        )

        # Award extra reward points from the challenge
        extra_points = challenge_info.get(
            const.DATA_CHALLENGE_REWARD_POINTS, const.DEFAULT_ZERO
        )
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            self.update_kid_points(
                kid_id, delta=extra_points, source=const.POINTS_SOURCE_CHALLENGES
            )

        # Notify kid and parents
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHALLENGE_ID: challenge_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Challenge Completed",
                message=f"You have completed the challenge: '{challenge_info.get(const.DATA_CHALLENGE_NAME)}'.",
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Challenge Completed",
                message=f"{self.kids_data[kid_id][const.DATA_KID_NAME]} has completed the challenge: '{challenge_info.get(const.DATA_CHALLENGE_NAME)}'.",
                extra_data=extra_data,
            )
        )
        const.LOGGER.debug(
            "DEBUG: Challenge Award - Challenge ID '%s' to Kid ID '%s'",
            challenge_info.get(const.DATA_CHALLENGE_NAME),
            kid_id,
        )
        self._persist()
        self.async_set_updated_data(self._data)

    def _update_streak_progress(self, progress: dict, today: date):
        """Update a streak progress dict.

        If the last approved date was yesterday, increment the streak.
        Otherwise, reset to 1.
        """
        last_date = None
        if progress.get(const.DATA_KID_LAST_STREAK_DATE):
            try:
                last_date = date.fromisoformat(
                    progress[const.DATA_KID_LAST_STREAK_DATE]
                )
            except Exception:
                last_date = None

        # If already updated today, do nothing
        if last_date == today:
            return

        # If yesterday was the last update, increment the streak
        elif last_date == today - timedelta(days=1):
            progress[const.DATA_KID_CURRENT_STREAK] += 1

        # Reset to 1 if not done yesterday
        else:
            progress[const.DATA_KID_CURRENT_STREAK] = 1

        progress[const.DATA_KID_LAST_STREAK_DATE] = today.isoformat()

    # -------------------------------------------------------------------------------------
    # Recurring / Reset / Overdue
    # -------------------------------------------------------------------------------------

    async def _check_overdue_chores(self):
        """Check and mark overdue chores if due date is passed.

        Send an overdue notification only if not sent in the last 24 hours.
        """
        now_utc = dt_util.utcnow()
        const.LOGGER.debug(
            "DEBUG: Overdue Chores - Starting check at %s. Enable debug flag to see more details.",
            now_utc.isoformat(),
        )

        # Add a flag to control debug messages
        debug_enabled = False

        for chore_id, chore_info in self.chores_data.items():
            # Get the list of assigned kids
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

            # Check if all assigned kids have either claimed or approved the chore
            all_kids_claimed_or_approved = all(
                chore_id
                in self.kids_data.get(kid_id, {}).get(const.DATA_KID_CLAIMED_CHORES, [])
                or chore_id
                in self.kids_data.get(kid_id, {}).get(
                    const.DATA_KID_APPROVED_CHORES, []
                )
                for kid_id in assigned_kids
            )

            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})

            # Only skip the chore if ALL assigned kids have acted on it
            if all_kids_claimed_or_approved:
                continue

            due_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
            if not due_str:
                if debug_enabled:
                    const.LOGGER.debug(
                        "DEBUG: Overdue Chores - Chore ID '%s' has no due date. Checking overdue status",
                        chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    )

                # If it has no due date, but is overdue, it should be marked as pending
                # Also check if status is independent, just in case
                if (
                    chore_info.get(const.DATA_CHORE_STATE) == const.CHORE_STATE_OVERDUE
                    or chore_info.get(const.DATA_CHORE_STATE)
                    == const.CHORE_STATE_INDEPENDENT
                ):
                    for kid_id in assigned_kids:
                        if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                            self._process_chore_state(
                                kid_id, chore_id, const.CHORE_STATE_PENDING
                            )
                            if debug_enabled:
                                const.LOGGER.debug(
                                    "DEBUG: Overdue Chores - Chore ID '%s' status is overdue but no due date. Cleared overdue status",
                                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                                )
                continue

            try:
                due_date_utc = kh.parse_datetime_to_utc(due_str)

            except Exception as err:
                const.LOGGER.error(
                    "ERROR: Overdue Chores - Error parsing due date '%s' for Chore ID '%s': %s",
                    due_str,
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    err,
                )
                continue

            # Check for applicable day is no longer required; the scheduling function ensures due_date matches applicable day criteria.
            if now_utc < due_date_utc:
                # Not past due date, but before resetting the state back to pending, check if global state is currently overdue
                for kid_id in assigned_kids:
                    if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                        self._process_chore_state(
                            kid_id, chore_id, const.CHORE_STATE_PENDING
                        )
                        if debug_enabled:
                            const.LOGGER.debug(
                                "DEBUG: Overdue Chores - Chore ID '%s' status is overdue but not yet due. Cleared overdue status",
                                chore_info.get(const.DATA_CHORE_NAME, chore_id),
                            )

                continue

            # Handling for overdue is the same for shared and non-shared chores
            # Status and global status will be determined by the chore state processor
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})

                # Skip if kid already claimed/approved on the chore.
                if chore_id in kid_info.get(
                    const.DATA_KID_CLAIMED_CHORES, []
                ) or chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                    continue

                # Mark chore as overdue for this kid.
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_OVERDUE)
                if debug_enabled:
                    const.LOGGER.debug(
                        "DEBUG: Overdue Chores - Setting Chore ID '%s' as overdue for Kid ID '%s'",
                        chore_info.get(const.DATA_CHORE_NAME, chore_id),
                        kid_id,
                    )

                # Check notification timestamp.
                last_notif_str = kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS].get(
                    chore_id
                )
                notify = False
                if last_notif_str:
                    try:
                        last_dt = kh.parse_datetime_to_utc(last_notif_str)
                        if (
                            last_dt is None
                            or (last_dt < due_date_utc)
                            or (
                                (now_utc - last_dt)
                                >= timedelta(hours=const.DEFAULT_NOTIFY_DELAY_REMINDER)
                            )
                        ):
                            notify = True
                        else:
                            if debug_enabled:
                                const.LOGGER.debug(
                                    "DEBUG: Overdue Chores - Chore ID '%s' for Kid ID '%s' already notified in the last 24 hours",
                                    chore_id,
                                    kid_id,
                                )
                    except Exception as err:
                        const.LOGGER.error(
                            "ERROR: Overdue Chores - Error parsing overdue notification '%s' for Chore ID '%s', Kid ID '%s': %s",
                            last_notif_str,
                            chore_info.get(const.DATA_CHORE_NAME, chore_id),
                            kid_id,
                            err,
                        )
                        notify = True
                else:
                    notify = True

                if notify:
                    kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS][chore_id] = (
                        now_utc.isoformat()
                    )
                    extra_data = {
                        const.DATA_KID_ID: kid_id,
                        const.DATA_CHORE_ID: chore_id,
                    }
                    actions = [
                        {
                            const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                            const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                        },
                        {
                            const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                            const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                        },
                        {
                            const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                            const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                        },
                    ]
                    if debug_enabled:
                        const.LOGGER.debug(
                            "DEBUG: Overdue Chores - Sending overdue notification for Chore ID '%s' to Kid ID '%s'",
                            chore_info.get(const.DATA_CHORE_NAME, chore_id),
                            kid_id,
                        )
                    self.hass.async_create_task(
                        self._notify_kid(
                            kid_id,
                            title="KidsChores: Chore Overdue",
                            message=f"Your chore '{chore_info.get('name', 'Unnamed Chore')}' is overdue",
                            extra_data=extra_data,
                        )
                    )
                    self.hass.async_create_task(
                        self._notify_parents(
                            kid_id,
                            title="KidsChores: Chore Overdue",
                            message=f"{kh.get_kid_name_by_id(self, kid_id)}'s chore '{chore_info.get('name', 'Unnamed Chore')}' is overdue",
                            actions=actions,
                            extra_data=extra_data,
                        )
                    )
        if debug_enabled:
            const.LOGGER.debug("DEBUG: Overdue Chores - Check completed")

    async def _reset_all_chore_counts(self, now: datetime):
        """Trigger resets based on the current time for all frequencies."""
        await self._handle_recurring_chore_resets(now)
        await self._reset_daily_reward_statuses()
        await self._check_overdue_chores()

        for kid_id, kid_info in self.kids_data.items():
            kid_info[const.DATA_KID_TODAY_CHORE_APPROVALS] = {}

    async def _handle_recurring_chore_resets(self, now: datetime):
        """Handle recurring resets for daily, weekly, and monthly frequencies."""

        await self._reschedule_recurring_chores(now)

        # Daily
        if now.hour == const.DEFAULT_DAILY_RESET_TIME.get(
            const.CONF_HOUR, const.DEFAULT_HOUR
        ):
            await self._reset_chore_counts(const.FREQUENCY_DAILY, now)

        # Weekly
        if now.weekday() == const.DEFAULT_WEEKLY_RESET_DAY:
            await self._reset_chore_counts(const.FREQUENCY_WEEKLY, now)

        # Monthly
        days_in_month = monthrange(now.year, now.month)[1]
        reset_day = min(const.DEFAULT_MONTHLY_RESET_DAY, days_in_month)
        if now.day == reset_day:
            await self._reset_chore_counts(const.FREQUENCY_MONTHLY, now)

    async def _reset_chore_counts(self, frequency: str, now: datetime):
        """Reset chore counts and statuses based on the recurring frequency."""
        # Reset counters on kids
        for kid_info in self.kids_data.values():
            if frequency == const.FREQUENCY_DAILY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY] = (
                    const.DEFAULT_ZERO
                )
                kid_info[const.DATA_KID_POINTS_EARNED_TODAY_LEGACY] = const.DEFAULT_ZERO
            elif frequency == const.FREQUENCY_WEEKLY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_WEEKLY_LEGACY] = (
                    const.DEFAULT_ZERO
                )
                kid_info[const.DATA_KID_POINTS_EARNED_WEEKLY_LEGACY] = (
                    const.DEFAULT_ZERO
                )
            elif frequency == const.FREQUENCY_MONTHLY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_MONTHLY_LEGACY] = (
                    const.DEFAULT_ZERO
                )
                kid_info[const.DATA_KID_POINTS_EARNED_MONTHLY_LEGACY] = (
                    const.DEFAULT_ZERO
                )
            elif frequency == const.FREQUENCY_YEARLY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_YEARLY_LEGACY] = (
                    const.DEFAULT_ZERO
                )
                kid_info[const.DATA_KID_POINTS_EARNED_YEARLY_LEGACY] = (
                    const.DEFAULT_ZERO
                )

        const.LOGGER.debug(
            f"DEBUG: Reset Chore Counts: {frequency.capitalize()} chore counts have been reset"
        )

        # If daily reset -> reset statuses
        if frequency == const.FREQUENCY_DAILY:
            await self._reset_daily_chore_statuses([frequency])
        elif frequency == const.FREQUENCY_WEEKLY:
            await self._reset_daily_chore_statuses([frequency, const.FREQUENCY_WEEKLY])

    async def _reschedule_recurring_chores(self, now: datetime):
        """For chores with the given recurring frequency, reschedule due date if they are approved and past due."""

        for chore_id, chore_info in self.chores_data.items():
            # Only consider chores with a recurring frequency and a defined due_date:
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) not in (
                const.FREQUENCY_DAILY,
                const.FREQUENCY_WEEKLY,
                const.FREQUENCY_BIWEEKLY,
                const.FREQUENCY_MONTHLY,
                const.FREQUENCY_CUSTOM,
            ):
                continue
            if not chore_info.get(const.DATA_CHORE_DUE_DATE):
                continue

            due_date_utc = kh.parse_datetime_to_utc(
                chore_info[const.DATA_CHORE_DUE_DATE]
            )
            if due_date_utc is None:
                const.LOGGER.debug(
                    "DEBUG: Chore Rescheduling - Error parsing due date for Chore ID '%s'.",
                    chore_id,
                )
                continue

            # If the due date is in the past and the chore is approved or approved_in_part
            if now > due_date_utc and chore_info.get(const.DATA_CHORE_STATE) in [
                const.CHORE_STATE_APPROVED,
                const.CHORE_STATE_APPROVED_IN_PART,
            ]:
                # Reschedule the chore
                self._reschedule_chore_next_due_date(chore_info)
                const.LOGGER.debug(
                    "DEBUG: Chore Rescheduling - Rescheduled recurring Chore ID '%s'",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                )

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.debug(
            "DEBUG: Chore Rescheduling - Daily recurring chores rescheduling complete"
        )

    async def _reset_daily_chore_statuses(self, target_freqs: list[str]):
        """Reset chore statuses and clear approved/claimed chores for chores with these freq."""

        now_utc = dt_util.utcnow()
        for chore_id, chore_info in self.chores_data.items():
            frequency = chore_info.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
            )
            # Only consider chores whose frequency is either in target_freqs or const.FREQUENCY_NONE.
            if frequency in target_freqs or frequency == const.FREQUENCY_NONE:
                due_date_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
                if due_date_str:
                    due_date_utc = kh.parse_datetime_to_utc(due_date_str)
                    if due_date_utc is None:
                        const.LOGGER.debug(
                            "DEBUG: Chore Reset - Failed to parse due date '%s' for Chore ID '%s'",
                            due_date_str,
                            chore_id,
                        )
                        continue
                    # If the due date has not yet been reached, skip resetting this chore.
                    if now_utc < due_date_utc:
                        continue
                # If no due date or the due date has passed, then reset the chore state
                if chore_info[const.DATA_CHORE_STATE] not in [
                    const.CHORE_STATE_PENDING,
                    const.CHORE_STATE_OVERDUE,
                ]:
                    previous_state = chore_info[const.DATA_CHORE_STATE]
                    for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                        if kid_id:
                            self._process_chore_state(
                                kid_id, chore_id, const.CHORE_STATE_PENDING
                            )
                    const.LOGGER.debug(
                        "DEBUG: Chore Reset - Resetting Chore IF '%s' from '%s' to '%s'",
                        chore_id,
                        previous_state,
                        const.CHORE_STATE_PENDING,
                    )

        # Clear pending chore approvals
        target_chore_ids = [
            chore_id
            for chore_id, chore_info in self.chores_data.items()
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) in target_freqs
        ]
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data[const.DATA_PENDING_CHORE_APPROVALS]
            if ap[const.DATA_CHORE_ID] not in target_chore_ids
        ]

        self._persist()

    async def _reset_daily_reward_statuses(self):
        """Reset all kids' reward states daily."""
        # Remove from global pending reward approvals
        self._data[const.DATA_PENDING_REWARD_APPROVALS] = []
        const.LOGGER.debug(
            "DEBUG: Daily Reset - Rewards - Pending approvals reset complete"
        )

        # For each kid, clear pending/approved reward lists to reflect daily reset
        for kid_id, kid_info in self.kids_data.items():
            kid_info[const.DATA_KID_PENDING_REWARDS] = []
            kid_info[const.DATA_KID_REDEEMED_REWARDS] = []

            const.LOGGER.debug(
                "DEBUG: Daily Reset - Rewards - Cleared daily reward statuses for Kid ID '%s' (%s)",
                kid_id,
                kid_info.get(const.DATA_KID_NAME, const.UNKNOWN_KID),
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def _reschedule_chore_next_due_date(self, chore_info: dict[str, Any]):
        """Reschedule the next due date for a chore based on its recurring frequency using scheduling helpers."""
        freq = chore_info.get(
            const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )

        # Validate custom frequency parameters.
        if freq == const.FREQUENCY_CUSTOM:
            custom_interval = chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL)
            custom_unit = chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT)
            if custom_interval is None or custom_unit not in [
                const.CONF_DAYS,
                const.CONF_WEEKS,
                const.CONF_MONTHS,
            ]:
                const.LOGGER.warning(
                    "WARNING: Chore Due Date - Reschedule - Custom frequency set, but custom interval or unit invalid for Chore ID '%s'",
                    chore_info.get(const.DATA_CHORE_NAME),
                )
                return

        due_date_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
        if not freq or freq == const.FREQUENCY_NONE or not due_date_str:
            const.LOGGER.debug(
                "DEBUG: Chore Due Date - Reschedule - Skipping reschedule. Recurring frequency '%s', Due date '%s'",
                freq,
                due_date_str,
            )
            return

        # Parse the original due date to a UTC timezone-aware datetime.
        original_due_utc = kh.parse_datetime_to_utc(due_date_str)
        if original_due_utc is None:
            const.LOGGER.debug(
                "DEBUG: Chore Due Date - Reschedule - Unable to parse due date '%s'",
                due_date_str,
            )
            return

        # Get the configured applicable weekdays (or default values if not provided).
        # Expect that the order/index of WEEKDAY_OPTIONS matches the weekday number. i.e. 0=mon 1=tue
        raw_applicable = chore_info.get(
            const.CONF_APPLICABLE_DAYS, const.DEFAULT_APPLICABLE_DAYS
        )
        if raw_applicable and isinstance(next(iter(raw_applicable), None), str):
            # Use the order of keys in WEEKDAY_OPTIONS.  The keys are in insertion order.
            order = list(
                const.WEEKDAY_OPTIONS.keys()
            )  # This should be: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            applicable_days = [
                order.index(day.lower())
                for day in raw_applicable
                if day.lower() in order
            ]
        else:
            applicable_days = list(raw_applicable) if raw_applicable else []

        now_local = kh.get_now_local_time()

        # Advance the due date based on frequency.
        if freq == const.FREQUENCY_CUSTOM:
            # For custom frequencies, use add_interval_to_datetime directly.
            next_due_utc = kh.adjust_datetime_by_interval(
                base_date=original_due_utc,
                interval_unit=custom_unit,
                delta=custom_interval,
                require_future=True,
                return_type=const.HELPER_RETURN_DATETIME,
            )
            const.LOGGER.debug(
                "DEBUG: Chore Due Date - Reschedule (Custom) - Advanced using add_interval_to_datetime: %s",
                dt_util.as_local(next_due_utc).isoformat(),
            )
        else:
            # Helper is already configured to accept standard frequencies in chore config
            helper_interval = freq

            next_due_utc = kh.get_next_scheduled_datetime(
                base_date=original_due_utc,
                interval_type=helper_interval,
                require_future=True,
                reference_datetime=now_local,
                return_type=const.HELPER_RETURN_DATETIME,
            )
            const.LOGGER.debug(
                "DEBUG: Chore Due Date - Reschedule - Advanced using get_next_scheduled_datetime: %s",
                dt_util.as_local(next_due_utc).isoformat(),
            )

        # Snap next_due to an applicable weekday if applicable_days is defined.
        # Note that function for applicable days retuns next_due local time because that is the only way
        # to determine an applicable day correctly.
        if applicable_days:
            next_due_local = kh.get_next_applicable_day(
                next_due_utc,
                applicable_days=applicable_days,
                return_type=const.HELPER_RETURN_DATETIME,
            )
            # Convert result back to UTC
            next_due_utc = dt_util.as_utc(next_due_local)
            const.LOGGER.debug(
                "DEBUG: Chore Due Date - Reschedule - After snapping to applicable day: %s",
                dt_util.as_local(next_due_local).isoformat(),
            )

        # Update the chore's due date and refresh configuration/state.
        chore_info[const.DATA_CHORE_DUE_DATE] = next_due_utc.isoformat()
        chore_id = chore_info.get(const.DATA_CHORE_INTERNAL_ID)

        self.hass.async_create_task(
            self._update_chore_due_date_in_config(
                chore_id, chore_info[const.DATA_CHORE_DUE_DATE], None, None, None
            )
        )

        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        const.LOGGER.info(
            "INFO: Chore Due Date - Rescheduling Chore ID '%s' - Original due date '%s', New due date (local) '%s'",
            chore_info.get(const.DATA_CHORE_NAME, chore_id),
            dt_util.as_local(original_due_utc).isoformat(),
            dt_util.as_local(next_due_utc).isoformat(),
        )

    # Set Chore Due Date
    def set_chore_due_date(self, chore_id: str, due_date: Optional[datetime]) -> None:
        """Set the due date of a chore."""
        # Retrieve the chore data; raise error if not found.
        chore_info = self.chores_data.get(chore_id)
        if chore_info is None:
            raise HomeAssistantError(f"Chore ID '{chore_id}' not found.")

        # Convert the due_date to an ISO-formatted string if provided; otherwise use None.
        new_due_date_iso = due_date.isoformat() if due_date else None

        # Update the chore's due date. If the key is missing, add it.
        try:
            chore_info[const.DATA_CHORE_DUE_DATE] = new_due_date_iso
        except KeyError as err:
            raise HomeAssistantError(
                f"Missing 'due date' in Chore ID '{chore_id}': {err}"
            )

        # If the due date is cleared (None), then remove any recurring frequency
        # and custom interval settings unless the frequency is none, daily, or weekly.
        if new_due_date_iso is None:
            # const.FREQUENCY_DAILY, const.FREQUENCY_WEEKLY, and const.FREQUENCY_NONE are all OK without a due_date
            current_frequency = chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) not in (
                const.FREQUENCY_NONE,
                const.FREQUENCY_DAILY,
                const.FREQUENCY_WEEKLY,
            ):
                const.LOGGER.debug(
                    "DEBUG: Chore Due Date - Removing frequency for Chore ID '%s' - Current frequency '%s' does not work with a due date of None",
                    chore_id,
                    current_frequency,
                )
                chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] = const.FREQUENCY_NONE
                chore_info.pop(const.DATA_CHORE_CUSTOM_INTERVAL, None)
                chore_info.pop(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, None)

        # Update config_entry.options so that the new due date is visible in Options.
        # Use new_due_date here to ensure we’re passing the updated value.
        self.hass.async_create_task(
            self._update_chore_due_date_in_config(
                chore_id,
                chore_info.get(const.DATA_CHORE_DUE_DATE),
                chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY),
                chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL),
                chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT),
            )
        )

        # Reset the chore state to Pending
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        const.LOGGER.info(
            "INFO: Chore Due Date - Due date set for Chore ID '%s'",
            chore_info.get(const.DATA_CHORE_NAME, chore_id),
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # Skip Chore Due Date
    def skip_chore_due_date(self, chore_id: str) -> None:
        """Skip the current due date of a recurring chore and reschedule it."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            raise HomeAssistantError(f"Chore ID '{chore_id}' not found.")

        if (
            chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE)
            == const.FREQUENCY_NONE
        ):
            raise HomeAssistantError(
                f"Chore '{chore_info.get(const.DATA_CHORE_NAME, chore_id)}' does not have a recurring frequency."
            )
        if not chore_info.get(const.DATA_CHORE_DUE_DATE):
            raise HomeAssistantError(
                f"Chore '{chore_info.get(const.DATA_CHORE_NAME, chore_id)}' does not have a due date set."
            )

        # Compute the next due date and update the chore options/config.
        self._reschedule_chore_next_due_date(chore_info)

        self._persist()
        self.async_set_updated_data(self._data)

    # Reset Overdue Chores
    def reset_overdue_chores(
        self, chore_id: Optional[str] = None, kid_id: Optional[str] = None
    ) -> None:
        """Reset overdue chore(s) to Pending state and reschedule."""

        if chore_id:
            # Specific chore reset (with or without kid_id)
            chore_info = self.chores_data.get(chore_id)
            if not chore_info:
                raise HomeAssistantError(f"Chore ID '{chore_id}' not found.")

            const.LOGGER.info(
                "INFO: Reset Overdue Chores - Rescheduling chore: %s",
                chore_info.get(const.DATA_CHORE_NAME, chore_id),
            )
            # Reschedule happens at the chore level, so it is not necessary to check for kid_id
            # _rescheduled_next_due_date will also handle setting the status to Pending
            self._reschedule_chore_next_due_date(chore_info)

        elif kid_id:
            # Kid-only reset: reset all overdue chores for the specified kid.
            # Note that reschedule happens at the chore level, so it chores assigned to this
            # kid that are multi assigned will show as reset for those other kids
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")
            for chore_id, chore_info in self.chores_data.items():
                if kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                    if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                        const.LOGGER.info(
                            "INFO: Reset Overdue Chores - Rescheduling chore: %s for kid: %s",
                            chore_info.get(const.DATA_CHORE_NAME, chore_id),
                            kid_id,
                        )
                        # Reschedule chore which will also set status to Pending
                        self._reschedule_chore_next_due_date(chore_info)
        else:
            # Global reset: Reset all chores that are overdue.
            for kid_id, kid_info in self.kids_data.items():
                for chore_id, chore_info in self.chores_data.items():
                    if kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                        if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                            const.LOGGER.info(
                                "INFO: Reset Overdue Chores - Rescheduling chore: %s for kid: %s",
                                chore_info.get(const.DATA_CHORE_NAME, chore_id),
                                kid_id,
                            )
                            # Reschedule chore which will also set status to Pending
                            self._reschedule_chore_next_due_date(chore_info)

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Penalties: Reset
    # -------------------------------------------------------------------------------------

    def reset_penalties(
        self, kid_id: Optional[str] = None, penalty_id: Optional[str] = None
    ) -> None:
        """Reset penalties based on provided kid_id and penalty_id."""

        if penalty_id and kid_id:
            # Reset a specific penalty for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Penalties - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")
            if penalty_id not in kid_info.get(const.DATA_KID_PENALTY_APPLIES, {}):
                const.LOGGER.error(
                    "ERROR: Reset Penalties - Penalty ID '%s' does not apply to Kid ID '%s'.",
                    penalty_id,
                    kid_id,
                )
                raise HomeAssistantError(
                    f"Penalty ID '{penalty_id}' does not apply to Kid ID '{kid_id}'."
                )

            kid_info[const.DATA_KID_PENALTY_APPLIES].pop(penalty_id, None)

        elif penalty_id:
            # Reset a specific penalty for all kids
            found = False
            for kid_info in self.kids_data.values():
                if penalty_id in kid_info.get(const.DATA_KID_PENALTY_APPLIES, {}):
                    found = True
                    kid_info[const.DATA_KID_PENALTY_APPLIES].pop(penalty_id, None)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Reset Penalties - Penalty ID '%s' not found in any kid's data.",
                    penalty_id,
                )

        elif kid_id:
            # Reset all penalties for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Penalties - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_PENALTY_APPLIES].clear()

        else:
            # Reset all penalties for all kids
            const.LOGGER.info(
                "INFO: Reset Penalties - Resetting all penalties for all kids"
            )
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_PENALTY_APPLIES].clear()

        const.LOGGER.debug(
            "DEBUG: Reset Penalties - Penalties reset completed - Kid ID '%s',  Penalty ID '%s'",
            kid_id,
            penalty_id,
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Bonuses: Reset
    # -------------------------------------------------------------------------------------

    def reset_bonuses(
        self, kid_id: Optional[str] = None, bonus_id: Optional[str] = None
    ) -> None:
        """Reset bonuses based on provided kid_id and bonus_id."""

        if bonus_id and kid_id:
            # Reset a specific bonus for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Bonuses - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")
            if bonus_id not in kid_info.get(const.DATA_KID_BONUS_APPLIES, {}):
                const.LOGGER.error(
                    "ERROR: Reset Bonuses - Bonus '%s' does not apply to Kid ID '%s'.",
                    bonus_id,
                    kid_id,
                )
                raise HomeAssistantError(
                    f"Bonus ID '{bonus_id}' does not apply to Kid ID '{kid_id}'."
                )

            kid_info[const.DATA_KID_BONUS_APPLIES].pop(bonus_id, None)

        elif bonus_id:
            # Reset a specific bonus for all kids
            found = False
            for kid_info in self.kids_data.values():
                if bonus_id in kid_info.get(const.DATA_KID_BONUS_APPLIES, {}):
                    found = True
                    kid_info[const.DATA_KID_BONUS_APPLIES].pop(bonus_id, None)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Reset Bonuses - Bonus '%s' not found in any kid's data.",
                    bonus_id,
                )

        elif kid_id:
            # Reset all bonuses for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Bonuses - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_BONUS_APPLIES].clear()

        else:
            # Reset all bonuses for all kids
            const.LOGGER.info(
                "INFO: Reset Bonuses - Resetting all bonuses for all kids."
            )
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_BONUS_APPLIES].clear()

        const.LOGGER.debug(
            "DEBUG: Reset Bonuses - Bonuses reset completed - Kid ID '%s', Bonus ID '%s'",
            kid_id,
            bonus_id,
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Rewards: Reset
    # This function resets reward-related data for a specified kid and/or reward by
    # clearing claims, approvals, redeemed and pending rewards, and removing associated
    # pending reward approvals from the global data.
    # -------------------------------------------------------------------------------------

    def reset_rewards(
        self, kid_id: Optional[str] = None, reward_id: Optional[str] = None
    ) -> None:
        """Reset rewards based on provided kid_id and reward_id."""

        if reward_id and kid_id:
            # Reset a specific reward for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Rewards - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_REWARD_CLAIMS].pop(reward_id, None)
            kid_info[const.DATA_KID_REWARD_APPROVALS].pop(reward_id, None)
            kid_info[const.DATA_KID_REDEEMED_REWARDS] = [
                reward
                for reward in kid_info[const.DATA_KID_REDEEMED_REWARDS]
                if reward != reward_id
            ]
            kid_info[const.DATA_KID_PENDING_REWARDS] = [
                reward
                for reward in kid_info[const.DATA_KID_PENDING_REWARDS]
                if reward != reward_id
            ]

            # Remove open claims from pending approvals for this kid and reward.
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
                ap
                for ap in self._data[const.DATA_PENDING_REWARD_APPROVALS]
                if not (
                    ap[const.DATA_KID_ID] == kid_id
                    and ap[const.DATA_REWARD_ID] == reward_id
                )
            ]

        elif reward_id:
            # Reset a specific reward for all kids
            found = False
            for kid_info in self.kids_data.values():
                if reward_id in kid_info.get(const.DATA_KID_REWARD_CLAIMS, {}):
                    found = True
                    kid_info[const.DATA_KID_REWARD_CLAIMS].pop(reward_id, None)
                if reward_id in kid_info.get(const.DATA_KID_REWARD_APPROVALS, {}):
                    found = True
                    kid_info[const.DATA_KID_REWARD_APPROVALS].pop(reward_id, None)
                kid_info[const.DATA_KID_REDEEMED_REWARDS] = [
                    reward
                    for reward in kid_info[const.DATA_KID_REDEEMED_REWARDS]
                    if reward != reward_id
                ]
                kid_info[const.DATA_KID_PENDING_REWARDS] = [
                    reward
                    for reward in kid_info[const.DATA_KID_PENDING_REWARDS]
                    if reward != reward_id
                ]
            # Remove open claims from pending approvals for this reward (all kids).
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
                ap
                for ap in self._data[const.DATA_PENDING_REWARD_APPROVALS]
                if ap[const.DATA_REWARD_ID] != reward_id
            ]
            if not found:
                const.LOGGER.warning(
                    "WARNING: Reset Rewards - Reward '%s' not found in any kid's data.",
                    reward_id,
                )

        elif kid_id:
            # Reset all rewards for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Rewards - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_REWARD_CLAIMS].clear()
            kid_info[const.DATA_KID_REWARD_APPROVALS].clear()
            kid_info[const.DATA_KID_REDEEMED_REWARDS].clear()
            kid_info[const.DATA_KID_PENDING_REWARDS].clear()

            # Remove open claims from pending approvals for that kid.
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
                ap
                for ap in self._data[const.DATA_PENDING_REWARD_APPROVALS]
                if ap[const.DATA_KID_ID] != kid_id
            ]

        else:
            # Reset all rewards for all kids
            const.LOGGER.info(
                "INFO: Reset Rewards - Resetting all rewards for all kids."
            )
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_REWARD_CLAIMS].clear()
                kid_info[const.DATA_KID_REWARD_APPROVALS].clear()
                kid_info[const.DATA_KID_REDEEMED_REWARDS].clear()
                kid_info[const.DATA_KID_PENDING_REWARDS].clear()

            # Clear all pending reward approvals.
            self._data[const.DATA_PENDING_REWARD_APPROVALS].clear()

        const.LOGGER.debug(
            "DEBUG: Reset Rewards - Rewards reset completed - Kid ID '%s', Reward ID '%s'",
            kid_id,
            reward_id,
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # Persist new due dates on config entries
    # This is not being used currently, but was refactored so it calls a new function _update_chore_due_date_in_config
    # which can be used to update a single chore's due date and frequency.  New function can be used in multiple places.

    async def _update_all_chore_due_dates_in_config(self) -> None:
        """Update due dates for all chores in config_entry.options."""
        tasks = []
        for chore_id, chore_info in self.chores_data.items():
            if const.DATA_CHORE_DUE_DATE in chore_info:
                tasks.append(
                    self._update_chore_due_date_in_config(
                        chore_id,
                        chore_info.get(const.DATA_CHORE_DUE_DATE),
                        recurring_frequency=chore_info.get(
                            const.DATA_CHORE_RECURRING_FREQUENCY
                        ),
                        custom_interval=chore_info.get(
                            const.DATA_CHORE_CUSTOM_INTERVAL
                        ),
                        custom_interval_unit=chore_info.get(
                            const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
                        ),
                    )
                )

        # Run all updates concurrently
        if tasks:
            await asyncio.gather(*tasks)

    # Persist new due dates on config entries
    async def _update_chore_due_date_in_config(
        self,
        chore_id: str,
        due_date: Optional[str],
        recurring_frequency: Optional[str] = None,
        custom_interval: Optional[int] = None,
        custom_interval_unit: Optional[str] = None,
    ) -> None:
        """Update the due date and frequency fields for a specific chore in config_entry.options.

        - due_date should be an ISO-formatted string (or None).
        - If a frequency is passed, then that value is set.
        If the frequency is const.FREQUENCY_CUSTOM, custom_interval and custom_interval_unit are required.
        If the frequency is not custom, any custom interval settings are cleared.
        - If no frequency is passed, then do not change the frequency or custom interval settings.
        """
        updated_options = dict(self.config_entry.options)
        chores_conf = dict(updated_options.get(const.DATA_CHORES, {}))

        # Get existing options for the chore.
        existing_options = dict(chores_conf.get(chore_id, {}))

        # Update due_date: set if provided; otherwise remove.
        if due_date is not None:
            existing_options[const.DATA_CHORE_DUE_DATE] = due_date
        else:
            existing_options.pop(const.DATA_CHORE_DUE_DATE, None)

        # If a frequency is passed, update it.
        if recurring_frequency is not None:
            existing_options[const.DATA_CHORE_RECURRING_FREQUENCY] = recurring_frequency
            if recurring_frequency == const.FREQUENCY_CUSTOM:
                # For custom frequency, custom_interval and custom_interval_unit are required.
                if custom_interval is None or custom_interval_unit is None:
                    raise HomeAssistantError(
                        "For custom frequency, both custom interval and custom interval unit are required."
                    )
                existing_options[const.DATA_CHORE_CUSTOM_INTERVAL] = custom_interval
                existing_options[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = (
                    custom_interval_unit
                )
            else:
                # For non-custom frequencies, clear any custom interval settings.
                existing_options.pop(const.DATA_CHORE_CUSTOM_INTERVAL, None)
                existing_options.pop(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, None)
        # If no frequency is passed, leave the frequency and custom fields unchanged.

        chores_conf[chore_id] = existing_options
        updated_options[const.DATA_CHORES] = chores_conf

        new_data = dict(self.config_entry.data)
        new_data[const.DATA_LAST_CHANGE] = dt_util.utcnow().isoformat()

        update_result = self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data, options=updated_options
        )
        if asyncio.iscoroutine(update_result):
            await update_result

    # -------------------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------------------

    async def send_kc_notification(
        self,
        user_id: Optional[str],
        title: str,
        message: str,
        notification_id: str,
    ) -> None:
        """Send a persistent notification to a user if possible.

        Fallback to a general persistent notification if the user is not found or not set.
        """

        hass = self.hass
        if not user_id:
            # If no user_id is provided, use a general notification
            const.LOGGER.debug(
                "DEBUG: Notification - No User ID provided. Sending a general persistent notification"
            )
            await hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: notification_id,
                },
                blocking=True,
            )
            return

        try:
            user_obj: User = await hass.auth.async_get_user(user_id)
            if not user_obj:
                const.LOGGER.warning(
                    "WARNING: Notification - User ID '%s' not found. Sending fallback persistent notification",
                    user_id,
                )
                await hass.services.async_call(
                    const.NOTIFY_PERSISTENT_NOTIFICATION,
                    const.NOTIFY_CREATE,
                    {
                        const.NOTIFY_TITLE: title,
                        const.NOTIFY_MESSAGE: message,
                        const.NOTIFY_NOTIFICATION_ID: notification_id,
                    },
                    blocking=True,
                )
                return

            await hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: notification_id,
                },
                blocking=True,
            )
        except Exception as err:
            const.LOGGER.warning(
                "WARNING: Notification - Failed to send notification to '%s': %s. Fallback to persistent notification",
                user_id,
                err,
            )
            await hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: notification_id,
                },
                blocking=True,
            )

    async def _notify_kid(
        self,
        kid_id: str,
        title: str,
        message: str,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify a kid using their configured notification settings."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return
        if not kid_info.get(const.DATA_KID_ENABLE_NOTIFICATIONS, True):
            const.LOGGER.debug(
                "DEBUG: Notification - Notifications disabled for Kid ID '%s'", kid_id
            )
            return
        mobile_enabled = kid_info.get(const.CONF_ENABLE_MOBILE_NOTIFICATIONS, True)
        persistent_enabled = kid_info.get(
            const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS, True
        )
        mobile_notify_service = kid_info.get(
            const.CONF_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
        )
        if mobile_enabled and mobile_notify_service:
            await async_send_notification(
                self.hass,
                mobile_notify_service,
                title,
                message,
                actions=actions,
                extra_data=extra_data,
                use_persistent=persistent_enabled,
            )
        elif persistent_enabled:
            await self.hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: f"kid_{kid_id}",
                },
                blocking=True,
            )
        else:
            const.LOGGER.debug(
                "DEBUG: Notification - No notification method configured for Kid ID '%s'",
                kid_id,
            )

    async def _notify_parents(
        self,
        kid_id: str,
        title: str,
        message: str,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify all parents associated with a kid using their settings."""
        for parent_id, parent_info in self.parents_data.items():
            if kid_id not in parent_info.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
                continue
            if not parent_info.get(const.DATA_PARENT_ENABLE_NOTIFICATIONS, True):
                const.LOGGER.debug(
                    "DEBUG: Notification - Notifications disabled for Parent ID '%s'",
                    parent_id,
                )
                continue
            mobile_enabled = parent_info.get(
                const.CONF_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            persistent_enabled = parent_info.get(
                const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )
            mobile_notify_service = parent_info.get(
                const.CONF_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
            )
            if mobile_enabled and mobile_notify_service:
                await async_send_notification(
                    self.hass,
                    mobile_notify_service,
                    title,
                    message,
                    actions=actions,
                    extra_data=extra_data,
                    use_persistent=persistent_enabled,
                )
            elif persistent_enabled:
                await self.hass.services.async_call(
                    const.NOTIFY_PERSISTENT_NOTIFICATION,
                    const.NOTIFY_CREATE,
                    {
                        const.NOTIFY_TITLE: title,
                        const.NOTIFY_MESSAGE: message,
                        const.NOTIFY_NOTIFICATION_ID: f"parent_{parent_id}",
                    },
                    blocking=True,
                )
            else:
                const.LOGGER.debug(
                    "DEBUG: Notification - No notification method configured for Parent ID '%s'",
                    parent_id,
                )

    async def remind_in_minutes(
        self,
        kid_id: str,
        minutes: int,
        *,
        chore_id: Optional[str] = None,
        reward_id: Optional[str] = None,
    ) -> None:
        """
        Wait for the specified number of minutes and then resend the parent's
        notification if the chore or reward is still pending approval.

        If a chore_id is provided, the method checks the corresponding chore’s state.
        If a reward_id is provided, it checks whether that reward is still pending.
        """
        const.LOGGER.debug(
            "DEBUG: Notification - Scheduling reminder for Kid ID '%s', Chore ID '%s', Reward ID '%s' in %d minutes",
            kid_id,
            chore_id,
            reward_id,
            minutes,
        )
        await asyncio.sleep(minutes * 60)

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.warning(
                "WARNING: Notification - Kid ID '%s' not found during reminder check",
                kid_id,
            )
            return

        if chore_id:
            chore_info = self.chores_data.get(chore_id)
            if not chore_info:
                const.LOGGER.warning(
                    "WARNING: Notification - Chore ID '%s' not found during reminder check",
                    chore_id,
                )
                return
            # Only resend if the chore is still in a pending-like state.
            if chore_info.get(const.DATA_CHORE_STATE) not in [
                const.CHORE_STATE_PENDING,
                const.CHORE_STATE_CLAIMED,
                const.CHORE_STATE_OVERDUE,
            ]:
                const.LOGGER.info(
                    "INFO: Notification - Chore ID '%s' is no longer pending approval. No reminder sent",
                    chore_id,
                )
                return
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                },
            ]
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            await self._notify_parents(
                kid_id,
                title="KidsChores: Reminder for Pending Chore",
                message=f"Reminder: {kid_info.get(const.DATA_KID_NAME, 'A kid')} has '{chore_info.get(const.DATA_CHORE_NAME, 'Unnamed Chore')}' chore pending approval.",
                actions=actions,
                extra_data=extra_data,
            )
            const.LOGGER.info(
                "INFO: Notification - Resent reminder for Chore ID '%s' for Kid ID '%s'",
                chore_id,
                kid_id,
            )
        elif reward_id:
            # Check if the reward is still pending approval.
            if reward_id not in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
                const.LOGGER.info(
                    "INFO: Notification - Reward ID '%s' is no longer pending approval for Kid ID '%s'. No reminder sent",
                    reward_id,
                    kid_id,
                )
                return
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                },
            ]
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
            reward_info = self.rewards_data.get(reward_id, {})
            reward_name = reward_info.get(const.DATA_REWARD_NAME, "the reward")
            await self._notify_parents(
                kid_id,
                title="KidsChores: Reminder for Pending Reward",
                message=f"Reminder: {kid_info.get(const.DATA_KID_NAME, 'A kid')} has '{reward_name}' reward pending approval.",
                actions=actions,
                extra_data=extra_data,
            )
            const.LOGGER.info(
                "INFO: Notification - Resent reminder for Reward ID '%s' for Kid ID '%s'",
                reward_id,
                kid_id,
            )
        else:
            const.LOGGER.warning(
                "WARNING: Notification - No Chore ID or Reward ID provided for reminder action"
            )

    # -------------------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------------------

    def _persist(self):
        """Save to persistent storage."""
        self.storage_manager.set_data(self._data)
        self.hass.add_job(self.storage_manager.async_save)
