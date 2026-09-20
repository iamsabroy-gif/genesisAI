"""
Project Genesis: Hardware Health & Ceiling Watchdog for Apple Silicon.
Monitors memory pressure, swap usage, CPU load, and prevents system freezes.
"""

import os
import re
import subprocess
from typing import Dict, Any, Tuple


class SystemHealthWatchdog:
    """
    Real-time system health monitor calibrated for Apple Silicon (16 GB Unified Memory).
    Enforces safe operational ceilings to prevent virtual memory swap thrashing and beachballs.
    """

    # Safe default ceilings for Apple Silicon Mac (can be overridden via environment variables)
    MIN_AVAILABLE_MB = 1200.0     # 1.2 GB absolute minimum headroom before throttling
    WARN_AVAILABLE_MB = 2200.0    # 2.2 GB warning threshold for proactive pruning
    MAX_SWAP_USED_MB = 5120.0     # 5.0 GB swap ceiling (macOS routinely holds 1-3 GB for dormant apps)

    @classmethod
    def get_thresholds(cls) -> Tuple[float, float, float]:
        """Resolves dynamic or environment-specified memory and swap ceilings."""
        min_avail = float(os.getenv("GENESIS_MIN_AVAILABLE_MB", str(cls.MIN_AVAILABLE_MB)))
        warn_avail = float(os.getenv("GENESIS_WARN_AVAILABLE_MB", str(cls.WARN_AVAILABLE_MB)))
        max_swap = float(os.getenv("GENESIS_MAX_SWAP_MB", str(cls.MAX_SWAP_USED_MB)))
        return min_avail, warn_avail, max_swap

    @staticmethod
    def get_memory_stats() -> Dict[str, Any]:
        """
        Query macOS Mach virtual memory pages and swap statistics.
        Returns detailed memory usage in megabytes and kernel pressure level.
        """
        stats: Dict[str, Any] = {
            "total_ram_mb": 16384,
            "free_ram_mb": 0,
            "inactive_ram_mb": 0,
            "active_ram_mb": 0,
            "wired_ram_mb": 0,
            "purgeable_ram_mb": 0,
            "available_ram_mb": 0,
            "swap_used_mb": 0.0,
            "swap_total_mb": 0.0,
            "vm_pressure_level": 1,
            "vm_pressure_str": "NORMAL",
        }

        # 1. Total Hardware RAM
        try:
            total_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip())
            stats["total_ram_mb"] = round(total_bytes / (1024 * 1024), 1)
        except Exception:
            pass

        # 2. Swap Usage
        try:
            swap_out = subprocess.check_output(["sysctl", "vm.swapusage"], text=True)
            # Example: vm.swapusage: total = 0.00M  used = 0.00M  free = 0.00M  (encrypted)
            used_match = re.search(r"used\s*=\s*([\d\.]+)M", swap_out)
            total_match = re.search(r"total\s*=\s*([\d\.]+)M", swap_out)
            if used_match:
                stats["swap_used_mb"] = float(used_match.group(1))
            if total_match:
                stats["swap_total_mb"] = float(total_match.group(1))
        except Exception:
            pass

        # 3. Mach Virtual Memory Pages via vm_stat
        try:
            vm_out = subprocess.check_output(["vm_stat"], text=True)
            page_size = 16384  # Default Apple Silicon page size (16KB)
            for line in vm_out.splitlines():
                if "page size of" in line:
                    match = re.search(r"page size of (\d+) bytes", line)
                    if match:
                        page_size = int(match.group(1))
                elif line.startswith("Pages free:"):
                    stats["free_ram_mb"] = round((int(re.findall(r"\d+", line)[0]) * page_size) / (1024 * 1024), 1)
                elif line.startswith("Pages active:"):
                    stats["active_ram_mb"] = round((int(re.findall(r"\d+", line)[0]) * page_size) / (1024 * 1024), 1)
                elif line.startswith("Pages inactive:"):
                    stats["inactive_ram_mb"] = round((int(re.findall(r"\d+", line)[0]) * page_size) / (1024 * 1024), 1)
                elif line.startswith("Pages wired down:"):
                    stats["wired_ram_mb"] = round((int(re.findall(r"\d+", line)[0]) * page_size) / (1024 * 1024), 1)
                elif line.startswith("Pages purgeable:"):
                    stats["purgeable_ram_mb"] = round((int(re.findall(r"\d+", line)[0]) * page_size) / (1024 * 1024), 1)

            # Available = free + inactive + purgeable (pages macOS can instantly reclaim)
            stats["available_ram_mb"] = round(
                stats["free_ram_mb"] + stats["inactive_ram_mb"] + stats["purgeable_ram_mb"], 1
            )
        except Exception:
            stats["available_ram_mb"] = stats["total_ram_mb"] * 0.4

        # 4. macOS Kernel VM Pressure Level (1 = Normal, 2 = Warn, 4 = Critical)
        try:
            p_out = subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True).strip()
            level = int(p_out)
            stats["vm_pressure_level"] = level
            if level >= 4:
                stats["vm_pressure_str"] = "CRITICAL"
            elif level == 2:
                stats["vm_pressure_str"] = "WARNING"
            else:
                stats["vm_pressure_str"] = "NORMAL"
        except Exception:
            pass

        return stats

    @classmethod
    def evaluate_health_ceiling(cls) -> Tuple[str, str, Dict[str, Any]]:
        """
        Evaluate current health against Apple Silicon operating ceiling.
        Distinguishes between actual RAM exhaustion and benign background swap.

        Returns:
            status: "NOMINAL" | "WARNING" | "CRITICAL"
            message: Diagnostic status explanation
            stats: Raw numerical metrics
        """
        stats = cls.get_memory_stats()
        avail = stats["available_ram_mb"]
        swap = stats["swap_used_mb"]
        vm_pressure = stats.get("vm_pressure_level", 1)

        # CPU Load
        load_1m = 0.0
        try:
            load_1m, _, _ = os.getloadavg()
        except Exception:
            pass
        stats["cpu_load_1m"] = round(load_1m, 2)

        # Check explicit user bypass override
        if os.getenv("GENESIS_DISABLE_HEALTH_GUARD", "").lower() in ("1", "true", "yes"):
            return (
                "NOMINAL",
                f"Health guard bypass active (GENESIS_DISABLE_HEALTH_GUARD=1). Headroom: {avail:.0f} MB.",
                stats,
            )

        min_avail, warn_avail, max_swap = cls.get_thresholds()

        # CRITICAL conditions:
        # 1. Available physical memory genuinely depleted below absolute floor
        # 2. Kernel VM pressure level is critical (4) AND available memory is tight
        # 3. Extreme swap usage AND available memory below warning ceiling (active thrashing)
        is_critically_low_ram = avail < min_avail
        is_kernel_critical = vm_pressure >= 4 and avail < warn_avail
        is_swap_thrashing = swap > max_swap and avail < warn_avail

        if is_critically_low_ram or is_kernel_critical or is_swap_thrashing:
            reason = []
            if is_critically_low_ram:
                reason.append(f"Available RAM dangerously low ({avail:.0f} MB < {min_avail:.0f} MB floor)")
            if is_kernel_critical:
                reason.append(f"macOS kernel reported CRITICAL memory pressure level ({vm_pressure})")
            if is_swap_thrashing:
                reason.append(f"Swap exhaustion thrashing ({swap:.1f} MB > {max_swap:.0f} MB limit with low RAM)")

            return (
                "CRITICAL",
                f"Memory pressure critical! {'; '.join(reason)}. Throttling execution.",
                stats,
            )

        # WARNING conditions:
        # 1. Available RAM below warning threshold
        # 2. Kernel reports warning pressure level (2)
        # 3. Swap is very high (> max_swap) even if RAM headroom is currently adequate
        is_warning_ram = avail < warn_avail
        is_kernel_warn = vm_pressure == 2
        is_elevated_swap = swap > max_swap

        if is_warning_ram or is_kernel_warn or is_elevated_swap:
            reasons = []
            if is_warning_ram:
                reasons.append(f"available RAM {avail:.0f} MB < {warn_avail:.0f} MB threshold")
            if is_kernel_warn:
                reasons.append("macOS kernel elevated pressure (WARN)")
            if is_elevated_swap:
                reasons.append(f"elevated swap ({swap:.1f} MB > {max_swap:.0f} MB)")

            return (
                "WARNING",
                f"Elevated memory pressure: {', '.join(reasons)}. Aggressive context pruning recommended.",
                stats,
            )

        ram_pct_avail = round((avail / stats['total_ram_mb']) * 100) if stats['total_ram_mb'] > 0 else 0
        return (
            "NOMINAL",
            f"System healthy: {avail:.0f} MB RAM available ({ram_pct_avail}%), swap: {swap:.1f} MB, CPU load: {load_1m:.1f}.",
            stats,
        )

    @classmethod
    def format_status_panel(cls) -> str:
        """Return formatted human-readable diagnostic report."""
        status, msg, stats = cls.evaluate_health_ceiling()
        total = stats["total_ram_mb"]
        avail = stats["available_ram_mb"]
        used = max(0.0, total - avail)
        pct_used = round((used / total) * 100, 1) if total > 0 else 0.0
        pressure_str = stats.get("vm_pressure_str", "NORMAL")

        color_tag = "green" if status == "NOMINAL" else ("yellow" if status == "WARNING" else "red")

        return (
            f"Hardware Ceiling Status: [{color_tag}]{status}[/{color_tag}]\n"
            f"- Apple Silicon Unified RAM: {used:.0f} MB / {total:.0f} MB used ({pct_used}%)\n"
            f"- Dynamic Available Headroom: {avail:.0f} MB ({round((avail/total)*100)}% free)\n"
            f"- Kernel Memory Pressure: {pressure_str}\n"
            f"- Wired (Kernel/Ollama): {stats['wired_ram_mb']:.0f} MB\n"
            f"- Swap Space Used: {stats['swap_used_mb']:.1f} MB\n"
            f"- 1-min CPU Load Average: {stats['cpu_load_1m']}\n"
            f"- Guard Assessment: {msg}"
        )


def check_system_ceiling() -> Tuple[bool, str]:
    """
    Quick boolean gate check.
    Returns (is_safe, message). If is_safe is False, agent should back off or prune.
    """
    status, msg, _ = SystemHealthWatchdog.evaluate_health_ceiling()
    return status != "CRITICAL", msg
