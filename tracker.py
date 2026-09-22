import time

import M5
import lvgl as lv
import m5ui

import adsb_client
import config
import geocode
import settings
import wifi

COLUMNS = [
    ("FLIGHT", 240),
    ("TYPE", 150),
    ("ALT", 220),
    ("SPD", 190),
    ("DIST", 190),
    ("STATUS", 260),
]
TABLE_FONT = lv.font_montserrat_30
TABLE_X = 8
HEADER_Y = 68
HEADER_H = 54
TABLE_Y = HEADER_Y + HEADER_H
TABLE_H = 720 - TABLE_Y - 8

STATUS_ICONS = {
    "CLIMB": lv.SYMBOL.UP,
    "DESCEND": lv.SYMBOL.DOWN,
    "LEVEL": lv.SYMBOL.MINUS,
    "TAXI": lv.SYMBOL.DRIVE,
    "GROUND": lv.SYMBOL.HOME,
}

STATUS_FONT = lv.font_montserrat_24
BANNER_DURATION_S = 8
BANNER_UPDATING_S = 2
COLOR_UPDATING = 0xAAAAAA

ROW_HEIGHT = 52
MAX_ROWS = TABLE_H // ROW_HEIGHT
COLOR_TEXT_DEFAULT = 0xFFFFFF
COLOR_TEXT_NEW = 0x1B7A1B
COLOR_BORDER = 0x444444

# Landscape-only auto-rotate: accel X flips sign between the two landscape
# orientations (+ normal / - upside down) and stays small when the device is
# tilted toward portrait, so a simple threshold naturally ignores portrait
# tilts rather than needing to detect and exclude them explicitly.
ROTATION_CHECK_INTERVAL_S = 1
ROTATION_THRESHOLD = 0.5

state = {
    "lat": config.DEFAULT_LAT,
    "lon": config.DEFAULT_LON,
    "label": config.DEFAULT_LABEL,
    "seen": {},
    "baseline": True,
    "selected_result": None,
    "next_poll": 0,
    "banner_until": 0,
    "rotation": 3,
    "next_rotation_check": 0,
}

widgets = {}


def _rotate_to(new_rotation):
    M5.Display.setRotation(new_rotation)
    state["rotation"] = new_rotation
    # setRotation() only remaps the framebuffer - LVGL isn't told a rotation
    # happened, so it only repaints its own dirty regions and leaves stale
    # pixels from the old orientation. Force a full screen repaint.
    widgets["main_page"].invalidate()
    lv.refr_now(None)


def _check_rotation():
    x, _, _ = M5.Imu.getAccel()
    if x > ROTATION_THRESHOLD and state["rotation"] != 3:
        _rotate_to(3)
    elif x < -ROTATION_THRESHOLD and state["rotation"] != 1:
        _rotate_to(1)


def _set_banner(text, color, duration=BANNER_DURATION_S):
    for label in (widgets["status_label"], widgets["status_label_bold"]):
        label.set_text_color(color, 255, 0)
        label.set_text(text)
    widgets["status_label"].align_to(widgets["main_page"], lv.ALIGN.TOP_MID, 0, 16)
    widgets["status_label_bold"].align_to(widgets["main_page"], lv.ALIGN.TOP_MID, 1, 16)
    state["banner_until"] = time.time() + duration


