#!/usr/bin/env python3
"""
Smart Stop — Bus Stop Assistance UI (part 2)
Appended after bus_stop/app.py. Split for size.
"""

# Continuation of bus-assistance/bus_stop/app.py
# In the actual file this code lives below the header / info-page helpers.
# See that file for full context.

def _build_info_page():
    """One-shot: lay out the 4x4 grid. Pills are stored in info_widgets
    so the tick timer can update them in place."""
    # Clear any previous content
    for w in info_page.winfo_children():
        w.destroy()
    info_widgets.clear()

    # Bottom: prominent "Tap if you need assistance" pill (the only clickable element).
    # Packed FIRST with side="bottom" so it anchors to the bottom of info_page
    # and is never clipped, regardless of grid height.
    bottom = tk.Frame(info_page, bg=WHITE)
    bottom.pack(side="bottom", fill="x", padx=14, pady=(4, 6))
    info_widgets["bottom"] = bottom

    pill_btn = tk.Frame(bottom, bg=INFO_PILL_BG, cursor="hand2")
    pill_btn.pack(fill="x", ipady=6)
    info_widgets["pill_btn"] = pill_btn

    # Wheelchair icon (left)
    tk.Label(
        pill_btn,
        text="\u267f",
        bg=INFO_PILL_BG,
        fg=YELLOW,
        font=("Helvetica", 26, "bold"),
        anchor="w",
        padx=12,
    ).pack(side="left")

    # Main label + sub-hint
    txt_col = tk.Frame(pill_btn, bg=INFO_PILL_BG)
    txt_col.pack(side="left", fill="x", expand=True, padx=(2, 0))
    tk.Label(
        txt_col,
        text="TAP HERE IF YOU NEED ASSISTANCE",
        bg=INFO_PILL_BG,
        fg=WHITE,
        font=f_info_pill_main,
        anchor="w",
    ).pack(anchor="w")
    tk.Label(
        txt_col,
        text="For wheelchair users and passengers who need help boarding",
        bg=INFO_PILL_BG,
        fg="#aaaacc",
        font=f_info_pill_hint,
        anchor="w",
    ).pack(anchor="w")

    # Right side: a small arrow
    tk.Label(
        pill_btn,
        text="\u25b6",
        bg=INFO_PILL_BG,
        fg=YELLOW,
        font=("Helvetica", 18, "bold"),
        anchor="e",
        padx=12,
    ).pack(side="right")

    # Sub-header strip
    head = tk.Frame(info_page, bg=WHITE)
    head.pack(fill="x", padx=20, pady=(6, 0))
    tk.Label(
        head,
        text="Next arrivals",
        bg=WHITE,
        fg=NAVY,
        font=tkfont.Font(family="Helvetica", size=14, weight="bold"),
        anchor="w",
    ).pack(side="left")
    tk.Label(
        head,
        text="Tap below to request assistance",
        bg=WHITE,
        fg=DGREY,
        font=f_info_pill_hint,
        anchor="e",
    ).pack(side="right")

    # The grid: 4 rows x 4 cols. expand=True so it consumes leftover
    # vertical space between the sub-header and the bottom pill.
    grid = tk.Frame(info_page, bg=WHITE)
    grid.pack(fill="both", expand=True, padx=14, pady=4)
    info_widgets["grid"] = grid

    ROW_H = 70
    COL_W = 180
    for col in range(4):
        grid.columnconfigure(col, weight=1, uniform="info")
    for row in range(4):
        grid.rowconfigure(row, weight=1, uniform="info")

    for r, line in enumerate(BUS_LINES):
        # Col 0: line badge (colored square with the line number)
        badge_bg = LINE_COLORS.get(line, BTN_BG)
        badge = tk.Frame(grid, bg=badge_bg, width=COL_W - 20, height=ROW_H - 10)
        badge.grid(row=r, column=0, padx=6, pady=4, sticky="nsew")
        badge.pack_propagate(False)
        tk.Label(
            badge, text=line, bg=badge_bg, fg=WHITE, font=f_info_badge, anchor="center"
        ).pack(expand=True, fill="both")

        # Small accessibility badge in the top-right corner
        tk.Label(
            badge,
            text="\u267f",
            bg=badge_bg,
            fg="#dddddd",
            font=("Helvetica", 9),
            anchor="ne",
        ).place(relx=1.0, x=-4, y=2, anchor="ne")

        # Cols 1-3: timing pills
        for c, value in enumerate(ARRIVALS[line]):
            pill = _make_pill(grid, value, c, line)
            pill["frame"].config(width=COL_W - 20, height=ROW_H - 10)
            pill["frame"].grid(row=r, column=c + 1, padx=6, pady=4, sticky="nsew")
            info_widgets[(line, c)] = pill

    # Bind click on every part of the pill. We do this in two passes so
    # the event handler fires no matter which descendant of the pill the
    # user actually touches. The first pass hits the visible rectangle
    # and its direct children; the second pass walks one level into
    # txt_col (which holds the two labels) and binds those labels too.
    click_widgets = [bottom, pill_btn] + list(pill_btn.winfo_children())
    for w in txt_col.winfo_children():
        click_widgets.append(w)
    for w in click_widgets:
        w.bind("<Button-1>", lambda e: show_request())
    # Hover effect
    pill_btn.bind("<Enter>", lambda e: pill_btn.config(bg="#003872"))
    pill_btn.bind("<Leave>", lambda e: pill_btn.config(bg=INFO_PILL_BG))


