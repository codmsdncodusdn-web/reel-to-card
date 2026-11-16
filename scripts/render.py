#!/usr/bin/env python3
"""slides.json → 슬라이드별 PNG.

디자인은 '값'으로 정한다: 기본 묶음(프리셋 또는 저장해 둔 내 스타일) 위에 값을 덮어쓴다.
설치된 Chrome·Edge·Chromium을 화면 없이 실행해 찍는다 (Windows / Mac / Linux, 추가 설치 없음).

사용: python render.py <slides.json> [--out <폴더>] [--format carousel|square|story] [--style <이름>]
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = {"carousel": (1080, 1350), "square": (1080, 1080), "story": (1080, 1920)}
REEL_HOME = Path.home() / ".reel-skills"
STYLE_DIR = REEL_HOME / "card-styles"

# ───────────────────────────── 디자인 값
DEFAULT = {
    # 색
    "bg": "#0E0E0E", "text": "#FFFFFF", "accent": "#FFE53B",
    "accent2": None,        # 넣으면 accent→accent2 그라데이션을 쓸 수 있다
    "keyword_color": None,  # 마지막 장 키워드 색 (없으면 accent)
    "card_bg": None, "card_text": None,  # 목록 상자 색 (없으면 item에 맞춰 자동)
    # 글자
    "font": "gothic",       # 제목 글꼴: FONTS 참고
    "font_file": None,      # 내 글꼴 파일(.ttf/.otf/.woff2) 경로 — font보다 우선
    "weight": 800, "tracking": -0.02, "scale": 1.0,
    "title_size": 1.0,      # 본문 장 제목 크기 배율 (표지·마지막 장 제외)
    "emphasis": "color",    # *별표* 표시 방식
    "title_color": "text",  # 본문 장 제목 색
    # 배치
    "align": "left", "valign": "center", "radius": 28, "margin": 88,
    # 표지
    "cover": "fade",        # 장면: fade(위에 깔고 아래로 녹임) | framed(액자) | full(전체)
    "cover_image": 0.6,     # fade일 때 장면이 차지하는 높이 비율 (0.4~1.0)
    "cover_kicker": "inline",  # inline | tag(오른쪽 위 알약)
    "cover_divider": False,    # 제목 아래 가는 선 + @아이디
    "swipe": "fill",        # '넘겨서 보기' 버튼: fill | outline | none
    # 본문
    "image_mode": "shot",   # 본문 장의 장면: shot(사진 칸) | full(배경 전체)
    "item": "card", "bullet": "dot", "number": "fill", "kicker": "plain", "quote": "bar",
    # 마지막 장
    "cta": "box",           # box(키워드 상자) | button(아이콘+버튼+아이디)
    "cta_icon": "bookmark", "button_text": "지금 바로 팔로우하세요",
    # 그 밖
    "pattern": "glow", "pattern_on": "all", "footer": "full",
    "handle": "", "tagline": "",
}
ENUMS = {
    "emphasis": ["color", "gradient", "highlight", "box", "underline"],
    "title_color": ["text", "accent", "gradient"],
    "align": ["left", "center"], "valign": ["top", "center", "bottom"],
    "cover": ["fade", "framed", "full"], "cover_kicker": ["inline", "tag"],
    "swipe": ["fill", "outline", "none"], "image_mode": ["shot", "full"],
    "item": ["card", "line", "plain", "fill", "shadow"],
    "bullet": ["dot", "square", "dash", "check"], "number": ["fill", "outline", "plain"],
    "kicker": ["plain", "pill", "soft", "outline", "line"], "quote": ["bar", "mark", "plain"],
    "cta": ["box", "button"], "cta_icon": ["bookmark", "comment", "heart", "send", "none"],
    "pattern": ["none", "glow", "grid", "dots"], "pattern_on": ["all", "cover", "content", "cta"],
    "footer": ["full", "dots", "page", "handle", "none"],
}
META_KEYS = {"base", "name", "note", "source"}

# 기본 묶음 (출발점). 여기에 값을 덮어써서 릴스마다 다르게 만든다.
PRESETS = {
    "bold": {},
    "paper": {"bg": "#F3EEE4", "text": "#1C1917", "accent": "#C2410C", "font": "serif", "weight": 900,
              "tracking": -0.035, "radius": 4, "cover": "framed", "item": "line", "number": "outline",
              "kicker": "line", "quote": "mark", "swipe": "outline", "pattern": "none"},
    "photo": {"bg": "#0A0A0A", "accent": "#7CF5C0", "cover": "full", "image_mode": "full", "pattern": "none"},
    "pop": {"bg": "#FF6B3D", "text": "#111111", "accent": "#111111", "weight": 900, "emphasis": "box",
            "cover": "framed", "item": "shadow", "kicker": "pill", "radius": 22, "pattern": "none"},
    "clean": {"bg": "#FFFFFF", "text": "#111827", "accent": "#2563EB", "emphasis": "highlight",
              "cover": "framed", "item": "fill", "kicker": "soft", "radius": 24, "pattern": "none"},
}
THEMES = PRESETS  # 예전 이름

# 제목 글꼴: (CSS 이름, 구글 폰트 요청값)
FONTS = {
    "gothic": ('"Pretendard"', None),                               # 깔끔한 고딕
    "serif": ('"Noto Serif KR"', "Noto+Serif+KR:wght@600;900"),     # 명조
    "soft-serif": ('"Gowun Batang"', "Gowun+Batang:wght@400;700"),  # 부드러운 명조
    "round": ('"Jua"', "Jua"),                                      # 둥근 글씨
    "hand": ('"Gaegu"', "Gaegu:wght@400;700"),                      # 손글씨
    "display": ('"Black Han Sans"', "Black+Han+Sans"),              # 아주 두꺼운 제목용
    "retro": ('"Do Hyeon"', "Do+Hyeon"),                            # 복고풍 고딕
    "tech": ('"IBM Plex Sans KR"', "IBM+Plex+Sans+KR:wght@500;700"),  # 기술·개발 느낌
}
FALLBACK = '"Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif'

ICONS = {
    "bookmark": "M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z",
    "comment": "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z",
    "heart": "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z",
    "send": "M2.01 21L23 12 2.01 3 2 10l15 2-15 2z",
}


class RenderError(Exception):
    def __init__(self, msg: str, hint: str = ""):
        super().__init__(msg)
        self.hint = hint


# ───────────────────────────── 색 계산
def _rgb(c) -> tuple[int, int, int] | None:
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", str(c or "").strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lum(c) -> float | None:
    rgb = _rgb(c)
    if not rgb:
        return None
    f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float | None:
    la, lb = _lum(a), _lum(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def on_color(*colors) -> str:
    """이 색(들) 위에 올릴 글자색: 검정 또는 흰색"""
    ls = [l for l in (_lum(c) for c in colors) if l is not None]
    if not ls:
        return "#FFFFFF"
    return "#111111" if sum(ls) / len(ls) > 0.42 else "#FFFFFF"


# ───────────────────────────── 스타일 풀기
def saved_styles() -> list[str]:
    return sorted(p.stem for p in STYLE_DIR.glob("*.json")) if STYLE_DIR.exists() else []


def default_style() -> str | None:
    p = STYLE_DIR / "_default.txt"
    name = p.read_text(encoding="utf-8").strip() if p.exists() else ""
    return name if name in saved_styles() else None


def _load_base(name: str, seen: tuple = ()) -> dict:
    if name in seen:
        raise RenderError(f"스타일이 서로를 가리킵니다: {' → '.join(seen + (name,))}")
    if name in PRESETS:
        return dict(PRESETS[name])
    f = STYLE_DIR / f"{name}.json"
    if not f.exists():
        raise RenderError(f"알 수 없는 스타일: {name}",
                          f"기본 묶음: {', '.join(PRESETS)} / 저장된 내 스타일: {', '.join(saved_styles()) or '(없음)'}")
    try:
        d = json.loads(f.read_text(encoding="utf-8-sig"))
    except Exception as e:
        raise RenderError(f"스타일 파일을 읽지 못했습니다: {f} ({e})")
    out = _load_base(d["base"], seen + (name,)) if d.get("base") else {}
    out.update({k: v for k, v in d.items() if k not in META_KEYS})
    if d.get("font_file") and not Path(d["font_file"]).is_absolute():
        out["font_file"] = str(f.parent / d["font_file"])
    return out


def resolve_style(spec: dict, override: str | None = None) -> tuple[dict, str, list[str]]:
    """slides.json → (값 묶음, 기준 이름, 경고 목록)
    우선순위: DEFAULT < 기준(base) < brand(예전 방식) < style에 직접 쓴 값"""
    st = spec.get("style")
    st = {"base": st} if isinstance(st, str) else dict(st or {})
    if override:  # --style: 파일에 적힌 값은 무시하고 그 스타일 그대로
        st, spec = {}, {k: v for k, v in spec.items() if k not in ("brand", "use_brand", "theme")}
    base = override or st.pop("base", None) or spec.get("theme") or "bold"
    tok = dict(DEFAULT)
    tok.update(_load_base(base))

    saved: dict = {}
    try:
        saved = json.loads((REEL_HOME / "brand.json").read_text(encoding="utf-8-sig"))
    except Exception:
        pass
    if spec.get("use_brand"):
        tok.update({k: v for k, v in (saved.get("colors") or {}).items() if k in ("bg", "text", "accent") and v})
    b = spec.get("brand") or {}
    tok.update({k: b[k] for k in ("bg", "text", "accent", "handle") if b.get(k)})
    tok.update({k: v for k, v in st.items() if k not in META_KEYS})
    if not tok.get("handle"):
        tok["handle"] = saved.get("handle") or ""

    warns: list[str] = []
    for k in list(tok):
        if k not in DEFAULT:
            warns.append(f"모르는 값 '{k}'는 무시했습니다.")
            tok.pop(k)
    for k, allowed in ENUMS.items():
        if tok[k] not in allowed:
            warns.append(f"{k}: '{tok[k]}'는 쓸 수 없어 '{DEFAULT[k]}'로 바꿨습니다. (가능: {', '.join(allowed)})")
            tok[k] = DEFAULT[k]
    if tok["font"] not in FONTS and not tok.get("font_file"):
        warns.append(f"font: '{tok['font']}'는 없어 gothic으로 바꿨습니다. (가능: {', '.join(FONTS)})")
        tok["font"] = "gothic"
    if tok.get("font_file") and not Path(tok["font_file"]).exists():
        warns.append(f"글꼴 파일이 없어 '{tok['font']}'로 대신합니다: {tok['font_file']}")
        tok["font_file"] = None
    for k, lo, hi in (("scale", 0.7, 1.3), ("cover_image", 0.4, 1.0), ("radius", 0, 60), ("margin", 40, 140), ("title_size", 0.6, 1.4), ("tracking", -0.08, 0.1),
                      ("weight", 300, 900)):
        try:
            tok[k] = min(hi, max(lo, float(tok[k])))
        except (TypeError, ValueError):
            tok[k] = DEFAULT[k]
    if tok["emphasis"] == "gradient" or tok["title_color"] == "gradient":
        if not tok.get("accent2"):
            warns.append("그라데이션을 쓰려면 accent2가 필요합니다. accent 한 가지 색으로 표시합니다.")

    # 읽기 어려운 색 조합 경고
    c = contrast(tok["bg"], tok["text"])
    if c is not None and c < 4.5:
        warns.append(f"배경({tok['bg']})과 글자({tok['text']}) 색이 비슷해 읽기 어렵습니다 (대비 {c:.1f}, 4.5 이상 권장).")
    if tok["emphasis"] in ("color", "gradient") or tok["title_color"] != "text":
        for name in ("accent", "accent2"):
            c = contrast(tok["bg"], tok.get(name))
            if c is not None and c < 2.6:
                warns.append(f"{name}({tok[name]})가 배경과 비슷해 강조가 잘 안 보입니다 (대비 {c:.1f}, 3 이상 권장).")
    return tok, base, warns


def find_browser() -> str | None:
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    cands: list[Path] = []
    if sys.platform == "win32":
        roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", "")]
        for r in filter(None, roots):
            cands += [Path(r) / "Google/Chrome/Application/chrome.exe",
                      Path(r) / "Microsoft/Edge/Application/msedge.exe"]
    elif sys.platform == "darwin":
        for base in (Path("/Applications"), Path.home() / "Applications"):
            cands += [base / "Google Chrome.app/Contents/MacOS/Google Chrome",
                      base / "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                      base / "Chromium.app/Contents/MacOS/Chromium",
                      base / "Brave Browser.app/Contents/MacOS/Brave Browser"]
    for c in cands:
        if c.exists():
            return str(c)
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        w = shutil.which(name)
        if w:
            return w
    return None


# ───────────────────────────── HTML 조립
def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=False)


def rich(s) -> str:
    """*강조* → em, 줄바꿈 유지"""
    return re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", esc(s)).replace("\n", "<br>")


def ol(items, cls: str) -> str:
    if not isinstance(items, list) or not items:
        return ""
    lis = "".join(f'<li><span class="n">{i + 1}</span><span>{rich(t)}</span></li>' for i, t in enumerate(items))
    return f'<ol class="{cls}">{lis}</ol>'


def img_pos(s: dict) -> str:
    p = s.get("image_pos", "top")
    if isinstance(p, (int, float)):
        return f"{min(100, max(0, p))}%"
    p = str(p)
    if re.fullmatch(r"\d+%", p):
        return p
    return {"top": "0%", "center": "50%", "bottom": "100%"}.get(p, "0%")


def body(s: dict, i: int, total: int, shot_img: str, tok: dict) -> str:
    t = s.get("type", "point")
    handle = "@" + str(tok["handle"]).lstrip("@") if tok["handle"] else ""
    shot = f'<div class="shot"><img src="{shot_img}"></div>' if shot_img else ""
    kick = f'<div class="kicker">{rich(s["kicker"])}</div>' if s.get("kicker") else ""
    title = f'<h1 class="fit">{rich(s["title"])}</h1>' if s.get("title") else ""
    sub = f'<p class="sub">{rich(s["sub"])}</p>' if s.get("sub") else ""
    text = f'<p class="body">{rich(s["body"])}</p>' if s.get("body") else ""
    head = shot + kick + title + sub

    if t == "cover":
        if tok["cover_kicker"] == "tag" and s.get("kicker"):
            kick = f'<div class="tag"><span>{rich(s["kicker"])}</span></div>'
        note = s.get("note")
        swipe = ""
        if tok["swipe"] != "none" and note is not False and i < total - 1:
            swipe = f'<div class="swipe">{rich(note or "넘겨서 보기 →")}</div>'
        div = ""
        if tok["cover_divider"]:
            div = '<div class="divider"></div>' + (f'<div class="chandle">{esc(handle)}</div>' if handle else "")
        return kick + title + sub + text + swipe + div
    if t == "steps":
        return head + ol(s.get("items"), "steps") + text
    if t == "list":
        return head + ol(s.get("items"), "bullets") + text
    if t == "compare":
        def col(c, cls):
            c = c or {}
            lis = "".join(f"<li>{rich(x)}</li>" for x in c.get("items", []))
            return f'<div class="col {cls}"><div class="label">{rich(c.get("label"))}</div><ul>{lis}</ul></div>'
        return f'{head}<div class="compare">{col(s.get("left"), "left")}{col(s.get("right"), "right")}</div>{text}'
    if t == "quote":
        q = f'<blockquote class="fit">{rich(s.get("title") or s.get("body"))}</blockquote>'
        return shot + kick + q + (text if s.get("title") and s.get("body") else "")
    if t == "cta":
        if tok["cta"] == "button":
            icon = ""
            if tok["cta_icon"] in ICONS:
                icon = f'<div class="icon"><svg viewBox="0 0 24 24"><path d="{ICONS[tok["cta_icon"]]}"/></svg></div>'
            kw = f'<div class="kwline">“{esc(s["keyword"])}”</div>' if s.get("keyword") else ""
            btn = s.get("button", tok["button_text"])
            btn = f'<div class="btn">{rich(btn)}</div>' if btn else ""
            sign = ""
            if handle or tok["tagline"]:
                sign = (f'<div class="sign">{f"<b>{esc(handle)}</b>" if handle else ""}'
                        f'{f"<i>{esc(tok["tagline"])}</i>" if tok["tagline"] else ""}</div>')
            return icon + kw + title + sub + text + btn + sign
        kw = ""
        if s.get("keyword"):
            kw = (f'<div class="keyword"><span>{rich(s.get("keywordLabel") or "댓글에 남겨 주세요")}</span>'
                  f'<strong>“{esc(s["keyword"])}”</strong></div>')
        return kick + title + sub + kw + text
    return head + text + ol(s.get("items"), "bullets")


def css_vars(tok: dict) -> dict:
    grad = bool(tok.get("accent2"))
    accent2 = tok["accent2"] if grad else tok["accent"]
    item = tok["item"]
    card_bg = tok.get("card_bg") or {
        "card": "color-mix(in srgb, var(--text) 7%, transparent)",
        "fill": "color-mix(in srgb, var(--text) 7%, var(--bg))",
        "shadow": "#FFFFFF",
    }.get(item, "transparent")
    card_text = tok.get("card_text") or ("#111111" if item == "shadow" and not tok.get("card_bg") else "var(--text)")
    links, face = "", ""
    if tok.get("font_file"):
        face = f'@font-face {{ font-family: "MyTitle"; src: url("{Path(tok["font_file"]).resolve().as_uri()}"); font-weight: 100 900; }}'
        tfont = f'"MyTitle", {FALLBACK}'
    else:
        fam, g = FONTS[tok["font"]]
        if g:
            links = f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={g}&display=swap">'
        tfont = f"{fam}, {FALLBACK}"
    num = lambda v: f"{float(v):g}"
    return {
        "{{FONT_LINKS}}": links, "{{FONT_FACE}}": face,
        "{{ACCENT}}": esc(tok["accent"]), "{{ACCENT2}}": esc(accent2), "{{BG}}": esc(tok["bg"]), "{{TEXT}}": esc(tok["text"]),
        "{{ON_ACCENT}}": on_color(tok["accent"], accent2),
        "{{KEYWORD_COLOR}}": esc(tok.get("keyword_color") or tok["accent"]),
        "{{CARD_BG}}": esc(card_bg), "{{CARD_TEXT}}": esc(card_text),
        "{{RADIUS}}": num(tok["radius"]), "{{MARGIN}}": num(tok["margin"]), "{{TITLE_SIZE}}": num(tok["title_size"]), "{{SCALE}}": num(tok["scale"]), "{{TRACKING}}": num(tok["tracking"]),
        "{{TITLE_FONT}}": tfont, "{{TITLE_WEIGHT}}": num(tok["weight"]), "{{COVER_IMAGE}}": num(tok["cover_image"]),
        "{{BODY_FONT}}": FALLBACK,
    }


def slide_classes(tok: dict, t: str, has_bg: bool, bg_kind: str, has_shot: bool) -> str:
    c = [f"em-{tok['emphasis']}", f"title-{tok['title_color']}", f"align-{tok['align']}", f"valign-{tok['valign']}",
         f"item-{tok['item']}", f"bullet-{tok['bullet']}", f"num-{tok['number']}", f"kicker-{tok['kicker']}",
         f"quote-{tok['quote']}", f"cta-{tok['cta']}", f"swipe-{tok['swipe']}", f"foot-{tok['footer']}",
         f"cover-{tok['cover']}"]
    if has_bg:
        c += ["has-bg", f"bg-{bg_kind}"]
    if has_shot:
        c.append("has-shot")
    on = tok["pattern_on"]
    kind = "cover" if t == "cover" else "cta" if t == "cta" else "content"
    if tok["pattern"] != "none" and (on == "all" or on == kind):
        c.append(f"pat-{tok['pattern']}")
    return " ".join(c)


def render(slides_json: str | Path, out: str | Path | None = None, fmt: str | None = None,
           style: str | None = None) -> list[Path]:
    file = Path(slides_json).resolve()
    if not file.exists():
        raise RenderError(f"파일을 찾을 수 없습니다: {file}")
    try:
        spec = json.loads(file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        raise RenderError(f"slides.json을 읽지 못했습니다: {e}", "쉼표·따옴표가 빠진 곳이 없는지 확인하세요.")
    slides = spec if isinstance(spec, list) else spec.get("slides")
    if not isinstance(slides, list) or not slides:
        raise RenderError("slides 배열이 비어 있습니다.")
    if isinstance(spec, list):
        spec = {}

    fmt = fmt or spec.get("format") or "carousel"
    if fmt not in SIZES:
        raise RenderError(f"알 수 없는 형식: {fmt}", "carousel(4:5), square(1:1), story(9:16) 중 하나를 쓰세요.")
    W, H = SIZES[fmt]
    out_dir = Path(out) if out else file.parent / ("story" if fmt == "story" else "carousel")
    out_dir.mkdir(parents=True, exist_ok=True)

    browser = find_browser()
    if not browser:
        raise RenderError("Chrome 또는 Edge를 찾지 못했습니다.",
                          "Chrome을 설치하거나, 설치 위치를 CHROME_PATH 환경 변수로 알려 주세요.")

    tok, base, warns = resolve_style(spec, style)
    for w in warns:
        print(f"  ⚠ {w}", flush=True)
    handle = "@" + str(tok["handle"]).lstrip("@") if tok["handle"] else ""
    template = (HERE / "template.html").read_text(encoding="utf-8")
    for k, v in css_vars(tok).items():
        template = template.replace(k, v)
    total = len(slides)
    made: list[Path] = []

    def img_url(p) -> str:
        if not p:
            return ""
        a = Path(p)
        a = a if a.is_absolute() else file.parent / a
        return a.resolve().as_uri() if a.exists() else ""

    with tempfile.TemporaryDirectory(prefix="slides-") as tmp:
        tmp = Path(tmp)
        for i, s in enumerate(slides):
            img = img_url(s.get("image"))
            t = s.get("type", "point")
            # 장면을 배경으로 깔지(표지, image_mode=full), 본문 위 사진 칸으로 넣을지
            has_bg = bool(img) and (t == "cover" or (tok["image_mode"] == "full" and t != "cta"))
            bg_kind = tok["cover"] if t == "cover" else "full"
            has_shot = bool(img) and not has_bg and t != "cta"
            bg = f'<img class="bgimg" src="{img}"><div class="shade"></div>' if has_bg else ""
            dots = "".join(f'<i class="{"on" if k == i else ""}"></i>' for k in range(total))
            page = template
            for k, v in {
                "{{IMGPOS}}": img_pos(s), "{{W}}": str(W), "{{H}}": str(H),
                "{{FORMAT}}": fmt, "{{TYPE}}": esc(t),
                "{{CLASSES}}": slide_classes(tok, t, has_bg, bg_kind, has_shot),
                "{{HANDLE}}": esc(handle), "{{PAGE}}": f"{i + 1:02d} / {total:02d}",
                "{{DOTS}}": dots, "{{BGIMAGE}}": bg,
            }.items():
                page = page.replace(k, v)
            page = page.replace("{{CONTENT}}", body(s, i, total, img if has_shot else "", tok), 1)

            html_path = tmp / f"s{i + 1}.html"
            html_path.write_text(page, encoding="utf-8")
            if os.environ.get("RENDER_DEBUG"):  # 문제를 찾을 때: HTML을 결과 폴더에 남긴다
                (out_dir / f"{i + 1:02d}.html").write_text(page, encoding="utf-8")
            png = out_dir / f"{i + 1:02d}.png"
            if png.exists():
                png.unlink()
            for headless in ("--headless=new", "--headless"):
                try:
                    subprocess.run(
                        [browser, headless, "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                         "--no-default-browser-check", "--force-device-scale-factor=1",
                         f"--user-data-dir={tmp / 'profile'}", f"--window-size={W},{H}",
                         "--virtual-time-budget=6000", f"--screenshot={png}", html_path.as_uri()],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90,
                    )
                except subprocess.TimeoutExpired:
                    pass
                if png.exists():
                    break
            if not png.exists():
                raise RenderError(f"{i + 1}번 슬라이드를 찍지 못했습니다.", "Chrome을 최신 버전으로 업데이트한 뒤 다시 실행해 보세요.")
            made.append(png)
            print(f"  {i + 1:02d}.png  ({t})", flush=True)

    # 남은 옛 장 정리 (장 수가 줄었을 때)
    for old in out_dir.glob("[0-9][0-9].png"):
        if old not in made:
            old.unlink()
    print(f"\n✅ {len(made)}장 저장 ({W}x{H}, 스타일 기준 {base}): {out_dir}")
    return made


if __name__ == "__main__":
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:]
    opt = lambda n: a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else None
    files = [x for j, x in enumerate(a) if not x.startswith("--") and (j == 0 or not a[j - 1].startswith("--"))]
    if not files:
        print("사용법: python render.py <slides.json> [--out 폴더] [--format carousel|square|story] [--style 이름]")
        sys.exit(1)
    try:
        render(files[0], opt("--out"), opt("--format"), opt("--style") or opt("--theme"))
    except RenderError as e:
        print(f"❌ {e}", file=sys.stderr)
        if e.hint:
            print(f"👉 {e.hint}", file=sys.stderr)
        sys.exit(1)
