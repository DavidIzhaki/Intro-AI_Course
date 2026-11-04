"""Draws a problem so you can see it. Choose a problem from ex1_check, or type or paste your own and press Draw.

    python ex1_maker.py          start with p1
    python ex1_maker.py x3       start with x3

Green shapes are islands (locations joined by roads). Squares are ports, circles are other locations.
A dashed line is a ferry route. T10 2/5 is truck 10 holding weight 2 of 5. F20 1/2 is ferry 20 with 1 of 2 trucks.
A brown label 30:7>5 is package 30 of weight 7, going to location 5. It turns dark green when delivered.
A package on top of a truck is inside it, and a truck on top of a ferry is aboard it.
A docked ferry stands next to its port, on the side of its route. Other labels stand next to their location.
ex1_gui.py uses this drawing to play a plan.
"""
import ast
import itertools
import math
import pprint
import random
import re
import sys
import tkinter as tk
from collections import Counter, defaultdict
from tkinter import font as tkfont
from tkinter import ttk

import ex1_check

WIDTH, HEIGHT = 860, 640
MARGIN_X, MARGIN_Y = 48, 30     # room for labels at the edges of the window
SHORE = 0.7             # land around a location, in map units (two joined locations are 1 apart)
SEA_GAP = 1.5           # the least sea between two islands, in map units
LONGEST_STRAIGHT = 8    # beyond this many links, a chain may turn back to fit the window
CURVE = 9             # the radius of the tightest curve of a long chain, in links
MOST_ZOOM = 150         # pixels for a map unit, so that a tiny problem does not fill the window with one island
SEA, ISLAND, ISLAND_EDGE, ROAD = "#cfe6f5", "#e7f0d4", "#a9c08a", "#8a8a7a"
LOCATION, PORT, INK = "#ffffff", "#ffe8a3", "#222222"
PACKAGE, DELIVERED, TRUCK_INK = "#d9b98a", "#3f7f3f", "#ffffff"
COLORS = ["#1f77b4", "#d62728", "#7b4fb0", "#c2185b", "#d95f02", "#00838f", "#8c564b", "#546e7a", "#2e7d32", "#827717"]
ANGLES = [2 * math.pi * k / 24 for k in range(24)]
# The ways to split the labels of a location: trucks go this way, packages the opposite way. Up is the first choice.
SIDES = [(math.sin(math.radians(a)), -math.cos(math.radians(a))) for a in (0, 25, -25, 50, -50, 75, -75, 90)]


def islands_of(game):
    """The groups of locations joined by roads."""
    group = list(range(game["Locations"]))

    def find(location):
        while group[location] != location:
            group[location] = group[group[location]]
            location = group[location]
        return location

    for a, b in game["Roads"]:
        group[find(a)] = find(b)
    islands = {}
    for location in range(game["Locations"]):
        islands.setdefault(find(location), []).append(location)
    return list(islands.values())


def spread(radius, links, rounds=120):
    """Places circles of the given radii, {name: radius}, and returns {name: (x, y)} around (0, 0).
    It starts from a ring and moves each pair in turn until it obeys its rule, the same way every time,
    so that a problem always looks the same."""
    around = defaultdict(list)
    for a, b in links:
        around[a].append(b)
        around[b].append(a)
    place = ring_of(radius, around)
    rules = distance_rules(radius, around)
    for step in range(rounds):
        for a, b, least, most in rules:
            dx, dy = place[a][0] - place[b][0], place[a][1] - place[b][1]
            distance = max(math.hypot(dx, dy), 0.01)
            wanted = max(distance, least)
            if step < rounds - 30:      # at the end only push, since many ferries may want more touching than can be
                wanted = min(wanted, most)
            push = (wanted - distance) / distance / 2
            place[a][0] += dx * push
            place[a][1] += dy * push
            place[b][0] -= dx * push
            place[b][1] -= dy * push
    middle_x = sum(p[0] for p in place.values()) / len(place)
    middle_y = sum(p[1] for p in place.values()) / len(place)
    return {n: (p[0] - middle_x, p[1] - middle_y) for n, p in place.items()}


