"""Core-ийн автомат тест.  Ажиллуулах:  python -m unittest discover -s tests -v"""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from src.ta_core import (Config, Simulation, TA_SLEEPING, TA_START, TA_DONE,
                     STUDENT_WAITS, STUDENT_LEAVES, STUDENT_WAKES_TA)


def run_sim(cfg: Config, seconds: float):
    sim = Simulation(cfg)
    sim.start()
    time.sleep(seconds)
    sim.stop()
    return sim, sim.drain_events()


class TestValidation(unittest.TestCase):
    def test_bad_inputs(self):
        bad = [("-1", "5", "1", "1"), ("21", "5", "1", "1"), ("abc", "5", "1", "1"),
               ("3", "0", "1", "1"), ("3", "5", "0", "1"), ("3", "5", "1", "-2"),
               ("3", "5", "", "1"), ("3.5", "5", "1", "1")]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    Config.from_text(*args)

    def test_good_and_edge_inputs(self):
        Config.from_text("3", "5", "1.5", "2")
        Config.from_text("0", "1", "0.01", "0.01")      # хамгийн бага
        Config.from_text("20", "50", "60", "60")        # хамгийн их


class TestCorrectness(unittest.TestCase):
    def check_invariants(self, cfg, events):
        helping = None
        for ev in events:
            self.assertLessEqual(len(ev.waiting), cfg.num_chairs)           # сандлаас хэтрэхгүй
            self.assertEqual(ev.free_chairs, cfg.num_chairs - len(ev.waiting))
            self.assertEqual(len(set(ev.waiting)), len(ev.waiting))         # давхцахгүй
            if ev.kind == TA_START:
                self.assertIsNone(helping, "TA нэг дор 2 оюутанд үйлчилсэн!")
                helping = ev.student
                self.assertNotIn(ev.student, ev.waiting)
            if ev.kind == TA_DONE:
                self.assertEqual(helping, ev.student)
                helping = None
        done = sum(e.kind == TA_DONE for e in events)
        self.assertEqual(done, events[-1].served)

    def test_book_default(self):
        cfg = Config(3, 5, 0.05, 0.05, seed=1)
        sim, ev = run_sim(cfg, 2.0)
        self.check_invariants(cfg, ev)
        self.assertGreater(sim.served, 0)
        self.assertEqual(sim.alive_threads(), 0)

    def test_overload_students_get_turned_away(self):
        cfg = Config(1, 20, 0.02, 0.1, seed=2)
        sim, ev = run_sim(cfg, 2.0)
        self.check_invariants(cfg, ev)
        self.assertGreater(sim.turned_away, 0)
        self.assertTrue(any(e.kind == STUDENT_LEAVES for e in ev))

    def test_zero_chairs(self):
        cfg = Config(0, 5, 0.02, 0.05, seed=3)
        sim, ev = run_sim(cfg, 1.0)
        self.assertEqual(sim.served, 0)
        self.assertGreater(sim.turned_away, 0)
        self.assertFalse(any(e.kind == STUDENT_WAITS for e in ev))

    def test_ta_sleeps_when_nobody_comes(self):
        sim = Simulation(Config(3, 1, 30, 1))
        sim.start()
        time.sleep(0.3)
        self.assertEqual(sim.ta_state, TA_SLEEPING)
        sim.stop()
        self.assertFalse(any(e.kind == TA_START for e in sim.drain_events()))

    def test_student_wakes_ta(self):
        cfg = Config(3, 1, 0.05, 0.05, seed=4)
        sim, ev = run_sim(cfg, 1.0)
        self.assertTrue(any(e.kind == STUDENT_WAKES_TA for e in ev))

    def test_no_deadlock_many_configs(self):
        for chairs, studs in [(1, 3), (2, 10), (5, 30), (3, 3)]:
            with self.subTest(chairs=chairs, students=studs):
                cfg = Config(chairs, studs, 0.03, 0.03, seed=5)
                sim, ev = run_sim(cfg, 1.5)
                self.check_invariants(cfg, ev)
                self.assertGreater(sim.served, 3)
                self.assertEqual(sim.alive_threads(), 0)


class TestControl(unittest.TestCase):
    def test_pause_resume_stop(self):
        sim = Simulation(Config(3, 5, 0.03, 0.03, seed=6))
        sim.start()
        time.sleep(0.3)
        sim.pause()
        time.sleep(0.15)
        sim.drain_events()
        time.sleep(0.4)
        self.assertEqual(len(sim.drain_events()), 0, "pause үед event гарсан")
        sim.resume()
        time.sleep(0.3)
        self.assertGreater(len(sim.drain_events()), 0)
        sim.pause()
        sim.stop()                      # pause-тай байхад ч гацахгүй
        self.assertEqual(sim.alive_threads(), 0)

    def test_reset_with_new_config(self):
        sim = Simulation(Config(3, 5, 0.03, 0.03, seed=7))
        sim.start()
        time.sleep(0.5)
        sim.reset(Config(2, 3, 0.03, 0.03, seed=7))
        self.assertEqual((sim.served, sim.turned_away, len(sim.waiting)), (0, 0, 0))
        self.assertEqual(sim.drain_events(), [])
        sim.start()
        time.sleep(0.5)
        sim.stop()
        self.assertGreater(sim.served, 0)

    def test_double_start_rejected(self):
        sim = Simulation(Config())
        sim.start()
        with self.assertRaises(RuntimeError):
            sim.start()
        sim.stop()


if __name__ == "__main__":
    unittest.main()
