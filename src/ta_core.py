"""
ta_core.py - The Sleeping Teaching Assistant: CORE (UI-аас хамааралгүй)

Бие даалт 1, код II-4-10 (Silberschatz, Chapter 7, Programming Project 10)

Нөхцөл:
  * TA-ийн өрөөнд 1 сандал (TA), коридорт N хүлээлгийн сандал байна.
  * Оюутан байхгүй бол TA унтана.
  * Оюутан ирэхэд: TA унтаж байвал сэрээнэ; сул сандал байвал суугаад хүлээнэ;
    сандал дүүрэн бол буцаж явна (хэсэг хугацааны дараа дахин ирнэ).

Synchronization (номын шийдэлтэй ижил):
  * mutex          - хүлээлгийн сандлын мэдээллийг (waiting, ta_state ...) хамгаална
  * students_sem   - хүлээж буй оюутны тоог тоолно. TA үүн дээр wait() хийж унтана.
  * turn[i]        - i-р оюутан бүрийн хувийн semaphore. TA үйлчилж дуустал оюутан
                     үүн дээр хүлээнэ.

UI-тай холбох арга:
  Thread бүр өөрийн үйлдлийг `Event` болгон `sim.events` (queue.Queue)-д хийнэ.
  UI (Tkinter) нь root.after(...)-ээр тэр queue-г уншаад зурна.
  Ингэснээр дүрслэл нь БОДИТ thread-үүдийн төлөвийг харуулна.
"""
from __future__ import annotations

import argparse
import queue
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

# ---------------------------------------------------------------- TA-ийн төлөв
TA_SLEEPING = "SLEEPING"   # унтаж байна
TA_AWAKE = "AWAKE"         # сэрсэн (оюутан дуудах гэж байна)
TA_HELPING = "HELPING"     # оюутанд үйлчилж байна

# ------------------------------------------------------------- Event-ийн төрөл
SIM_START = "SIM_START"
SIM_STOP = "SIM_STOP"
TA_SLEEP = "TA_SLEEP"                   # TA унтлаа
STUDENT_WAKES_TA = "STUDENT_WAKES_TA"   # оюутан TA-г сэрээв
STUDENT_WAITS = "STUDENT_WAITS"         # оюутан сандалд суув
STUDENT_LEAVES = "STUDENT_LEAVES"       # сандал дүүрэн, оюутан буцав
TA_START = "TA_START"                   # TA үйлчилж эхэлэв
TA_DONE = "TA_DONE"                     # TA үйлчилж дууслаа


# ------------------------------------------------------------------- Тохиргоо
@dataclass
class Config:
    num_chairs: int = 3          # хүлээлгийн сандлын тоо
    num_students: int = 5        # нийт оюутны тоо
    arrival_interval: float = 3.0  # оюутан дунджаар хэдэн секунд programming хийгээд ирэх
    service_time: float = 2.0    # TA нэг оюутанд дунджаар зарцуулах секунд
    seed: Optional[int] = None   # давтагдах үр дүн авахын тулд (заавал биш)

    MAX_CHAIRS = 20
    MAX_STUDENTS = 50
    MAX_SECONDS = 60.0

    def validate(self) -> None:
        """Буруу утга байвал ValueError (ойлгомжтой мессежтэй) шиднэ."""
        if not 0 <= self.num_chairs <= self.MAX_CHAIRS:
            raise ValueError(f"Сандлын тоо 0-{self.MAX_CHAIRS} хооронд бүхэл тоо байна.")
        if not 1 <= self.num_students <= self.MAX_STUDENTS:
            raise ValueError(f"Оюутны тоо 1-{self.MAX_STUDENTS} хооронд бүхэл тоо байна.")
        if not 0 < self.arrival_interval <= self.MAX_SECONDS:
            raise ValueError(f"Ирэх хугацаа 0-ээс их, {self.MAX_SECONDS:g} секундээс ихгүй байна.")
        if not 0 < self.service_time <= self.MAX_SECONDS:
            raise ValueError(f"Үйлчилгээний хугацаа 0-ээс их, {self.MAX_SECONDS:g} секундээс ихгүй байна.")

    @classmethod
    def from_text(cls, chairs: str, students: str, interval: str, service: str,
                  seed: str = "") -> "Config":
        """UI-ийн текст талбаруудаас Config үүсгэнэ. Буруу бол ValueError."""
        def to_int(name: str, s: str) -> int:
            try:
                return int(str(s).strip())
            except ValueError:
                raise ValueError(f"'{name}' нь бүхэл тоо байх ёстой (оруулсан: '{s}').") from None

        def to_float(name: str, s: str) -> float:
            try:
                return float(str(s).strip())
            except ValueError:
                raise ValueError(f"'{name}' нь тоо байх ёстой (оруулсан: '{s}').") from None

        cfg = cls(
            num_chairs=to_int("Сандлын тоо", chairs),
            num_students=to_int("Оюутны тоо", students),
            arrival_interval=to_float("Ирэх хугацаа", interval),
            service_time=to_float("Үйлчилгээний хугацаа", service),
            seed=to_int("Seed", seed) if str(seed).strip() else None,
        )
        cfg.validate()
        return cfg


