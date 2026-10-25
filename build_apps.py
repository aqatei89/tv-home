"""Write apps.json for the launcher from the TV's app list (applist.json, pulled over the remote channel).
Colours are worked out here because the TV's browser may not read VIDAA's icons (no CORS)."""
import base64, io, json, sys, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
apps = json.loads((ROOT / "applist.json").read_text(encoding="utf-8"))
CFG = json.loads((ROOT / "launcher.json").read_text(encoding="utf-8"))
hidden, native, web_urls = set(CFG["hidden"]), set(CFG["native"]), CFG.get("web_urls", {})

def icon_url(a):
    raw = a.get("httpIcon") or ""
    return raw[raw.find("http"):] if "http" in raw else ""

def colours(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=15).read())).convert("RGBA")
    except Exception as e:
        print("icon failed", url, e); return {}
    small = img.resize((24, 24))
    px = small.load(); er = eg = eb = en = 0; vr = vg = vb = vw = 0.0
    for y in range(24):
        for x in range(24):
            r, g, b, a = px[x, y]
            if a < 200: continue
            if x in (0, 23): er += r; eg += g; eb += b; en += 1
            mx, mn = max(r, g, b), min(r, g, b); sat = (mx - mn) / mx if mx else 0; w = sat * sat * (mx / 255)
            vr += r * w; vg += g * w; vb += b * w; vw += w
    w, h = img.size
    back = Image.new("RGBA", (2, 5))
    back.paste(img.crop((0, 0, 2, h)).resize((1, 5)), (0, 0)); back.paste(img.crop((w - 2, 0, w, h)).resize((1, 5)), (1, 0))
    buf = io.BytesIO(); back.save(buf, "PNG")
    out = {"backdrop": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}
    if en > 20: out["bg"] = f"rgb({round(er/en)},{round(eg/en)},{round(eb/en)})"
    out["glow"] = [round(vr/vw), round(vg/vw), round(vb/vw)] if vw > 2 else [150, 150, 160]
    return out

out = []
for a in apps:
    aid = str(a.get("appId")); url = str(web_urls.get(aid, a.get("url", ""))).strip()
    if aid in hidden: continue
    is_web = str(url).startswith(("http://", "https://"))
    e = {"appId": aid, "name": a.get("name", "").replace("▶", "").split(" : ")[0].strip(), "icon": icon_url(a)}
    if aid in CFG.get("names", {}): e["name"] = CFG["names"][aid]
    if is_web: e["url"] = url.strip()
    else: e.update(native=True, nurl=a.get("url", ""), storeType=a.get("storeType", 99))
    e.update(colours(e["icon"]) if e["icon"] else {})
    out.append(e)
data = {"apps": out, "dock": CFG["dock"], "helper_dock": CFG["dock"], "sources": [], "browser": {},
        "greeting_name": CFG.get("greeting_name", ""), "clock_24h": CFG.get("clock_24h", False), "native_ok": CFG.get("native_ok")}
(ROOT / "apps.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"apps.json: {len(out)} apps, {sum(1 for e in out if e.get('native'))} native:", ", ".join(e["name"] for e in out))
