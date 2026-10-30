# II-4-10: The Sleeping Teaching Assistant

**F.CSM302 Үйлдлийн систем — Бие даалт 1**

Silberschatz, *Operating System Concepts* (10th Edition), Chapter 7, Programming Project 10 дээр суурилсан Sleeping Teaching Assistant симуляци. Олон thread-ийн synchronization-ийг Python-ийн `threading` санаар хэрэгжүүлж, Tkinter dashboard дээр бодит цагт дүрсэлнэ.

---

## Төслийн зорилго

- **Synchronization:** `Thread`, `Semaphore`, `Lock` (mutex) ашиглан TA ба оюутнуудын ажиллагааг синхрончлох. Deadlock, race condition гарахгүй байх.
- **Interactive UI:** TA, хүлээлгийн сандлууд, оюутнуудын ирэлт, дарааллыг хөдөлгөөнт дүрслэлээр харуулах. Дүрслэл нь бодит thread-үүдийн төлөвийг харуулдаг.

## Бодлогын нөхцөл

- TA-ийн өрөөнд 1 сандал (TA), коридорт N хүлээлгийн сандал байна.
- Оюутан байхгүй бол TA унтана.
- Оюутан ирэхэд: TA унтаж байвал сэрээнэ; сул сандал байвал суугаад хүлээнэ; сандал дүүрэн бол буцаж явна (хэсэг хугацааны дараа дахин ирнэ).
- Оюутнууд FIFO дарааллаар үйлчлүүлнэ.

## Багийн мэдээлэл

| Зүйл | Утга |
|---|---|
| Хуваарилалтын код | II-4-10 |
| Сэдэв | The Sleeping Teaching Assistant |
| GitHub | https://github.com/B242270001/II-4-10_SleepingTeachingAssistant |

### Гишүүд

| № | Нэр | Оюутны код |
|---|---|---|
| 1 | А.Төгөлдөр | B242270001 |
| 2 | Ц.Цогтжаргал | B241940005 |
| 3 | Д.Отгон-Эрдэнэ | B222270083 |
| 4 | О.Цэрэнлхавга | B232270113 |
| 5 | Г.Түвшинсайхан | B242270085 |

---

## Quick Start

### Орчны шаардлага

- **Python 3.14 + Tk 9.0** (туршсан орчин). macOS-ийн суурь Python 3.9-д UI зөв зурагдахгүй.
- Гадны сан шаардлагагүй (зөвхөн стандарт сан: `threading`, `tkinter`, `queue`).

### 1. Татаж авах

```bash
git clone https://github.com/B242270001/II-4-10_SleepingTeachingAssistant.git
cd II-4-10_SleepingTeachingAssistant
```

### 2. UI-тай ажиллуулах

```bash
python3 src/ui.py
```

Талбаруудад утгаа оруулаад **START** дарна.

> **Windows:** `python3`-ийн оронд `python` (эсвэл `py`) гэж бичнэ. Жишээ нь `python src/ui.py`.
> Хэрэв `ui.py` дээр `ta_core` import алдаа гарвал `cd src` хийгээд `python ui.py` гэж ажиллуулна.

### 3. Консол горимд ажиллуулах (UI-гүй)

```bash
python3 src/ta_core.py --chairs 3 --students 5 --interval 1.0 --service 1.5 --duration 10
```

Нэмэлт аргумент: `--seed 42` (ижил үр дүн давтахад).

---

## UI-ийн хэрэглээ

**Тохиргоо**

| Талбар | Хязгаар |
|---|---|
| Хүлээлгийн сандлын тоо | 0 – 20 (бүхэл) |
| Оюутны тоо | 1 – 50 (бүхэл) |
| Ирэх хугацаа (сек) | 0.001 – 60 |
| Үйлчилгээний хугацаа (сек) | 0.001 – 60 |

Буруу утга оруулбал `INVALID INPUT` төлөв гарч, симуляци эхлэхгүй.

**Удирдлага**

