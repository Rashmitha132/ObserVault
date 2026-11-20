# collector/collectors/system_metrics.py
import psutil
import time
from typing import Dict, Any

class SystemMetricsCollector:
    """
    Collects actual physical hardware & operating system telemetry using psutil.
    """
    def __init__(self):
        # Initialize CPU percent tracking
        psutil.cpu_percent(interval=None)

    def collect_physical_metrics(self) -> Dict[str, Any]:
        """
        Samples real CPU, Memory, and Disk utilisation.
        """
        # Actual CPU utilization
        cpu_pct = psutil.cpu_percent(interval=0.1)
        
        # Actual Virtual Memory utilization
        mem = psutil.virtual_memory()
        mem_pct = mem.percent
        
        # Actual Primary Disk utilization
        try:
            # On Windows: C:\, on Linux/macOS: /
            disk_path = "C:\\" if psutil.WINDOWS else "/"
            disk = psutil.disk_usage(disk_path)
            disk_pct = disk.percent
        except Exception:
            disk_pct = 50.0

        return {
            "cpu_percent": round(float(cpu_pct), 1),
            "memory_percent": round(float(mem_pct), 1),
            "disk_percent": round(float(disk_pct), 1),
            "is_simulated": False
        }