def _tick_arrivals():
    """Decrement all >0 timings once per minute, with per-slot offsets so
    that pills don't all change at the same wall-clock moment. When a slot
    has been at "Now" (0) for NOW_RESTART_DELAY_SEC, it gets re-seeded
    with a fresh value representing the *next* bus — so the info page
    keeps looking like live data instead of freezing with everything green.
    """
    global info_tick_job
    now_epoch = time.time()
    for line, slots in ARRIVALS.items():
        new_slots = []
        for c, v in enumerate(slots):
            key = (line, c)
            offset = TICK_OFFSETS.get(key, 0)
            if v > 0:
                new_slots.append(v - 1)
                SLOT_ZERO_SINCE.pop(key, None)
                continue
            # v == 0. Green is reserved for slot 0 only (the 'next bus').
            # For slot 1 and slot 2, re-seed immediately so they never
            # display green.
            if c != 0:
                # Re-seed slots 1 and 2 with a realistic headway after
                # slot 0 (or after the previous slot in the same row).
                prev = new_slots[-1] if new_slots else 0
                new_slots.append(max(prev + 1, prev + random.randint(6, 14)))
                TICK_OFFSETS[key] = random.randint(0, 55)
                SLOT_ZERO_SINCE.pop(key, None)
                continue
            # c == 0: slot 0 is at 'Now' (green). Hold for
            # NOW_RESTART_DELAY_SEC, then re-seed the next bus.
            if key not in SLOT_ZERO_SINCE:
                SLOT_ZERO_SINCE[key] = now_epoch
                new_slots.append(0)
                continue
            if now_epoch - SLOT_ZERO_SINCE[key] >= NOW_RESTART_DELAY_SEC:
                # Re-seed slot 0 with a realistic next-bus arrival: 8-22
                # min away, and shift the offset so this row doesn't tick
                # in lockstep with the others.
                new_slots.append(random.randint(8, 22))
                TICK_OFFSETS[key] = random.randint(0, 55)
                del SLOT_ZERO_SINCE[key]
            else:
                new_slots.append(0)
        ARRIVALS[line] = new_slots
        # Re-paint the pills in place if the info page is currently visible
        if current_screen == "info":
            for c, value in enumerate(new_slots):
                pill = info_widgets.get((line, c))
                if pill is not None:
                    _restyle_pill(pill, value)
    # Schedule the next global tick — but each slot's *effective* tick
    # happens at 60_000 - TICK_OFFSETS[key] ms from the previous fire
    # of that slot. We approximate this by ticking everyone at the global
    # 60s rhythm; the per-slot offset only affects the *initial* moment
    # when a slot transitions to a new value (e.g. right after a re-seed).
    info_tick_job = root.after(60_000, _tick_arrivals)


