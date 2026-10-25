
"""Sleeping Teaching Assistant — premium Tkinter dashboard.

Drop in as src/ui.py beside ta_core.py. Standard library only.
Run: python src/ui.py
"""
from __future__ import annotations

import csv
import math
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from ta_core import (
    Config, Simulation, TA_SLEEPING, TA_AWAKE, TA_HELPING,
    SIM_START, SIM_STOP, TA_SLEEP, STUDENT_WAKES_TA,
    STUDENT_WAITS, STUDENT_LEAVES, TA_START, TA_DONE,
)


class C:
    bg = '#080F1D'
    surface = '#111D30'
    surface2 = '#17263D'
    raised = '#20334F'
    border = '#2B405C'
    text = '#EDF4FF'
    muted = '#93A8C2'
    blue = '#63B3FF'
    teal = '#46DBCB'
    green = '#59DF99'
    yellow = '#FFD074'
    red = '#FF7B90'
    purple = '#B9A1FF'
    skin = '#E9B98E'
    floor = '#16273C'


EVENT_META = {
    SIM_START: ('START', C.blue, 'Simulation started'),
    SIM_STOP: ('STOP', C.muted, 'Simulation stopped'),
    TA_SLEEP: ('SLEEP', C.purple, 'TA is sleeping'),
    STUDENT_WAKES_TA: ('WAKE', C.blue, 'Student wakes the TA'),
    STUDENT_WAITS: ('WAIT', C.yellow, 'Student joined the queue'),
    STUDENT_LEAVES: ('LEFT', C.red, 'No chair available'),
    TA_START: ('HELP', C.green, 'TA begins helping'),
    TA_DONE: ('DONE', C.teal, 'Help session finished'),
}


@dataclass
class Actor:
    sid: int
    x: float
    y: float
    tx: float
    ty: float
    color: str
    phase: str = 'enter'
    opacity: float = 1.0


