import pygame
import ext_elev
import ex2_random as student   # swap to "import ex2 as student" to drive with your controller
from enum import Enum


# ---------------------------------------------------------------- #
# Problem                                                          #
# ---------------------------------------------------------------- #
problem = {
    "height": 6,
    "Elevators": {
        0: (0, (0, 1, 2, 3), 8),
        1: (4, (2, 4, 5, 6), 10),
    },
    "Persons": {
        10: (0, 3, 3),
        11: (2, 4, 6),
        12: (4, 5, 0),
    },
    "elevator_chosen_action_prob": {0: 0.8, 1: 0.7},
    "person_chosen_action_prob":   {10: 0.9, 11: 0.6, 12: 0.85},
    "persons_reward": {
        10: [2, 3, 6, 10],
        11: [1, 5, 6, 10],
        12: [3, 4, 8, 12],
    },
    "goal_reward": 30,
    "seed": 0,
    "horizon": 40,
}

# ---------------------------------------------------------------- #
# Pygame setup                                                     #
# ---------------------------------------------------------------- #
WIDTH, HEIGHT = 1100, 720
pygame.init()
pygame.font.init()

canvas = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stochastic Multi-Elevator")
font_lg = pygame.font.SysFont(None, 38)
font_md = pygame.font.SysFont(None, 24)
font_sm = pygame.font.SysFont(None, 18)

BG_COLOR        = (20, 80, 100)
BLDG_BG         = (240, 235, 220)
FLOOR_LINE      = (60, 60, 60)
SHAFT_LINE      = (150, 150, 160)
TRACK_REACH     = (210, 215, 225)
TRACK_UNREACH   = (180, 180, 180)
ELEV_FILL       = (60, 110, 200)
ELEV_BORDER     = (15, 30, 60)
PERSON_FLOOR    = (220, 80, 80)
PERSON_INSIDE   = (250, 220, 80)
PERSON_BORDER   = (40, 40, 40)
TEXT_DARK       = (0, 0, 0)
TEXT_LIGHT      = (245, 245, 245)
ACT_OK          = (170, 220, 255)
ACT_INFO        = (255, 220, 170)


# ---------------------------------------------------------------- #
# Rendering                                                        #
# ---------------------------------------------------------------- #
def floor_range(api, state):
    """Compute min/max floor to display (cover reachable sets and live state)."""
    elevators_t, persons_t, _ = state
    reachable = api.get_reachable()
    floors = set()
    for fset in reachable.values():
        floors.update(fset)
    for (_, f, _) in elevators_t:
        floors.add(f)
    for (_, loc) in persons_t:
        if isinstance(loc, tuple) and loc[0] == 'floor':
            floors.add(loc[1])
    if not floors:
        floors = {0}
    return min(floors), max(floors)


