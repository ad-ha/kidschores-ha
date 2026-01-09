"""Enhanced performance instrumentation for KidsChores.

This test measures the actual expensive operations that matter for optimization:
- Full integration setup time
- Entity creation and registration
- Coordinator data loading and processing
- Badge checking operations (PERF: _check_badges_for_kid)
- Overdue chore checking (PERF: _check_overdue_chores)
- Storage persistence operations (PERF: _persist)
- Home Assistant platform operations
- Memory usage analysis
"""

# pylint: disable=protected-access,unused-argument

import asyncio
import logging
import re
import time
import tracemalloc
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.kidschores.const import COORDINATOR, DOMAIN

pytestmark = pytest.mark.slow


class PerfCapture:
    """Capture PERF timing data from coordinator operations."""

    def __init__(self):
        self.operations = {}

    def parse_perf_message(self, message: str) -> None:
        """Extract timing data from PERF log messages."""
        # Pattern: "PERF: operation_name() took 0.123s ..."
        perf_pattern = r"PERF: ([^()]+)\(\) took ([\d.]+)s"
        match = re.search(perf_pattern, message)
        if match:
            operation, duration = match.groups()
            if operation not in self.operations:
                self.operations[operation] = []
            self.operations[operation].append(float(duration))

    def get_summary(self) -> dict[str, dict[str, float]]:
        """Get performance summary statistics."""
        summary = {}
        for op, times in self.operations.items():
            if times:
                summary[op] = {
                    "count": len(times),
                    "total": sum(times),
                    "avg": sum(times) / len(times),
                    "max": max(times),
                    "min": min(times),
                }
        return summary


class PerfLoggingHandler(logging.Handler):
    """Custom logging handler to capture PERF measurements."""

    def __init__(self, perf_capture: PerfCapture):
        super().__init__()
        self.perf_capture = perf_capture

    def emit(self, record):
        if hasattr(record, "getMessage"):
            message = record.getMessage()
            if "PERF:" in message:
                self.perf_capture.parse_perf_message(message)