@dataclass(frozen=True)
class Event:
    """UI-д дамжих нэг үйл явдал + тухайн мөчийн төлөвийн зураг (snapshot)."""
    t: float                  # симуляци эхэлснээс хойших секунд
    kind: str                 # дээрх төрлүүдийн нэг
    student: Optional[int]    # холбогдох оюутны дугаар (байхгүй бол None)
    message: str              # хүн уншихад зориулсан тайлбар
    ta_state: str             # TA_SLEEPING / TA_AWAKE / TA_HELPING
    waiting: Tuple[int, ...]  # хүлээлгийн дараалал (толгойгоос нь)
    free_chairs: int
    current: Optional[int]    # одоо үйлчлүүлж буй оюутан
    served: int               # үйлчлүүлж дууссан нийт тоо
    turned_away: int          # сандал дүүрэн байснаас буцсан тоо


# ------------------------------------------------------------------ Симуляци
class Simulation:
    def __init__(self, config: Config):
        config.validate()
        self.config = config
        self.events: "queue.Queue[Event]" = queue.Queue()
        self._threads: List[threading.Thread] = []
        self._init_state()

    # ---- төлвийг шинэчлэх (reset-д ч ашиглана)
    def _init_state(self) -> None:
        cfg = self.config
        self.mutex = threading.Lock()                  # waiting, ta_state, тоолуурыг хамгаална
        self.students_sem = threading.Semaphore(0)     # хүлээж буй оюутны тоо
        self.turn = [threading.Semaphore(0) for _ in range(cfg.num_students)]
        self.waiting: Deque[int] = deque()
        self.ta_state = TA_SLEEPING
        self.current: Optional[int] = None
        self.served = 0
        self.turned_away = 0
        self._stop = threading.Event()
        self._run = threading.Event()                  # set = ажиллаж байна, clear = pause
        self._run.set()
        self._t0 = 0.0
        self._started = False

    # ----------------------------------------------------------- Нийтийн API
    def start(self) -> None:
        if self._started:
            raise RuntimeError("Симуляци аль хэдийн эхэлсэн. Эхлээд reset() хий.")
        self._started = True
        self._t0 = time.monotonic()
        with self.mutex:
            self._emit(SIM_START, None, "Симуляци эхэллээ")
        rng_seed = self.config.seed
        self._threads = [threading.Thread(target=self._ta_loop, name="TA", daemon=True)]
        for i in range(self.config.num_students):
            rng = random.Random(None if rng_seed is None else rng_seed + i)
            self._threads.append(threading.Thread(
                target=self._student_loop, args=(i, rng), name=f"student-{i}", daemon=True))
        for th in self._threads:
            th.start()

    def pause(self) -> None:
        self._run.clear()

    def resume(self) -> None:
        self._run.set()

    @property
    def paused(self) -> bool:
        return not self._run.is_set()

    @property
    def running(self) -> bool:
        return self._started and not self._stop.is_set()

    def stop(self) -> None:
        """Бүх thread-ийг зогсооно (pause-тай байсан ч гацахгүй)."""
        if not self._started or self._stop.is_set():
            return
        self._stop.set()
        self._run.set()
        for th in self._threads:
            th.join(timeout=2.0)
        with self.mutex:
            self._emit(SIM_STOP, None, "Симуляци зогслоо")

    def reset(self, new_config: Optional[Config] = None) -> None:
        """Зогсоож, бүх төлөв + event queue-г цэвэрлэнэ. Шинэ тохиргоо өгч болно."""
        self.stop()
        if new_config is not None:
            new_config.validate()
            self.config = new_config
        self.events = queue.Queue()
        self._threads = []
        self._init_state()

    def drain_events(self) -> List[Event]:
        """UI-д зориулсан: queue-д байгаа бүх event-ийг гаргаж авна."""
        out: List[Event] = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                return out

    def alive_threads(self) -> int:
        return sum(th.is_alive() for th in self._threads)

    # ---------------------------------------------------------- Дотоод туслах
    def _emit(self, kind: str, student: Optional[int], message: str) -> None:
        """ЗААВАЛ self.mutex барьсан үед дууд (event-ийн дараалал төлөвтэй таарна)."""
        free = self.config.num_chairs - len(self.waiting)
        self.events.put(Event(
            t=round(time.monotonic() - self._t0, 3), kind=kind, student=student,
            message=message, ta_state=self.ta_state, waiting=tuple(self.waiting),
            free_chairs=free, current=self.current,
            served=self.served, turned_away=self.turned_away))

    def _sleep(self, seconds: float) -> None:
        """Pause болон stop-ыг хүндэтгэсэн sleep."""
        remaining = seconds
        while remaining > 0 and not self._stop.is_set():
            if not self._run.is_set():          # pause: хугацаа хасахгүй хүлээнэ
                self._run.wait(0.05)
                continue
            step = min(0.02, remaining)
            self._stop.wait(step)
            remaining -= step

    @staticmethod
    def _around(rng: random.Random, mean: float) -> float:
        """mean-ий 50%-150% хооронд санамсаргүй хугацаа."""
        return mean * rng.uniform(0.5, 1.5)

    # ------------------------------------------------------------- TA thread
    def _ta_loop(self) -> None:
        rng = random.Random(None if self.config.seed is None else self.config.seed + 10_000)
        while not self._stop.is_set():
            # 1) Хүлээж буй хүн байхгүй бол унтна
            with self.mutex:
                if not self.waiting and self.ta_state != TA_SLEEPING:
                    self.ta_state = TA_SLEEPING
                    self._emit(TA_SLEEP, None, "Хүлээж буй оюутан алга, TA унтлаа")
            # 2) students_sem.wait(): оюутан ирэх хүртэл блоклогдоно (= унтана)
            got = False
            while not self._stop.is_set() and not got:
                got = self.students_sem.acquire(timeout=0.05)
            if not got:
                break
            # 3) Дарааллын эхний оюутныг авна
            with self.mutex:
                sid = self.waiting.popleft()
                self.current = sid
                self.ta_state = TA_HELPING
                self._emit(TA_START, sid, f"TA оюутан {sid}-д үйлчилж эхлэв")
            # 4) Үйлчилнэ
            self._sleep(self._around(rng, self.config.service_time))
            if self._stop.is_set():
                break
            # 5) Дуусгана, оюутанд дохио өгнө
            with self.mutex:
                self.served += 1
                self.current = None
                self.ta_state = TA_AWAKE
                self._emit(TA_DONE, sid, f"Оюутан {sid}-д үйлчилж дууслаа")
            self.turn[sid].release()

    # -------------------------------------------------------- Оюутны thread
    def _student_loop(self, sid: int, rng: random.Random) -> None:
        cfg = self.config
        while not self._stop.is_set():
            # programming хийж байна
            self._sleep(self._around(rng, cfg.arrival_interval))
            if self._stop.is_set():
                break
            seated = False
            with self.mutex:
                if len(self.waiting) < cfg.num_chairs:
                    if self.ta_state == TA_SLEEPING:
                        self.ta_state = TA_AWAKE
                        self._emit(STUDENT_WAKES_TA, sid, f"Оюутан {sid} унтаж буй TA-г сэрээв")
                    self.waiting.append(sid)
                    self._emit(STUDENT_WAITS, sid, f"Оюутан {sid} сандалд суув")
                    self.students_sem.release()          # signal(students)
                    seated = True
                else:
                    self.turned_away += 1
                    self._emit(STUDENT_LEAVES, sid,
                               f"Сандал дүүрэн, оюутан {sid} буцав (дараа дахин ирнэ)")
            if seated:
                # өөрийн ээлж + үйлчилгээ дуустал хүлээнэ
                while not self._stop.is_set():
                    if self.turn[sid].acquire(timeout=0.05):
                        break


