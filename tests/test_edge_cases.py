"""Edge case-ийн нэмэлт тестүүд (src/test_ta_core.py-д байхгүй зүйлсийг шалгана).

Ажиллуулах (төслийн үндсэн хавтсанд):
    python3 -m unittest discover -s tests -v
"""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ta_core import (Config, Simulation, TA_SLEEPING, TA_HELPING,
                     SIM_START, SIM_STOP, TA_SLEEP, TA_START, TA_DONE,
                     STUDENT_WAKES_TA, STUDENT_WAITS, STUDENT_LEAVES)


def run_sim(cfg, seconds):
    sim = Simulation(cfg)
    sim.start()
    time.sleep(seconds)
    sim.stop()
    return sim, sim.drain_events()


# ---------------------------------------------------------------------------
class TestConfigBoundaries(unittest.TestCase):
    """Тохиргооны хязгаарын утгууд: яг хязгаар дээр зөв, хязгаараас хэтэрвэл алдаа."""

    def ok(self, *args):
        return Config.from_text(*args)

    def bad(self, *args):
        with self.assertRaises(ValueError):
            Config.from_text(*args)

    def test_chairs_boundary(self):
        self.ok("0", "1", "1", "1")
        self.ok("20", "1", "1", "1")
        self.bad("21", "1", "1", "1")
        self.bad("-1", "1", "1", "1")

    def test_students_boundary(self):
        self.ok("3", "1", "1", "1")
        self.ok("3", "50", "1", "1")
        self.bad("3", "0", "1", "1")
        self.bad("3", "51", "1", "1")

    def test_time_boundary(self):
        self.ok("3", "5", "60", "60")
        self.ok("3", "5", "0.001", "0.001")
        self.bad("3", "5", "60.01", "1")
        self.bad("3", "5", "1", "60.01")
        self.bad("3", "5", "0", "1")
        self.bad("3", "5", "1", "0")

    def test_nan_and_inf_rejected(self):
        for v in ("nan", "inf", "-inf", "NaN"):
            with self.subTest(value=v):
                self.bad("3", "5", v, "1")
                self.bad("3", "5", "1", v)

    def test_whitespace_and_scientific_notation(self):
        cfg = self.ok(" 3 ", " 5 ", " 1.5 ", " 2 ")
        self.assertEqual((cfg.num_chairs, cfg.num_students), (3, 5))
        self.assertEqual(self.ok("3", "5", "1e1", "1").arrival_interval, 10.0)

    def test_integer_fields_reject_decimals_and_text(self):
        self.bad("3.0", "5", "1", "1")
        self.bad("3", "5.5", "1", "1")
        self.bad("", "5", "1", "1")
        self.bad("три", "5", "1", "1")
        self.bad("3", "", "1", "1")

    def test_seed_field(self):
        self.assertIsNone(self.ok("3", "5", "1", "1", "").seed)
        self.assertIsNone(self.ok("3", "5", "1", "1", "   ").seed)
        self.assertEqual(self.ok("3", "5", "1", "1", "-5").seed, -5)
        self.bad("3", "5", "1", "1", "abc")
        self.bad("3", "5", "1", "1", "1.5")

    def test_error_message_is_readable(self):
        try:
            Config.from_text("abc", "5", "1", "1")
        except ValueError as exc:
            self.assertIn("Сандлын тоо", str(exc))
            self.assertIn("abc", str(exc))
        else:
            self.fail("ValueError шидээгүй")

    def test_simulation_rejects_invalid_config_directly(self):
        with self.assertRaises(ValueError):
            Simulation(Config(num_chairs=-1))


# ---------------------------------------------------------------------------
class TestLifecycleEdgeCases(unittest.TestCase):
    """Эхлэх, зогсоох, pause, reset-ийн ер бусын дараалал."""

    def test_stop_before_start_is_harmless(self):
        sim = Simulation(Config())
        sim.stop()
        self.assertFalse(sim.running)
        self.assertEqual(sim.alive_threads(), 0)

    def test_stop_twice_is_harmless(self):
        sim = Simulation(Config(3, 3, 0.03, 0.03, seed=1))
        sim.start()
        time.sleep(0.2)
        sim.stop()
        sim.stop()
        self.assertEqual(sim.alive_threads(), 0)

    def test_pause_before_start_blocks_until_resume(self):
        sim = Simulation(Config(3, 3, 0.03, 0.03, seed=2))
        sim.pause()
        sim.start()
        time.sleep(0.4)
        kinds = [e.kind for e in sim.drain_events()]
        self.assertEqual(kinds, [SIM_START], "pause үед SIM_START-аас өөр event гарсан")
        sim.resume()
        time.sleep(0.4)
        self.assertGreater(len(sim.drain_events()), 0)
        sim.stop()

    def test_reset_while_paused(self):
        sim = Simulation(Config(3, 5, 0.03, 0.03, seed=3))
        sim.start()
        time.sleep(0.3)
        sim.pause()
        sim.reset()
        self.assertFalse(sim.paused, "reset дараа pause үлдсэн")
        self.assertEqual(sim.drain_events(), [])
        sim.start()
        time.sleep(0.3)
        sim.stop()
        self.assertGreater(sim.served + sim.turned_away, 0)

    def test_invalid_reset_config_documented_behavior(self):
        """Буруу тохиргоотой reset: ValueError шидэх ба симуляци зогссон хэвээр үлдэнэ."""
        sim = Simulation(Config(3, 3, 0.03, 0.03, seed=4))
        sim.start()
        time.sleep(0.2)
        with self.assertRaises(ValueError):
            sim.reset(Config(num_chairs=99))
        self.assertFalse(sim.running)
        self.assertEqual(sim.alive_threads(), 0)
        sim.reset()                       # дараа нь хэвийн reset хийж болно
        sim.start()
        time.sleep(0.2)
        sim.stop()

    def test_many_reset_cycles_do_not_leak_threads(self):
        before = threading.active_count()
        sim = Simulation(Config(2, 6, 0.02, 0.02, seed=5))
        for _ in range(6):
            sim.start()
            time.sleep(0.15)
            sim.reset()
        self.assertEqual(sim.alive_threads(), 0)
        self.assertLessEqual(threading.active_count(), before + 1)

    def test_stop_emits_sim_stop_last(self):
        sim, ev = run_sim(Config(3, 3, 0.03, 0.03, seed=6), 0.5)
        self.assertEqual(ev[0].kind, SIM_START)
        self.assertEqual(ev[-1].kind, SIM_STOP)
        self.assertEqual(sum(e.kind == SIM_STOP for e in ev), 1)