async def test_true_performance_baseline(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Measure true performance bottlenecks including PERF operations."""
    print("\n" + "=" * 80)
    print("TRUE PERFORMANCE BASELINE - COMPREHENSIVE MEASUREMENT")
    print("=" * 80)

    # Set up PERF data capture
    perf_capture = PerfCapture()
    perf_handler = PerfLoggingHandler(perf_capture)

    # Get the kidschores logger and add our handler
    kc_logger = logging.getLogger("custom_components.kidschores")
    original_level = kc_logger.level
    kc_logger.setLevel(logging.INFO)  # Ensure INFO level to capture PERF messages
    kc_logger.addHandler(perf_handler)

    try:
        # Start memory tracking
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Measure full integration setup
        setup_start = time.perf_counter()

        # Add config entry and setup integration
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        setup_duration = time.perf_counter() - setup_start
        setup_memory = tracemalloc.get_traced_memory()[0] - baseline_memory

        print(f"🔥 CRITICAL MEASUREMENT: Full integration setup: {setup_duration:.3f}s")
        print(f"   Memory used during setup: {setup_memory / 1024 / 1024:.1f} MB")

        # Get coordinator
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id][COORDINATOR]

        # Measure entity registry operations
        er_start = time.perf_counter()
        ent_reg = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            ent_reg, mock_config_entry.entry_id
        )
        er_duration = time.perf_counter() - er_start

        print(
            f"🔥 ENTITY REGISTRY: {len(entities)} entities processed in {er_duration:.3f}s"
        )

        # Measure device registry operations
        dr_start = time.perf_counter()
        dev_reg = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(dev_reg, mock_config_entry.entry_id)
        dr_duration = time.perf_counter() - dr_start

        print(
            f"🔥 DEVICE REGISTRY: {len(devices)} devices processed in {dr_duration:.3f}s"
        )

        # Measure coordinator operations with PERF capture
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            # Clear previous PERF data
            perf_capture.operations.clear()

            # Force coordinator refresh to trigger PERF measurements
            refresh_start = time.perf_counter()
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            refresh_duration = time.perf_counter() - refresh_start

            # Force overdue checking to trigger PERF measurement
            overdue_start = time.perf_counter()
            await coordinator._check_overdue_chores()
            overdue_duration = time.perf_counter() - overdue_start

            # Force badge checking for all kids to trigger PERF measurement
            badge_start = time.perf_counter()
            for kid_id in coordinator.kids_data:
                await coordinator._check_badges_for_kid(kid_id)
            badge_duration = time.perf_counter() - badge_start

            # Force storage persistence to trigger PERF measurement
            persist_start = time.perf_counter()
            coordinator._persist()  # Not async - just call it
            await asyncio.sleep(0.05)  # Give async save time to complete
            persist_duration = time.perf_counter() - persist_start

        print(f"🔥 COORDINATOR REFRESH: {refresh_duration:.3f}s")
        print(f"🔥 OVERDUE CHECKING: {overdue_duration:.3f}s")
        print(f"🔥 BADGE CHECKING: {badge_duration:.3f}s")
        print(f"🔥 STORAGE PERSIST: {persist_duration:.3f}s")

        # Show PERF operation summary
        perf_summary = perf_capture.get_summary()
        if perf_summary:
            print("\n🔥 PERF OPERATION BREAKDOWN:")
            for op, stats in perf_summary.items():
                print(
                    f"   {op}: {stats['count']} calls, {stats['total']:.3f}s total, {stats['avg']:.3f}s avg"
                )
        else:
            print("\n⚠️  NO PERF DATA CAPTURED - Check logging level")

        # Measure entity state updates
        states_start = time.perf_counter()
        all_states = hass.states.async_all()
        kidschores_states = [
            s
            for s in all_states
            if s.entity_id.startswith("sensor.kc_")
            or s.entity_id.startswith("button.kc_")
            or s.entity_id.startswith("select.kc_")
        ]
        states_duration = time.perf_counter() - states_start

        print(
            f"🔥 STATE ENUMERATION: {len(kidschores_states)} entities in {states_duration:.3f}s"
        )

        # Get final memory usage
        final_memory = tracemalloc.get_traced_memory()[0] - baseline_memory
        tracemalloc.stop()

        print(f"🔥 TOTAL MEMORY: {final_memory / 1024 / 1024:.1f} MB")

        # Dataset scale info
        print("\n📊 DATASET SCALE:")
        print(f"   Kids: {len(coordinator.kids_data)}")
        print(f"   Parents: {len(coordinator.parents_data)}")
        print(f"   Chores: {len(coordinator.chores_data)}")
        print(f"   Badges: {len(coordinator.badges_data)}")
        print(f"   Rewards: {len(coordinator.rewards_data)}")
        print(f"   Total Entities: {len(entities)}")

        # Performance ratios
        print("\n⚡ PERFORMANCE RATIOS:")
        if len(entities) > 0:
            print(
                f"   Setup time per entity: {setup_duration * 1000 / len(entities):.1f}ms/entity"
            )
        if len(coordinator.kids_data) > 0:
            print(
                f"   Setup time per kid: {setup_duration * 1000 / len(coordinator.kids_data):.1f}ms/kid"
            )
            print(
                f"   Memory per kid: {final_memory / len(coordinator.kids_data) / 1024:.1f}KB/kid"
            )

        print("=" * 80)

    finally:
        # Restore logging
        kc_logger.removeHandler(perf_handler)
        kc_logger.setLevel(original_level)


async def test_stress_dataset_true_performance(
    hass: HomeAssistant,
    scenario_stress,
) -> None:
    """Measure performance with large stress test dataset (100 kids) including PERF operations."""
    print("\n" + "=" * 80)
    print("STRESS TEST - TRUE PERFORMANCE (100 KIDS)")
    print("=" * 80)

    config_entry, _ = scenario_stress

    # Set up PERF data capture
    perf_capture = PerfCapture()
    perf_handler = PerfLoggingHandler(perf_capture)

    # Get the kidschores logger and add our handler
    kc_logger = logging.getLogger("custom_components.kidschores")
    original_level = kc_logger.level
    kc_logger.setLevel(logging.INFO)  # Ensure INFO level to capture PERF messages
    kc_logger.addHandler(perf_handler)

    try:
        # Memory tracking
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Get coordinator (already set up by fixture)
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

        # Show dataset scale
        print("📊 STRESS DATASET LOADED:")
        print(f"   Kids: {len(coordinator.kids_data)}")
        print(f"   Parents: {len(coordinator.parents_data)}")
        print(f"   Chores: {len(coordinator.chores_data)}")
        print(f"   Badges: {len(coordinator.badges_data)}")
        print(f"   Rewards: {len(coordinator.rewards_data)}")

        # Clear previous PERF data and test all major operations
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            perf_capture.operations.clear()

            # Test overdue checking with full dataset
            overdue_start = time.perf_counter()
            await coordinator._check_overdue_chores()
            overdue_duration = time.perf_counter() - overdue_start
            print(f"🔥 OVERDUE CHECKING (100 kids): {overdue_duration:.3f}s")

            # Test badge checking for all kids (this will be the big one!)
            badge_start = time.perf_counter()
            badge_count = 0
            for kid_id in coordinator.kids_data:
                coordinator._check_badges_for_kid(kid_id)  # Not async - don't await
                badge_count += 1
                if badge_count % 20 == 0:  # Progress indicator
                    print(
                        f"   Badge checking progress: {badge_count}/{len(coordinator.kids_data)} kids"
                    )
            badge_duration = time.perf_counter() - badge_start
            print(f"🔥 BADGE CHECKING (100 kids): {badge_duration:.3f}s")

            # Test sequential badge processing sample (10 kids)
            concurrent_start = time.perf_counter()
            kid_list = list(coordinator.kids_data.keys())[:10]
            for kid_id in kid_list:
                coordinator._check_badges_for_kid(kid_id)  # Not async
            concurrent_duration = time.perf_counter() - concurrent_start
            print(f"🔥 SAMPLE BADGE PROCESSING (10 kids): {concurrent_duration:.3f}s")

            # Test full data persistence with large dataset
            persist_start = time.perf_counter()
            coordinator._persist()  # Not async - just call it
            await asyncio.sleep(0.1)  # Give async save time to complete
            persist_duration = time.perf_counter() - persist_start
            print(f"🔥 FULL DATA PERSISTENCE (large dataset): {persist_duration:.3f}s")

            # Test coordinator refresh with full dataset
            refresh_start = time.perf_counter()
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            refresh_duration = time.perf_counter() - refresh_start
            print(f"🔥 COORDINATOR REFRESH (large dataset): {refresh_duration:.3f}s")

        # Show comprehensive PERF operation breakdown
        perf_summary = perf_capture.get_summary()
        if perf_summary:
            print("\n🔥 PERF OPERATION BREAKDOWN (Stress Test):")
            for op, stats in perf_summary.items():
                total_time = stats["total"]
                calls = stats["count"]
                avg_time = stats["avg"]
                print(
                    f"   {op}: {calls} calls, {total_time:.3f}s total, {avg_time:.3f}s avg, {avg_time * 1000:.1f}ms/call"
                )

                # Calculate per-kid metrics where applicable
                if "check_badges_for_kid" in op and len(coordinator.kids_data) > 0:
                    per_kid = total_time / len(coordinator.kids_data) * 1000
                    print(f"     → {per_kid:.1f}ms per kid")
                elif "check_overdue_chores" in op and len(coordinator.chores_data) > 0:
                    operations = len(coordinator.chores_data) * len(
                        coordinator.kids_data
                    )
                    if operations > 0:
                        per_op = total_time / operations * 1000000
                        print(f"     → {per_op:.1f}μs per chore×kid operation")
        else:
            print("\n⚠️  NO PERF DATA CAPTURED - Check logging level")

        # Memory analysis
        current_memory = tracemalloc.get_traced_memory()[0] - baseline_memory
        print(f"\n🔥 MEMORY USAGE: {current_memory / 1024 / 1024:.1f} MB")

        # Entity count analysis
        ent_reg = er.async_get(hass)
        entities = er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
        print(f"🔥 TOTAL ENTITIES CREATED: {len(entities)}")

        # Performance ratios
        print("\n⚡ PERFORMANCE RATIOS (Stress Test):")
        if len(entities) > 0:
            print(
                f"   Entities per kid: {len(entities) / len(coordinator.kids_data):.1f}"
            )
            print(
                f"   Memory per entity: {current_memory / len(entities):.0f} bytes/entity"
            )
        if len(coordinator.kids_data) > 0:
            print(
                f"   Memory per kid: {current_memory / len(coordinator.kids_data) / 1024:.1f}KB/kid"
            )
            print(
                f"   Badge check time per kid: {badge_duration * 1000 / len(coordinator.kids_data):.1f}ms/kid"
            )

        # Compare sequential vs concurrent badge processing
        sequential_per_kid = badge_duration / len(coordinator.kids_data) * 1000
        concurrent_per_kid = concurrent_duration / 10 * 1000
        speedup = (
            sequential_per_kid / concurrent_per_kid if concurrent_per_kid > 0 else 0
        )
        print(f"   Sequential badge checking: {sequential_per_kid:.1f}ms/kid")
        print(f"   Concurrent badge checking: {concurrent_per_kid:.1f}ms/kid")
        if speedup > 0:
            print(f"   Concurrent speedup: {speedup:.1f}x faster")

        tracemalloc.stop()

        print("=" * 80)

    finally:
        # Restore logging
        kc_logger.removeHandler(perf_handler)
        kc_logger.setLevel(original_level)


@pytest.mark.slow  # Mark as slow test
async def test_full_scenario_performance_comprehensive(
    hass: HomeAssistant,
    scenario_full,
) -> None:
    """Comprehensive performance test with full scenario dataset including ALL PERF operations."""
    print("\n" + "=" * 80)
    print("FULL SCENARIO PERFORMANCE - COMPREHENSIVE MEASUREMENT")
    print("=" * 80)

    config_entry, _ = scenario_full

    # Set up PERF data capture
    perf_capture = PerfCapture()
    perf_handler = PerfLoggingHandler(perf_capture)

    # Get the kidschores logger and add our handler
    kc_logger = logging.getLogger("custom_components.kidschores")
    original_level = kc_logger.level
    kc_logger.setLevel(logging.INFO)  # Ensure INFO level to capture PERF messages
    kc_logger.addHandler(perf_handler)

    try:
        # Memory tracking
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Get coordinator (already set up by fixture)
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

        # Show dataset scale
        print("📊 FULL SCENARIO DATASET:")
        print(f"   Kids: {len(coordinator.kids_data)}")
        print(f"   Parents: {len(coordinator.parents_data)}")
        print(f"   Chores: {len(coordinator.chores_data)}")
        print(f"   Badges: {len(coordinator.badges_data)}")
        print(f"   Rewards: {len(coordinator.rewards_data)}")

        # Clear previous PERF data and test key operations
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            perf_capture.operations.clear()

            # Test overdue checking with actual data (REPEATED for stable baseline)
            print(f"\n{'=' * 80}")
            print("🔥 CUMULATIVE PERFORMANCE BASELINE (for optimization tracking)")
            print(f"{'=' * 80}")

            overdue_times = []
            for _ in range(10):
                overdue_start = time.perf_counter()
                await coordinator._check_overdue_chores()
                overdue_duration = (
                    time.perf_counter() - overdue_start
                ) * 1000  # milliseconds
                overdue_times.append(overdue_duration)

            overdue_avg_ms = sum(overdue_times) / len(overdue_times)
            overdue_min_ms = min(overdue_times)
            overdue_max_ms = max(overdue_times)
            ops_count = len(coordinator.chores_data) * len(coordinator.kids_data)
            print("📊 OVERDUE CHECKING (10 iterations):")
            print(
                f"   Average: {overdue_avg_ms:.3f}ms for {ops_count} ops ({overdue_avg_ms * 1000 / ops_count:.2f}µs/op)"
            )
            print(f"   Range: {overdue_min_ms:.3f}ms - {overdue_max_ms:.3f}ms")

            # Test badge checking for all kids with real data (CUMULATIVE)
            badge_start = time.perf_counter()
            for kid_id in coordinator.kids_data:
                coordinator._check_badges_for_kid(kid_id)
            badge_duration_ms = (
                time.perf_counter() - badge_start
            ) * 1000  # milliseconds
            badge_per_kid_ms = badge_duration_ms / len(coordinator.kids_data)
            badge_per_check_us = (badge_duration_ms * 1000) / (
                len(coordinator.kids_data) * len(coordinator.badges_data)
            )
            print("📊 BADGE CHECKING (cumulative for all kids):")
            print(
                f"   Total: {badge_duration_ms:.3f}ms for {len(coordinator.kids_data)} kids"
            )
            print(f"   Per kid: {badge_per_kid_ms:.3f}ms avg")
            print(f"   Per badge check: {badge_per_check_us:.2f}µs avg")

            # Test data persistence (measure queue time precisely)
            persist_start = time.perf_counter()
            coordinator._persist()  # Not async
            persist_queue_us = (
                time.perf_counter() - persist_start
            ) * 1000000  # microseconds
            print("📊 DATA PERSISTENCE:")
            print(f"   Queue time: {persist_queue_us:.1f}µs (async save)")

            await asyncio.sleep(0.05)  # Give async save time to complete

            # Performance assertions (generous limits - optimizations should improve these)
            assert overdue_avg_ms < 50, (
                f"Overdue scanning too slow: {overdue_avg_ms:.3f}ms (expected <50ms)"
            )
            assert badge_duration_ms < 1000, (
                f"Badge checking too slow: {badge_duration_ms:.3f}ms (expected <1000ms)"
            )
            assert persist_queue_us < 5000, (
                f"Persistence queueing too slow: {persist_queue_us:.1f}µs (expected <5000µs)"
            )

            print(f"{'=' * 80}")
            print("✅ BASELINE METRICS CAPTURED - Ready for optimization tracking")
            print(f"{'=' * 80}\n")

            # Test coordinator refresh
            refresh_start = time.perf_counter()
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            refresh_duration = time.perf_counter() - refresh_start
            print(f"🔥 COORDINATOR REFRESH (full scenario): {refresh_duration:.3f}s")

        # Show comprehensive PERF operation breakdown
        perf_summary = perf_capture.get_summary()
        if perf_summary:
            print("\n🔥 PERF OPERATION BREAKDOWN (Full Scenario):")
            for op, stats in perf_summary.items():
                total_time = stats["total"]
                calls = stats["count"]
                avg_time = stats["avg"]
                print(
                    f"   {op}: {calls} calls, {total_time:.3f}s total, {avg_time:.3f}s avg"
                )

                # Show time per call in appropriate units
                if avg_time >= 1:
                    print(f"     → {avg_time:.3f}s per call")
                elif avg_time >= 0.001:
                    print(f"     → {avg_time * 1000:.1f}ms per call")
                else:
                    print(f"     → {avg_time * 1000000:.1f}μs per call")

                # Calculate per-kid metrics for badge operations
                if "check_badges_for_kid" in op and len(coordinator.kids_data) > 0:
                    per_kid = total_time / len(coordinator.kids_data)
                    if per_kid >= 0.001:
                        print(f"     → {per_kid * 1000:.1f}ms per kid")
                    else:
                        print(f"     → {per_kid * 1000000:.1f}μs per kid")
        else:
            print("\n⚠️  NO PERF DATA CAPTURED - Check logging level")

        # Memory analysis
        current_memory = tracemalloc.get_traced_memory()[0] - baseline_memory
        print(f"\n🔥 MEMORY USAGE: {current_memory / 1024:.1f} KB")

        # Entity registry analysis
        ent_reg = er.async_get(hass)
        entities = er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
        print(f"🔥 TOTAL ENTITIES: {len(entities)}")

        # Performance ratios
        print("\n⚡ PERFORMANCE METRICS (Full Scenario):")
        if len(coordinator.kids_data) > 0:
            print(
                f"   Badge check time per kid: {badge_duration_ms / len(coordinator.kids_data):.3f}ms"
            )
            print(
                f"   Memory per kid: {current_memory / len(coordinator.kids_data):.0f} bytes"
            )
        if len(entities) > 0:
            print(f"   Memory per entity: {current_memory / len(entities):.0f} bytes")
            print(
                f"   Entities per kid: {len(entities) / len(coordinator.kids_data):.1f}"
            )
        if len(coordinator.chores_data) > 0:
            chore_ops = len(coordinator.chores_data) * len(coordinator.kids_data)
            print(f"   Chore × Kid operations: {chore_ops}")
            if overdue_avg_ms > 0 and chore_ops > 0:
                per_op = (
                    overdue_avg_ms * 1000
                ) / chore_ops  # Convert ms to µs, then divide
                print(f"   Overdue check per operation: {per_op:.1f}μs")

        tracemalloc.stop()

        print("=" * 80)

    finally:
        # Restore logging
        kc_logger.removeHandler(perf_handler)
        kc_logger.setLevel(original_level)


async def test_operation_timing_breakdown(
    hass: HomeAssistant,
    scenario_stress,
) -> None:
    """Break down timing of individual operations to find bottlenecks."""
    config_entry, _ = scenario_stress
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    print("\n" + "=" * 80)
    print("OPERATION TIMING BREAKDOWN")
    print("=" * 80)

    # Test individual operations timing
    kid_id = list(coordinator.kids_data.keys())[0]  # Get first kid

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Badge processing timing
        start = time.perf_counter()
        coordinator._check_badges_for_kid(kid_id)
        badge_time = time.perf_counter() - start
        print(f"Badge processing (1 kid, 18 badges): {badge_time * 1000:.2f}ms")

        # Overdue check timing
        start = time.perf_counter()
        await coordinator._check_overdue_chores()
        overdue_time = time.perf_counter() - start
        print(f"Overdue check (all chores × all kids): {overdue_time * 1000:.2f}ms")

        # Data lookup timing
        start = time.perf_counter()
        chore_id = list(coordinator.chores_data.keys())[0]
        for _ in range(1000):
            _ = coordinator.chores_data[chore_id]
        lookup_time = time.perf_counter() - start
        print(f"Data lookups (1000 operations): {lookup_time * 1000:.2f}ms")

        # Entity state update simulation
        start = time.perf_counter()
        coordinator.async_update_listeners()
        await hass.async_block_till_done()
        update_time = time.perf_counter() - start
        print(f"Entity state updates: {update_time * 1000:.2f}ms")

    print("=" * 80)
