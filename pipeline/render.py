"""
Render helper, run on a built episode file:
    blender -b <ep>/<ep>.blend --python pipeline/render.py -- raw   preview|final
    blender -b <ep>/<ep>.blend --python pipeline/render.py -- sheet            # one still per shot -> render/sheet/
    blender -b <ep>/<ep>.blend --python pipeline/render.py -- thumb  <frame>   # full-res still -> render/thumb.png

preview = 540x960, few samples (fast check). final = 1080x1920, more samples, raytraced reflections.
"""
import bpy, os, sys, json

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode = argv[0] if argv else "raw"
sc = bpy.context.scene
r = sc.render
ep = os.path.dirname(bpy.data.filepath)
out_dir = os.path.join(ep, "render")
os.makedirs(out_dir, exist_ok=True)

QUALITY = {
    "preview": dict(pct=50, samples=2, rt=False),
    "final":   dict(pct=100, samples=48, rt=True),
    "sheet":   dict(pct=25, samples=8, rt=False),
    "thumb":   dict(pct=100, samples=64, rt=True),
}


def apply(q):
    r.resolution_percentage = q["pct"]
    try:
        sc.eevee.taa_render_samples = q["samples"]
        sc.eevee.use_raytracing = q["rt"]
        sc.eevee.shadow_pool_size = "1024"
    except Exception:
        pass
    r.use_motion_blur = False


def still(frame, path):
    try:
        r.image_settings.media_type = 'IMAGE'
    except Exception:
        pass
    r.image_settings.file_format = 'PNG'
    sc.frame_set(frame)
    r.filepath = path
    bpy.ops.render.render(write_still=True)


if mode == "raw":
    q = argv[1] if len(argv) > 1 else "preview"
    apply(QUALITY[q])
    r.filepath = os.path.join(out_dir, f"raw_{q}.mp4")
    print(f"RENDER raw {q} {sc.frame_start}-{sc.frame_end} -> {r.filepath}", flush=True)
    bpy.ops.render.render(animation=True)
    print("DONE", r.filepath, flush=True)
elif mode == "sheet":
    apply(QUALITY["sheet"])
    sheet = os.path.join(out_dir, "sheet")
    os.makedirs(sheet, exist_ok=True)
    marks = sorted(sc.timeline_markers, key=lambda m: m.frame)
    ends = [m.frame for m in marks[1:]] + [sc.frame_end + 1]
    info = []
    for m, e in zip(marks, ends):
        f = (m.frame + e) // 2 if len(argv) < 2 else min(e - 1, m.frame + int(argv[1]))
        p = os.path.join(sheet, f"{m.name}.png")
        still(f, p)
        info.append({"id": m.name, "frame": f, "png": p})
    with open(os.path.join(sheet, "sheet.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    print("DONE sheet", len(info), flush=True)
elif mode == "thumb":
    apply(QUALITY["thumb"])
    still(int(argv[1]) if len(argv) > 1 else 1, os.path.join(out_dir, "thumb.png"))
    print("DONE thumb", flush=True)