def refresh_aircraft():
    # Sockets can't be created from a secondary _thread on this firmware
    # (confirmed: OSError -202 on socket creation, HTTP and HTTPS alike,
    # regardless of thread stack size) so this runs synchronously on the
    # UI thread; the "Updating..." label in loop() is the only mitigation.
    aircraft = adsb_client.fetch(state["lat"], state["lon"])
    now = time.time()
    current_hexes = set()
    new_hexes = set()
    for ac in aircraft:
        h = ac["hex"]
        current_hexes.add(h)
        if h not in state["seen"] and not state["baseline"]:
            new_hexes.add(h)
        state["seen"][h] = now
    state["baseline"] = False

    for h in list(state["seen"].keys()):
        if now - state["seen"][h] > config.FORGET_AFTER_S:
            del state["seen"][h]

    rows = widgets["rows"]
    if not aircraft:
        rows[0][0].set_text("No aircraft in range")
        rows[0][0].set_text_color(COLOR_TEXT_DEFAULT, 255, 0)
        for col in range(1, len(COLUMNS)):
            rows[0][col].set_text("")
        for r in range(1, len(rows)):
            for lbl in rows[r]:
                lbl.set_text("")
        return

    for i, row_labels in enumerate(rows):
        if i >= len(aircraft):
            for lbl in row_labels:
                lbl.set_text("")
            continue
        ac = aircraft[i]
        dist = "{:.0f}nm".format(ac["dist_nm"]) if ac["dist_nm"] is not None else "?"
        alt = ac["alt"] if ac["alt"] == "GND" else ac["alt"] + "ft"
        icon = STATUS_ICONS.get(ac["status"], "")
        values = [ac["callsign"], ac["type"], alt, ac["speed"] + "kt", dist, icon + " " + ac["status"]]
        color = COLOR_TEXT_NEW if ac["hex"] in new_hexes else COLOR_TEXT_DEFAULT
        for lbl, val in zip(row_labels, values):
            lbl.set_text(val)
            lbl.set_text_color(color, 255, 0)


def open_location_page():
    widgets["search_ta"].set_text("")
    widgets["results_list"].clean()
    widgets["result_label"].set_text("")
    widgets["set_btn"].set_flag(lv.obj.FLAG.HIDDEN, True)
    state["selected_result"] = None
    widgets["location_page"].screen_load()


def on_search():
    query = widgets["search_ta"].get_text().strip()
    if not query:
        return
    widgets["result_label"].set_text("Searching...")
    results = geocode.search(query)
    widgets["results_list"].clean()
    if not results:
        widgets["result_label"].set_text("No matches")
        return
    widgets["result_label"].set_text("")
    for r in results:
        btn = widgets["results_list"].add_button(0, text=r["label"])
        btn.add_event_cb(lambda e, rr=r: on_result_tap(rr), lv.EVENT.CLICKED, None)


def on_result_tap(result):
    state["selected_result"] = result
    widgets["result_label"].set_text("Selected: " + result["label"])
    widgets["set_btn"].set_flag(lv.obj.FLAG.HIDDEN, False)


def commit_location():
    result = state["selected_result"]
    if result is None:
        return
    state["lat"], state["lon"], state["label"] = result["lat"], result["lon"], result["label"]
    state["seen"] = {}
    state["baseline"] = True
    settings.save(state["lat"], state["lon"], state["label"])
    widgets["loc_btn"].set_btn_text(state["label"])
    widgets["main_page"].screen_load()


def build_main_page():
    page = m5ui.M5Page(bg_c=0x101418)

    m5ui.M5Label("ADSB Flight Display", x=16, y=10, text_c=0xFFFFFF, font=lv.font_montserrat_30, parent=page)

    loc_btn = m5ui.M5Button(state["label"], x=940, y=6, w=324, h=52, bg_c=0x2C3E50, text_c=0xFFFFFF, parent=page)
    loc_btn.add_event_cb(lambda e: open_location_page(), lv.EVENT.CLICKED, None)

    status_label = m5ui.M5Label("", x=600, y=16, text_c=0xAAAAAA, font=STATUS_FONT, parent=page)
    status_label_bold = m5ui.M5Label("", x=601, y=16, text_c=0xAAAAAA, font=STATUS_FONT, parent=page)

    x = TABLE_X
    for title, width in COLUMNS:
        hdr = m5ui.M5Button(
            title, x=x, y=HEADER_Y, w=width, h=HEADER_H, bg_c=0xB6F2B6, text_c=0x102010, font=TABLE_FONT, parent=page
        )
        hdr.set_flag(lv.obj.FLAG.CLICKABLE, False)
        x += width

    # M5Table has no working per-cell/per-row style override on this firmware
    # (tested: CELL_CTRL states and set_selected_cell both no-op visually), so
    # the grid is built from individual labels instead, which do support it.
    rows = []
    for r in range(MAX_ROWS):
        row_labels = []
        x = TABLE_X
        y = TABLE_Y + r * ROW_HEIGHT
        for _, width in COLUMNS:
            lbl = m5ui.M5Label("", x=x, y=y + 10, text_c=COLOR_TEXT_DEFAULT, font=TABLE_FONT, parent=page)
            lbl.set_width(width - 12)
            lbl.set_border_color(COLOR_BORDER, 255, 0)
            lbl.set_style_border_width(1, 0)
            lbl.set_style_pad_all(6, 0)
            row_labels.append(lbl)
            x += width
        rows.append(row_labels)

    widgets["main_page"] = page
    widgets["loc_btn"] = loc_btn
    widgets["status_label"] = status_label
    widgets["status_label_bold"] = status_label_bold
    widgets["rows"] = rows
    return page


