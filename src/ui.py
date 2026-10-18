import tkinter as tk
from tkinter import messagebox, scrolledtext

class UIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Оюутан & TA Удирдлагын Систем (UI Panel)")
        self.root.geometry("800x650")
        self.root.minsize(750, 600)
        
        # Системийн төлөв хувьсагчид
        self.is_running = False
        self.current_step = 0
        self.animation_delay = 600  # милисекунд
        
        self.create_widgets()

    def create_widgets(self):
        # Үндсэн контейнер frame-үүд
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=15, pady=10)

        # 1. Тохиргооны самбар (4 оролт)
        input_frame = tk.LabelFrame(top_frame, text=" Тохиргооны Самбар (4 Оролт) ", font=("Arial", 10, "bold"), padx=10, pady=10)
        input_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.entries = {}
        labels_keys = [
            ("param1", "Оюутны тоо:"),
            ("param2", "TA-гийн тоо:"),
            ("param3", "Сандлын тоо:"),
            ("param4", "Хурд (ms):")
        ]
        defaults = ["10", "2", "5", "500"]
        
        for i, (key, text) in enumerate(labels_keys):
            lbl = tk.Label(input_frame, text=text, font=("Arial", 9))
            lbl.grid(row=i, column=0, sticky="w", pady=4)
            
            ent = tk.Entry(input_frame, width=15, font=("Arial", 9))
            ent.insert(0, defaults[i])
            ent.grid(row=i, column=1, padx=5, pady=4)
            self.entries[key] = ent

        # 2. Удирдлагын товчнууд болон Status
        control_frame = tk.LabelFrame(top_frame, text=" Удирдлага & Төлөв ", font=("Arial", 10, "bold"), padx=10, pady=10)
        control_frame.pack(side="right", fill="both", expand=True)

        btn_grid_frame = tk.Frame(control_frame)
        btn_grid_frame.pack(fill="x", pady=5)
        
        self.btn_start = tk.Button(btn_grid_frame, text="▶ Start", width=10, bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=self.start_animation)
        self.btn_start.grid(row=0, column=0, padx=4, pady=2)
        
        self.btn_pause = tk.Button(btn_grid_frame, text="⏸ Pause", width=10, bg="#ffc107", fg="black", font=("Arial", 9, "bold"), command=self.pause_animation)
        self.btn_pause.grid(row=0, column=1, padx=4, pady=2)
        
        self.btn_step = tk.Button(btn_grid_frame, text="⏭ Step", width=10, bg="#007bff", fg="white", font=("Arial", 9, "bold"), command=self.step_forward)
        self.btn_step.grid(row=1, column=0, padx=4, pady=2)
        
        self.btn_reset = tk.Button(btn_grid_frame, text="🔄 Reset", width=10, bg="#dc3545", fg="white", font=("Arial", 9, "bold"), command=self.reset_system)
        self.btn_reset.grid(row=1, column=1, padx=4, pady=2)

        self.status_lbl = tk.Label(control_frame, text="Төлөв: Бэлэн байна.", fg="blue", font=("Arial", 9, "italic"), anchor="w")
        self.status_lbl.pack(fill="x", pady=(5, 0))

        # 3. Визуализацийн хэсэг (Canvas: Сандал, TA, Оюутны дүрслэл)
        vis_frame = tk.LabelFrame(self.root, text=" Визуализаци (Simulation View & Legend) ", font=("Arial", 10, "bold"), padx=10, pady=10)
        vis_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Legend (Тайлбар) хэсэг
        legend_frame = tk.Frame(vis_frame)
        legend_frame.pack(fill="x", pady=(0, 5))
        
        legends = [("TA (Багш)", "#dc3545"), ("Сандал", "#6c757d"), ("Оюутан (Хүлээж буй)", "#ffc107"), ("Оюутан (Үйлчлүүлж буй)", "#28a745")]
        for text, color in legends:
            indicator = tk.Canvas(legend_frame, width=12, height=12, highlightthickness=0)
            indicator.pack(side="left", padx=(10, 2))
            indicator.create_oval(1, 1, 11, 11, fill=color, outline="")
            lbl = tk.Label(legend_frame, text=text, font=("Arial", 8))
            lbl.pack(side="left", padx=(0, 10))

        # Canvas талбар
        self.canvas = tk.Canvas(vis_frame, bg="white", height=200, highlightthickness=1, highlightbackground="#ccc")
        self.canvas.pack(fill="both", expand=True)

        # 4. Event Log (Үйл явдлын лог)
        log_frame = tk.LabelFrame(self.root, text=" Event Log (Үйл явдлын бүртгэл) ", font=("Arial", 10, "bold"), padx=10, pady=5)
        log_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=5, font=("Consolas", 8), bg="#f8f9fa")
        self.log_area.pack(fill="both", expand=True)
        self.log_message("Систем амжилттай аслаа. Тохиргоогоо хийгээд Start дарна уу.")

        self.draw_initial_scene()

    def log_message(self, message):
        """Event log хэсэгт мэдээлэл нэмэх"""
        self.log_area.insert(tk.END, f"[Алхам {self.current_step}] {message}\n")
        self.log_area.see(tk.END)

    def validate_inputs(self):
        """4 оролтын утгыг шалгах (Validation)"""
        values = {}
        for key, ent in self.entries.items():
            val = ent.get().strip()
            if not val:
                msg = f"Алдаа: '{key}' утга хоосон байна!"
                self.status_lbl.config(text=msg, fg="red")
                messagebox.showerror("Баталгаажуулалтын Алдаа", msg)
                return None
            try:
                num = int(val)
                if num < 0:
                    raise ValueError
                values[key] = num
            except ValueError:
                msg = f"Алдаа: '{key}' зөвхөн эерэг бүхэл тоо байх ёстой!"
                self.status_lbl.config(text=msg, fg="red")
                messagebox.showerror("Баталгаажуулалтын Алдаа", msg)
                return None
                
        self.status_lbl.config(text="Баталгаажилт амжилттай.", fg="green")
        return values

    def start_animation(self):
        """Start горим - Автомат хөдөлгөөнт дүрслэл эхлүүлэх"""
        vals = self.validate_inputs()
        if not vals:
            return
        if not self.is_running:
            self.is_running = True
            self.status_lbl.config(text="Статус: Ажиллаж байна...", fg="green")
            self.log_message("Симулятор ажиллаж эхэллээ.")
            self.animate_loop()

    def pause_animation(self):
        """Pause горим - Түр зогсоох"""
        self.is_running = False
        self.status_lbl.config(text="Статус: Түр зогслоо (Paused).", fg="orange")
        self.log_message("Симулятор түр зогссон.")

    def step_forward(self):
        """Step горим - Нэг алхмаар урагшлах"""
        vals = self.validate_inputs()
        if not vals:
            return
        self.is_running = False
        self.current_step += 1
        self.status_lbl.config(text=f"Статус: Алхам {self.current_step} хийгдлээ.", fg="blue")
        self.log_message(f"Гарын авлагын алхам {self.current_step} амжилттай хийгдлээ.")
        self.update_simulation_graphics()

    def reset_system(self):
        """Reset горим - Анхны байдалд оруулах"""
        self.is_running = False
        self.current_step = 0
        self.status_lbl.config(text="Систем анхны төлөвтөө шилжлээ.", fg="gray")
        self.log_message("Систем анхны байдалд орлоо.")
        self.draw_initial_scene()

    def animate_loop(self):
        """root.after ашигласан анимейшн давталтын логик"""
        if self.is_running:
            self.current_step += 1
            self.update_simulation_graphics()
            self.root.after(self.animation_delay, self.animate_loop)

    def draw_initial_scene(self):
        """Анхны хоосон эсвэл суурь дүрсийг Canvas дээр зурах"""
        self.canvas.delete("all")
        self.canvas.create_text(380, 90, text="Симуляцийн дүрслэл (Сандал, TA, Оюутнууд)", font=("Arial", 11, "bold"), fill="#888")

    def update_simulation_graphics(self):
        """Алхам бүрт сандал, TA, оюутнуудын байрлалыг шинэчлэн зурах"""
        self.canvas.delete("all")
        
        # TA (Багш/Туслах) дүрслэх
        self.canvas.create_rectangle(50, 80, 110, 140, fill="#dc3545", outline="#a71d2a", width=2)
        self.canvas.create_text(80, 110, text="TA", font=("Arial", 10, "bold"), fill="white")

        # Сандлууд зурах (Жишээ байдлаар динамикаар гаргах)
        chair_count = 5
        try:
            chair_count = int(self.entries["param3"].get())
        except:
            pass

        start_x = 180
        for i in range(min(chair_count, 8)):
            cx = start_x + (i * 65)
            cy = 100
            # Сандлын суурь
            self.canvas.create_rectangle(cx, cy, cx + 45, cy + 45, fill="#6c757d", outline="#343a40", width=2)
            self.canvas.create_text(cx + 22.5, cy + 22.5, text=f"С{i+1}", font=("Arial", 9, "bold"), fill="white")

        # Оюутнуудын динамик хөдөлгөөн/байрлал
        student_offset = (self.current_step * 15) % 350
        sx = 180 + student_offset
        sy = 30
        self.canvas.create_oval(sx, sy, sx + 30, sy + 30, fill="#28a745" if (self.current_step % 2 == 0) else "#ffc107", outline="")
        self.canvas.create_text(sx + 15, sy + 15, text=f"O{self.current_step}", font=("Arial", 8, "bold"), fill="black")
        
        self.log_message(f"Алхам {self.current_step}-н график шинэчлэгдлээ.")

if __name__ == "__main__":
    root = tk.Tk()
    app = UIApp(root)
    root.mainloop()