def draw_state(api, state):
    elevators_t, persons_t, _total = state
    reachable = api.get_reachable()
    capacities = api.get_capacities()
    min_f, max_f = floor_range(api, state)
    num_floors = max_f - min_f + 1
    num_elev = len(elevators_t)

    MARGIN = 20
    UI_PANEL_W = 360
    bldg_x = MARGIN
    bldg_y = MARGIN
    bldg_w = WIDTH - UI_PANEL_W - 2 * MARGIN
    bldg_h = HEIGHT - 2 * MARGIN

    label_w = 60
    persons_zone_w = 160
    shaft_zone_w = bldg_w - label_w - persons_zone_w
    shaft_w = shaft_zone_w // max(num_elev, 1)
    floor_h = bldg_h // num_floors

    # building background
    pygame.draw.rect(canvas, BLDG_BG, (bldg_x, bldg_y, bldg_w, num_floors * floor_h))

    # floor rows + labels
    for i in range(num_floors):
        f = max_f - i
        y = bldg_y + i * floor_h
        if i > 0:
            pygame.draw.line(canvas, FLOOR_LINE,
                             (bldg_x, y), (bldg_x + bldg_w, y), 1)
        lbl = font_md.render(f"F{f}", True, TEXT_DARK)
        canvas.blit(lbl, lbl.get_rect(center=(bldg_x + label_w // 2,
                                              y + floor_h // 2)))

    # vertical dividers
    pygame.draw.line(canvas, FLOOR_LINE,
                     (bldg_x + label_w, bldg_y),
                     (bldg_x + label_w, bldg_y + num_floors * floor_h), 2)
    pygame.draw.line(canvas, FLOOR_LINE,
                     (bldg_x + label_w + shaft_zone_w, bldg_y),
                     (bldg_x + label_w + shaft_zone_w, bldg_y + num_floors * floor_h), 2)
    pygame.draw.rect(canvas, FLOOR_LINE,
                     (bldg_x, bldg_y, bldg_w, num_floors * floor_h), 2)

    # elevator shafts: reachable cells lightly tinted
    shaft_x0 = bldg_x + label_w
    for k, (eid, _, _) in enumerate(elevators_t):
        col_x = shaft_x0 + k * shaft_w
        for f in range(min_f, max_f + 1):
            row = max_f - f
            y = bldg_y + row * floor_h
            color = TRACK_REACH if f in reachable[eid] else TRACK_UNREACH
            pygame.draw.rect(canvas, color,
                             (col_x + 6, y + 6, shaft_w - 12, floor_h - 12))
        if k > 0:
            pygame.draw.line(canvas, SHAFT_LINE,
                             (col_x, bldg_y), (col_x, bldg_y + num_floors * floor_h), 1)
        # shaft header
        header = font_sm.render(f"E{eid}", True, (100, 100, 100))
        canvas.blit(header, header.get_rect(center=(col_x + shaft_w // 2,
                                                     bldg_y - 2)))

    # group persons
    persons_inside = {eid: [] for (eid, _, _) in elevators_t}
    persons_on_floor = {}
    for (pid, loc) in persons_t:
        if isinstance(loc, tuple):
            if loc[0] == 'in' and loc[1] in persons_inside:
                persons_inside[loc[1]].append(pid)
            elif loc[0] == 'floor':
                persons_on_floor.setdefault(loc[1], []).append(pid)

    # draw elevators
    for k, (eid, cur_f, w_load) in enumerate(elevators_t):
        col_x = shaft_x0 + k * shaft_w
        row = max_f - cur_f
        y = bldg_y + row * floor_h
        box_x = col_x + 8
        box_y = y + 8
        box_w = shaft_w - 16
        box_h = floor_h - 16
        pygame.draw.rect(canvas, ELEV_FILL, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(canvas, ELEV_BORDER, (box_x, box_y, box_w, box_h), 2)
        label = font_sm.render(f"E{eid}  w {w_load}/{capacities[eid]}",
                               True, TEXT_LIGHT)
        canvas.blit(label, (box_x + 4, box_y + 3))

        # persons inside
        ppl = persons_inside.get(eid, [])
        if ppl:
            r_max = min(box_w, box_h) // 6
            radius = max(6, min(14, r_max))
            per_row = max(1, (box_w - 8) // (radius * 2 + 4))
            for i_p, pid in enumerate(ppl):
                col = i_p % per_row
                rr = i_p // per_row
                cx = box_x + 6 + radius + col * (radius * 2 + 4)
                cy = box_y + box_h - 6 - radius - rr * (radius * 2 + 4)
                pygame.draw.circle(canvas, PERSON_INSIDE, (int(cx), int(cy)), radius)
                pygame.draw.circle(canvas, PERSON_BORDER, (int(cx), int(cy)), radius, 1)
                t = font_sm.render(str(pid), True, TEXT_DARK)
                canvas.blit(t, t.get_rect(center=(cx, cy)))

    # draw persons standing on floors (right zone)
    zone_x0 = bldg_x + label_w + shaft_zone_w
    for f, ppl in persons_on_floor.items():
        row = max_f - f
        y = bldg_y + row * floor_h
        radius = 10
        per_row = max(1, (persons_zone_w - 8) // (radius * 2 + 6))
        for i_p, pid in enumerate(ppl):
            col = i_p % per_row
            rr = i_p // per_row
            cx = zone_x0 + 14 + radius + col * (radius * 2 + 6)
            cy = y + floor_h // 2 + rr * (radius * 2 + 4) - 4
            pygame.draw.circle(canvas, PERSON_FLOOR, (int(cx), int(cy)), radius)
            pygame.draw.circle(canvas, PERSON_BORDER, (int(cx), int(cy)), radius, 1)
            t = font_sm.render(str(pid), True, TEXT_DARK)
            canvas.blit(t, t.get_rect(center=(cx, cy)))


def draw_ui(api, episode, step, last_action, last_episode_reward):
    panel_x = WIDTH - 340
    pygame.draw.rect(canvas, (30, 60, 80), (panel_x, 20, 320, HEIGHT - 40))
    pygame.draw.rect(canvas, (200, 220, 235), (panel_x, 20, 320, HEIGHT - 40), 2)

    lines = [
        (font_lg, f"Episode {episode}",     TEXT_LIGHT),
        (font_md, f"Step {step} / {api.get_max_steps()}", TEXT_LIGHT),
        (font_md, f"Total reward: {api.get_current_reward():.1f}", TEXT_LIGHT),
        (font_md, f"Last ep reward: {last_episode_reward:.1f}", TEXT_LIGHT),
        (font_md, "", TEXT_LIGHT),
        (font_md, "Last action:", TEXT_LIGHT),
        (font_lg, last_action if last_action else "-", ACT_OK),
        (font_md, "", TEXT_LIGHT),
        (font_sm, "SPACE = step", ACT_INFO),
        (font_sm, "1     = run episode", ACT_INFO),
        (font_sm, "0     = run all", ACT_INFO),
        (font_sm, "ESC   = quit", ACT_INFO),
    ]
    y = 40
    for f, text, color in lines:
        if text == "":
            y += 8
            continue
        surf = f.render(text, True, color)
        canvas.blit(surf, (panel_x + 16, y))
        y += surf.get_height() + 4


# ---------------------------------------------------------------- #
# Main loop                                                        #
# ---------------------------------------------------------------- #
class RUN(Enum):
    WAIT     = 0
    STEP     = 1
    EPISODE  = 2
    ALL      = 3
    STOP     = 4


def main_loop():
    n_runs = 30
    debug_mode = False

    episode = 0
    step = 0
    last_action = ""
    last_episode_reward = 0.0
    total_reward = 0.0
    api = None
    policy = None

    running = True
    mode = RUN.WAIT

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif mode == RUN.STOP:
                    continue
                elif event.key == pygame.K_SPACE:
                    mode = RUN.STEP
                elif event.key == pygame.K_1:
                    mode = RUN.EPISODE
                elif event.key == pygame.K_0:
                    mode = RUN.ALL

        if mode in (RUN.STEP, RUN.EPISODE, RUN.ALL):
            # Start a new episode if needed
            if api is None or step == 0:
                problem["seed"] = episode
                api = ext_elev.create_elevators_game(problem, debug=debug_mode)
                policy = student.Controller(api)
                last_action = ""
                step = 0

            # Run one step
            if not api.get_done():
                last_action = policy.choose_next_action(api.get_current_state())
                api.submit_next_action(last_action)
                step = api.get_current_steps()

            # End of episode handling
            if api.get_done():
                ep_reward = api.get_current_reward()
                last_episode_reward = ep_reward
                total_reward += ep_reward
                print(f"Episode {episode}: reward = {ep_reward}")
                if debug_mode:
                    api.show_history()
                episode += 1
                step = 0
                api = None
                if episode >= n_runs:
                    mode = RUN.STOP
                elif mode == RUN.STEP or mode == RUN.EPISODE:
                    mode = RUN.WAIT
            else:
                if mode == RUN.STEP:
                    mode = RUN.WAIT

        # render
        canvas.fill(BG_COLOR)
        if api is not None:
            draw_state(api, api.get_current_state())
        draw_ui(api if api else _DummyAPI(), episode, step, last_action, last_episode_reward)
        pygame.display.update()

    if episode > 0:
        print(f"\nAverage reward over {episode} runs: {total_reward / episode:.3f}")
    pygame.quit()


class _DummyAPI:
    """Tiny stand-in so draw_ui can render before the first episode starts."""
    def get_max_steps(self): return problem["horizon"]
    def get_current_reward(self): return 0.0


if __name__ == "__main__":
    main_loop()