class Dashboard:
    """UI only. Core owns concurrency; Tk main thread owns widgets."""

    POLL_MS = 70
    FRAME_MS = 33
    MAX_LOG_ROWS = 1200
    ROOM_LEFT = 292
    CHAIR_W = 91
    CHAIR_H = 106

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Sleeping TA  •  Synchronization Studio')
        self.root.geometry('1370x900')
        self.root.minsize(1040, 690)
        self.root.configure(bg=C.bg)

        self.sim: Simulation | None = None
        self.events: deque = deque()
        self.history = []
        self.samples = []
        self.last_event = None
        self.actors: dict[int, Actor] = {}
        self.running = False
        self.stepping = False
        self.closed = False
        self.run_generation = 0
        self.frame_id = None
        self.poll_id = None
        self.event_accum = 0.0
        self.last_frame = time.monotonic()
        self.event_number = 0
        self.last_highlight = 0.0
        self.last_kind = ''
        self.last_student = None
        self.last_message = 'Configure the simulation and press START.'
        self.display_state = TA_SLEEPING
        self.display_waiting = []
        self.display_current = None
        self.display_served = 0
        self.display_away = 0
        self.chair_count = 3
        self.student_count = 10
        self.speed = tk.DoubleVar(value=1.0)
        self.filter_var = tk.StringVar(value='All events')
        self.search_var = tk.StringVar(value='')
        self.form = {}
        self.metrics = {}
        self._setup_style()
        self._build()
        self._reset_view()
        self._refresh_log()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_id = self.root.after(self.POLL_MS, self._poll)
        self.frame_id = self.root.after(self.FRAME_MS, self._frame)

    def _setup_style(self):
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure(
            'Dark.Vertical.TScrollbar',
            background=C.raised,
            troughcolor=C.surface,
            bordercolor=C.surface,
            arrowcolor=C.text,
            relief='flat'
        )
        style.map(
            'Dark.Vertical.TScrollbar',
            background=[('active', C.blue)]
        )
        style.configure(
            'Dark.TCombobox',
            fieldbackground=C.surface2,
            background=C.surface2,
            foreground=C.text,
            arrowcolor=C.blue,
            bordercolor=C.border
        )

    def _txt(
        self,
        parent,
        text,
        size=10,
        color=C.text,
        weight='normal',
        bg=None,
        **kw
    ):
        return tk.Label(
            parent,
            text=text,
            bg=bg or C.surface,
            fg=color,
            font=('Segoe UI', size, weight),
            **kw
        )

    def _panel(self, parent, title, subtitle=None):
        outer = tk.Frame(
            parent,
            bg=C.surface,
            highlightbackground=C.border,
            highlightthickness=1
        )
        head = tk.Frame(outer, bg=C.surface)
        head.pack(fill='x', padx=17, pady=(13, 9))

        self._txt(
            head, title, 11, weight='bold'
        ).pack(side='left')

        if subtitle:
            self._txt(
                head, subtitle, 9, C.muted
            ).pack(side='right')

        return outer

    def _button(self, parent, text, color, cmd):
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=color,
            fg=C.bg,
            activebackground=color,
            activeforeground=C.bg,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            bd=0,
            cursor='hand2',
            padx=12,
            pady=9
        )

    def _build(self):
        # Header
        header = tk.Frame(self.root, bg=C.bg)
        header.pack(fill='x', padx=24, pady=(16, 13))

        title_col = tk.Frame(header, bg=C.bg)
        title_col.pack(side='left')

        self._txt(
            title_col,
            'SLEEPING TA  /  STUDIO',
            22,
            C.text,
            'bold',
            C.bg
        ).pack(anchor='w')

        self._txt(
            title_col,
            'THREAD SYNCHRONIZATION  •  INTERACTIVE VISUALIZER',
            9,
            C.muted,
            bg=C.bg
        ).pack(anchor='w', pady=(3, 0))

        self.pill = self._txt(
            header,
            '  ●  READY  ',
            10,
            C.blue,
            'bold',
            C.surface
        )
        self.pill.pack(side='right', pady=12)

        # Statistics cards
        metrics_row = tk.Frame(self.root, bg=C.bg)
        metrics_row.pack(fill='x', padx=20, pady=(0, 12))

        for label, key, color in [
            ('TOTAL STUDENTS', 'students', C.blue),
            ('SESSIONS SERVED', 'served', C.green),
            ('WAITING NOW', 'waiting', C.yellow),
            ('TURNED AWAY', 'away', C.red),
        ]:
            panel = tk.Frame(
                metrics_row,
                bg=C.surface,
                highlightbackground=C.border,
                highlightthickness=1
            )
            panel.pack(
                side='left',
                fill='x',
                expand=True,
                padx=4
            )

            self._txt(
                panel,
                label,
                9,
                C.muted,
                'bold'
            ).pack(
                anchor='w',
                padx=15,
                pady=(11, 1)
            )

            num = self._txt(
                panel,
                '00',
                25,
                color,
                'bold'
            )
            num.pack(
                anchor='w',
                padx=15,
                pady=(0, 10)
            )

            self.metrics[key] = num

        # Main split
        self.main = tk.Frame(self.root, bg=C.bg)
        self.main.pack(
            fill='both',
            expand=True,
            padx=24,
            pady=(0, 12)
        )

        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_columnconfigure(
            1,
            weight=0,
            minsize=325
        )
        self.main.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.main, bg=C.bg)
        left.grid(
            row=0,
            column=0,
            sticky='nsew',
            padx=(0, 12)
        )

        right = tk.Frame(
            self.main,
            bg=C.bg,
            width=325
        )
        right.grid(
            row=0,
            column=1,
            sticky='ns'
        )
        right.grid_propagate(False)

        # Classroom panel
        room_panel = self._panel(
            left,
            'LIVE CLASSROOM',
            'SCROLL TO SEE ALL CHAIRS'
        )
        room_panel.pack(
            fill='both',
            expand=True
        )

        room_header = tk.Frame(
            room_panel,
            bg=C.surface
        )
        room_header.pack(
            fill='x',
            padx=16,
            pady=(0, 8)
        )

        self.room_state = self._txt(
            room_header,
            '● TA SLEEPING',
            10,
            C.purple,
            'bold'
        )
        self.room_state.pack(side='left')

        self.occupancy = self._txt(
            room_header,
            '0 / 3 seats',
            9,
            C.muted
        )
        self.occupancy.pack(side='right')

        # Legend
        legend = tk.Frame(
            room_panel,
            bg=C.surface
        )
        legend.pack(
            fill='x',
            padx=16,
            pady=(0, 9)
        )

        for name, color in [
            ('Sleeping', C.purple),
            ('Helping', C.green),
            ('Waiting', C.yellow),
            ('Leaving', C.red)
        ]:
            item = tk.Frame(
                legend,
                bg=C.surface
            )
            item.pack(
                side='left',
                padx=(0, 13)
            )

            swatch = tk.Canvas(
                item,
                width=12,
                height=12,
                bg=C.surface,
                highlightthickness=0
            )
            swatch.pack(side='left')
            swatch.create_oval(
                2, 2, 10, 10,
                fill=color,
                outline=''
            )

            self._txt(
                item,
                name,
                8,
                C.muted
            ).pack(
                side='left',
                padx=(3, 0)
            )

        canvas_holder = tk.Frame(
            room_panel,
            bg=C.surface
        )
        canvas_holder.pack(
            fill='both',
            expand=True,
            padx=12,
            pady=(0, 12)
        )

        self.canvas = tk.Canvas(
            canvas_holder,
            bg='#0C1729',
            highlightthickness=0,
            height=380
        )

        self.canvas.configure(yscrollincrement=22)

        self.scroll = ttk.Scrollbar(
            canvas_holder,
            orient='vertical',
            command=self.canvas.yview,
            style='Dark.Vertical.TScrollbar'
        )
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        self.canvas.bind(
            '<Configure>',
            lambda _e: self._draw_room()
        )
        self.canvas.bind('<MouseWheel>', self._wheel)
        self.canvas.bind(
            '<Button-4>',
            lambda _e: self.canvas.yview_scroll(-2, 'units')
        )
        self.canvas.bind(
            '<Button-5>',
            lambda _e: self.canvas.yview_scroll(2, 'units')
        )

        # ==========================================
        # PERFORMANCE CHART
        # ==========================================

        chart_panel = self._panel(
            left,
            'PERFORMANCE MONITOR',
            'EVENT-BASED HISTORY'
        )
        chart_panel.pack(fill='x', pady=(12, 0))

        self.chart = tk.Canvas(
            chart_panel,
            bg=C.surface,
            height=125,
            highlightthickness=0
        )
        self.chart.pack(
            fill='x',
            padx=14,
            pady=(0, 11)
        )
        self.chart.bind(
            '<Configure>',
            lambda _e: self._draw_chart()
        )

        # ==========================================
        # CONFIGURATION
        # ==========================================

        settings = self._panel(
            right,
            'CONFIGURATION',
            'CORE PARAMETERS'
        )
        settings.pack(fill='x')

        form = tk.Frame(
            settings,
            bg=C.surface
        )
        form.pack(
            fill='x',
            padx=16,
            pady=(0, 12)
        )

        for i, (key, label, default) in enumerate([
            ('chairs', 'Waiting chairs (0–20)', '3'),
            ('students', 'Students (1–50)', '10'),
            ('interval', 'Arrival interval (sec)', '1.0'),
            ('service', 'Service time (sec)', '1.5'),
        ]):
            self._txt(
                form,
                label,
                9,
                C.muted
            ).grid(
                row=i,
                column=0,
                sticky='w',
                pady=5
            )

            entry = tk.Entry(
                form,
                width=9,
                bg=C.surface2,
                fg=C.text,
                insertbackground=C.text,
                justify='center',
                font=('Segoe UI', 10),
                relief='flat',
                bd=0
            )
            entry.insert(0, default)
            entry.grid(
                row=i,
                column=1,
                sticky='e',
                padx=(10, 0),
                pady=5,
                ipady=5
            )
            self.form[key] = entry

        form.grid_columnconfigure(0, weight=1)

        # ==========================================
        # PLAYBACK CONTROLS
        # ==========================================

        controls = self._panel(
            right,
            'PLAYBACK CONTROLS'
        )
        controls.pack(
            fill='x',
            pady=(12, 0)
        )

        btns = tk.Frame(
            controls,
            bg=C.surface
        )
        btns.pack(
            fill='x',
            padx=12,
            pady=(0, 10)
        )
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        for row, col, text, color, cmd in [
            (0, 0, '▶ START', C.green, self.start),
            (0, 1, 'Ⅱ PAUSE', C.yellow, self.pause),
            (1, 0, '⏭ STEP', C.blue, self.step),
            (1, 1, '↻ RESET', C.red, self.reset),
        ]:
            self._button(
                btns,
                text,
                color,
                cmd
            ).grid(
                row=row,
                column=col,
                sticky='ew',
                padx=4,
                pady=4
            )

        # ==========================================
        # SIMULATION SPEED
        # ==========================================

        speedrow = tk.Frame(
            controls,
            bg=C.surface
        )
        speedrow.pack(
            fill='x',
            padx=16,
            pady=(0, 12)
        )

        self._txt(
            speedrow,
            'VISUAL SPEED',
            9,
            C.muted,
            'bold'
        ).pack(anchor='w')

        scale_line = tk.Frame(
            speedrow,
            bg=C.surface
        )
        scale_line.pack(fill='x')

        tk.Scale(
            scale_line,
            from_=0.25,
            to=4.0,
            resolution=0.25,
            orient='horizontal',
            variable=self.speed,
            bg=C.surface,
            fg=C.text,
            troughcolor=C.raised,
            activebackground=C.blue,
            highlightthickness=0,
            bd=0,
            showvalue=False
        ).pack(
            side='left',
            fill='x',
            expand=True
        )

        self.speed_label = self._txt(
            scale_line,
            '1.00×',
            10,
            C.blue,
            'bold'
        )
        self.speed_label.pack(
            side='right',
            padx=(8, 0)
        )

        self.speed.trace_add(
            'write',
            lambda *_: self.speed_label.config(
                text=f'{self.speed.get():.2f}×'
            )
        )

        self._txt(
            controls,
            'Speed affects playback, not core thread timing.',
            8,
            C.muted,
            wraplength=275,
            justify='left'
        ).pack(
            anchor='w',
            padx=16,
            pady=(0, 12)
        )

        # ==========================================
        # LATEST ACTIVITY
        # ==========================================

        focus = self._panel(
            right,
            'LATEST ACTIVITY'
        )
        focus.pack(
            fill='both',
            expand=True,
            pady=(12, 0)
        )

        self.latest_title = self._txt(
            focus,
            'Waiting for simulation',
            12,
            C.blue,
            'bold',
            wraplength=270,
            justify='left'
        )
        self.latest_title.pack(
            anchor='w',
            padx=17,
            pady=(0, 7)
        )

        self.latest_detail = self._txt(
            focus,
            self.last_message,
            10,
            C.muted,
            wraplength=275,
            justify='left'
        )
        self.latest_detail.pack(
            anchor='w',
            padx=17,
            pady=(0, 10)
        )

        self.latest_time = self._txt(
            focus,
            't = 0.000 s',
            9,
            C.muted
        )
        self.latest_time.pack(
            anchor='w',
            padx=17,
            pady=(0, 15)
        )

        # ==========================================
        # EVENT TIMELINE
        # ==========================================

        bottom = self._panel(
            self.root,
            'EVENT TIMELINE',
            'LIVE CORE EVENTS'
        )
        bottom.pack(
            fill='x',
            padx=24,
            pady=(0, 16)
        )

        toolbar = tk.Frame(
            bottom,
            bg=C.surface
        )
        toolbar.pack(
            fill='x',
            padx=14,
            pady=(0, 8)
        )

        self.filter_menu = ttk.Combobox(
            toolbar,
            textvariable=self.filter_var,
            state='readonly',
            width=19,
            style='Dark.TCombobox',
            values=[
                'All events',
                'TA events',
                'Student events',
                'Waiting',
                'Help sessions',
                'Turned away'
            ]
        )
        self.filter_menu.pack(side='left')
        self.filter_menu.bind(
            '<<ComboboxSelected>>',
            lambda _e: self._refresh_log()
        )

        search = tk.Entry(
            toolbar,
            textvariable=self.search_var,
            bg=C.surface2,
            fg=C.text,
            insertbackground=C.text,
            font=('Segoe UI', 9),
            relief='flat',
            width=29
        )
        search.pack(
            side='left',
            padx=9,
            ipady=5
        )

        self.search_var.trace_add(
            'write',
            lambda *_: self._refresh_log()
        )

        self._button(
            toolbar,
            'EXPORT CSV',
            C.blue,
            self.export_csv
        ).pack(side='right')

        self.log = tk.Text(
            bottom,
            height=7,
            bg='#0B1628',
            fg=C.muted,
            insertbackground=C.text,
            font=('Consolas', 9),
            relief='flat',
            wrap='none',
            state='disabled'
        )
        self.log.pack(
            fill='x',
            padx=14,
            pady=(0, 12)
        )

        for kind, (_, color, _) in EVENT_META.items():
            self.log.tag_config(
                kind,
                foreground=color
            )

        self.log.tag_config(
            'ui',
            foreground=C.blue
        )
        self.log.tag_config(
            'neutral',
            foreground=C.muted
        )

    # ==============================================
    # CONFIGURATION & CORE LIFECYCLE
    # ==============================================

    def _read_config(self):
        try:
            return Config.from_text(
                self.form['chairs'].get(),
                self.form['students'].get(),
                self.form['interval'].get(),
                self.form['service'].get(),
            )
        except (ValueError, TypeError) as exc:
            self._status('INVALID INPUT', C.red)
            messagebox.showerror(
                'Invalid configuration',
                str(exc),
                parent=self.root
            )
            return None

    def _status(self, title, color):
        self.pill.config(
            text=f'  ●  {title}  ',
            fg=color
        )

    def _start_new(self):
        cfg = self._read_config()
        if cfg is None:
            return False

        self._stop_core()
        self.run_generation += 1
        self._reset_view()

        self.chair_count = cfg.num_chairs
        self.student_count = cfg.num_students

        self.sim = Simulation(cfg)

        try:
            self.sim.start()
        except Exception as exc:
            self.sim = None
            self._status('ERROR', C.red)
            messagebox.showerror(
                'Simulation error',
                str(exc),
                parent=self.root
            )
            return False

        return True

    def _stop_core(self):
        if self.sim is not None:
            self.sim.stop()
            self.sim = None

    def start(self):
        if self.sim is None or not self.sim.running:
            if not self._start_new():
                return
        else:
            self.sim.resume()

        self.running = True
        self.stepping = False
        self._status('RUNNING', C.green)

    def pause(self):
        if self.sim is None:
            return

        self.sim.pause()
        self.running = False
        self.stepping = False
        self._status('PAUSED', C.yellow)

    def step(self):
        if self.sim is None or not self.sim.running:
            if not self._start_new():
                return

        self.running = False
        self.stepping = True

        # Step displays one buffered event.
        # Core threads may produce multiple events.
        self.events.extend(self.sim.drain_events())

        if self.events:
            self._consume_one()
            self.sim.pause()
            self.stepping = False
            self._status(
                f'STEP {self.event_number}',
                C.blue
            )
        else:
            self.sim.resume()
            self._status(
                'WAITING FOR EVENT',
                C.blue
            )

    def reset(self):
        self.running = False
        self.stepping = False
        self._stop_core()
        self.run_generation += 1
        self._reset_view()
        self._status('READY', C.blue)
        self._draw_room()
        self._draw_chart()
        self._refresh_log()

    def _reset_view(self):
        self.events.clear()
        self.history.clear()
        self.samples.clear()
        self.actors.clear()

        self.last_event = None
        self.event_number = 0
        self.event_accum = 0.0

        self.display_state = TA_SLEEPING
        self.display_waiting = []
        self.display_current = None
        self.display_served = 0
        self.display_away = 0

        self.last_kind = ''
        self.last_student = None
        self.last_message = (
            'Configure the simulation and press START.'
        )

        if hasattr(self, 'latest_title'):
            self.latest_title.config(
                text='Waiting for simulation',
                fg=C.blue
            )
            self.latest_detail.config(
                text=self.last_message
            )
            self.latest_time.config(
                text='t = 0.000 s'
            )

        if hasattr(self, 'canvas'):
            self.canvas.yview_moveto(0)

    # ==============================================
    # EVENT LOOP AND ANIMATION
    # ==============================================

    def _poll(self):
        if self.closed:
            return

        try:
            if self.sim is not None:
                self.events.extend(
                    self.sim.drain_events()
                )

                if self.stepping and self.events:
                    self._consume_one()
                    self.sim.pause()
                    self.stepping = False
                    self._status(
                        f'STEP {self.event_number}',
                        C.blue
                    )

        except Exception as exc:
            self.running = False
            self.stepping = False
            self._status('EVENT ERROR', C.red)
            messagebox.showerror(
                'Event processing error',
                str(exc),
                parent=self.root
            )

        finally:
            if not self.closed:
                self.poll_id = self.root.after(
                    self.POLL_MS,
                    self._poll
                )

    def _frame(self):
        if self.closed:
            return

        now = time.monotonic()
        dt = min(
            0.12,
            now - self.last_frame
        )
        self.last_frame = now

        if self.running:
            self.event_accum += (
                dt * self.speed.get()
            )

            # Limit event playback per frame.
            count = 0

            while (
                self.events
                and self.event_accum >= 0.23
                and count < 4
            ):
                self._consume_one()
                self.event_accum -= 0.23
                count += 1

            if (
                self.sim is not None
                and not self.sim.running
                and not self.events
            ):
                self.running = False
                self._status('FINISHED', C.blue)

        self._advance_actors(dt)
        self._draw_room()

        self.frame_id = self.root.after(
            self.FRAME_MS,
            self._frame
        )

    def _consume_one(self):
        if not self.events:
            return

        event = self.events.popleft()
        self.last_event = event
        self.event_number += 1
        self.history.append(event)

        self.display_state = event.ta_state
        self.display_waiting = list(event.waiting)
        self.display_current = event.current
        self.display_served = event.served
        self.display_away = event.turned_away

        self.last_kind = event.kind
        self.last_student = event.student
        self.last_message = event.message
        self.last_highlight = time.monotonic()

        tag, color, summary = EVENT_META.get(
            event.kind,
            ('EVENT', C.blue, event.kind)
        )

        self.latest_title.config(
            text=f'{tag}  •  {summary}',
            fg=color
        )
        self.latest_detail.config(
            text=event.message
        )
        self.latest_time.config(
            text=f't = {event.t:.3f} s'
        )

        self.samples.append((
            event.t,
            event.served,
            len(event.waiting),
            event.turned_away
        ))

        self._sync_actors(event)
        self._update_metrics()
        self._draw_chart()
        self._refresh_log()

    def _sync_actors(self, event):
        # Students move between the entrance,
        # waiting seats, help desk and exit.

        targets = {}

        for idx, sid in enumerate(event.waiting):
            targets[sid] = ('wait', idx)

        if event.current is not None:
            targets[event.current] = ('help', 0)

        if (
            event.student is not None
            and event.kind == STUDENT_LEAVES
        ):
            targets[event.student] = ('leave', 0)

        for sid, (phase, index) in targets.items():
            if sid not in self.actors:
                self.actors[sid] = Actor(
                    sid,
                    280,
                    95,
                    280,
                    95,
                    C.yellow,
                    'enter'
                )

            actor = self.actors[sid]
            actor.phase = phase

            actor.color = (
                C.green if phase == 'help'
                else C.red if phase == 'leave'
                else C.yellow
            )

            if phase == 'help':
                actor.tx = 192
                actor.ty = 184

            elif phase == 'wait':
                x, y = self._chair_position(index)
                actor.tx = x
                actor.ty = y

            elif phase == 'leave':
                actor.tx = 285
                actor.ty = 75

        for sid, actor in self.actors.items():
            if sid not in targets and actor.phase != 'leave':
                actor.phase = 'leave'
                actor.color = C.teal
                actor.tx = 285
                actor.ty = 75

    def _chair_position(self, index):
        width = max(self.canvas.winfo_width(), 650)
        available = max(100, width - self.ROOM_LEFT - 35)
        columns = max(1, min(6, int(available // self.CHAIR_W)))
        col = index % columns
        row = index // columns
        x = self.ROOM_LEFT + col * self.CHAIR_W + 45
        y = 125 + row * self.CHAIR_H
        return x, y

    def _advance_actors(self, dt):
        speed = min(1.0, dt * 6.0 * self.speed.get())
        remove = []

        for sid, actor in self.actors.items():
            actor.x += (actor.tx - actor.x) * speed
            actor.y += (actor.ty - actor.y) * speed

            distance = math.hypot(
                actor.tx - actor.x,
                actor.ty - actor.y
            )

            if actor.phase == 'leave' and distance < 5:
                remove.append(sid)

        for sid in remove:
            self.actors.pop(sid, None)

    def _rounded_rect(self, canvas, x1, y1, x2, y2,
                      radius=12, fill=C.surface2,
                      outline=C.border, width=1):
        radius = max(0, min(radius, (x2-x1)/2, (y2-y1)/2))
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=12,
            fill=fill,
            outline=outline,
            width=width
        )

    def _draw_person(self, canvas, x, y, color, name="",
                     scale=1.0):
        r = 11 * scale

        canvas.create_oval(
            x-r, y-31*scale,
            x+r, y-9*scale,
            fill=C.skin,
            outline=''
        )

        canvas.create_arc(
            x-r, y-34*scale,
            x+r, y-13*scale,
            start=0,
            extent=180,
            fill='#28364B',
            outline='#28364B'
        )

        canvas.create_oval(
            x-14*scale, y-8*scale,
            x+14*scale, y+21*scale,
            fill=color,
            outline=''
        )

        canvas.create_line(
            x-7*scale, y+17*scale,
            x-9*scale, y+29*scale,
            fill=C.muted,
            width=3
        )
        canvas.create_line(
            x+7*scale, y+17*scale,
            x+9*scale, y+29*scale,
            fill=C.muted,
            width=3
        )

        if name:
            canvas.create_text(
                x,
                y+42*scale,
                text=str(name),
                fill=C.text,
                font=('Segoe UI', max(7, int(9*scale)), 'bold')
            )

    def _draw_room(self):
        if not hasattr(self, 'canvas'):
            return

        canvas = self.canvas
        canvas.delete('all')

        width = max(canvas.winfo_width(), 650)
        height = max(canvas.winfo_height(), 350)

        available = max(100, width - self.ROOM_LEFT - 35)
        columns = max(1, min(6, int(available // self.CHAIR_W)))
        rows = math.ceil(max(1, self.chair_count) / columns)

        content_height = max(
            height,
            175 + rows * self.CHAIR_H
        )

        canvas.configure(
            scrollregion=(0, 0, width, content_height)
        )

        canvas.create_rectangle(
            0, 0, width, content_height,
            fill='#0C1729',
            outline=''
        )

        # Background grid
        for x in range(0, width, 35):
            canvas.create_line(
                x, 0, x, content_height,
                fill='#12233A'
            )

        for y in range(0, content_height, 35):
            canvas.create_line(
                0, y, width, y,
                fill='#12233A'
            )

        # TA office
        self._rounded_rect(
            canvas, 20, 45, 260, 290,
            18, '#1B2C45', '#365270'
        )

        canvas.create_text(
            38, 68,
            text='TEACHING ASSISTANT',
            anchor='w',
            fill=C.muted,
            font=('Segoe UI', 10, 'bold')
        )

        state = str(self.display_state).upper()

        if self.display_state == TA_SLEEPING or 'SLEEP' in state:
            status = 'SLEEPING'
            color = C.purple
            icon = 'Z z z'
        elif self.display_state == TA_HELPING or 'HELP' in state:
            status = 'HELPING'
            color = C.green
            icon = 'ACTIVE'
        else:
            status = 'AWAKE'
            color = C.blue
            icon = 'READY'

        self.room_state.config(
            text=f'● TA {status}',
            fg=color
        )

        canvas.create_text(
            140, 105,
            text=icon,
            fill=color,
            font=('Segoe UI', 16, 'bold')
        )

        # Desk
        self._rounded_rect(
            canvas, 55, 192, 225, 222,
            8, '#526982', '#7892AC'
        )

        canvas.create_rectangle(
            67, 220, 75, 260,
            fill='#526982', outline=''
        )
        canvas.create_rectangle(
            205, 220, 213, 260,
            fill='#526982', outline=''
        )

        # Laptop
        self._rounded_rect(
            canvas, 112, 170, 165, 195,
            4, '#33475E', '#7892AC'
        )

        self._draw_person(
            canvas, 140, 151,
            color, 'TA', 1.1
        )

        canvas.create_text(
            140, 275,
            text=f'Current: {self.display_current or "None"}',
            fill=C.muted,
            font=('Segoe UI', 9)
        )

        # Waiting room title
        canvas.create_text(
            self.ROOM_LEFT,
            57,
            text='STUDENT WAITING AREA',
            anchor='w',
            fill=C.text,
            font=('Segoe UI', 12, 'bold')
        )

        canvas.create_text(
            self.ROOM_LEFT,
            79,
            text='Students are served in queue order',
            anchor='w',
            fill=C.muted,
            font=('Segoe UI', 9)
        )

        waiting = list(self.display_waiting)

        for i in range(self.chair_count):
            x, y = self._chair_position(i)
            occupied = i < len(waiting)

            chair_color = (
                '#344B64' if occupied
                else '#20344B'
            )

            border = C.yellow if occupied else C.border

            self._rounded_rect(
                canvas,
                x-34, y-38,
                x+34, y+33,
                10, chair_color, border
            )

            canvas.create_text(
                x, y-25,
                text=f'SEAT {i+1:02d}',
                fill=C.muted,
                font=('Segoe UI', 8, 'bold')
            )

            if occupied:
                sid = waiting[i]
                actor = self.actors.get(sid)

                # Draw seated students using animated position.
                if actor is not None and actor.phase == 'wait':
                    self._draw_person(
                        canvas,
                        actor.x,
                        actor.y+4,
                        C.yellow,
                        f'#{sid}',
                        0.75
                    )
                else:
                    self._draw_person(
                        canvas,
                        x,
                        y+4,
                        C.yellow,
                        f'#{sid}',
                        0.75
                    )
            else:
                canvas.create_text(
                    x, y+6,
                    text='EMPTY',
                    fill='#607893',
                    font=('Segoe UI', 9)
                )

        # Moving students
        for actor in self.actors.values():
            if actor.phase in ('leave', 'help'):
                self._draw_person(
                    canvas,
                    actor.x,
                    actor.y,
                    actor.color,
                    f'#{actor.sid}',
                    0.8
                )

        self.occupancy.config(
            text=f'{len(waiting)} / {self.chair_count} seats'
        )

    def _draw_chart(self):
        if not hasattr(self, 'chart'):
            return

        c = self.chart
        c.delete('all')

        w = max(c.winfo_width(), 300)
        h = max(c.winfo_height(), 125)

        left, right = 40, w-15
        top, bottom = 12, h-25

        for i in range(5):
            y = top + (bottom-top)*i/4
            c.create_line(
                left, y, right, y,
                fill=C.border,
                dash=(3, 5)
            )

        if not self.samples:
            c.create_text(
                w/2, h/2,
                text='Waiting for simulation data...',
                fill=C.muted,
                font=('Segoe UI', 10)
            )
            return

        data = self.samples[-100:]
        max_value = max(
            1,
            max(max(s[1], s[2], s[3]) for s in data)
        )

        series = [
            (1, C.green, 'Served'),
            (2, C.yellow, 'Waiting'),
            (3, C.red, 'Left')
        ]

        for index, color, label in series:
            points = []

            for i, sample in enumerate(data):
                x = left + (
                    (right-left)*i/max(1, len(data)-1)
                )
                y = bottom - (
                    sample[index]/max_value
                )*(bottom-top)

                points.extend([x, y])

            if len(points) >= 4:
                c.create_line(
                    *points,
                    fill=color,
                    width=2,
                    smooth=False
                )
            elif len(points) == 2:
                x, y = points
                c.create_oval(
                    x-3, y-3, x+3, y+3,
                    fill=color,
                    outline=''
                )

        x = left
        for _, color, label in series:
            c.create_oval(
                x, h-14, x+8, h-6,
                fill=color, outline=''
            )
            c.create_text(
                x+12, h-10,
                text=label,
                anchor='w',
                fill=C.muted,
                font=('Segoe UI', 8)
            )
            x += 90

    def _update_metrics(self):
        self.metrics['students'].config(
            text=f'{self.student_count:02d}'
        )
        self.metrics['served'].config(
            text=f'{self.display_served:02d}'
        )
        self.metrics['waiting'].config(
            text=f'{len(self.display_waiting):02d}'
        )
        self.metrics['away'].config(
            text=f'{self.display_away:02d}'
        )

    def _event_visible(self, event):
        selected = self.filter_var.get()
        kind = event.kind

        groups = {
            'All events': None,
            'TA events': {
                TA_SLEEP, STUDENT_WAKES_TA,
                TA_START, TA_DONE
            },
            'Student events': {
                STUDENT_WAKES_TA,
                STUDENT_WAITS,
                STUDENT_LEAVES,
                TA_START, TA_DONE
            },
            'Waiting': {STUDENT_WAITS},
            'Help sessions': {TA_START, TA_DONE},
            'Turned away': {STUDENT_LEAVES}
        }

        allowed = groups.get(selected)

        if allowed is not None and kind not in allowed:
            return False

        query = self.search_var.get().strip().lower()

        if query:
            content = (
                f'{event.kind} '
                f'{event.student} '
                f'{event.message}'
            ).lower()

            if query not in content:
                return False

        return True

    def _refresh_log(self):
        if not hasattr(self, 'log'):
            return

        self.log.config(state='normal')
        self.log.delete('1.0', 'end')

        for event in self.history[-self.MAX_LOG_ROWS:]:
            if not self._event_visible(event):
                continue

            tag, color, summary = EVENT_META.get(
                event.kind,
                ('EVENT', C.blue, event.kind)
            )

            sid = (
                f'Student #{event.student}'
                if event.student is not None
                else 'System'
            )

            line = (
                f'[{event.t:08.3f}s] '
                f'{tag:<7} '
                f'{sid:<15} '
                f'{event.message}\n'
            )

            self.log.insert('end', line, event.kind)

        self.log.config(state='disabled')
        self.log.see('end')

    def export_csv(self):
        if not self.history:
            messagebox.showinfo(
                'No events',
                'There are no events to export.',
                parent=self.root
            )
            return

        filename = (
            'sleeping_ta_events_'
            + datetime.now().strftime('%Y%m%d_%H%M%S')
            + '.csv'
        )

        path = filedialog.asksaveasfilename(
            parent=self.root,
            title='Export event history',
            defaultextension='.csv',
            initialfile=filename,
            filetypes=[
                ('CSV files', '*.csv'),
                ('All files', '*.*')
            ]
        )

        if not path:
            return

        try:
            with open(
                path, 'w',
                newline='',
                encoding='utf-8-sig'
            ) as file:
                writer = csv.writer(file)
                writer.writerow([
                    'Time',
                    'Event',
                    'Student',
                    'Message',
                    'TA State',
                    'Waiting',
                    'Current',
                    'Served',
                    'Turned Away'
                ])

                for event in self.history:
                    writer.writerow([
                        event.t,
                        event.kind,
                        event.student,
                        event.message,
                        event.ta_state,
                        list(event.waiting),
                        event.current,
                        event.served,
                        event.turned_away
                    ])

            messagebox.showinfo(
                'Export successful',
                f'Events saved to:\n{path}',
                parent=self.root
            )

        except OSError as exc:
            messagebox.showerror(
                'Export failed',
                str(exc),
                parent=self.root
            )

    def _wheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(
                -int(event.delta / 120),
                'units'
            )

    def close(self):
        if self.closed:
            return

        self.closed = True
        self.running = False
        self.stepping = False

        if self.poll_id is not None:
            self.root.after_cancel(self.poll_id)

        if self.frame_id is not None:
            self.root.after_cancel(self.frame_id)

        try:
            self._stop_core()
        finally:
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = Dashboard(root)
    root.mainloop()
