"""Сценариудыг UI-гүйгээр core (ta_core.py) дээр шууд ажиллуулж, бодит тоог гаргана.

UI дээр харагдсан тоотой харьцуулахад ашиглана (UI event-үүдийг тогтмол хурдаар
тоглуулдаг тул ачаалал ихтэй үед хоцорч харагдаж болно).

Ажиллуулах:   python3 tests/core_scenarios.py
Гаралт:       tests/screenshots/core_results.json
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from ta_core import (Config, Simulation, TA_SLEEP, TA_START, STUDENT_WAKES_TA,  # noqa: E402
                     STUDENT_WAITS, STUDENT_LEAVES)

# ID: (сандал, оюутан, ирэх, үйлчилгээ, секунд)
SCENARIOS = {
    "S1": (3, 5, 1.0, 1.5, 20),
    "S2": (1, 10, 0.3, 1.5, 20),
    "S3": (10, 3, 1.5, 0.5, 20),
    "S4": (0, 5, 0.5, 1.0, 15),
    "S5": (1, 1, 2.0, 0.5, 20),
    "S6": (20, 50, 0.2, 0.5, 20),
}


def run(chairs, students, interval, service, seconds):
    sim = Simulation(Config(chairs, students, interval, service))
    sim.start()
    time.sleep(seconds)
    sim.stop()
    ev = sim.drain_events()
    return {
        "served": sim.served,
        "turned_away": sim.turned_away,
        "seated": sum(e.kind == STUDENT_WAITS for e in ev),
        "ta_wakes": sum(e.kind == STUDENT_WAKES_TA for e in ev),
        "ta_sleeps": sum(e.kind == TA_SLEEP for e in ev),
        "max_queue": max((len(e.waiting) for e in ev), default=0),
        "events": len(ev),
        "threads_left": sim.alive_threads(),
    }


if __name__ == "__main__":
    out = {}
    for sid, args in SCENARIOS.items():
        out[sid] = {"input": list(args[:4]), "seconds": args[4], **run(*args)}
        print(sid, out[sid], flush=True)
    os.makedirs(os.path.join(HERE, "screenshots"), exist_ok=True)
    with open(os.path.join(HERE, "screenshots", "core_results.json"), "w", encoding="utf8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