def ring_of(radius, around):
    """Starting positions on a ring, in depth-first order, which keeps long chains from tangling."""
    order, stack = [], list(radius)[::-1]
    while stack:
        name = stack.pop()
        if name not in order:
            order.append(name)
            stack.extend(sorted(around[name], reverse=True))
    rng = random.Random(0)
    ring = sum(radius.values()) / math.pi
    return {n: [ring * math.cos(2 * math.pi * i / len(order)) + rng.random() / 10,
                ring * math.sin(2 * math.pi * i / len(order)) + rng.random() / 10] for i, n in enumerate(order)}


def distance_rules(radius, around):
    """A list of (a, b, least distance, most distance). Joined circles touch. Others are as far apart as the way
    along the links, a bit less for a long way so that a long chain can curve to fit the window, and never overlap."""
    names = list(radius)
    way = {(a, b): math.inf for a in names for b in names}
    for a in names:
        for b in around[a]:
            way[a, b] = radius[a] + radius[b]
    for middle, a, b in itertools.product(names, repeat=3):
        way[a, b] = min(way[a, b], way[a, middle] + way[middle, b])
    unit = 2 * sum(radius.values()) / len(names)
    rules = []
    for a, b in itertools.combinations(names, 2):
        touching = radius[a] + radius[b]
        along = min(way[a, b], LONGEST_STRAIGHT * unit) if way[a, b] < math.inf else 0
        chord = 2 * CURVE * unit * math.sin(along / (2 * CURVE * unit))
        rules.append((a, b, max(touching, chord), touching if b in around[a] else math.inf))
    return rules


def convex_hull(points):
    """The corners of the smallest convex shape around the points, in order."""
    points = sorted(set(points))

    def half(ordered):
        chain = []
        for x, y in ordered:
            while len(chain) > 1 and ((chain[-1][0] - chain[-2][0]) * (y - chain[-2][1])
                                      - (chain[-1][1] - chain[-2][1]) * (x - chain[-2][0])) <= 0:
                chain.pop()
            chain.append((x, y))
        return chain[:-1]

    return half(points) + half(points[::-1])


def box_around(spot, size):
    return spot[0] - size[0] / 2, spot[1] - size[1] / 2, spot[0] + size[0] / 2, spot[1] + size[1] / 2


def overlap(a, b):
    """The area shared by two boxes (left, top, right, bottom)."""
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def turned(point, angle):
    x, y = point
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


class Layout:
    """Where everything goes, in map units. location: {location: (x, y)}. islands: a list of polygons.
    dock: {(ferry, port): (ux, uy, slot)}, the way from the port to the ferry, and its place in a pile of
    ferries going the same way."""

    def __init__(self, game):
        islands = islands_of(game)
        island_of = {location: i for i, members in enumerate(islands) for location in members}
        routes = [pair for _, ports, _ in game["Ferries"].values()
                  for pair in itertools.combinations(sorted(set(ports)), 2)]
        links = list({tuple(sorted((island_of[a], island_of[b]))) for a, b in routes if island_of[a] != island_of[b]})
        shapes = [spread(dict.fromkeys(members, 0.5), [(a, b) for a, b in game["Roads"] if a in members and a != b])
                  for members in islands]
        radii = [max(math.hypot(*p) for p in shape.values()) + SHORE for shape in shapes]
        centers = self.island_centers(radii, links)
        self.location, self.islands = {}, []
        shore = [turned((SHORE, 0), angle) for angle in ANGLES]
        for i, shape in enumerate(shapes):
            angle = self.best_turn(shape, i, centers, routes, island_of)
            for location, point in shape.items():
                x, y = turned(point, angle)
                self.location[location] = (centers[i][0] + x, centers[i][1] + y)
            self.islands.append(convex_hull([(self.location[n][0] + x, self.location[n][1] + y)
                                             for n in shape for x, y in shore]))
        xs = [x for polygon in self.islands for x, _ in polygon]
        ys = [y for polygon in self.islands for _, y in polygon]
        self.bounds = min(xs), min(ys), max(xs), max(ys)
        self.dock = self.docks(game)

    @staticmethod
    def island_centers(radii, links):
        """Spreads the islands as wide as it can, since the window is wider than it is high."""
        centers = spread({i: r + SEA_GAP / 2 for i, r in enumerate(radii)}, links)
        angle = max(ANGLES, key=lambda turn: sum(turned(p, turn)[0] ** 2 for p in centers.values()))
        return [turned(centers[i], angle) for i in range(len(radii))]

    @staticmethod
    def best_turn(shape, island, centers, routes, island_of):
        """Turns an island so that its ports face the islands their ferries go to. Apart from that, as wide as it can."""
        pulls = []
        for a, b in routes:
            for port, other in ((a, b), (b, a)):
                if port in shape and island_of[other] != island:
                    target = centers[island_of[other]]
                    pulls.append((shape[port], (target[0] - centers[island][0], target[1] - centers[island][1])))

        def score(angle):
            facing = sum(x * tx + y * ty for (x, y), (tx, ty) in ((turned(p, angle), t) for p, t in pulls))
            return facing + 0.01 * sum(turned(p, angle)[0] ** 2 for p in shape.values())

        return max(ANGLES, key=score)

    def docks(self, game):
        """A ferry docks on the side of the port that faces the other ports it serves."""
        docks = {}
        for f, (_, ports, _) in sorted(game["Ferries"].items()):
            for port in sorted(ports):
                x, y = self.location[port]
                dx = sum(self.location[other][0] - x for other in ports)
                dy = sum(self.location[other][1] - y for other in ports)
                length = math.hypot(dx, dy)
                ux, uy = (dx / length, dy / length) if length > 0.01 else (0.0, -1.0)
                same_way = [d for (_, q), d in docks.items() if q == port and ux * d[0] + uy * d[1] > 0.85]
                docks[f, port] = (ux, uy, len(same_way))
        return docks