def build_location_page():
    page = m5ui.M5Page(bg_c=0x101418)

    m5ui.M5Label("Set location", x=16, y=12, text_c=0xFFFFFF, font=lv.font_montserrat_24, parent=page)

    back_btn = m5ui.M5Button("Back", x=1140, y=8, w=124, h=44, bg_c=0x2C3E50, text_c=0xFFFFFF, parent=page)
    back_btn.add_event_cb(lambda e: widgets["main_page"].screen_load(), lv.EVENT.CLICKED, None)

    search_ta = m5ui.M5TextArea(x=16, y=64, w=700, h=50, placeholder="Search city or place", parent=page)
    search_ta.set_one_line(True)

    search_btn = m5ui.M5Button("Search", x=726, y=64, w=140, h=50, bg_c=0x2980B9, text_c=0xFFFFFF, parent=page)
    search_btn.add_event_cb(lambda e: on_search(), lv.EVENT.CLICKED, None)

    set_btn = m5ui.M5Button("Set location", x=876, y=64, w=220, h=50, bg_c=0x27AE60, text_c=0xFFFFFF, parent=page)
    set_btn.add_event_cb(lambda e: commit_location(), lv.EVENT.CLICKED, None)
    set_btn.set_flag(lv.obj.FLAG.HIDDEN, True)

    result_label = m5ui.M5Label("", x=16, y=126, text_c=0xBBBBBB, parent=page)

    results_list = m5ui.M5List(x=16, y=156, w=1248, h=294, parent=page)

    keyboard = m5ui.M5Keyboard(x=0, y=466, w=1280, h=254, target_textarea=search_ta, parent=page)

    widgets["location_page"] = page
    widgets["search_ta"] = search_ta
    widgets["result_label"] = result_label
    widgets["results_list"] = results_list
    widgets["set_btn"] = set_btn
    widgets["keyboard"] = keyboard
    return page


def setup():
    M5.begin()
    M5.Display.setRotation(3)
    m5ui.init()

    lat, lon, label = settings.load()
    state["lat"], state["lon"], state["label"] = lat, lon, label

    build_main_page()
    build_location_page()
    widgets["main_page"].screen_load()

    wifi.connect()


def loop():
    M5.update()
    now = time.time()
    if now >= state["next_rotation_check"]:
        state["next_rotation_check"] = now + ROTATION_CHECK_INTERVAL_S
        try:
            _check_rotation()
        except Exception as e:
            print("rotation check error:", e)
    if now >= state["next_poll"]:
        state["next_poll"] = now + config.POLL_INTERVAL_S
        if now >= state["banner_until"]:
            _set_banner("Updating...", COLOR_UPDATING, duration=BANNER_UPDATING_S)
            M5.update()
        try:
            refresh_aircraft()  # on failure: leaves the table showing last-known-good data
        except Exception as e:
            print("poll error:", e)  # logged only - user asked not to surface this in the header

    if time.time() >= state["banner_until"] and widgets["status_label"].get_text():
        widgets["status_label"].set_text("")
        widgets["status_label_bold"].set_text("")


def run():
    setup()
    while True:
        loop()
        time.sleep_ms(10)
