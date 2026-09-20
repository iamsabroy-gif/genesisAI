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

    # Safe ceilings for 16 GB Apple Silicon Mac
    MIN_AVAILABLE_MB = 1500      # 1.5 GB minimum available RAM ceiling
    WARN_AVAILABLE_MB = 2500     # 2.5 GB warning threshold
    MAX_SWAP_USED_MB = 800       # If swap exceeds 800 MB, flag critical memory pressure

    @staticmethod
    def get_memory_stats() -> Dict[str, Any]:
        """
        Query macOS Mach virtual memory pages and swap statistics.
        Returns detailed memory usage in megabytes.
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

        return stats

    @classmethod
    def evaluate_health_ceiling(cls) -> Tuple[str, str, Dict[str, Any]]:
        """
        Evaluate current health against 16GB Apple Silicon operating ceiling.
        Returns:
            status: "NOMINAL" | "WARNING" | "CRITICAL"
            message: Diagnostic status explanation
            stats: Raw numerical metrics
        """
        stats = cls.get_memory_stats()
        avail = stats["available_ram_mb"]
        swap = stats["swap_used_mb"]

        # CPU Load
        load_1m, _, _ = os.getloadavg()
        stats["cpu_load_1m"] = round(load_1m, 2)

        if avail < cls.MIN_AVAILABLE_MB or swap > cls.MAX_SWAP_USED_MB:
            return (
                "CRITICAL",
                f"Memory pressure critical! Only {avail:.0f} MB RAM available, swap used: {swap:.1f} MB. Throttling execution.",
                stats,
            )

        if avail < cls.WARN_AVAILABLE_MB or swap > 100.0:
            return (
                "WARNING",
                f"Elevated memory pressure: {avail:.0f} MB RAM available, swap used: {swap:.1f} MB. Aggressive context pruning recommended.",
                stats,
            )

        return (
            "NOMINAL",
            f"System healthy: {avail:.0f} MB RAM available ({round(avail / stats['total_ram_mb'] * 100)}%), swap: {swap:.1f} MB, CPU load: {load_1m:.1f}.",
            stats,
        )

    @classmethod
    def format_status_panel(cls) -> str:
        """Return formatted human-readable diagnostic report."""
        status, msg, stats = cls.evaluate_health_ceiling()
        total = stats["total_ram_mb"]
        avail = stats["available_ram_mb"]
        used = total - avail
        pct_used = round((used / total) * 100, 1)

        color_tag = "green" if status == "NOMINAL" else ("yellow" if status == "WARNING" else "red")

        return (
            f"Hardware Ceiling Status: [{color_tag}]{status}[/{color_tag}]\n"
            f"- Apple Silicon Unified RAM: {used:.0f} MB / {total:.0f} MB used ({pct_used}%)\n"
            f"- Dynamic Available Headroom: {avail:.0f} MB ({round((avail/total)*100)}% free)\n"
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
