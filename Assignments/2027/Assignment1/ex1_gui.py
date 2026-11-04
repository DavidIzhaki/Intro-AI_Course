"""Runs your ex1.py on a problem and plays the plan it returns.

    python ex1_gui.py          start with p1
    python ex1_gui.py x3       start with x3

Choose a problem and press Solve. Then play the plan, step through it, or click any action in the list.
The drawing is explained at the top of ex1_maker.py.
"""
import math
import multiprocessing
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

import ex1_check
from ex1_maker import MapView, fit_on_screen, problem_names

FRAME_MS = 30
SPEEDS = {"slow": 1200, "normal": 600, "fast": 250, "very fast": 90}   # milliseconds for one action
TRACEBACK_LINES = 6     # the part of a crash to show; the terminal gets all of it
RED, BLACK = "#b00020", "#222222"


class Player(tk.Tk):
    def __init__(self, start):
        super().__init__()
        self.title("Island Logistics: plan player")
        self.states, self.plan, self.step, self.playing = [], [], 0, False
        self.game = self.optimal = self.timer = self.solver = None
        self.build_top()
        self.build_side()       # before the map, so that a small window takes its room from the map
        self.view = MapView(self)
        self.view.pack(side="left", fill="both", expand=True)
        self.choose(start)
        fit_on_screen(self)

    def build_top(self):
        top = ttk.Frame(self, padding=6)
        top.pack(side="top", fill="x")
        self.choice = ttk.Combobox(top, values=problem_names(), state="readonly", width=14)
        self.choice.pack(side="left")
        self.choice.bind("<<ComboboxSelected>>", lambda event: self.choose(self.choice.get().split()[0]))
        self.solve_button = ttk.Button(top, text="Solve", command=self.solve)
        self.solve_button.pack(side="left", padx=6)
        ttk.Label(top, text="Time limit (s):").pack(side="left")
        self.limit = tk.StringVar(value=str(ex1_check.TIME_LIMIT))
        ttk.Entry(top, textvariable=self.limit, width=5).pack(side="left", padx=(2, 10))
        self.status = ttk.Label(self, padding=(6, 0, 6, 4), justify="left")
        self.status.pack(side="top", fill="x")
        self.status.bind("<Configure>", lambda event: self.status.configure(wraplength=event.width - 12))

    def build_side(self):
        side = ttk.Frame(self, padding=6)
        side.pack(side="right", fill="y")
        buttons = ttk.Frame(side)
        buttons.pack(fill="x")
        for text, command in (("|<", self.first), ("<", self.back), ("Play", self.toggle), (">", self.forward), (">|", self.last)):
            button = ttk.Button(buttons, text=text, width=5, command=command)
            button.pack(side="left")
            if text == "Play":
                self.play_button = button
        self.speed = ttk.Combobox(side, values=list(SPEEDS), state="readonly", width=12)
        self.speed.set("normal")
        self.speed.pack(fill="x", pady=4)
        self.progress = ttk.Label(side, text="")
        self.progress.pack(fill="x")
        frame = ttk.Frame(side)
        frame.pack(fill="both", expand=True)
        bar = ttk.Scrollbar(frame)
        bar.pack(side="right", fill="y")
        self.actions = tk.Listbox(frame, width=26, yscrollcommand=bar.set, exportselection=False, font="TkFixedFont")
        self.actions.pack(side="left", fill="both", expand=True)
        bar.configure(command=self.actions.yview)
        self.actions.bind("<<ListboxSelect>>", self.clicked)

    def say(self, text, color=BLACK):
        self.status.configure(text=text, foreground=color)

    def choose(self, name):
        self.cancel()
        _, self.game, self.optimal = ex1_check.find_problem(name)
        self.choice.set(next(n for n in problem_names() if n.split()[0] == name))
        self.say(f"Optimal cost {self.optimal}. Press Solve to run your ex1.py.")
        self.view.set_game(self.game)
        self.set_plan([])

    def set_plan(self, plan):
        """Replays the plan by the rules in ex1_check, keeping a state for each step up to any illegal action."""
        self.stop()
        world = ex1_check.World(self.game)
        self.states, self.plan = [world.snapshot()], []
        self.actions.delete(0, "end")
        self.actions.insert("end", "start")
        for action in plan:
            try:
                world.apply(action)
            except ex1_check.IllegalAction:
                self.actions.insert("end", f"{action}  ILLEGAL")
                self.actions.itemconfigure("end", foreground=RED)
                break
            self.plan.append(action)
            self.states.append(world.snapshot())
            self.actions.insert("end", action)
        self.go_to(0)

    def solve(self):
        try:
            limit = float(self.limit.get())
        except ValueError:
            limit = 0
        if not 0 < limit < math.inf:
            self.say("The time limit must be a positive number of seconds.", RED)
            return
        self.stop()
        self.solve_button.configure(state="disabled")
        answer = []
        game = self.game
        self.solver = threading.Thread(target=lambda: answer.append(ex1_check.solve(game, limit)), daemon=True)
        self.solver.start()
        self.wait_for(self.solver, answer, time.perf_counter())

    def wait_for(self, solver, answer, began):
        """Looks at the solver from time to time, so that the window never waits for it."""
        if solver is not self.solver:
            return      # the student chose another problem while this one ran
        if solver.is_alive():
            self.say(f"Solving... {time.perf_counter() - began:.0f} s")
            self.after(100, self.wait_for, solver, answer, began)
            return
        self.solver = None
        self.solve_button.configure(state="normal")
        self.solved(answer[0] if answer else dict(error="The solver could not start."))

    def cancel(self):
        """Stops a solver that is still running. Its thread then ends by itself, and nobody looks at its answer."""
        if self.solver:
            self.solver = None
            self.solve_button.configure(state="normal")
            for process in multiprocessing.active_children():
                process.terminate()

    def solved(self, result):
        verdict, why = ex1_check.judge(self.game, result, self.optimal)
        lines = [line for line in why.strip().splitlines() if line.strip(" ~^")]    # without the lines that only underline
        if len(lines) > 1:
            print(why)
        if "raiseNotDefined" in why:
            lines.append("Your ex1.py is not finished: the function named above still calls utils.raiseNotDefined().")
        speed = f", {result['seconds']:.2f} s, {result['expanded']} expanded" if "expanded" in result else ""
        text = "\n".join(lines[-TRACEBACK_LINES:])
        self.say(f"{verdict}: {text}{speed}", BLACK if verdict == "PASS" else RED)
        self.set_plan(result.get("plan") or [])

    def go_to(self, step):
        self.step = max(0, min(step, len(self.states) - 1))
        self.view.show(self.states[self.step])
        self.actions.selection_clear(0, "end")
        self.actions.selection_set(self.step)
        self.actions.see(self.step)
        self.progress.configure(text=f"Step {self.step}/{len(self.plan)}, cost so far {self.states[self.step]['cost']}")

    def clicked(self, event):
        chosen = self.actions.curselection()
        if chosen:
            self.stop()
            self.go_to(chosen[0])

    def first(self):
        self.stop()
        self.go_to(0)

    def back(self):
        self.stop()
        self.go_to(self.step - 1)

    def forward(self):
        self.stop()
        self.go_to(self.step + 1)

    def last(self):
        self.stop()
        self.go_to(len(self.states) - 1)

    def stop(self):
        self.playing = False
        self.play_button.configure(text="Play")
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None

    def toggle(self):
        if self.playing:
            self.stop()
            self.go_to(self.step)
            return
        if self.step >= len(self.states) - 1:
            self.go_to(0)
        if len(self.states) > 1:
            self.playing = True
            self.play_button.configure(text="Pause")
            self.animate(time.perf_counter())

    def animate(self, began):
        """Draws one frame of the move from this step to the next, then goes on to the next step."""
        fraction = (time.perf_counter() - began) * 1000 / SPEEDS[self.speed.get()]
        if fraction >= 1:
            self.go_to(self.step + 1)
            if self.step >= len(self.states) - 1:
                self.stop()
                return
            began, fraction = time.perf_counter(), 0
        self.view.show(self.states[self.step], self.states[self.step + 1], fraction)
        self.timer = self.after(FRAME_MS, self.animate, began)


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "p1"
    ex1_check.find_problem(start)   # a wrong name stops here, with a message saying so
    Player(start).mainloop()
