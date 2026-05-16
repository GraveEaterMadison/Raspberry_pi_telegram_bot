"""utils/metrics.py — Background system metrics collection."""

import asyncio
import time
import logging
from collections import deque
from typing import Optional, Callable

import psutil

from config import METRICS_HISTORY_SIZE, METRICS_INTERVAL

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self.cpu_history:  deque[tuple[float, float]] = deque(maxlen=METRICS_HISTORY_SIZE)
        self.ram_history:  deque[tuple[float, float]] = deque(maxlen=METRICS_HISTORY_SIZE)
        self.temp_history: deque[tuple[float, float]] = deque(maxlen=METRICS_HISTORY_SIZE)
        self._alerts: list[dict] = []   # {metric, op, threshold, user_id}
        self._notifier: Optional[Callable] = None
        # BUG FIX: track which alerts have fired to avoid spamming every interval
        self._fired_alerts: set[int] = set()

    def init(self):
        logger.info("MetricsCollector initialized (interval=%ds, history=%d)",
                    METRICS_INTERVAL, METRICS_HISTORY_SIZE)

    def set_notifier(self, fn):
        """Register an async callback for alert notifications."""
        self._notifier = fn

    def add_alert(self, user_id: int, metric: str, op: str, threshold: float):
        self._alerts.append({
            "user_id": user_id, "metric": metric, "op": op, "threshold": threshold
        })
        # reset fired state so new alert can fire immediately
        self._fired_alerts.discard(id(self._alerts[-1]))

    def list_alerts(self, user_id: int) -> list[dict]:
        return [a for a in self._alerts if a["user_id"] == user_id]

    def clear_alerts(self, user_id: int):
        self._alerts = [a for a in self._alerts if a["user_id"] != user_id]
        # clean up fired set — rebuild from surviving alerts
        self._fired_alerts = {id(a) for a in self._alerts if id(a) in self._fired_alerts}

    def get_cpu(self) -> float:
        return psutil.cpu_percent(interval=0.1)

    def get_ram(self) -> float:
        return psutil.virtual_memory().percent

    def get_temp(self) -> Optional[float]:
        try:
            temps = psutil.sensors_temperatures()
            if "cpu_thermal" in temps:
                return temps["cpu_thermal"][0].current
            if "coretemp" in temps:
                return temps["coretemp"][0].current
        except Exception:
            pass
        # Fallback: read thermal zone directly
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            return None

    async def collect_loop(self):
        logger.info("Metrics collection loop started")
        while True:
            try:
                now = time.time()
                cpu = self.get_cpu()
                ram = self.get_ram()
                temp = self.get_temp()

                self.cpu_history.append((now, cpu))
                self.ram_history.append((now, ram))
                if temp is not None:
                    self.temp_history.append((now, temp))

                # Check alerts
                if self._notifier:
                    await self._check_alerts(cpu, ram, temp)

            except Exception as e:
                logger.error("Metrics collection error: %s", e)

            await asyncio.sleep(METRICS_INTERVAL)

    async def _check_alerts(self, cpu: float, ram: float, temp: Optional[float]):
        values = {"cpu": cpu, "ram": ram, "temp": temp}
        ops = {">": lambda a, b: a > b, "<": lambda a, b: a < b,
               ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}

        for alert in self._alerts:
            alert_id = id(alert)
            val = values.get(alert["metric"])
            if val is None:
                continue
            op_fn = ops.get(alert["op"])
            if not op_fn:
                continue

            condition_true = op_fn(val, alert["threshold"])

            # BUG FIX: only fire once per trigger; reset when condition clears
            if condition_true and alert_id not in self._fired_alerts:
                self._fired_alerts.add(alert_id)
                try:
                    await self._notifier(
                        alert["user_id"],
                        f"🚨 *ALERT*: `{alert['metric']}` is `{val:.1f}` "
                        f"({alert['op']} {alert['threshold']})",
                    )
                except Exception as e:
                    logger.error("Alert notification failed: %s", e)
            elif not condition_true:
                # reset so it can fire again next time the threshold is crossed
                self._fired_alerts.discard(alert_id)
