"""
Check an episode's shots.json against the engine vocabulary before anything slow runs.

    python pipeline/validate.py episodes/<ep>

Exit code 1 on errors. Warnings are pacing / style hints (they don't block).
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vocab as V  # noqa: E402

PROP_KINDS = set(V.PROP_KINDS)
PLACE_KEYS = {"prop", "mark", "id", "dx", "dy", "z", "scale", "rot", "pop_at", "poof_at"}
CHANGE_KEYS = {"at", "pose", "face", "action", "scale", "over", "tint", "props", "to", "to_offset", "to_dx", "to_dy",
               "from", "to_side", "face_after"}
CAST_KEYS = {"name", "mark", "dx", "dy", "facing", "pose", "face", "action", "changes", "scale", "tint", "props",
             "to", "to_offset", "to_dx", "to_dy", "from", "to_side", "face_after"}


def validate(ep_dir):
    ep = Path(ep_dir)
    errs, warns = [], []
    E, W = errs.append, warns.append
    try:
        d = json.loads((ep / "shots.json").read_text(encoding="utf-8"))
    except Exception as e:
        return [f"shots.json unreadable: {e}"], []
    cat = V.catalog()
    sfx = set(V.sfx_names())
    fmts = set(V.formats())

    if d.get("format") not in fmts:
        E(f"format {d.get('format')!r} not in {sorted(fmts)}")
    for k in ("episode", "title", "shots"):
        if k not in d:
            E(f"missing top-level {k!r}")
    if d.get("episode") and d["episode"] != ep.name:
        E(f"episode {d['episode']!r} must equal the folder name {ep.name!r}")
    if d.get("music") and d["music"] not in V.music_moods():
        E(f"music {d['music']!r} not in {V.music_moods()}")

    custom = d.get("characters", {})
    for n, spec in custom.items():
        if spec.get("base", "Theo") not in V.PRESETS:
            E(f"character {n}: base {spec.get('base')!r} not in {V.PRESETS}")
        if spec.get("hair_style") and spec["hair_style"] not in V.HAIR_STYLES:
            E(f"character {n}: hair_style {spec['hair_style']!r} not in {V.HAIR_STYLES}")
        if spec.get("hat") not in V.HATS:
            E(f"character {n}: hat {spec.get('hat')!r} not in {V.HATS}")
        for x in spec.get("extras", []):
            if x not in V.EXTRAS:
                E(f"character {n}: extra {x!r} not in {V.EXTRAS}")
        for x in spec.get("details", []):
            if x not in V.DETAILS:
                E(f"character {n}: detail {x!r} not in {V.DETAILS}")
        if n in cat["characters"]:
            E(f"character {n}: name clashes with a prebuilt character")
    cast_ok = set(cat["characters"]) | set(custom)
    speakers = {"narrator"} | cast_ok

    ids = set()
    shots = d.get("shots", [])
    if not shots:
        E("no shots")
    for i, s in enumerate(shots):
        sid = s.get("id", f"#{i}")
        P = f"{sid}:"
        if sid in ids:
            E(f"{P} duplicate id")
        ids.add(sid)
        st = s.get("set")
        if st not in cat["sets"]:
            E(f"{P} set {st!r} not in {list(cat['sets'])}"); continue
        marks = cat["sets"][st]["marks"]
        if s.get("dressing") and s["dressing"] not in cat["sets"][st]["dressings"]:
            E(f"{P} dressing {s['dressing']!r} not in {cat['sets'][st]['dressings']}")
        text = (s.get("text") or "").strip()
        if s.get("speaker", "narrator") not in speakers:
            E(f"{P} speaker {s.get('speaker')!r} must be 'narrator' or a cast name")
        if not text and "duration" not in s:
            E(f"{P} silent shot needs a 'duration'")
        nw = len(text.split())
        if nw > 16:
            W(f"{P} {nw} words in one shot (~{nw / 2.8:.1f}s) - split it, cuts should land every 1.5-3 s")
        names = [c.get("name") for c in s.get("cast", [])]
        if len(names) != len(set(names)):
            E(f"{P} a character appears twice")
        cam = s.get("camera", {})
        if cam.get("shot", "medium") not in V.CAMERA_SHOTS:
            E(f"{P} camera.shot {cam.get('shot')!r} not in {V.CAMERA_SHOTS}")
        if cam.get("angle", "eye") not in V.CAMERA_ANGLES:
            E(f"{P} camera.angle {cam.get('angle')!r} not in {V.CAMERA_ANGLES}")
        if cam.get("move", "static") not in V.CAMERA_MOVES:
            E(f"{P} camera.move {cam.get('move')!r} not in {V.CAMERA_MOVES}")
        placed = set()
        for k, pl in enumerate(s.get("place", [])):
            R = f"{P} place[{k}]:"
            for key in pl:
                if key not in PLACE_KEYS:
                    E(f"{R} unknown key {key!r} (allowed {sorted(PLACE_KEYS)})")
            if str(pl.get("prop", "")).split(":")[0] not in PROP_KINDS:
                E(f"{R} prop {pl.get('prop')!r} not in {V.PROPS}")
            if pl.get("mark") not in marks:
                E(f"{R} mark {pl.get('mark')!r} not a mark of {st}")
            for key in ("dx", "dy", "z", "scale", "rot", "pop_at", "poof_at"):
                if key in pl and not isinstance(pl[key], (int, float)):
                    E(f"{R} {key} must be a number")
            if isinstance(pl.get("scale"), (int, float)) and not 0.1 <= pl["scale"] <= 30:
                W(f"{R} scale {pl['scale']} is extreme")
            for key in ("pop_at", "poof_at"):
                if isinstance(pl.get(key), (int, float)) and pl[key] < 0:
                    E(f"{R} {key} must be >= 0 seconds")
            pid = pl.get("id", f"place{k}")
            if pid in placed or pid in names:
                E(f"{R} id {pid!r} is used twice in this shot")
            placed.add(pid)
        tgt = cam.get("target")
        if tgt and tgt not in names and tgt not in marks and tgt not in placed:
            E(f"{P} camera.target {tgt!r} is neither a cast member, a mark of {st}, nor a placed prop id")
        if cam.get("shot") in ("two_shot", "over_shoulder") and len(names) < 2:
            W(f"{P} {cam.get('shot')} with fewer than 2 characters")
        if s.get("transition", "cut") not in V.TRANSITIONS:
            E(f"{P} transition {s.get('transition')!r} not in {V.TRANSITIONS}")
        for fx in s.get("fx", []):
            if fx.get("type") not in V.FX or fx.get("type") == "slowmo":
                E(f"{P} fx {fx.get('type')!r} not supported")
            if fx.get("type") == "tint" and fx.get("target") not in names:
                E(f"{P} tint target {fx.get('target')!r} not in this shot")
        for x in s.get("sfx", []):
            if x.get("name") not in sfx:
                E(f"{P} sfx {x.get('name')!r} not in {sorted(sfx)}")
        low = re.sub(r"[^\w' ]", "", text.lower()).split()
        for w in s.get("emphasis", []):
            if w.lower() not in low:
                W(f"{P} emphasis {w!r} is not a word of the line")
        for c in s.get("cast", []):
            n = c.get("name")
            Q = f"{P} {n}:"
            if n not in cast_ok:
                E(f"{Q} unknown character (prebuilt: {cat['characters']}, or define it in 'characters')")
            for k in c:
                if k not in CAST_KEYS:
                    E(f"{Q} unknown key {k!r}")
            if c.get("mark") not in marks:
                E(f"{Q} mark {c.get('mark')!r} not in {st} marks {[m for m in marks if not m.startswith('cam_')]}")
            if c.get("pose", "relaxed") not in V.POSES:
                E(f"{Q} pose {c.get('pose')!r} not in POSES")
            if c.get("face", "smile") not in V.FACES:
                E(f"{Q} face {c.get('face')!r} not in {V.FACES}")
            if c.get("action", "idle") not in V.ACTIONS:
                E(f"{Q} action {c.get('action')!r} not in ACTIONS")
            f = c.get("facing", "camera")
            if f not in ("camera", "left", "right", "away") and f not in names and f not in marks:
                E(f"{Q} facing {f!r} must be camera/left/right/away, a cast member of this shot or a mark")
            if c.get("pose") == "sit" and "seat" not in marks.get(c.get("mark"), {}):
                W(f"{Q} sits on mark {c.get('mark')!r} which has no seat (will hover / clip)")
            for p in c.get("props", []):
                if p.split(":")[0] not in PROP_KINDS:
                    E(f"{Q} prop {p!r} not in {V.PROPS}")
            if c.get("props") and cam.get("target") == n and cam.get("shot") in ("medium_close", "close_up", "extreme_close_up"):
                W(f"{Q} holds {c['props']} but the {cam.get('shot')} crops below the chest - use medium to show the prop")
            if c.get("to") and c["to"] not in marks:
                E(f"{Q} walk target {c['to']!r} not a mark of {st}")
            for ch in c.get("changes", []):
                for k in ch:
                    if k not in CHANGE_KEYS:
                        E(f"{Q} change has unknown key {k!r}")
                if "at" not in ch:
                    E(f"{Q} change without 'at'")
                if "pose" in ch and ch["pose"] not in V.POSES:
                    E(f"{Q} change pose {ch['pose']!r} unknown")
                if "face" in ch and ch["face"] not in V.FACES:
                    E(f"{Q} change face {ch['face']!r} unknown")
                if "action" in ch and ch["action"] not in V.ACTIONS:
                    E(f"{Q} change action {ch['action']!r} unknown")
                if ch.get("to") and ch["to"] not in marks:
                    E(f"{Q} change walk target {ch['to']!r} not a mark of {st}")
                for p in ch.get("props", []):
                    if p.split(":")[0] not in PROP_KINDS:
                        E(f"{Q} change prop {p!r} unknown")
    th = d.get("thumbnail", {})
    if th and th.get("shot") not in ids:
        E(f"thumbnail.shot {th.get('shot')!r} is not a shot id")
    if shots and len(shots) < 6:
        W(f"only {len(shots)} shots - short videos still need a cut every 1.5-3 s")
    return errs, warns


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    e, w = validate(sys.argv[1])
    for x in w:
        print("WARN ", x)
    for x in e:
        print("ERROR", x)
    print(f"{len(e)} error(s), {len(w)} warning(s)")
    sys.exit(1 if e else 0)
