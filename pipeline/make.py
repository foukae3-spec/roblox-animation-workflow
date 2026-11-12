"""
One command from shots.json to a finished, upload-ready video.

    python pipeline/make.py episodes/<ep>                 # preview: validate, voice, build, sheet, raw, edit
    python pipeline/make.py episodes/<ep> --final         # 1080x1920 + no-music copy + thumbnail + publish/
    python pipeline/make.py episodes/<ep> --only sheet    # run single stages (comma list)
    python pipeline/make.py episodes/<ep> --from build    # resume from a stage

Stages: validate, voice, build, sheet, raw, edit, thumb, publish
  sheet   -> render/contact_sheet.png  (one labelled still per shot: the quick visual check)
  raw     -> render/raw_<q>.mp4        (3D only, no sound)
  edit    -> out/<ep>_<q>.mp4          (voice + music + sfx + captions + transitions)
  publish -> publish/<ep>/             (final mp4s, thumbnail, tiktok.txt, youtube.txt)
Blender logs go to render/logs/<stage>.log.
"""
import argparse, glob, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"
STAGES = ["validate", "voice", "build", "sheet", "raw", "edit", "thumb", "publish"]


def blender_exe():
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    found = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"),
                   key=lambda p: [int(x) if x.isdigit() else x for x in Path(p).parent.name.split()[-1].split(".")])
    if found:
        return found[-1]
    which = shutil.which("blender")
    if which:
        return which
    sys.exit("Blender not found: set the BLENDER environment variable to blender.exe")


def run(cmd, log=None, label=""):
    t = time.time()
    print(f"[{label}] ...", flush=True)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "w", encoding="utf-8", errors="replace") as fh:
            p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)
        text = log.read_text(encoding="utf-8", errors="replace")
        failed = p.returncode != 0 or "Traceback" in text or "DONE" not in text and "BUILT" not in text
        if failed:
            print("\n".join(text.splitlines()[-40:]))
            sys.exit(f"[{label}] FAILED (log: {log})")
    else:
        p = subprocess.run(cmd, cwd=ROOT)
        if p.returncode != 0:
            sys.exit(f"[{label}] FAILED")
    print(f"[{label}] ok  {time.time() - t:.0f}s", flush=True)


