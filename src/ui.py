import tkinter as tk
from tkinter import messagebox

class UIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Тохиргооны Самбар ба Удирдлага (UI Panel)")
        self.root.geometry("650x500")
        self.root.resizable(False, False)
        
        # Анимейшн болон алхамын төлөв хувьсагчид
        self.is_running = False
        self.current_step = 0
        self.animation_delay = 500  # милисекунд
        
        self.create_widgets()

    def create_widgets(self):
        # 1. Тохиргооны самбар (4 оролт)
        input_frame = tk.LabelFrame(self.root, text=" Тохиргооны Самбар (4 Оролт) ", font=("Arial", 11, "bold"), padx=15, pady=15)
        input_frame.pack(fill="x", padx=15, pady=15)
        
        self.entries = []
        labels = ["Оролт 1:", "Оролт 2:", "Оролт 3:", "Оролт 4:"]
        
        for i, text in enumerate(labels):
            lbl = tk.Label(input_frame, text=text, font=("Arial", 10))
            lbl.grid(row=i, column=0, sticky="w", pady=6)
            
            ent = tk.Entry(input_frame, width=35, font=("Arial", 10))
            ent.grid(row=i, column=1, padx=10, pady=6)
            self.entries.append(ent)
            
        # 2. Validation / Status Мессеж харуулах хэсэг
        self.status_lbl = tk.Label(self.root, text="Төлөв: Өгөгдлөө оруулж Start эсвэл Step дарна уу.", fg="blue", font=("Arial", 10, "italic"))
        self.status_lbl.pack(anchor="w", padx=20, pady=5)

        # 3. Удирдлагын товчнууд (Start / Pause / Step / Reset)
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack()
        
        self.btn_start = tk.Button(btn_frame, text="▶ Start", width=12, bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=self.start_animation)
        self.btn_start.grid(row=0, column=0, padx=8)
        
        self.btn_pause = tk.Button(btn_frame, text="⏸ Pause", width=12, bg="#ffc107", fg="black", font=("Arial", 10, "bold"), command=self.pause_animation)
        self.btn_pause.grid(row=0, column=1, padx=8)
        
        self.btn_step = tk.Button(btn_frame, text="⏭ Step", width=12, bg="#007bff", fg="white", font=("Arial", 10, "bold"), command=self.step_forward)
        self.btn_step.grid(row=0, column=2, padx=8)
        
        self.btn_reset = tk.Button(btn_frame, text="🔄 Reset", width=12, bg="#dc3545", fg="white", font=("Arial", 10, "bold"), command=self.reset_system)
        self.btn_reset.grid(row=0, column=3, padx=8)

        # 4. Step / Animation Дүрслэлийн Урьдчилсан Харагдац (Preview Area)
        preview_frame = tk.LabelFrame(self.root, text=" Урьдчилсан Харагдац (Preview & Simulation) ", font=("Arial", 11, "bold"), padx=10, pady=10)
        preview_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.canvas = tk.Canvas(preview_frame, bg="white", height=120)
        self.canvas.pack(fill="both", expand=True)
        
        self.draw_preview_initial()

    def validate_inputs(self):
        """Оролтын утгуудыг шалгах (Validation) логик"""
        values = []
        for i, ent in enumerate(self.entries):
            val = ent.get().strip()
            if not val:
                error_msg = f"Алдаа: {i+1}-р оролт хоосон байна!"
                self.status_lbl.config(text=error_msg, fg="red")
                messagebox.showerror("Баталгаажуулалтын Алдаа", error_msg)
                return None
            values.append(val)
        
        self.status_lbl.config(text="Баталгаажилт амжилттай боллоо.", fg="green")
        return values

    def start_animation(self):
        """Start горим - Автомат хөдөлгөөнт дүрслэл эхлүүлэх"""
        values = self.validate_inputs()
        if values is None:
            return
        if not self.is_running:
            self.is_running = True
            self.status_lbl.config(text="Статус: Ажиллаж байна (Animation Running)...", fg="green")
            self.animate_loop()

    def pause_animation(self):
        """Pause горим - Түр зогсоох"""
        self.is_running = False
        self.status_lbl.config(text="Статус: Түр зогслоо (Paused).", fg="orange")

    def step_forward(self):
        """Step горим - Нэг алхмаар урагшлах"""
        values = self.validate_inputs()
        if values is None:
            return
        self.is_running = False
        self.current_step += 1
        self.status_lbl.config(text=f"Статус: Алхам {self.current_step} хийгдлээ.", fg="blue")
        self.update_preview_graphics()

    def reset_system(self):
        """Reset горим - Анхны байдалд нь оруулах"""
        self.is_running = False
        self.current_step = 0
        for ent in self.entries:
            ent.delete(0, tk.END)
        self.status_lbl.config(text="Систем анхны төлөвтөө шилжлээ.", fg="gray")
        self.draw_preview_initial()

    def animate_loop(self):
        """Анимейшн давталтын логик"""
        if self.is_running:
            self.current_step += 1
            self.status_lbl.config(text=f"Ажиллаж байна... Алхам: {self.current_step}", fg="green")
            self.update_preview_graphics()
            self.root.after(self.animation_delay, self.animate_loop)

    def draw_preview_initial(self):
        """Анхны харагдац зурах"""
        self.canvas.delete("all")
        self.canvas.create_text(300, 50, text="Урьдчилсан харагдац бэлэн байна", font=("Arial", 11, "bold"), fill="#666")

    def update_preview_graphics(self):
        """Алхам бүрт харагдацыг шинэчлэх"""
        self.canvas.delete("all")
        # Жишээ дүрслэл (Canvas дээр тухайн алхамын төлвийг харуулах хэсэг)
        self.canvas.create_text(300, 30, text=f"Гүйцэтгэлийн явц - Одоогийн алхам: {self.current_step}", font=("Arial", 10, "bold"), fill="#003366")
        
        # Динамик хөдөлгөөнт элемент жишээ
        x_pos = (self.current_step * 25) % 550 + 25
        self.canvas.create_rectangle(x_pos, 50, x_pos + 40, 90, fill="#17a2b8", outline="#0056b3", width=2)
        self.canvas.create_text(x_pos + 20, 70, text=str(self.current_step), font=("Arial", 10, "bold"), fill="white")

if __name__ == "__main__":
    root = tk.Tk()
    app = UIApp(root)
    root.mainloop()