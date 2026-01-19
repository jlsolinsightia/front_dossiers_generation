from tkinter import ttk


def apply_styles(root):
    style = ttk.Style(root)

    # Selección de tema
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
    style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