# ------------------------------------------------------------ Консол demo
def _main() -> None:
    p = argparse.ArgumentParser(description="Sleeping TA - консол demo")
    p.add_argument("--chairs", default="3")
    p.add_argument("--students", default="5")
    p.add_argument("--interval", default="1.0", help="ирэх дундаж хугацаа (с)")
    p.add_argument("--service", default="1.0", help="үйлчилгээний дундаж хугацаа (с)")
    p.add_argument("--duration", type=float, default=10.0, help="хэдэн секунд ажиллуулах")
    p.add_argument("--seed", default="")
    a = p.parse_args()
    try:
        cfg = Config.from_text(a.chairs, a.students, a.interval, a.service, a.seed)
    except ValueError as e:
        raise SystemExit(f"Алдаа: {e}")
    sim = Simulation(cfg)
    sim.start()
    end = time.monotonic() + a.duration
    while time.monotonic() < end:
        for ev in sim.drain_events():
            print(f"[{ev.t:7.2f}s] {ev.message:<55} TA={ev.ta_state:<8} "
                  f"queue={list(ev.waiting)} free={ev.free_chairs}")
        time.sleep(0.05)
    sim.stop()
    for ev in sim.drain_events():
        print(f"[{ev.t:7.2f}s] {ev.message}")
    print(f"\nДүн: үйлчлүүлсэн={sim.served}, буцсан={sim.turned_away}")


if __name__ == "__main__":
    _main()
