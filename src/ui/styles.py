from tkinter import ttk

def apply_styles(root):
    style = ttk.Style(root)

    # Usar 'clam' para que ttk respete fieldbackground en Windows
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
    style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))

    # =========================
    # Combobox con fondo blanco
    # =========================
    style.configure(
        "White.TCombobox",
        fieldbackground="white",  # fondo del campo
        background="white",
        foreground="black",
        padding=3
    )

    style.map(
        "White.TCombobox",
        fieldbackground=[("readonly", "white"), ("!disabled", "white")],
        foreground=[("readonly", "black"), ("!disabled", "black")],
        background=[("readonly", "white"), ("!disabled", "white")]
    )