# ---------------------------------------------------------------------------
class TestSimulationSemantics(unittest.TestCase):
    """Synchronization-ы зөв байдал: дараалал, тоолуур, TA-ын төлөв."""

    def test_fifo_order(self):
        """Сандалд эхэлж суусан оюутан эхэлж үйлчлүүлнэ."""
        sim, ev = run_sim(Config(5, 8, 0.03, 0.06, seed=7), 2.0)
        seated = [e.student for e in ev if e.kind == STUDENT_WAITS]
        started = [e.student for e in ev if e.kind == TA_START]
        self.assertGreater(len(started), 3)
        self.assertEqual(started, seated[:len(started)], "FIFO дараалал зөрчигдсөн")

    def test_every_arrival_is_seated_or_turned_away(self):
        sim, ev = run_sim(Config(2, 10, 0.02, 0.08, seed=8), 2.0)
        seated = sum(e.kind == STUDENT_WAITS for e in ev)
        left = sum(e.kind == STUDENT_LEAVES for e in ev)
        self.assertEqual(left, sim.turned_away)
        self.assertGreater(seated, 0)
        self.assertGreater(left, 0)

    def test_served_never_exceeds_seated(self):
        sim, ev = run_sim(Config(3, 6, 0.03, 0.05, seed=9), 1.5)
        seated = sum(e.kind == STUDENT_WAITS for e in ev)
        self.assertLessEqual(sim.served, seated)

    def test_timestamps_never_go_backwards(self):
        _, ev = run_sim(Config(3, 10, 0.02, 0.03, seed=10), 1.5)
        times = [e.t for e in ev]
        self.assertEqual(times, sorted(times))

    def test_current_matches_event_student(self):
        _, ev = run_sim(Config(3, 5, 0.03, 0.04, seed=11), 1.5)
        for e in ev:
            if e.kind == TA_START:
                self.assertEqual(e.current, e.student)
                self.assertEqual(e.ta_state, TA_HELPING)
            if e.kind == TA_DONE:
                self.assertIsNone(e.current)

    def test_first_arrival_wakes_sleeping_ta(self):
        _, ev = run_sim(Config(3, 1, 0.05, 0.05, seed=12), 0.8)
        kinds = [e.kind for e in ev]
        self.assertEqual(kinds[0], SIM_START)
        self.assertEqual(kinds[1], STUDENT_WAKES_TA)
        self.assertEqual(kinds[2], STUDENT_WAITS)
        self.assertEqual(kinds[3], TA_START)

    def test_ta_goes_back_to_sleep_when_queue_empties(self):
        _, ev = run_sim(Config(3, 1, 0.4, 0.05, seed=13), 2.5)
        kinds = [e.kind for e in ev]
        self.assertIn(TA_DONE, kinds)
        self.assertIn(TA_SLEEP, kinds[kinds.index(TA_DONE):])

    def test_one_chair_one_student(self):
        sim, ev = run_sim(Config(1, 1, 0.03, 0.03, seed=14), 1.0)
        self.assertGreater(sim.served, 3)
        self.assertEqual(sim.turned_away, 0, "ганц оюутан хэзээ ч буцах ёсгүй")

    def test_enough_chairs_nobody_turned_away(self):
        sim, ev = run_sim(Config(20, 10, 0.05, 0.02, seed=15), 1.5)
        self.assertEqual(sim.turned_away, 0)
        self.assertFalse(any(e.kind == STUDENT_LEAVES for e in ev))

    def test_max_load_20_chairs_50_students(self):
        cfg = Config(20, 50, 0.02, 0.03, seed=16)
        sim, ev = run_sim(cfg, 3.0)
        self.assertGreater(sim.served, 10)
        self.assertEqual(sim.alive_threads(), 0)
        for e in ev:
            self.assertLessEqual(len(e.waiting), 20)
            self.assertEqual(len(set(e.waiting)), len(e.waiting))
        self.assertEqual(ev[-1].kind, SIM_STOP)

    def test_zero_chairs_ta_never_works(self):
        sim, ev = run_sim(Config(0, 5, 0.02, 0.05, seed=17), 1.0)
        self.assertEqual(sim.ta_state, TA_SLEEPING)
        self.assertFalse(any(e.kind in (TA_START, TA_DONE, STUDENT_WAKES_TA) for e in ev))


if __name__ == "__main__":
    unittest.main()
