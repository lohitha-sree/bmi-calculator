import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import sqlite3
import csv
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ---------------- DATABASE ----------------
DB_FILE = "bmi_data.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bmi_records(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            weight REAL,
            height REAL,
            bmi REAL,
            category TEXT,
            date TEXT
        )""")
        conn.commit()

# ---------------- BMI LOGIC ----------------
def calculate_bmi(weight, height_cm):
    h_m = height_cm / 100
    bmi = weight / (h_m ** 2)

    if bmi < 18.5:
        cat = "Underweight"
    elif bmi < 25:
        cat = "Normal"
    elif bmi < 30:
        cat = "Overweight"
    else:
        cat = "Obese"

    return round(bmi, 2), cat

def ideal_weight(height_cm):
    h_m = height_cm / 100
    return round(18.5 * h_m * h_m, 1), round(24.9 * h_m * h_m, 1)

# ---------------- APP ----------------
class BMIEntryApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("BMI Calculator")
        self.geometry("1100x650")
        ctk.set_appearance_mode("Dark")

        init_db()

        self.user_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.weight_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Enter height and weight")

        self.build_ui()

    # ---------------- UI ----------------
    def build_ui(self):

        # LEFT PANEL
        self.left = ctk.CTkFrame(self, width=260)
        self.left.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(
            self.left, text="BMI INPUT",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=20)

        # USER
        self.user_combo = ctk.CTkComboBox(
            self.left,
            values=self.get_users(),
            variable=self.user_var
        )
        self.user_combo.pack(pady=10)

        ctk.CTkButton(
            self.left, text="Add User",
            command=self.add_user
        ).pack(pady=5)

        # WEIGHT INPUT
        ctk.CTkLabel(self.left, text="Weight (kg)").pack(pady=(20, 5))
        self.weight_entry = ctk.CTkEntry(
            self.left, textvariable=self.weight_var
        )
        self.weight_entry.pack(padx=20)

        self.weight_display = ctk.CTkLabel(
            self.left, text="Entered: -- kg"
        )
        self.weight_display.pack(pady=5)

        # HEIGHT INPUT
        ctk.CTkLabel(self.left, text="Height (cm)").pack(pady=(20, 5))
        self.height_entry = ctk.CTkEntry(
            self.left, textvariable=self.height_var
        )
        self.height_entry.pack(padx=20)

        self.height_display = ctk.CTkLabel(
            self.left, text="Entered: -- cm"
        )
        self.height_display.pack(pady=5)

        # REAL-TIME UPDATE
        self.weight_var.trace_add("write", self.update_display)
        self.height_var.trace_add("write", self.update_display)

        ctk.CTkButton(
            self.left, text="Calculate BMI",
            command=self.calculate
        ).pack(pady=25)

        ctk.CTkButton(
            self.left, text="Export CSV",
            command=self.export_csv
        ).pack(pady=5)

        # DARK MODE TOGGLE
        self.theme_switch = ctk.CTkSwitch(
            self.left, text="Dark Mode",
            command=self.toggle_theme
        )
        self.theme_switch.select()
        self.theme_switch.pack(pady=15)

        # RIGHT DASHBOARD
        self.main = ctk.CTkFrame(self)
        self.main.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.bmi_label = ctk.CTkLabel(
            self.main, text="BMI: --",
            font=("Segoe UI", 34, "bold")
        )
        self.bmi_label.pack(pady=20)

        self.info_label = ctk.CTkLabel(
            self.main, text="Ideal Weight: --",
            font=("Segoe UI", 16)
        )
        self.info_label.pack()

        self.chart_frame = ctk.CTkFrame(self.main)
        self.chart_frame.pack(fill="both", expand=True, pady=10)

        self.init_chart()

        # STATUS BAR
        self.status = ctk.CTkLabel(
            self, textvariable=self.status_var, anchor="w"
        )
        self.status.pack(side="bottom", fill="x")

    # ---------------- REAL-TIME DISPLAY ----------------
    def update_display(self, *args):
        if self.weight_var.get():
            self.weight_display.configure(
                text=f"Entered: {self.weight_var.get()} kg"
            )
        if self.height_var.get():
            self.height_display.configure(
                text=f"Entered: {self.height_var.get()} cm"
            )

    # ---------------- CALCULATE ----------------
    def calculate(self):
        try:
            user = self.user_var.get()
            if not user:
                raise ValueError("Select a user")

            weight = float(self.weight_var.get())
            height = float(self.height_var.get())

            if weight <= 0 or height <= 0:
                raise ValueError

            bmi, cat = calculate_bmi(weight, height)
            low, high = ideal_weight(height)

            self.bmi_label.configure(
                text=f"{bmi} ({cat})",
                text_color=self.color(cat)
            )

            self.info_label.configure(
                text=f"Ideal Weight Range: {low} – {high} kg"
            )

            self.save_data(user, weight, height, bmi, cat)
            self.update_chart(user)

            self.status_var.set(
                f"Last calculated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        except ValueError:
            messagebox.showerror(
                "Input Error",
                "Please enter valid numeric values for height and weight"
            )

    # ---------------- DATABASE ----------------
    def get_users(self):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM users")
            return [r[0] for r in cur.fetchall()]

    def add_user(self):
        name = tk.simpledialog.askstring("User", "Enter user name")
        if not name:
            return
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO users(name) VALUES (?)", (name,))
            self.user_combo.configure(values=self.get_users())
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "User already exists")

    def save_data(self, user, w, h, bmi, cat):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE name=?", (user,))
            uid = cur.fetchone()[0]
            cur.execute("""
            INSERT INTO bmi_records(user_id, weight, height, bmi, category, date)
            VALUES (?,?,?,?,?,?)
            """, (uid, w, h, bmi, cat, datetime.now().isoformat()))
            conn.commit()

    # ---------------- CHART ----------------
    def init_chart(self):
        self.fig = Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("BMI Trend")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def update_chart(self, user):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT bmi, date FROM bmi_records
            WHERE user_id=(SELECT id FROM users WHERE name=?)
            ORDER BY date
            """, (user,))
            data = cur.fetchall()

        self.ax.clear()
        self.ax.plot(
            [d[1] for d in data],
            [d[0] for d in data],
            marker="o"
        )
        self.ax.axhline(18.5, color="blue", linestyle="--")
        self.ax.axhline(25, color="green", linestyle="--")
        self.ax.axhline(30, color="red", linestyle="--")
        self.ax.set_title("BMI Trend")
        self.canvas.draw()

    # ---------------- EXPORT ----------------
    def export_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file:
            return
        with sqlite3.connect(DB_FILE) as conn, open(file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["UserID", "Weight", "Height", "BMI", "Category", "Date"]
            )
            for row in conn.execute("SELECT * FROM bmi_records"):
                writer.writerow(row)
        messagebox.showinfo("Export", "CSV exported successfully")

    # ---------------- UTIL ----------------
    def toggle_theme(self):
        ctk.set_appearance_mode(
            "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        )

    def color(self, cat):
        return {
            "Underweight": "skyblue",
            "Normal": "green",
            "Overweight": "orange",
            "Obese": "red"
        }[cat]


# ---------------- RUN ----------------
if __name__ == "__main__":
    app = BMIEntryApp()
    app.mainloop()