class MapView(tk.Canvas):
    """Draws a problem and a state of it. show() takes the state from ex1_check.World.snapshot().
    With a second state and a fraction, it draws the trucks and ferries part of the way between them."""

    def __init__(self, parent, **options):
        super().__init__(parent, background=SEA, highlightthickness=0, width=WIDTH, height=HEIGHT, **options)
        self.game = self.layout = self.last = self.chosen_for = None
        self.bold, self.plain = (tkfont.nametofont("TkDefaultFont").copy() for _ in range(2))
        self.bold.configure(size=8, weight="bold")
        self.plain.configure(size=8)
        self.bind("<Configure>", lambda event: self.redraw())

    def set_game(self, game):
        self.game = game
        self.layout = Layout(game)
        self.chosen_for = None
        numbers = [*sorted(game["Trucks"]), *sorted(game["Ferries"])]
        self.colors = {number: COLORS[i % len(COLORS)] for i, number in enumerate(numbers)}
        line = self.bold.metrics("linespace")
        self.truck_box = self.box_for(self.bold, [f"T{t} {c}/{c}" for t, (_, c) in game["Trucks"].items()], line + 3)
        self.ferry_box = self.box_for(self.bold, [f"F{f} {k}/{k}" for f, (_, _, k) in game["Ferries"].items()], line + 5)
        self.package_box = self.box_for(self.plain, [f"{p}:{w}>{g}" for p, (_, w, g) in game["Packages"].items()], line + 1)
        self.show(ex1_check.World(game).snapshot())

    @staticmethod
    def box_for(font, texts, height):
        """A box that fits the longest of the texts."""
        return max((font.measure(text) for text in texts), default=0) + 8, height

    def redraw(self):
        if self.last:
            self.show(*self.last)

    def fit(self):
        """Chooses the zoom for the size of the window."""
        left, top, right, bottom = self.layout.bounds
        self.width, self.height = max(self.winfo_width(), 200), max(self.winfo_height(), 200)
        self.zoom = min(MOST_ZOOM, (self.width - 2 * MARGIN_X) / (right - left), (self.height - 2 * MARGIN_Y) / (bottom - top))
        self.shift_x = self.width / 2 - (left + right) / 2 * self.zoom
        self.shift_y = self.height / 2 - (top + bottom) / 2 * self.zoom
        self.radius = max(9, min(13, 0.34 * self.zoom))
        if self.zoom != self.chosen_for:
            self.chosen_for = self.zoom
            self.choose_sides()

    def choose_sides(self):
        """For each location, the first of SIDES where its labels cover the least of the map and of the labels so far.
        The busiest locations choose first. The labels are those of the start, and the goals of packages."""
        trucks, packages = Counter(place for place, _ in self.game["Trucks"].values()), Counter()
        for start, _, goal in self.game["Packages"].values():
            packages.update({start, goal})
        taken = [box_around(self.at(n), (2 * self.radius, 2 * self.radius)) for n in self.layout.location]
        taken += [box_around(self.docked(f, port), self.ferry_box) for f, port in self.layout.dock]
        far = 9999      # outside the window counts as covered
        taken += [(-far, -far, 0, far), (-far, -far, far, 0), (self.width, -far, far, far), (-far, self.height, far, far)]
        self.side = {}
        for location in sorted(self.layout.location, key=lambda n: -trucks[n] - packages[n]):
            counts = trucks[location] or 1, packages[location] or 1
            self.side[location] = min(SIDES, key=lambda side: sum(overlap(label, other)
                                                                 for label in self.boxes_at(location, side, *counts)
                                                                 for other in taken))
            taken += self.boxes_at(location, self.side[location], *counts)

    def boxes_at(self, location, side, trucks, packages):
        """The boxes of this many trucks and packages at a location, if its labels split this way."""
        opposite = -side[0], -side[1]
        return ([box_around(spot, self.truck_box) for spot in self.beside(location, side, trucks, self.truck_box)]
                + [box_around(spot, self.package_box) for spot in self.beside(location, opposite, packages, self.package_box)])

    def to_screen(self, x, y):
        return self.shift_x + x * self.zoom, self.shift_y + y * self.zoom

    def at(self, location):
        return self.to_screen(*self.layout.location[location])

    def show(self, state, following=None, fraction=0.0):
        self.last = (state, following, fraction)
        self.delete("all")
        self.fit()
        self.draw_map()
        now = self.positions(state)
        if following:
            later = self.positions(following)
            now = {k: (a[0] + (later[k][0] - a[0]) * fraction, a[1] + (later[k][1] - a[1]) * fraction)
                   for k, a in now.items()}
        self.draw_things(following if following and fraction >= 0.5 else state, now)

    def draw_map(self):
        game = self.game
        for polygon in self.layout.islands:
            corners = [c for point in polygon for c in self.to_screen(*point)]
            self.create_polygon(corners, fill=ISLAND, outline=ISLAND_EDGE, width=2)
        self.draw_routes()
        for a, b in game["Roads"]:
            if a != b:
                self.create_line(*self.at(a), *self.at(b), fill=ROAD, width=4)
        r = self.radius
        for location in range(game["Locations"]):
            x, y = self.at(location)
            shape = self.create_rectangle if location in game["Ports"] else self.create_oval
            shape(x - r, y - r, x + r, y + r, fill=PORT if location in game["Ports"] else LOCATION, outline=INK)
            self.create_text(x, y, text=str(location), fill=INK, font=self.bold)

    def draw_routes(self):
        """A dashed line for each pair of ports of a ferry. Ferries that share a pair get lines side by side."""
        sharing = defaultdict(list)
        for f, (_, ports, _) in sorted(self.game["Ferries"].items()):
            for pair in itertools.combinations(sorted(set(ports)), 2):
                sharing[pair].append(f)
        for (a, b), ferries in sharing.items():
            ax, ay = self.at(a)
            bx, by = self.at(b)
            length = max(math.hypot(bx - ax, by - ay), 1)
            across_x, across_y = (by - ay) / length, (ax - bx) / length
            for i, f in enumerate(ferries):
                gap = 5 * (i - (len(ferries) - 1) / 2)
                self.create_line(ax + across_x * gap, ay + across_y * gap, bx + across_x * gap, by + across_y * gap,
                                 fill=self.colors[f], width=2, dash=(6, 4))

    def beside(self, location, side, count, box):
        """Spots for count boxes, in rows of three, next to a location on the given side."""
        width, height = box
        columns, rows = min(count, 3), math.ceil(count / 3)
        x, y = self.at(location)
        reach = self.radius + 3 + abs(side[0]) * columns * width / 2 + abs(side[1]) * rows * height / 2
        return [(x + side[0] * reach + (i % 3 - (columns - 1) / 2) * width,
                 y + side[1] * reach + (i // 3 - (rows - 1) / 2) * height) for i in range(count)]

    def docked(self, ferry, port):
        """Where a ferry stands at a port: next to it, on the side of its route."""
        ux, uy, slot = self.layout.dock[ferry, port]
        x, y = self.at(port)
        width, height = self.ferry_box
        room_for_truck = self.truck_box[1] if uy > 0 else 0     # a truck aboard stands on top of the ferry
        reach = self.radius + 6 + abs(ux) * width / 2 + abs(uy) * (height / 2 + room_for_truck)
        reach += slot * (abs(ux) * width + abs(uy) * (height + room_for_truck) + 3)
        return x + ux * reach, y + uy * reach

    def positions(self, state):
        """Where each ferry, truck and package stands in this state, in pixels."""
        place = {("ferry", f): self.docked(f, port) for f, port in state["ferry_at"].items()}
        standing, aboard, lying, inside = (defaultdict(list) for _ in range(4))
        for t in sorted(state["truck_at"]):
            if state["truck_on"][t] is None:
                standing[state["truck_at"][t]].append(t)
            else:
                aboard[state["truck_on"][t]].append(t)
        for p in sorted(state["package_at"]):
            if state["package_in"][p] is None:
                lying[state["package_at"][p]].append(p)
            else:
                inside[state["package_in"][p]].append(p)
        truck_width, truck_height = self.truck_box
        package_height = self.package_box[1]
        for location, trucks in standing.items():
            spots = self.beside(location, self.side[location], len(trucks), self.truck_box)
            place.update((("truck", t), spot) for t, spot in zip(trucks, spots))
        for ferry, trucks in aboard.items():
            x, y = place["ferry", ferry]
            for i, t in enumerate(trucks):
                place["truck", t] = (x + (i - (len(trucks) - 1) / 2) * truck_width,
                                     y - (self.ferry_box[1] + truck_height) / 2)
        for location, packages in lying.items():
            ux, uy = self.side[location]
            spots = self.beside(location, (-ux, -uy), len(packages), self.package_box)
            place.update((("package", p), spot) for p, spot in zip(packages, spots))
        for truck, packages in inside.items():
            x, y = place["truck", truck]
            for i, p in enumerate(packages):
                place["package", p] = (x, y - (truck_height + package_height) / 2 - i * package_height)
        return place

    def label(self, spot, box, text, fill, outline, ink, font, width=1):
        x = max(box[0] / 2 + 1, min(spot[0], self.width - box[0] / 2 - 1))     # a label stays inside the window
        y = max(box[1] / 2 + 1, min(spot[1], self.height - box[1] / 2 - 1))
        self.create_rectangle(*box_around((x, y), box), fill=fill, outline=outline, width=width)
        self.create_text(x, y, text=text, fill=ink, font=font)

    def draw_things(self, state, place):
        game = self.game
        for f, (_, _, room) in sorted(game["Ferries"].items()):
            count = sum(1 for v in state["truck_on"].values() if v == f)
            self.label(place["ferry", f], self.ferry_box, f"F{f} {count}/{room}",
                       SEA, self.colors[f], self.colors[f], self.bold, 3)
        for t, (_, capacity) in sorted(game["Trucks"].items()):
            load = sum(game["Packages"][p][1] for p, v in state["package_in"].items() if v == t)
            self.label(place["truck", t], self.truck_box, f"T{t} {load}/{capacity}",
                       self.colors[t], INK, TRUCK_INK, self.bold)
        for p, (_, weight, goal) in sorted(game["Packages"].items()):
            done = state["package_at"][p] == goal
            self.label(place["package", p], self.package_box, f"{p}:{weight}>{goal}",
                       DELIVERED if done else PACKAGE, INK, TRUCK_INK if done else INK, self.plain)


def parse_problem(text):
    """Reads a problem typed as a Python dictionary, with or without comments and `name =` in front. Raises ValueError."""
    in_front = r"^(\s*#.*\n)*\s*(\w+\s*=\s*)?"
    text = re.sub(in_front, lambda match: "\n" * match.group().count("\n"), text)    # keeps the line numbers of errors right
    try:
        game = ast.literal_eval(text)
    except SyntaxError as error:
        raise ValueError(f"Python cannot read this, line {error.lineno}: {error.msg}.") from None
    except (ValueError, TypeError):
        raise ValueError("Only a plain dictionary works here: numbers, tuples, sets and set(), without names or calls.") from None
    problems = check_problem(game)
    if problems:
        raise ValueError("\n".join(problems))
    return game


def check_problem(game):
    """The mistakes in a problem, as a list of sentences. An empty list means it is valid."""
    if not isinstance(game, dict):
        return ["The problem must be a dictionary."]
    missing = {"Locations", "Roads", "Ports", "Trucks", "Ferries", "Packages"} - game.keys()
    if missing:
        return [f"Missing entries: {', '.join(sorted(missing))}."]
    try:
        places = range(game["Locations"])
        if not places:
            return ["There must be at least one location."]
        unknown = lambda place: not isinstance(place, int) or place not in places
        errors = [f"Road {road} must join two known locations." for road in game["Roads"]
                  if len(road) != 2 or any(map(unknown, road))]
        errors += [f"Port {port} is not a location." for port in game["Ports"] if unknown(port)]
        errors += [f"Truck {t} starts at unknown location {place}." for t, (place, _) in game["Trucks"].items()
                   if unknown(place)]
        for f, (dock, served, _) in game["Ferries"].items():
            errors += [f"Ferry {f} serves {port}, which is not in Ports." for port in served
                       if port not in game["Ports"] or unknown(port)]
            if dock not in served:
                errors.append(f"Ferry {f} is docked at {dock}, which it does not serve.")
        for p, (start, weight, goal) in game["Packages"].items():
            if unknown(start) or unknown(goal):
                errors.append(f"Package {p} uses an unknown location.")
            if weight < 1:
                errors.append(f"Package {p} must have weight at least 1.")
        ids = [*game["Trucks"], *game["Ferries"], *game["Packages"]]
        if not all(isinstance(number, int) for number in ids):
            errors.append("All IDs of trucks, ferries and packages must be whole numbers.")
        if len(ids) != len(set(ids)):
            errors.append("All IDs of trucks, ferries and packages must be different.")
    except (TypeError, ValueError, AttributeError) as error:
        return [f"Some entry has the wrong shape: {error}. See the format in ex1_check.py."]
    return errors


def problem_names():
    """All the problem names in ex1_check, like 'x3 (X)'."""
    return [f"{name} ({set_name})" for set_name, problems in ex1_check.SETS.items() for name in problems]


def fit_on_screen(window):
    """Fixes the size of a new window, so that messages take their room from the map, and keeps it on small screens."""
    window.update_idletasks()
    width = min(window.winfo_reqwidth(), window.winfo_screenwidth() - 20)
    height = min(window.winfo_reqheight(), window.winfo_screenheight() - 100)
    window.geometry(f"{width}x{height}+10+10")


class Maker(tk.Tk):
    def __init__(self, start):
        super().__init__()
        self.title("Island Logistics: problem maker")
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        self.choice = ttk.Combobox(left, values=problem_names(), state="readonly")
        self.choice.pack(fill="x")
        self.choice.bind("<<ComboboxSelected>>", lambda event: self.load(self.choice.get().split()[0]))
        ttk.Button(left, text="Draw", command=self.draw).pack(side="bottom", fill="x")
        self.message = ttk.Label(left, foreground="#b00020", wraplength=340)
        self.message.pack(side="bottom", fill="x", pady=4)
        box = ttk.Frame(left)
        box.pack(fill="both", expand=True, pady=6)
        self.text = tk.Text(box, width=44, height=30, font="TkFixedFont")
        bar = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.view = MapView(self)
        self.view.pack(side="right", fill="both", expand=True)
        self.load(start)
        fit_on_screen(self)

    def load(self, name):
        _, game, _ = ex1_check.find_problem(name)
        self.choice.set(next(n for n in problem_names() if n.split()[0] == name))
        self.text.delete("1.0", "end")
        self.text.insert("1.0", pprint.pformat(game, width=42, compact=True, sort_dicts=False))
        self.draw()

    def draw(self):
        try:
            game = parse_problem(self.text.get("1.0", "end"))
        except ValueError as error:
            self.message.configure(text=str(error))
            return
        self.message.configure(text="")
        self.view.set_game(game)


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "p1"
    ex1_check.find_problem(start)   # a wrong name stops here, with a message saying so
    Maker(start).mainloop()