def _seed_arrivals_for_request(line):
    """Restart the demo cycle for the requested line so the user sees a
    fresh countdown starting from the moment they tapped a line. Slots
    are spread out (not staggered) so the row doesn't look fake."""
    if line not in ARRIVALS:
        return
    ARRIVALS[line] = _seed_arrivals_for_line(line)
    SLOT_ZERO_SINCE = globals().get("SLOT_ZERO_SINCE", {})
    for c in range(3):
        SLOT_ZERO_SINCE.pop((line, c), None)
        TICK_OFFSETS[(line, c)] = random.randint(0, 55)
    if current_screen == "info":
        for c, value in enumerate(ARRIVALS[line]):
            pill = info_widgets.get((line, c))
            if pill is not None:
                _restyle_pill(pill, value)


def show_info():
    """Switch to the info page (default landing screen)."""
    global current_screen
    if current_screen == "info" and info_widgets:
        return
    if not info_widgets:
        _build_info_page()
    # Hide request page if it's currently packed
    try:
        idle_page.pack_forget()
    except Exception:
        pass
    info_page.pack(fill="both", expand=True)
    current_screen = "info"


def show_request():
    """Switch to the request page (the 4 line buttons)."""
    global current_screen
    info_page.pack_forget()
    idle_page.pack(fill="both", expand=True)
    current_screen = "request"


# ══════════════════════════════════════════════════════
# IDLE PAGE (now the "request" screen — 4 line buttons that publish)
# ══════════════════════════════════════════════════════
idle_page = tk.Frame(main, bg=WHITE)
# Not packed here — show_request() / show_info() toggle between this and info_page.

# Instruction
tk.Label(
    idle_page,
    text="Tap a line to get assistance from the driver",
    bg=WHITE,
    fg=NAVY,
    font=f_instr,
    anchor="w",
    padx=26,
).pack(pady=(12, 2))

# Subtitle
sub_frame = tk.Frame(idle_page, bg=WHITE)
sub_frame.pack(fill="x", padx=26, pady=(0, 8))

tk.Label(
    sub_frame,
    text="Nobody gets unseen — inclusive transit for everyone.  ",
    bg=WHITE,
    fg=DGREY,
    font=f_sub,
    anchor="w",
).pack(side="left")
tk.Label(
    sub_frame,
    text="Priority: wheelchair users and disabled passengers.",
    bg=WHITE,
    fg=NAVY,
    font=tkfont.Font(family="Helvetica", size=10, weight="bold"),
    anchor="w",
).pack(side="left")

# Bus line buttons — 2 rows x 2 cols
grid = tk.Frame(idle_page, bg=WHITE)
grid.pack(fill="both", expand=True, padx=20, pady=(2, 0))
buttons = {}


def make_button(parent, line, row, col):
    line_bg = LINE_COLORS.get(line, BTN_BG)
    card = tk.Frame(parent, bg=line_bg, cursor="hand2")
    card.grid(row=row, column=col, padx=7, pady=5, sticky="nsew")

    inner = tk.Frame(card, bg=line_bg)
    inner.pack(expand=True, fill="both", padx=3, pady=3)

    tk.Label(inner, text=line, bg=line_bg, fg=WHITE, font=f_btn, anchor="center").pack(
        expand=True
    )

    tk.Label(
        inner, text="Tap to request", bg=line_bg, fg=YELLOW, font=f_tap, anchor="center"
    ).pack(pady=(1, 3))

    def on_click(ev, _line=line):
        if waiting:
            return
        open_waiting(_line)

    card.bind("<Button-1>", on_click)
    for w in inner.winfo_children():
        w.bind("<Button-1>", on_click)
    card.bind("<Enter>", lambda e, c=card: c.config(bg=BTN_HOV))
    card.bind("<Leave>", lambda e, c=card: c.config(bg=line_bg))
    return card