| Товч | Үйлдэл |
|---|---|
| START | Симуляци эхлүүлэх / түр зогссоныг үргэлжлүүлэх |
| PAUSE | Түр зогсоох |
| STEP | Түр зогссон үед нэг event-ээр урагшлах |
| RESET | Бүх төлөв, тоолуурыг цэвэрлэх |
| Visual speed | Зөвхөн дүрслэлийн хурд (core thread-ийн хугацаанд нөлөөлөхгүй) |

**Нэмэлт боломжууд:** Event түүхийг төрлөөр нь шүүх (filter), хайх (search), CSV болгон экспортлох боломжтой.

---

## Synchronization-ийн загвар

Номын шийдэлтэй ижил бүтэцтэй:

| Объект | Төрөл | Үүрэг |
|---|---|---|
| `mutex` | `Lock` | Хүлээлгийн дараалал, TA-ийн төлөв, тоолуурыг хамгаална |
| `students_sem` | `Semaphore(0)` | Хүлээж буй оюутны тоо. TA үүн дээр `wait` хийж унтана |
| `turn[i]` | `Semaphore(0)` | Оюутан бүрийн хувийн semaphore. TA үйлчилж дуустал оюутан хүлээнэ |

Thread бүр өөрийн үйлдлийг `Event` болгон `queue.Queue`-д хийнэ, UI нь `root.after(...)`-ээр уншиж зурна.

---

## Төслийн бүтэц

```
├── src/
│   ├── ta_core.py        # Core: Simulation, Config, thread-үүд (UI-аас хамааралгүй)
│   ├── ui.py             # Tkinter dashboard
│   └── test_ta_core.py   # Багийн автомат тест (11)
├── tests/
│   ├── test_edge_cases.py   # Edge case тест (27)
│   ├── core_scenarios.py    # Core дээрх сценарийн тоо
│   ├── ui_scenarios.py      # UI сценари + screenshot
│   └── screenshots/
├── testing_results.md / .pdf  # Туршилтын тайлан
└── README.md
```

---

## Тест ажиллуулах

Төслийн үндсэн хавтсанд:

```bash
python3 -m unittest src.test_ta_core            # багийн 11 тест
python3 -m unittest discover -s tests -v        # 27 edge case тест
python3 tests/core_scenarios.py                 # core дээрх бодит тоо (~2 мин)
python3 tests/ui_scenarios.py all               # UI сценари + screenshot (~3.5 мин, macOS)
```

> `test_ta_core.py` нь `src/`-д, `test_edge_cases.py` нь `tests/`-д байдаг тул тест тус бүрийг дээрх хоёр өөр командаар ажиллуулна.
> Windows дээр `python3`-ийн оронд `python` гэж бичнэ.

## Туршилтын дүн

| Түвшин | Үр дүн |
|---|---|
| Багийн автомат тест | 11 / 11 тэнцсэн |
| Edge case тест | 27 / 27 тэнцсэн |
| UI сценари (S1–S11) | 11 / 11 тэнцсэн |

Дэлгэрэнгүйг [testing_results.pdf](testing_results.pdf)-ээс харна уу.

## Мэдэгдэж буй хязгаарлалт

- Ачаалал ихтэй үед (олон оюутан буцдаг тохиргоо) UI event-үүдийг тогтмол хурдаар тоглуулдаг тул дэлгэц дээрх "үйлчлүүлсэн" тоо core-ийн бодит тооноос хоцорч харагдана. Core-ийн ажиллагаа зөв.
- `STEP` товч буфер хоосон үед нэгээс олон event нэг дор үзүүлж болно.
- Буруу тохиргоотой `reset(new_config)` симуляцийг зогссон хэвээр үлдээнэ.
- UI-д seed талбар байхгүй тул үр дүн ажиллуулалт бүрт өөр гарна (seed нь зөвхөн консол горимд `--seed`-ээр ажиллана).
- `tests/ui_scenarios.py` нь macOS-ийн `screencapture` ашигладаг тул **зөвхөн macOS** дээр ажиллана.
- Туршилтыг macOS дээр хийсэн. Windows дээр `Segoe UI` фонт өөр харагдаж болно.