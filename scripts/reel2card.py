#!/usr/bin/env python3
"""인스타그램 릴스 → 카드뉴스(4:5, 1080x1350) 도구. Windows / Mac 공용, API 키 불필요.

슬라이드 문구는 이 도구를 부르는 Claude가 쓴다. 이 스크립트는 그 앞뒤의 기계적인 일만 한다.

  check                        설치 점검
  prepare <릴스주소|영상파일>   영상 받기 → 받아쓰기 → 장면 모음(sheet.jpg)
  render <작업폴더>             slides.json → 장면 뽑기 → PNG

예)
  python reel2card.py check
  python reel2card.py prepare https://www.instagram.com/reel/XXXX/
  python reel2card.py render 카드뉴스/XXXX
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render as renderer  # noqa: E402

REEL_HOME = Path.home() / ".reel-skills"
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
PY = "python" if IS_WIN else "python3"

HINT = {
    "ffmpeg": "winget install Gyan.FFmpeg  (설치 후 터미널을 새로 열기)" if IS_WIN
    else "brew install ffmpeg  (brew가 없으면 https://brew.sh 먼저)" if IS_MAC
    else "sudo apt install ffmpeg",
    "yt-dlp": f"{PY} -m pip install -U yt-dlp",
    "stt": f"{PY} -m pip install faster-whisper",
    "browser": "Google Chrome 설치 (https://www.google.com/chrome)",
}


class Fail(Exception):
    def __init__(self, msg: str, hint: str = ""):
        super().__init__(msg)
        self.hint = hint


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def tool(name: str) -> str:
    p = shutil.which(name)
    if not p:
        raise Fail(f"{name}을(를) 찾지 못했습니다.", HINT["ffmpeg"])
    return p


def has_module(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is not None


def find_whisper_cpp() -> tuple[str, str] | None:
    """whisper.cpp 실행 파일과 모델 (있으면 더 빠르고 정확)."""
    bins = [REEL_HOME / "whisper/bin/Release/whisper-cli.exe", REEL_HOME / "whisper/bin/whisper-cli",
            REEL_HOME / "whisper/bin/whisper-cli.exe"]
    exe = next((str(b) for b in bins if b.exists()), None) or shutil.which("whisper-cli")
    mdir = REEL_HOME / "whisper/models"
    models = sorted(mdir.glob("ggml-*.bin"), key=lambda p: ("turbo" not in p.name, "large" not in p.name)) if mdir.exists() else []
    return (exe, str(models[0])) if exe and models else None


# ---------------------------------------------------------------- check
def cmd_check(_args) -> int:
    rows = []
    rows.append(("Python 3.8+", sys.version_info >= (3, 8), sys.version.split()[0], "https://www.python.org"))
    rows.append(("ffmpeg", bool(shutil.which("ffmpeg")), shutil.which("ffmpeg") or "", HINT["ffmpeg"]))
    rows.append(("ffprobe", bool(shutil.which("ffprobe")), "", HINT["ffmpeg"]))
    rows.append(("yt-dlp", has_module("yt_dlp"), "", HINT["yt-dlp"]))
    wc = find_whisper_cpp()
    fw = has_module("faster_whisper")
    rows.append(("받아쓰기", bool(wc or fw), "whisper.cpp" if wc else "faster-whisper" if fw else "", HINT["stt"]))
    br = renderer.find_browser()
    rows.append(("Chrome/Edge", bool(br), br or "", HINT["browser"]))
    ok = True
    print("설치 점검\n")
    for name, good, info, hint in rows:
        print(f"  {'✅' if good else '❌'} {name:12} {info}")
        if not good:
            ok = False
            print(f"     👉 {hint}")
    print("\n" + ("모두 준비됐습니다." if ok else "❌ 표시를 설치한 뒤 다시 점검하세요."))
    return 0 if ok else 1


# ---------------------------------------------------------------- prepare
def shortcode_of(url: str) -> str:
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else re.sub(r"[^A-Za-z0-9_-]", "_", url)[-40:]


def find_video(work: Path) -> Path | None:
    for p in sorted(work.glob("video.*")):
        if p.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm", ".mkv"):
            return p
    return None


def download(url: str, work: Path, args) -> Path:
    v = find_video(work)
    if v:
        print("  이미 받은 영상이 있어 건너뜁니다.")
        return v
    if not has_module("yt_dlp"):
        raise Fail("yt-dlp가 없습니다.", HINT["yt-dlp"])
    cmd = [sys.executable, "-m", "yt_dlp", url, "-f", "bv*+ba/b", "--merge-output-format", "mp4",
           "-o", str(work / "video.%(ext)s"), "--write-info-json", "--no-playlist", "--no-warnings"]
    if args.cookies_browser:
        cmd += ["--cookies-from-browser", args.cookies_browser]
    if args.cookies:
        cmd += ["--cookies", args.cookies]
    r = run(cmd)
    v = find_video(work)
    if not v:
        tail = "\n".join("  " + t for t in (r.stderr or r.stdout).strip().splitlines()[-3:])
        browser = "safari" if IS_MAC else "firefox"
        raise Fail(f"릴스 영상을 받지 못했습니다.\n{tail}",
                   f"로그인이 필요한 경우가 많습니다. 인스타에 로그인된 브라우저 이름을 붙여 다시 실행하세요: "
                   f"--cookies-browser {browser} (또는 chrome — Windows는 Chrome을 완전히 닫고). "
                   f"영상 파일이 있으면 주소 대신 파일 경로를 넣어도 됩니다.")
    return v


def read_info(work: Path) -> tuple[str, str]:
    """(캡션 원문, 올린 사람 아이디)"""
    info = work / "video.info.json"
    if not info.exists():
        return "", ""
    try:
        d = json.loads(info.read_text(encoding="utf-8"))
        cap = (d.get("description") or d.get("title") or "").strip()
        who = d.get("channel") or d.get("uploader_id") or d.get("uploader") or ""
        return cap, str(who)
    except Exception:
        return "", ""


def probe_duration(video: Path) -> float:
    r = run([tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def transcribe(video: Path, work: Path, lang: str) -> list[dict]:
    out_json = work / "transcript.json"
    if out_json.exists():
        print("  이미 받아쓴 내용이 있어 건너뜁니다.")
        return json.loads(out_json.read_text(encoding="utf-8"))

    wav = work / "audio.wav"
    run([tool("ffmpeg"), "-y", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav])
    segs: list[dict] = []
    if not wav.exists():
        print("  ⚠ 소리가 없는 영상입니다. 화면 자막과 장면만으로 만듭니다.")
    else:
        wc = find_whisper_cpp()
        if wc:
            base = work / "whisper"
            run([wc[0], "-m", wc[1], "-f", wav, "-l", lang, "-oj", "-of", base, "-np"])
            wj = base.with_suffix(".json")
            if wj.exists():
                data = json.loads(wj.read_text(encoding="utf-8", errors="replace"))
                for t in data.get("transcription", []):
                    if t.get("text", "").strip():
                        segs.append({"start": t["offsets"]["from"] / 1000, "end": t["offsets"]["to"] / 1000,
                                     "text": t["text"].strip()})
        if not segs and has_module("faster_whisper"):
            from faster_whisper import WhisperModel
            print("  faster-whisper로 받아쓰는 중 (처음 한 번은 모델을 내려받아 몇 분 걸립니다)", flush=True)
            model = WhisperModel("small", device="cpu", compute_type="int8")
            result, _ = model.transcribe(str(wav), language=None if lang == "auto" else lang, vad_filter=True)
            segs = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in result if s.text.strip()]
        elif not segs and not wc:
            print(f"  ⚠ 받아쓰기 도구가 없어 건너뜁니다. 화면 자막과 장면만으로 만듭니다. (설치: {HINT['stt']})")

    out_json.write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
    (work / "transcript.txt").write_text("\n".join(f"[{s['start']:.1f}] {s['text']}" for s in segs), encoding="utf-8")
    return segs


def make_frames(video: Path, work: Path, duration: float) -> tuple[Path, int, int]:
    """1초마다 후보 장면(frames/all) + 한눈에 보는 장면 모음(sheet.jpg)."""
    ff = tool("ffmpeg")
    alldir = work / "frames" / "all"
    if not alldir.exists() and 0 < duration <= 900:
        alldir.mkdir(parents=True)
        run([ff, "-v", "error", "-i", video, "-vf", "fps=1,scale=540:-2", "-q:v", "4",
             "-start_number", "0", alldir / "t%04d.jpg"])
    interval = max(1, math.ceil(duration / 30)) if duration else 2
    cols = 6
    n = int(duration // interval) + 1 if duration else 30
    rows = max(1, math.ceil(n / cols))
    sheet = work / "sheet.jpg"
    run([ff, "-y", "-v", "error", "-i", video, "-vf", f"fps=1/{interval},scale=240:-2,tile={cols}x{rows}",
         "-frames:v", "1", "-q:v", "3", sheet])
    return sheet, interval, cols


def video_palette(video: Path, work: Path, n: int = 8) -> list[str]:
    """영상 전체에서 많이 쓰인 색 n개 (#RRGGBB). 디자인을 영상 분위기에 맞출 때 쓴다."""
    ff = tool("ffmpeg")
    pal = work / "palette.png"
    run([ff, "-y", "-v", "error", "-i", video, "-vf",
         f"fps=2,scale=96:-2,palettegen=max_colors={n}:reserve_transparent=0:stats_mode=full", "-frames:v", "1", pal])
    if not pal.exists():
        return []
    raw = subprocess.run([ff, "-v", "error", "-i", str(pal), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    out: list[str] = []
    for i in range(0, min(len(raw), 256 * 3), 3):
        h = "#{:02X}{:02X}{:02X}".format(*raw[i:i + 3])
        if h not in out:
            out.append(h)
    return [h for h in out if h != "#000000" or len(out) <= n][:n]


def cmd_prepare(args) -> int:
    src = args.source.strip()
    local = Path(src).expanduser()
    is_file = local.is_file()
    name = local.stem if is_file else shortcode_of(src)
    work = Path(args.out).expanduser().resolve() / name
    work.mkdir(parents=True, exist_ok=True)
    print(f"📁 작업 폴더: {work}")

    step("1/3 영상 받기")
    if is_file:
        video = find_video(work)
        if not video:
            video = work / ("video" + local.suffix.lower())
            shutil.copy2(local, video)
    else:
        video = download(src, work, args)
    duration = probe_duration(video)
    caption, uploader = read_info(work)
    if caption:
        (work / "caption_original.txt").write_text(caption, encoding="utf-8")
    print(f"  {duration:.1f}초 영상")

    step("2/3 받아쓰기")
    segs = transcribe(video, work, args.lang)
    print(f"  {len(segs)}개 문장")

    step("3/3 장면 모음 만들기")
    sheet, interval, cols = make_frames(video, work, duration)
    print(f"  {sheet.name}: {interval}초 간격, 한 줄 {cols}칸")
    palette = video_palette(video, work)
    (work / "palette.txt").write_text(" ".join(palette), encoding="utf-8")

    # Claude가 읽을 요약
    print("\n" + "=" * 60)
    print(f"WORK_DIR: {work}")
    print(f"DURATION: {duration:.1f}")
    print(f"UPLOADER: {('@' + uploader.lstrip('@')) if uploader else '(알 수 없음 — 내 영상 파일일 수 있음)'}")
    print(f"SHEET: {sheet}  (칸 번호 k = 왼→오, 위→아래로 0부터 셈 / 그 장면 ≈ k×{interval}초)")
    print(f"FRAMES: {work / 'frames' / 'all'}  (tNNNN.jpg = NNNN초 장면)")
    print(f"PALETTE: {' '.join(palette) or '(추출 실패)'}  (영상에 많이 쓰인 색 — 순서는 빈도순이 아님)")
    print(f"MY_STYLES: {styles_line()}  (기본 표시가 있으면 그 스타일로 만든다)")
    print("\n[캡션 원문]\n" + (caption or "(없음)"))
    print("\n[받아쓰기 — 초 단위 시작 시각]")
    print("\n".join(f"[{s['start']:.1f}] {s['text']}" for s in segs) or "(없음 — 장면 모음의 화면 자막을 읽을 것)")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------- render
def grab_frames(data: dict, work: Path) -> int:
    video = find_video(work)
    if not video:
        return 0
    duration = probe_duration(video)
    fdir = work / "frames"
    fdir.mkdir(exist_ok=True)
    n = 0
    for i, s in enumerate(data["slides"], 1):
        if "image_time" not in s:
            continue
        try:
            t = float(s.pop("image_time"))
        except (TypeError, ValueError):
            continue
        if duration:
            t = min(max(t, 0.0), max(duration - 0.2, 0.0))
        out = fdir / f"{i:02d}.jpg"
        run([tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-q:v", "2", out])
        if out.exists():
            s["image"] = f"frames/{out.name}"
            n += 1
    return n


def extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("JSON을 찾지 못했습니다")
    return json.loads(text[a: b + 1])


def cmd_render(args) -> int:
    work = Path(args.workdir).expanduser().resolve()
    if work.is_file():
        work = work.parent
    sp = work / "slides.json"
    if not sp.exists():
        raise Fail(f"slides.json이 없습니다: {work}")
    try:
        data = extract_json(sp.read_text(encoding="utf-8-sig"))
    except Exception as e:
        raise Fail(f"slides.json을 읽지 못했습니다: {e}", "쉼표·따옴표가 빠진 곳이 없는지 확인하세요.")
    if not data.get("slides"):
        raise Fail("slides가 비어 있습니다.")

    changed = False
    if any("image_time" in s for s in data["slides"]):
        step("영상 장면 뽑기")
        print(f"  {grab_frames(data, work)}장에 장면 넣음")
        changed = True
    if data.get("caption"):
        (work / "caption.txt").write_text(data.pop("caption"), encoding="utf-8")
        changed = True
    if args.square:
        data["format"] = "square"
        changed = True
    if args.handle:
        data.setdefault("brand", {})["handle"] = args.handle
        changed = True
    data.setdefault("format", "carousel")
    if changed:
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    step("이미지 만들기")
    try:
        renderer.render(sp, style=args.style)
    except renderer.RenderError as e:
        raise Fail(str(e), e.hint)
    print(f"\n🎉 이미지: {work / ('carousel' if data['format'] != 'story' else 'story')}")
    if (work / "caption.txt").exists():
        print(f"   캡션:   {work / 'caption.txt'}")
    return 0


def styles_line() -> str:
    names = renderer.saved_styles()
    d = renderer.default_style()
    return ", ".join(f"{n} (기본)" if n == d else n for n in names) or "(등록된 내 스타일 없음)"


DEMO = [
    {"type": "cover", "kicker": "퍼스널브랜딩", "title": "7일 만에\n브랜드 만드는 법\n*프롬프트 공개*"},
    {"type": "list", "title": "Day 1: 틈새시장 발견", "sub": "당신은 무엇으로 알려지고 싶나요?",
     "items": ["내가 잘 아는 주제 *3가지*", "사람들이 자주 묻는 질문", "돈을 내고 배운 경험"]},
    {"type": "steps", "kicker": "02", "title": "이렇게 진행합니다", "items": ["주제를 정한다", "*고객*을 정의한다", "첫 콘텐츠를 올린다"]},
    {"type": "compare", "title": "전과 후", "left": {"label": "전", "items": ["주제가 매번 바뀜", "반응이 없음"]},
     "right": {"label": "후", "items": ["한 가지로 기억됨", "문의가 옴"]}},
    {"type": "quote", "title": "브랜드는\n*반복*에서\n만들어집니다"},
    {"type": "cta", "keyword": "일주일", "title": "댓글 남기시면\n자료 보내드릴게요", "body": "더 많은 정보가 필요하다면"},
]


def cmd_style(args) -> int:
    renderer.STYLE_DIR.mkdir(parents=True, exist_ok=True)
    if args.action == "list":
        print(f"저장 위치: {renderer.STYLE_DIR}")
        print(f"내 스타일: {styles_line()}")
        print(f"기본 묶음: {', '.join(renderer.PRESETS)}")
        return 0
    if not args.name:
        raise Fail("스타일 이름이 필요합니다.")
    if args.action == "default":
        ptr = renderer.STYLE_DIR / "_default.txt"
        if args.name == "none":
            ptr.unlink(missing_ok=True)
            print("기본 스타일을 해제했습니다. (릴스마다 영상에 맞춰 디자인)")
            return 0
        if args.name not in renderer.saved_styles():
            raise Fail(f"저장된 스타일이 아닙니다: {args.name}", f"저장된 스타일: {styles_line()}")
        ptr.write_text(args.name, encoding="utf-8")
        print(f"기본 스타일: {args.name}")
        return 0
    # demo: 견본 6장을 찍어 원본과 비교한다
    out = renderer.STYLE_DIR / f"{args.name}_demo"
    out.mkdir(parents=True, exist_ok=True)
    slides = [dict(x) for x in DEMO]
    if args.image:
        slides[0]["image"] = str(Path(args.image).expanduser().resolve())
    sj = out / "slides.json"
    sj.write_text(json.dumps({"style": args.name, "slides": slides}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        renderer.render(sj, out=out)
    except renderer.RenderError as e:
        raise Fail(str(e), e.hint)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="인스타그램 릴스 → 4:5 카드뉴스")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="설치 점검")

    p = sub.add_parser("prepare", help="영상 받기 → 받아쓰기 → 장면 모음")
    p.add_argument("source", help="릴스 주소 또는 영상 파일 경로")
    p.add_argument("--out", default="카드뉴스", help="결과를 모을 폴더 (기본: ./카드뉴스)")
    p.add_argument("--lang", default="auto", help="영상 언어 (기본 auto, ko, en …)")
    p.add_argument("--cookies-browser", help="인스타 로그인 쿠키를 빌릴 브라우저 (chrome, safari, firefox, edge)")
    p.add_argument("--cookies", help="cookies.txt 경로")

    r = sub.add_parser("render", help="slides.json → PNG")
    r.add_argument("workdir", help="prepare가 만든 작업 폴더")
    r.add_argument("--square", action="store_true", help="1:1(1080x1080)로")
    r.add_argument("--handle", help="하단에 표시할 인스타 아이디")
    r.add_argument("--style", "--theme", dest="style",
                   help="이번만 다른 스타일 기준으로 찍기 (기본 묶음 이름 또는 저장한 내 스타일 이름)")

    s = sub.add_parser("style", help="내 스타일 관리")
    s.add_argument("action", choices=["list", "demo", "default"])
    s.add_argument("name", nargs="?", help="스타일 이름 (default는 none을 주면 해제)")
    s.add_argument("--image", help="demo 표지에 넣을 이미지")

    args = ap.parse_args()
    try:
        code = {"check": cmd_check, "prepare": cmd_prepare, "render": cmd_render, "style": cmd_style}[args.cmd](args)
    except Fail as e:
        print(f"\n❌ {e}", file=sys.stderr)
        if e.hint:
            print(f"👉 {e.hint}", file=sys.stderr)
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
