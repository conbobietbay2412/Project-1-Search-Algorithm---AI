import tkinter as tk
from tkinter import ttk
import Search_function as algo
from PIL import Image, ImageTk
import os

from Constants import (
    BG, PANEL, BORDER, ACCENT, ACCENT2, DANGER, WARNING,
    TEXT_PRI, TEXT_SEC, BTN_BG, BTN_HOVER,
    CELL_WALL, CELL_OPEN, CELL_VISITED, CELL_PATH,
    CELL_START, CELL_GOAL, CELL_CURR, CELL_WATER,
    WATER_COST
)
from Map_utils import (
    bfs_path_exists, generate_random_map, validate_positions, get_run_grid
)


# ── Texture loader ─────────────────────────────────────────────────────────────
TEXTURE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_texture(filename, size):
    path = os.path.join(TEXTURE_DIR, filename)
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def _load_texture_tint(filename, size, tint_rgba, alpha=0.55):
    """Load texture and blend a color tint over it (for visited / path states)."""
    path = os.path.join(TEXTURE_DIR, filename)
    try:
        base = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        overlay = Image.new("RGBA", (size, size), tint_rgba)
        blended = Image.blend(base, overlay, alpha)
        return ImageTk.PhotoImage(blended)
    except Exception:
        return None


class SearchVisualizerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Search Visualizer")
        self.root.geometry("1280x760")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.grid       = []
        self.rows       = 15
        self.cols       = 30
        self.cell_size  = 25
        self.running    = False
        self.visited_order = []
        self.path          = []
        self.step_index    = 0

        # Texture cache — rebuilt when cell_size changes
        self._tex_size   = 0
        self._tex        = {}   # key → PhotoImage (must be kept alive)

        self._setup_styles()
        self.create_widgets()
        self.generate_random_map()

    # ── ttk styles ──────────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
            fieldbackground=BTN_BG, background=BTN_BG,
            foreground=TEXT_PRI, bordercolor=BORDER,
            arrowcolor=ACCENT, selectbackground=ACCENT,
            selectforeground=TEXT_PRI, font=("Consolas", 11, "bold"), padding=6)
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", BTN_BG)],
            background=[("readonly", BTN_BG)],
            foreground=[("readonly", TEXT_PRI)])
        style.configure("Small.TCombobox",
            fieldbackground=BTN_BG, background=BTN_BG,
            foreground=TEXT_SEC, bordercolor=BORDER,
            arrowcolor=ACCENT, font=("Consolas", 10), padding=4)
        style.map("Small.TCombobox",
            fieldbackground=[("readonly", BTN_BG)],
            background=[("readonly", BTN_BG)],
            foreground=[("readonly", TEXT_SEC)])

    # ── widget factory ──────────────────────────────────────────────────────────
    def _btn(self, parent, text, command, color=ACCENT, text_color=BG, width=13):
        f = tk.Frame(parent, bg=BG)
        b = tk.Label(f, text=text, bg=color, fg=text_color,
                     font=("Consolas", 9, "bold"), cursor="hand2",
                     width=width, pady=7, relief="flat")
        b.pack(padx=1, pady=1)
        b.bind("<Button-1>", lambda e: command())
        b.bind("<Enter>",    lambda e: b.config(bg=self._lighten(color)))
        b.bind("<Leave>",    lambda e: b.config(bg=color))
        return f

    @staticmethod
    def _lighten(hex_color):
        r = min(255, int(hex_color[1:3], 16) + 22)
        g = min(255, int(hex_color[3:5], 16) + 22)
        b = min(255, int(hex_color[5:7], 16) + 22)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _label(self, parent, text, size=9, color=TEXT_SEC, bold=False):
        weight = "bold" if bold else "normal"
        return tk.Label(parent, text=text, bg=BG,
                        fg=color, font=("Consolas", size, weight))

    def _entry(self, parent, default, width=8):
        e = tk.Entry(parent, width=width, justify="center",
                     font=("Consolas", 11, "bold"),
                     bg=BTN_BG, fg=ACCENT, insertbackground=ACCENT,
                     relief="flat", bd=0,
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT)
        e.insert(0, default)
        return e

    # ── Texture management ──────────────────────────────────────────────────────
    def _rebuild_textures(self, size):
        """(Re)load all textures at the current cell size."""
        if size == self._tex_size:
            return
        self._tex_size = size
        s = size

        self._tex["ground"]       = _load_texture("../images/ground_texture.jpg", s)
        self._tex["wall"]         = _load_texture("../images/wall_texture.jpg",   s)
        self._tex["start"]        = _load_texture("../images/start_texture.jpg",  s)
        self._tex["goal"]         = _load_texture("../images/goal_texture.jpg",   s)
        self._tex["water"]        = _load_texture("../images/water_texture.jpg",  s)

        # Tinted variants for animation states
        self._tex["visited"] = _load_texture_tint(
            "../images/ground_texture.jpg", s, (96, 165, 250, 255), alpha=0.60)   # sky-blue tint
        self._tex["path"]    = _load_texture_tint(
            "../images/ground_texture.jpg", s, (34, 197, 94, 255),  alpha=0.65)   # green tint
        self._tex["current"] = _load_texture_tint(
            "../images/start_texture.jpg",  s, (255, 107, 0,  255), alpha=0.45)   # orange tint

    def _tex_for_cell(self, i, j, start_pos, goal_pos, state="normal"):
        """Return the PhotoImage (or None) to use for cell (i,j) given its state."""
        val = self.grid[i][j]

        # Priority: start/goal always show their icon
        if (i, j) == start_pos:
            return self._tex.get("start")
        if (i, j) == goal_pos:
            return self._tex.get("goal")

        # Animation states
        if state == "visited":
            return self._tex.get("visited")
        if state == "path":
            return self._tex.get("path")
        if state == "current":
            return self._tex.get("current")

        # Static cell type
        if val == 0:
            return self._tex.get("wall")
        if val == WATER_COST:
            return self._tex.get("water")
        return self._tex.get("ground")

    # ── layout ──────────────────────────────────────────────────────────────────
    def create_widgets(self):
        topbar = tk.Frame(self.root, bg=PANEL, height=2)
        topbar.pack(fill=tk.X)

        header = tk.Frame(self.root, bg=BG, pady=14)
        header.pack(fill=tk.X, padx=24)

        title_frame = tk.Frame(header, bg=BG)
        title_frame.pack(side=tk.LEFT)
        tk.Label(title_frame, text="SEARCH",    bg=BG, fg=ACCENT,
                 font=("Consolas", 20, "bold")).pack(side=tk.LEFT)
        tk.Label(title_frame, text=" VISUALIZER", bg=BG, fg=TEXT_PRI,
                 font=("Consolas", 20)).pack(side=tk.LEFT)

        ctrl  = tk.Frame(self.root, bg=PANEL, pady=16)
        ctrl.pack(fill=tk.X)
        inner = tk.Frame(ctrl, bg=PANEL)
        inner.pack(anchor="center")

        # Group 1 — Algorithm
        g1 = tk.Frame(inner, bg=PANEL)
        g1.pack(side=tk.LEFT, padx=24)

        self._label(g1, "ALGORITHM", bold=True, color=TEXT_SEC).pack(anchor="w")
        self.algo_box = ttk.Combobox(
            g1,
            values=["DFS","BFS","UCS","IDDFS","A*","IDA*","Bidirectional","Beam Search"],
            width=22, style="Dark.TCombobox", state="readonly")
        self.algo_box.current(0)
        self.algo_box.pack(pady=(2, 10), ipady=2)

        mode_row = tk.Frame(g1, bg=PANEL)
        mode_row.pack(anchor="w", pady=(0, 10))
        self._label(mode_row, "MODE:", bold=True, color=TEXT_SEC).pack(side=tk.LEFT, padx=(0,6))
        self.weight_var = tk.StringVar(value="weighted")
        for val, txt in [("weighted","Weighted"), ("unweighted","Unweighted")]:
            tk.Radiobutton(mode_row, text=txt, variable=self.weight_var, value=val,
                           bg=PANEL, fg=TEXT_PRI, selectcolor=PANEL,
                           activebackground=PANEL, activeforeground=ACCENT,
                           font=("Consolas", 9), cursor="hand2",
                           command=self.draw_grid).pack(side=tk.LEFT, padx=4)

        pos_row = tk.Frame(g1, bg=PANEL)
        pos_row.pack(anchor="w", pady=(0, 10))
        self._label(pos_row, "START", bold=True, color=ACCENT2).pack(side=tk.LEFT, padx=(0,4))
        self.start_entry = self._entry(pos_row, "0,0")
        self.start_entry.pack(side=tk.LEFT, padx=(0, 12), ipady=2)
        self._label(pos_row, "GOAL", bold=True, color=DANGER).pack(side=tk.LEFT, padx=(0,4))
        self.goal_entry = self._entry(pos_row, "14,29")
        self.goal_entry.pack(side=tk.LEFT, ipady=2)

        spd_row = tk.Frame(g1, bg=PANEL)
        spd_row.pack(fill=tk.X)
        self._label(spd_row, "SPEED", bold=True, color=TEXT_SEC).pack(side=tk.LEFT, padx=(0,8))
        self.speed_scale = tk.Scale(
            spd_row, from_=1, to=100, orient=tk.HORIZONTAL, showvalue=0,
            bg=PANEL, fg=ACCENT, troughcolor=BORDER, highlightthickness=0,
            bd=0, sliderlength=16, width=10, relief="flat", activebackground=ACCENT)
        self.speed_scale.set(50)
        self.speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Frame(inner, width=1, bg=BORDER).pack(side=tk.LEFT, fill=tk.Y, padx=20)

        # Group 2 — Map controls
        g2 = tk.Frame(inner, bg=PANEL)
        g2.pack(side=tk.LEFT, padx=20)
        self._label(g2, "MAP CONTROLS", bold=True, color=TEXT_SEC).pack(anchor="w", pady=(0,8))
        row1 = tk.Frame(g2, bg=PANEL)
        row1.pack()
        self._btn(row1, "UPDATE", self.run_algorithm, color=ACCENT,  text_color=BG).pack(side=tk.LEFT, padx=4, pady=3)
        self._btn(row1, "RESET",  self.reset,         color=BTN_BG,  text_color=TEXT_PRI).pack(side=tk.LEFT, padx=4, pady=3)
        row2 = tk.Frame(g2, bg=PANEL)
        row2.pack(pady=(2,0))
        self._btn(row2, "RANDOM MAP", self.generate_random_map, color=BTN_BG, text_color=TEXT_SEC).pack(side=tk.LEFT, padx=4, pady=3)
        self._label(g2, "GRID SIZE", bold=True, color=TEXT_SEC).pack(anchor="w", pady=(8,2))
        self.size_box = ttk.Combobox(g2, values=["15x30","10x25","5x15","5x5","3x3"],
                                     width=12, style="Small.TCombobox", state="readonly")
        self.size_box.current(0)
        self.size_box.pack(anchor="w")
        self.size_box.bind("<<ComboboxSelected>>", self.change_size)

        tk.Frame(inner, width=1, bg=BORDER).pack(side=tk.LEFT, fill=tk.Y, padx=20)

        # Group 3 — Playback
        g3 = tk.Frame(inner, bg=PANEL)
        g3.pack(side=tk.LEFT, padx=20)
        self._label(g3, "PLAYBACK", bold=True, color=TEXT_SEC).pack(anchor="w", pady=(0,8))
        self._btn(g3, "▶  AUTO RUN",  self.auto_run,  color=ACCENT,  text_color=BG,       width=14).pack(pady=3)
        self._btn(g3, "■  STOP",      self.stop_auto, color=DANGER,  text_color=TEXT_PRI, width=14).pack(pady=3)
        self._btn(g3, "▷  NEXT STEP", self.next_step, color=BTN_BG,  text_color=TEXT_SEC, width=14).pack(pady=3)

        # Status bar
        self.status_bar = tk.Label(
            self.root, text="", font=("Consolas", 9),
            bg="#fff7ed", fg="#92400e", anchor="w", padx=12, pady=5, relief="flat", bd=0)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(self.root, height=1, bg=BORDER).pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(self.root, height=1, bg=BORDER).pack(fill=tk.X)

        # ── Canvas + Stats ──────────────────────────────────────────────────────
        main = tk.Frame(self.root, bg=BG, padx=18, pady=18)
        main.pack(fill=tk.BOTH, expand=True)

        canvas_wrap = tk.Frame(main, bg=ACCENT, bd=0)
        canvas_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,18))
        inner_wrap = tk.Frame(canvas_wrap, bg="#dde3f5", bd=1)
        inner_wrap.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.canvas = tk.Canvas(inner_wrap, bg="#dde3f5", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Stats panel
        stats_frame = tk.Frame(main, width=200, bg=PANEL, bd=0)
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y)
        stats_frame.pack_propagate(False)

        tk.Frame(stats_frame, bg=ACCENT, height=2).pack(fill=tk.X)
        tk.Label(stats_frame, text="STATISTICS", font=("Consolas", 11, "bold"),
                 bg=PANEL, fg=ACCENT, pady=12).pack()
        tk.Frame(stats_frame, bg=BORDER, height=1).pack(fill=tk.X, padx=12)

        self.stats = {}
        for label, key, val_color in [
            ("VISITED",     "visited",     ACCENT),
            ("CURRENT",     "current",     TEXT_PRI),
            ("STEP",        "step",        TEXT_PRI),
            ("PATH LENGTH", "path_length", ACCENT2),
            ("COST",        "cost",        WARNING),
            ("TIME (ms)",   "time",        TEXT_SEC),
        ]:
            row = tk.Frame(stats_frame, bg=PANEL)
            row.pack(fill=tk.X, padx=14, pady=(10, 0))
            tk.Label(row, text=label, font=("Consolas", 8, "bold"),
                     bg=PANEL, fg=TEXT_SEC, anchor="w").pack(fill=tk.X)
            lbl = tk.Label(row, text="—", font=("Consolas", 14, "bold"),
                           bg=PANEL, fg=val_color, anchor="w")
            lbl.pack(fill=tk.X)
            tk.Frame(stats_frame, bg=BORDER, height=1).pack(fill=tk.X, padx=14, pady=(6,0))
            self.stats[key] = lbl

        # Legend
        tk.Frame(stats_frame, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(12,0))
        tk.Label(stats_frame, text="LEGEND", font=("Consolas", 8, "bold"),
                 bg=PANEL, fg=TEXT_SEC, pady=6).pack()
        for color, lbl_txt in [
            (CELL_START,   "Start"),
            (CELL_GOAL,    "Goal"),
            (CELL_VISITED, "Visited"),
            (CELL_CURR,    "Current"),
            (CELL_PATH,    "Path"),
            (CELL_WALL,    "Wall"),
            (CELL_WATER,   f"Water (cost {WATER_COST})"),
        ]:
            lrow = tk.Frame(stats_frame, bg=PANEL)
            lrow.pack(anchor="w", padx=14, pady=1)
            tk.Frame(lrow, bg=color, width=12, height=12).pack(side=tk.LEFT, padx=(0,6))
            tk.Label(lrow, text=lbl_txt, font=("Consolas", 8),
                     bg=PANEL, fg=TEXT_SEC).pack(side=tk.LEFT)

    # ── Grid helpers ────────────────────────────────────────────────────────────
    def _get_run_grid(self):
        return get_run_grid(self.grid, self.weight_var.get())

    def _parse_start_goal(self):
        try:
            sp = tuple(map(int, self.start_entry.get().split(",")))
            gp = tuple(map(int, self.goal_entry.get().split(",")))
            assert 0 <= sp[0] < self.rows and 0 <= sp[1] < self.cols
            assert 0 <= gp[0] < self.rows and 0 <= gp[1] < self.cols
            return sp, gp
        except Exception:
            return None, None

    def _bfs_path_exists(self, grid, start, goal):
        return bfs_path_exists(grid, start, goal, self.rows, self.cols)

    # ── Random map with water river ─────────────────────────────────────────────
    def generate_random_map(self):
        sp, gp = self._parse_start_goal()
        if sp is None:
            sp, gp = (0, 0), (self.rows - 1, self.cols - 1)

        self.grid = generate_random_map(self.rows, self.cols, sp, gp)

        self._show_status("")
        self.draw_grid()

    # ── Validate ────────────────────────────────────────────────────────────────
    def _validate_positions(self, sp, gp):
        return validate_positions(self.grid, sp, gp, self.rows, self.cols)

    # ── Draw ────────────────────────────────────────────────────────────────────
    def draw_grid(self):
        self.canvas.delete("all")
        self.update_cell_size()
        self._rebuild_textures(self.cell_size)

        grid_w   = self.cols * self.cell_size
        grid_h   = self.rows * self.cell_size
        x_offset = max(0, (self.canvas.winfo_width()  - grid_w) // 2)
        y_offset = max(0, (self.canvas.winfo_height() - grid_h) // 2)

        try:
            start_pos = tuple(map(int, self.start_entry.get().split(",")))
            goal_pos  = tuple(map(int, self.goal_entry.get().split(",")))
        except Exception:
            start_pos = goal_pos = None

        unweighted = (self.weight_var.get() == "unweighted")

        for i in range(self.rows):
            for j in range(self.cols):
                x1 = j * self.cell_size + x_offset
                y1 = i * self.cell_size + y_offset
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size

                tex = self._tex_for_cell(i, j, start_pos, goal_pos)

                if tex:
                    self.canvas.create_image(x1, y1, anchor="nw", image=tex,
                                             tags=(f"rect_{i}_{j}", "cell_img"))
                    # thin border
                    self.canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill="", outline="#555555", width=1,
                                                 tags=f"rect_{i}_{j}")
                else:
                    # fallback solid color
                    val = self.grid[i][j]
                    if   (i, j) == start_pos:  color = CELL_START
                    elif (i, j) == goal_pos:   color = CELL_GOAL
                    elif val == 0:             color = CELL_WALL
                    elif val == WATER_COST:    color = CELL_WATER
                    else:                      color = CELL_OPEN
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color,
                                                 outline="#b0bbdd", width=1,
                                                 tags=f"rect_{i}_{j}")

                # Cost label (skip walls and start/goal icons)
                val = self.grid[i][j]
                if val != 0 and (i, j) != start_pos and (i, j) != goal_pos:
                    if unweighted:
                        label = "1" if val == WATER_COST else "1"
                    else:
                        label = str(val)
                    is_water = (val == WATER_COST)
                    txt_color = "#ffffff" if is_water else "#1e2a4a"
                    txt_font  = ("Consolas", max(6, self.cell_size // 4), "bold") if is_water \
                                else ("Consolas", max(7, self.cell_size // 3))
                    self.canvas.create_text(
                        x1 + self.cell_size // 2, y1 + self.cell_size // 2,
                        text=label, font=txt_font, fill=txt_color,
                        tags=f"text_{i}_{j}")

    def _show_status(self, msg, is_error=False):
        if not msg:
            self.status_bar.config(text="", bg="#f0f4ff")
        elif is_error:
            self.status_bar.config(text=msg, bg="#fff1f0", fg="#b91c1c")
        else:
            self.status_bar.config(text=msg, bg="#fffbeb", fg="#92400e")

    # ── Algorithm ───────────────────────────────────────────────────────────────
    def run_algorithm(self):
        self.running    = False
        self.step_index = 0
        self.visited_order = []
        self.path          = []

        sp, gp = self._parse_start_goal()
        err = self._validate_positions(sp, gp)
        if err:
            self._show_status(err, is_error=True)
            return
        self._show_status("")

        algo_name = self.algo_box.get()
        run_grid  = self._get_run_grid()

        dispatch = {
            "DFS"          : lambda: algo.dfs(run_grid, sp, gp),
            "BFS"          : lambda: algo.bfs(run_grid, sp, gp),
            "UCS"          : lambda: algo.ucs(run_grid, sp, gp),
            "IDDFS"        : lambda: algo.iddfs(run_grid, sp, gp),
            "A*"           : lambda: algo.astar(run_grid, *sp, *gp),
            "IDA*"         : lambda: algo.idastar(run_grid, *sp, *gp),
            "Bidirectional": lambda: algo.bidirectional(run_grid, sp, gp),
            "Beam Search"  : lambda: algo.beam_search(run_grid, sp, gp),
        }

        result = dispatch[algo_name]()
        self.visited_order = result["visited_order"]
        self.path          = result["path"]

        self.stats["path_length"].config(text=str(result["path_length"]))
        self.stats["cost"].config(text=str(result["path_cost"]))
        self.stats["time"].config(text=str(result["time_ms"]))
        self.stats["visited"].config(text=str(result["nodes_explored"]))
        self.step_index = 0

    # ── Animation ───────────────────────────────────────────────────────────────
    def auto_run(self):
        if self.running:
            return
        if not self.visited_order:
            self.run_algorithm()
        self.running = True
        self.run_step_loop()

    def _draw_cell_state(self, node, state):
        """Redraw a single cell with a given state: normal/visited/path/current."""
        r, c = node
        try:
            start_pos = tuple(map(int, self.start_entry.get().split(",")))
            goal_pos  = tuple(map(int, self.goal_entry.get().split(",")))
        except Exception:
            start_pos = goal_pos = None

        # Compute position
        grid_w   = self.cols * self.cell_size
        grid_h   = self.rows * self.cell_size
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x_offset = max(0, (cw - grid_w) // 2)
        y_offset = max(0, (ch - grid_h) // 2)

        x1 = c * self.cell_size + x_offset
        y1 = r * self.cell_size + y_offset
        x2, y2 = x1 + self.cell_size, y1 + self.cell_size

        # Don't overwrite start/goal
        if node == start_pos or node == goal_pos:
            return

        tex = self._tex_for_cell(r, c, start_pos, goal_pos, state)

        self.canvas.delete(f"rect_{r}_{c}")
        self.canvas.delete(f"text_{r}_{c}")

        if tex:
            self.canvas.create_image(x1, y1, anchor="nw", image=tex,
                                     tags=f"rect_{r}_{c}")
            self.canvas.create_rectangle(x1, y1, x2, y2,
                                         fill="", outline="#555555", width=1,
                                         tags=f"rect_{r}_{c}")
        else:
            color_map = {"visited": CELL_VISITED, "path": CELL_PATH,
                         "current": CELL_CURR, "normal": CELL_OPEN}
            color = color_map.get(state, CELL_OPEN)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color,
                                         outline="#b0bbdd", width=1,
                                         tags=f"rect_{r}_{c}")

        # Redraw cost label
        val = self.grid[r][c]
        if val != 0:
            unweighted = (self.weight_var.get() == "unweighted")
            if unweighted:
                label = "1" if val == WATER_COST else "1"
            else:
                label = str(val)
            is_water = (val == WATER_COST)
            txt_color = "#ffffff" if (is_water or state in ("visited","current","path")) else "#1e2a4a"
            self.canvas.create_text(
                x1 + self.cell_size // 2, y1 + self.cell_size // 2,
                text=label,
                font=("Consolas", max(7, self.cell_size // 3)),
                fill=txt_color, tags=f"text_{r}_{c}")

    def _highlight_current(self, node):
        self._draw_cell_state(node, "current")

    def _unhighlight_current(self, node):
        if node is None:
            return
        self._draw_cell_state(node, "visited")

    def run_step_loop(self):
        if not self.running:
            return
        if self.step_index < len(self.visited_order):
            if self.step_index > 0:
                self._unhighlight_current(self.visited_order[self.step_index - 1])
            node = self.visited_order[self.step_index]
            self._draw_cell_state(node, "visited")
            self._highlight_current(node)
            self.stats["step"].config(text=str(self.step_index + 1))
            self.stats["current"].config(text=f"{node[0]},{node[1]}")
            self.step_index += 1
            speed = self.speed_scale.get()
            delay = max(1, 200 - speed * 2)
            self.root.after(delay, self.run_step_loop)
        else:
            if self.visited_order:
                self._unhighlight_current(self.visited_order[-1])
            for node in self.path:
                self._draw_cell_state(node, "path")
            self.running = False

    def stop_auto(self):
        self.running = False

    def next_step(self):
        if self.step_index < len(self.visited_order):
            if self.step_index > 0:
                self._unhighlight_current(self.visited_order[self.step_index - 1])
            node = self.visited_order[self.step_index]
            self._draw_cell_state(node, "visited")
            self._highlight_current(node)
            self.stats["step"].config(text=str(self.step_index + 1))
            self.stats["current"].config(text=f"{node[0]},{node[1]}")
            self.step_index += 1
        else:
            if self.visited_order:
                self._unhighlight_current(self.visited_order[-1])
            for node in self.path:
                self._draw_cell_state(node, "path")

    def color_cell(self, node, color):
        """Legacy shim — map flat colors to texture states."""
        state_map = {
            CELL_VISITED: "visited",
            CELL_PATH:    "path",
            CELL_CURR:    "current",
        }
        self._draw_cell_state(node, state_map.get(color, "normal"))

    # ── Reset / Size ────────────────────────────────────────────────────────────
    def reset(self):
        self.running       = False
        self.step_index    = 0
        self.visited_order = []
        self.path          = []
        self.draw_grid()
        for key in self.stats:
            self.stats[key].config(text="—")

    def update_cell_size(self):
        self.canvas.update()
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        sw  = (c_w - 20) // self.cols
        sh  = (c_h - 20) // self.rows
        self.cell_size = max(10, min(sw, sh, 60))
        # print(self.cell_size)

    def change_size(self, event=None):
        sel = self.size_box.get()
        if   sel == "15x30": self.rows, self.cols = 15, 30
        elif sel == "10x25": self.rows, self.cols = 10, 25
        elif sel == "5x15":  self.rows, self.cols =  5, 15
        elif sel == "5x5":   self.rows, self.cols =  5,  5
        elif sel == "3x3": self.rows, self.cols = 3, 3

        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, "0,0")
        self.goal_entry.delete(0, tk.END)
        self.goal_entry.insert(0, f"{self.rows-1},{self.cols-1}")

        self.running    = False
        self.step_index = 0
        self._tex_size  = 0   # force texture reload at new size
        self.generate_random_map()


if __name__ == "__main__":
    root = tk.Tk()
    app  = SearchVisualizerUI(root)
    root.mainloop()