for i, line in enumerate(BUS_LINES):
    buttons[line] = make_button(grid, line, i // 2, i % 2)

grid.columnconfigure(0, weight=1, uniform="col")
grid.columnconfigure(1, weight=1, uniform="col")
grid.rowconfigure(0, weight=1, uniform="row")
grid.rowconfigure(1, weight=1, uniform="row")

# ══════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════
footer = tk.Frame(main, bg=LGREY, height=28)
footer.pack(fill="x", side="bottom")

tk.Label(
    footer,
    text="Challenge@Polito",
    bg=LGREY,
    fg="#333333",
    font=f_footer,
    anchor="w",
    padx=22,
).pack(side="left", pady=5)

# Footer right side — pack in reverse so screen reads: Made with [heart] by Yellow Team
# Pack first = closest to right edge
tk.Label(footer, text="by Yellow Team", bg=LGREY, fg="#333333", font=f_footer).pack(
    side="right", padx=(0, 4), pady=5
)

# Red heart — proper filled heart shape
heart_canv = tk.Canvas(footer, width=18, height=17, bg=LGREY, highlightthickness=0)
heart_canv.pack(side="right", padx=0, pady=3)
# 8-point filled heart polygon
heart_canv.create_polygon(
    9,
    2,  # top centre dip
    12,
    5,  # upper right
    16,
    5,  # right of top lobe
    17,
    8,  # right of lobe
    9,
    16,  # bottom tip
    1,
    8,  # left of lobe
    2,
    5,  # left of top lobe
    6,
    5,  # upper left
    fill=RED_BTN,
    outline="",
)

tk.Label(footer, text="Made with ", bg=LGREY, fg="#333333", font=f_footer).pack(
    side="right", padx=(2, 0), pady=5
)

# ══════════════════════════════════════════════════════
# WAITING SCREEN
# ══════════════════════════════════════════════════════


def stop_pulse():
    global pulse_job
    if pulse_job:
        root.after_cancel(pulse_job)
        pulse_job = None


def stop_anim():
    global anim_job
    if anim_job:
        root.after_cancel(anim_job)
        anim_job = None


def go_home():
    """Return to home page without re-triggering request."""
    close_waiting(cancelled=True, re_request=False)


def open_waiting(line):
    global waiting, active_line, timer, wait_page

    if waiting:
        return

    waiting = True
    active_line = line

    # Reset the demo cycle for the requested line so the user can see a
    # fresh orange-to-green countdown start from the moment they tapped.
    _seed_arrivals_for_request(line)

    stop_pulse()
    stop_anim()
    threading.Thread(target=haptic_pulse, daemon=True).start()

    for btn in buttons.values():
        btn.configure(bg=BTN_DIS, cursor="arrow")

    idle_page.pack_forget()
    show_wait_page(line)

    if mqtt_ready:
        topic = request_topic(line)
        rc = client.publish(topic, f"STOP {STOP_NUMBER} -- {STOP_NAME} -- LINE {line}")
        if rc.rc != mqtt.MQTT_ERR_SUCCESS:
            _wait_set("Send failed", RED_BTN)
    else:
        _wait_set("Not connected", "#ff9900")

    timer = threading.Timer(REQUEST_TIMEOUT_SEC, _do_timeout)
    timer.start()


def show_wait_page(line):
    global wait_page, wait_cv, wait_rect, pulse_job, anim_job

    stop_pulse()
    stop_anim()

    if wait_page is not None:
        try:
            wait_page.destroy()
        except Exception:
            pass

    wait_page = tk.Frame(main, bg=WHITE)
    wait_page.pack(fill="both", expand=True)

    # ── Centre content ─────────────────────────────
    centre = tk.Frame(wait_page, bg=WHITE)
    centre.pack(expand=True, fill="both")

    big_lbl = tk.Label(
        centre, text=line, bg=WHITE, fg=NAVY, font=f_big, anchor="center"
    )
    big_lbl.pack(pady=(14, 0))

    tk.Label(
        centre,
        text="Request sent -- driver has been notified",
        bg=WHITE,
        fg=DGREY,
        font=f_body,
        anchor="center",
    ).pack()

    wait_sub = tk.Label(
        centre,
        text="The bus is on the way...",
        bg=WHITE,
        fg=BLUE,
        font=f_small,
        anchor="center",
    )
    wait_sub.pack()

    # Pulsing circle
    circle_frm = tk.Frame(centre, bg=WHITE)
    circle_frm.pack(pady=12)
    wait_cv = tk.Canvas(circle_frm, width=64, height=64, bg=WHITE, highlightthickness=0)
    wait_cv.pack()
    circle_id = wait_cv.create_oval(5, 5, 59, 59, fill="#004080", outline=YELLOW)

    # Progress bar
    pb_frame = tk.Frame(centre, bg=WHITE)
    pb_frame.pack(fill="x", padx=60)
    wait_rect = tk.Canvas(
        pb_frame, width=440, height=7, bg="#dde4ec", highlightthickness=0
    )
    wait_rect.pack()
    progress_id = wait_rect.create_rectangle(0, 0, 0, 7, fill=YELLOW, outline="")

    time_lbl = tk.Label(
        centre,
        text=f"Auto-reset in {REQUEST_TIMEOUT_SEC}s",
        bg=WHITE,
        fg=DGREY,
        font=f_small,
    )
    time_lbl.pack(pady=(4, 0))

    # ── Buttons row ────────────────────────────────
    btn_row = tk.Frame(centre, bg=WHITE)
    btn_row.pack(pady=(10, 14))

    # Cancel button (left)
    tk.Button(
        btn_row,
        text="CANCEL",
        font=f_cancel,
        bg=RED_BTN,
        fg=WHITE,
        activebackground="#aa1111",
        activeforeground=WHITE,
        relief="flat",
        cursor="hand2",
        width=14,
        command=lambda: _do_cancel(line),
    ).pack(side="left", padx=8)

    # Request another bus (right) — returns to home
    tk.Button(
        btn_row,
        text="REQUEST ANOTHER BUS",
        font=f_other,
        bg=BTN_BG,
        fg=WHITE,
        activebackground=BTN_HOV,
        activeforeground=WHITE,
        relief="flat",
        cursor="hand2",
        width=18,
        command=go_home,
    ).pack(side="left", padx=8)

    # Store refs
    wait_page._big = big_lbl
    wait_page._sub = wait_sub
    wait_page._lbl = time_lbl
    wait_page._cv = wait_cv
    wait_page._cid = circle_id

    # Start animations
    _pulse_circle(wait_cv, circle_id)
    _animate(wait_rect, progress_id, time_lbl)


def _wait_set(text, fg=None):
    if wait_page is None:
        return
    for attr in ["_sub", "_lbl"]:
        w = getattr(wait_page, attr, None)
        if w and w.winfo_exists():
            w.config(text=text, fg=fg or DGREY)


def _pulse_circle(canvas, item_id):
    global pulse_job

    def _p(scale=0.15, growing=True):
        if not waiting or wait_page is None:
            return
        try:
            s = int(5 + 49 * scale)
            e = int(59 - 49 * scale)
            canvas.coords(item_id, s, s, e, e)
            canvas.update()
        except Exception:
            return
        if growing:
            pulse_job = root.after(65, lambda: _p(min(scale + 0.06, 1.0), True))
        else:
            pulse_job = root.after(65, lambda: _p(max(scale - 0.06, 0.0), False))

    _p(0.5, True)


def _animate(canvas, rect_id, lbl):
    global anim_job
    WIDTH = 440
    elapsed = [0.0]
    STEP = 0.15

    def _step():
        if not waiting or wait_page is None:
            return
        elapsed[0] += STEP
        p = min(elapsed[0] / REQUEST_TIMEOUT_SEC, 1.0)
        try:
            canvas.coords(rect_id, 0, 0, int(WIDTH * p), 7)
            canvas.update()
        except Exception:
            return
        rem = max(0, int(REQUEST_TIMEOUT_SEC - elapsed[0]))
        if lbl.winfo_exists():
            lbl.config(text=f"Auto-reset in {rem}s" if rem > 0 else "Resetting...")
        if p < 1.0 and waiting:
            anim_job = root.after(int(STEP * 1000), _step)
        elif waiting:
            try:
                canvas.coords(rect_id, 0, 0, WIDTH, 7)
                canvas.update()
            except Exception:
                pass

    anim_job = root.after(int(STEP * 1000), _step)


def _do_timeout():
    root.after(0, lambda: close_waiting(timeout=True))


def _do_cancel(line):
    """User pressed cancel — reset to idle and tell bus Pi."""
    # Cancel the local timer
    global timer
    if timer:
        timer.cancel()
        timer = None

    # Publish cancelled to broker so bus Pi resets
    if mqtt_ready:
        client.publish(cancelled_topic(line), "CANCELLED")

    # Reset UI to home immediately
    close_waiting(cancelled=True, re_request=False)


def show_accepted():
    global waiting
    if not waiting:
        return
    waiting = False

    if wait_page is None:
        return

    stop_pulse()
    stop_anim()

    try:
        if hasattr(wait_page, "_cv") and hasattr(wait_page, "_cid"):
            wait_page._cv.itemconfigure(wait_page._cid, fill=GREEN_D, outline=GREEN)
        if hasattr(wait_page, "_big"):
            wait_page._big.config(fg=GREEN_D)
        if hasattr(wait_page, "_sub"):
            wait_page._sub.config(
                text="Driver accepted -- bus is on the way!", fg=GREEN_D
            )
        if hasattr(wait_page, "_lbl"):
            wait_page._lbl.config(text="Request confirmed", fg=GREEN_D)
    except Exception:
        pass

    root.after(6000, lambda: close_waiting(accepted=True))


def close_waiting(cancelled=False, timeout=False, accepted=False, re_request=True):
    global waiting, active_line, timer, wait_page, wait_cv, wait_rect

    stop_pulse()
    stop_anim()

    if not waiting and not accepted:
        return

    saved_line = active_line
    waiting = False

    if timer:
        timer.cancel()
        timer = None

    if wait_page is not None:
        try:
            wait_page.destroy()
        except Exception:
            pass
        wait_page = None
    wait_cv = None
    wait_rect = None

    # Reset each line button back to its own color (per-line)
    for line, btn in buttons.items():
        line_bg = LINE_COLORS.get(line, BTN_BG)
        btn.configure(bg=line_bg, cursor="hand2")

    if saved_line and saved_line in buttons:
        colour = GREEN_D if accepted else "#ff9900" if timeout else RED_BTN
        btn = buttons[saved_line]
        orig = btn.cget("bg")
        btn.config(bg=colour)
        root.after(800, lambda b=btn, o=orig: b.config(bg=o))

    if cancelled and re_request:
        root.after(400, lambda: open_waiting(saved_line))
        return

    if cancelled and not re_request:
        root.after(400, open_home)
        return

    active_line = None
    # After a request flow ends, return to the info screen (not the request grid)
    root.after(900, show_info)


def open_home():
    global waiting, active_line, timer, wait_page

    stop_pulse()
    stop_anim()

    if timer:
        timer.cancel()
        timer = None

    if wait_page is not None:
        try:
            wait_page.destroy()
        except Exception:
            pass
        wait_page = None

    waiting = False
    active_line = None
    wait_cv = None
    wait_rect = None

    for line, btn in buttons.items():
        line_bg = LINE_COLORS.get(line, BTN_BG)
        btn.configure(bg=line_bg, cursor="hand2")

    # "REQUEST ANOTHER BUS" → return to info screen
    show_info()


# ══════════════════════════════════════════════════════
# MQTT Setup
# ══════════════════════════════════════════════════════
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

try:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    for line in BUS_LINES:
        client.subscribe(accepted_topic(line))
except Exception as e:
    status_lbl.config(text=f"Broker unreachable: {e}", fg=RED_BTN)

update_clock()

# Show the info screen on startup and start the per-minute tick timer
print("[INFO] Initial state:", flush=True)
for line in BUS_LINES:
    stars = [s for s in range(3) if REAL_TIME.get((line, s))]
    star_str = f"  ★ on slots {stars}" if stars else ""
    print(f"  Line {line}: {ARRIVALS[line]}{star_str}", flush=True)
show_info()
_tick_arrivals()


def on_cleanup():
    global info_tick_job
    stop_pulse()
    stop_anim()
    if info_tick_job:
        try:
            root.after_cancel(info_tick_job)
        except Exception:
            pass
        info_tick_job = None
    if timer:
        timer.cancel()
    client.loop_stop()
    client.disconnect()
    root.destroy()
    sys.exit(0)


root.protocol("WM_DELETE_WINDOW", on_cleanup)

root.mainloop()
