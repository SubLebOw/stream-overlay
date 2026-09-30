#!/usr/bin/env python3
"""Builds the portable OBS scene collection obs/trynd-web-scenes.json (OBS 30.x format) and embeds the
same template into tools/make-scenes.html (so that page works offline, e.g. opened from a USB stick).

The overlay URLs use the placeholder base  https://YOUR-SITE/  -> swap it with tools/make-scenes.html.
Run:  python scripts/build_obs_scenes.py
"""
import json
import os
import re
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://YOUR-SITE/"
PREV_VER = 503447555  # libobs 30.2.3  (30 << 24 | 2 << 16 | 3)
NS = uuid.UUID("7b0c6a52-7f1e-4d0e-9a3a-5452594e4430")
CANVAS = (1920.0, 1080.0)
LOL_WINDOW = "League of Legends (TM) Client:RiotWindowClass:League of Legends.exe"
BROWSER_CSS = "body { background-color: rgba(0, 0, 0, 0); margin: 0px auto; overflow: hidden; }"


def uid(name):
    return str(uuid.uuid5(NS, name))


def source(name, sid, settings, **extra):
    d = {
        "prev_ver": PREV_VER, "name": name, "uuid": uid(name), "id": sid, "versioned_id": sid,
        "settings": settings, "mixers": 255 if sid not in ("scene",) else 0, "sync": 0, "flags": 0,
        "volume": 1.0, "balance": 0.5, "enabled": True, "muted": False,
        "push-to-mute": False, "push-to-mute-delay": 0, "push-to-talk": False, "push-to-talk-delay": 0,
        "hotkeys": {}, "deinterlace_mode": 0, "deinterlace_field_order": 0, "monitoring_type": 0,
        "private_settings": {},
    }
    d.update(extra)
    return d


def browser(name, path):
    return source(name, "browser_source", {
        "is_local_file": False, "url": BASE + path, "width": 1920, "height": 1080,
        "fps_custom": False, "fps": 30, "reroute_audio": False,
        "restart_when_active": False, "shutdown": False,   # keep chat connected when hidden
        "css": BROWSER_CSS, "webpage_control_level": 1,
    }, mixers=255)


def item(src, iid, visible=True, pos=(0.0, 0.0), bounds=None, locked=False):
    it = {
        "name": src["name"], "source_uuid": src["uuid"], "visible": visible, "locked": locked,
        "rot": 0.0, "pos": {"x": float(pos[0]), "y": float(pos[1])}, "scale": {"x": 1.0, "y": 1.0},
        "align": 5,  # top-left
        "bounds_type": 0, "bounds_align": 0, "bounds_crop": False, "bounds": {"x": 0.0, "y": 0.0},
        "crop_left": 0, "crop_top": 0, "crop_right": 0, "crop_bottom": 0,
        "id": iid, "group_item_backup": False, "scale_filter": "disable",
        "blend_method": "default", "blend_type": "normal",
        "show_transition": {"duration": 0}, "hide_transition": {"duration": 0}, "private_settings": {},
    }
    if bounds:  # "Scale to inner bounds", centred: any capture resolution fits the box without stretching
        it.update({"bounds_type": 2, "bounds_align": 0, "bounds": {"x": float(bounds[0]), "y": float(bounds[1])}})
    return it


def scene(name, items):
    return source(name, "scene", {"id_counter": len(items), "custom_size": False, "items": items},
                  mixers=0, volume=1.0)


def build():
    display = source("Display Capture (fallback - turn on if Game Capture is black)", "monitor_capture",
                     {"method": 0, "capture_cursor": True, "force_sdr": False}, mixers=0)
    game = source("Game Capture (League of Legends)", "game_capture", {
        "capture_mode": "window", "window": LOL_WINDOW, "priority": 2,  # match by .exe
        "sli_compatibility": False, "capture_cursor": True, "allow_transparency": False,
        "premultiplied_alpha": False, "limit_framerate": False, "capture_overlays": False,
        "anti_cheat_hook": True, "hook_rate": 1,
    }, mixers=255)
    overlay = browser("Trynd Overlay (chat + rank + song)", "overlay.html?channel=calebgcameron")
    cam = source("Webcam (optional)", "dshow_input", {"video_device_id": "", "active": True}, mixers=255)
    queue = browser("Trynd Queue Scene", "queue.html?timer=1")

    game_scene = scene("Game", [
        item(display, 1, visible=False, bounds=CANVAS),
        item(game, 2, bounds=CANVAS),
        item(overlay, 3, locked=True),
    ])
    queue_scene = scene("Queue", [
        item(cam, 1, pos=(80, 222), bounds=(640, 360)),   # camera sits BEHIND the queue overlay's frame
        item(queue, 2, locked=True),
    ])
    desktop = source("Desktop Audio", "wasapi_output_capture", {"device_id": "default"}, mixers=255)
    mic = source("Mic/Aux", "wasapi_input_capture", {"device_id": "default"}, mixers=255)
    return {
        "DesktopAudioDevice1": desktop,
        "AuxAudioDevice1": mic,
        "current_scene": "Game",
        "current_program_scene": "Game",
        "scene_order": [{"name": "Game"}, {"name": "Queue"}],
        "name": "Trynd Web Overlay",
        "sources": [game_scene, queue_scene, display, game, overlay, cam, queue],
        "groups": [],
        "quick_transitions": [
            {"name": "Cut", "duration": 300, "hotkeys": [], "id": 1, "fade_to_black": False},
            {"name": "Fade", "duration": 300, "hotkeys": [], "id": 2, "fade_to_black": False},
            {"name": "Fade", "duration": 300, "hotkeys": [], "id": 3, "fade_to_black": True},
        ],
        "transitions": [],
        "saved_projectors": [],
        "current_transition": "Fade",
        "transition_duration": 300,
        "preview_locked": False,
        "scaling_enabled": False,
        "scaling_level": 0,
        "scaling_off_x": 0.0,
        "scaling_off_y": 0.0,
        "virtual-camera": {"type2": 3},
        "modules": {"scripts-tool": [], "output-timer": {"streamTimerHours": 0, "streamTimerMinutes": 0,
                    "streamTimerSeconds": 30, "recordTimerHours": 0, "recordTimerMinutes": 0,
                    "recordTimerSeconds": 30, "autoStartStreamTimer": False, "autoStartRecordTimer": False,
                    "pauseRecordTimer": True}, "auto-scene-switcher": {"interval": 300, "non_matching_scene": "",
                    "switch_if_not_matching": False, "active": False, "switches": []}},
    }


def main():
    data = build()
    out = os.path.join(ROOT, "obs", "trynd-web-scenes.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")
    page = os.path.join(ROOT, "tools", "make-scenes.html")
    html = open(page, encoding="utf-8").read()
    blob = json.dumps(data, separators=(",", ":"))
    html2, n = re.subn(r"/\*TEMPLATE\*/.*?/\*END\*/", lambda m: "/*TEMPLATE*/" + blob + "/*END*/", html, flags=re.S)
    assert n == 1, "marker not found in make-scenes.html"
    with open(page, "w", encoding="utf-8") as f:
        f.write(html2)
    print("wrote", out, "and embedded it in", page)


if __name__ == "__main__":
    main()