def contact_sheet(ep, data):
    from PIL import Image, ImageDraw, ImageFont
    info = json.loads((ep / "render" / "sheet" / "sheet.json").read_text())
    text = {s["id"]: s.get("text", "") for s in data["shots"]}
    ims = [Image.open(i["png"]).convert("RGB") for i in info]
    w, h = ims[0].size
    cols = min(8, len(ims)); rows = (len(ims) + cols - 1) // cols
    lab = 46
    S = Image.new("RGB", (w * cols, (h + lab) * rows), (20, 20, 24))
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(S)
    for k, (im, i) in enumerate(zip(ims, info)):
        x, y = (k % cols) * w, (k // cols) * (h + lab)
        S.paste(im, (x, y))
        t = f"{i['id']}  {text.get(i['id'], '')}"
        lines, cur = [], ""
        for word in t.split():
            if len(cur) + len(word) > w // 7:
                lines.append(cur); cur = word
            else:
                cur = (cur + " " + word).strip()
        lines.append(cur)
        for j, ln in enumerate(lines[:3]):
            d.text((x + 4, y + h + 2 + j * 14), ln, fill=(235, 235, 235), font=font)
    out = ep / "render" / "contact_sheet.png"
    S.save(out)
    print("contact sheet:", out)


def thumbnail(ep, data, fmt):
    from PIL import Image, ImageDraw, ImageFont
    src = ep / "render" / "thumb.png"
    im = Image.open(src).convert("RGB")
    hook = data.get("hook_title") or data.get("title", "")
    if hook:
        d = ImageDraw.Draw(im)
        W, H = im.size
        size = int(W * 0.085)
        try:
            font = ImageFont.truetype(r"C:\Windows\Fonts\seguibl.ttf", size)
        except Exception:
            font = ImageFont.load_default()
        words, lines, cur = hook.split(), [], ""
        for wd in words:
            test = (cur + " " + wd).strip()
            if d.textlength(test, font=font) > W * 0.86:
                lines.append(cur); cur = wd
            else:
                cur = test
        lines.append(cur)
        lh = int(size * 1.15)
        top = int(H * 0.08)
        box_h = lh * len(lines) + int(size * 0.5)
        d.rounded_rectangle((int(W * 0.04), top, int(W * 0.96), top + box_h), radius=int(size * 0.4), fill=(255, 255, 255))
        for j, ln in enumerate(lines):
            tw = d.textlength(ln, font=font)
            d.text(((W - tw) / 2, top + int(size * 0.2) + j * lh), ln, fill=(15, 15, 18), font=font)
    out = ep / "out" / "thumbnail.png"
    out.parent.mkdir(exist_ok=True)
    im.save(out)
    print("thumbnail:", out)


def publish(ep, data, fmt):
    dst = ROOT / "publish" / data["episode"]
    dst.mkdir(parents=True, exist_ok=True)
    for f in (ep / "out").glob("*_final.mp4"):
        shutil.copy2(f, dst / f.name)
    if (ep / "out" / "thumbnail.png").exists():
        shutil.copy2(ep / "out" / "thumbnail.png", dst / "thumbnail.png")
    pub = data.get("publish", {})
    fp = fmt.get("publish", {})
    tags = list(dict.fromkeys(pub.get("hashtags", []) + fp.get("hashtags", [])))
    tt = pub.get("tiktok_caption", data.get("title", ""))
    (dst / "tiktok.txt").write_text(f"{tt}\n\n{' '.join(tags)}\n", encoding="utf-8")
    yt_title = pub.get("youtube_title", data.get("title", ""))
    yt_desc = pub.get("youtube_description", data.get("logline", data.get("title", "")))
    yt_tags = list(dict.fromkeys(pub.get("tags", []) + fp.get("youtube_tags", [])))
    (dst / "youtube.txt").write_text(
        f"TITLE:\n{yt_title}\n\nDESCRIPTION:\n{yt_desc}\n\n{' '.join(tags)}\n\nTAGS:\n{', '.join(yt_tags)}\n",
        encoding="utf-8")
    print("publish package:", dst)
    for p in sorted(dst.iterdir()):
        print("   ", p.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--from", dest="start", default="")
    a = ap.parse_args()
    ep = Path(a.episode_dir).resolve()
    q = "final" if a.final else "preview"
    if a.only:
        stages = [s for s in a.only.split(",") if s]
    else:
        stages = ["validate", "voice", "build", "sheet", "raw", "edit"] + (["thumb", "publish"] if a.final else [])
        if a.start:
            stages = stages[stages.index(a.start):]
    bad = [s for s in stages if s not in STAGES]
    if bad:
        sys.exit(f"unknown stage(s) {bad}; stages: {STAGES}")

    data = json.loads((ep / "shots.json").read_text(encoding="utf-8"))
    fp = ROOT / "formats" / data.get("format", "_") / "format.json"
    fmt = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    B = blender_exe()
    blend = ep / f"{data['episode']}.blend"
    logs = ep / "render" / "logs"
    py = sys.executable
    t0 = time.time()

    for st in stages:
        if st == "validate":
            run([py, str(PIPE / "validate.py"), str(ep)], label="validate")
        elif st == "voice":
            run([py, str(PIPE / "voiceover.py"), str(ep)], label="voice")
        elif st == "build":
            run([B, "-b", "--factory-startup", "--python", str(PIPE / "episode.py"), "--", str(ep)], logs / "build.log", "build")
        elif st == "sheet":
            run([B, "-b", str(blend), "--python", str(PIPE / "render.py"), "--", "sheet"], logs / "sheet.log", "sheet")
            contact_sheet(ep, data)
        elif st == "raw":
            run([B, "-b", str(blend), "--python", str(PIPE / "render.py"), "--", "raw", q], logs / f"raw_{q}.log", f"raw {q}")
        elif st == "edit":
            run([B, "-b", "--factory-startup", "--python", str(PIPE / "edit.py"), "--", str(ep), q], logs / f"edit_{q}.log", f"edit {q}")
            if q == "final":
                run([B, "-b", "--factory-startup", "--python", str(PIPE / "edit.py"), "--", str(ep), q, "--no-music"],
                    logs / "edit_final_nomusic.log", "edit final (no music)")
        elif st == "thumb":
            timing = json.loads((ep / "timing.json").read_text(encoding="utf-8"))
            th = data.get("thumbnail", {})
            T = {s["id"]: s for s in timing["shots"]}
            sid = th.get("shot") or data["shots"][min(1, len(data["shots"]) - 1)]["id"]
            fr = T[sid]["start_frame"] + int(round(th.get("at", T[sid]["duration"] / 2) * data.get("fps", 30)))
            run([B, "-b", str(blend), "--python", str(PIPE / "render.py"), "--", "thumb", str(fr)], logs / "thumb.log", "thumb")
            thumbnail(ep, data, fmt)
        elif st == "publish":
            publish(ep, data, fmt)
    outs = sorted((ep / "out").glob(f"*_{q}.mp4")) if (ep / "out").exists() else []
    print(f"\nfinished in {(time.time() - t0) / 60:.1f} min")
    for o in outs:
        print("video:", o)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
