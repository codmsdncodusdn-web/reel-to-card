---
name: reel-to-card
description: 릴스 주소 카드뉴스 스킬. 인스타그램 릴스 주소(또는 영상 파일) 하나를 받아 영상을 내려받고 받아쓴 뒤, 영상 속 장면을 넣은 4:5(1080x1350) 카드뉴스 PNG와 캡션 초안을 만든다. 디자인은 등록해 둔 '내 스타일'로 일관되게 만들거나, 릴스마다 영상의 글꼴·색·분위기에 맞춰 다르게 만든다. 기존 카드뉴스 이미지를 주면 그 스타일을 분석해 '내 스타일'로 등록한다. Windows·Mac 모두 동작하고 API 키가 필요 없다. 사용자가 "/reel-to-card", "릴스 주소로 카드뉴스", "이 릴스 카드뉴스로 만들어줘", "릴스 링크 캐러셀", "릴스를 캐러셀로", "내 카드뉴스 스타일 등록", "내 스타일로 카드뉴스" 등을 요청하거나, 인스타 릴스 링크를 주며 카드뉴스·캐러셀·슬라이드를 원하면 사용한다.
---

# 릴스 → 카드뉴스 `/reel-to-card`

릴스 주소 1개 → **영상 장면이 들어간 4:5 카드뉴스 PNG + 캡션 초안**.
기계적인 일(다운로드·받아쓰기·장면 추출·이미지 촬영)은 스크립트가, **슬라이드 문구와 디자인 값은 Claude(너)가 직접** 정한다. API 키를 쓰지 않는다.

`RUN` = `<파이썬> "<이 스킬 폴더>/scripts/reel2card.py"`
- 파이썬: Windows는 `python`, Mac은 `python3`. 경로는 항상 큰따옴표로 감싼다.
- 명령은 사용자의 현재 작업 폴더에서 실행한다. 결과는 `./카드뉴스/<릴스코드>/`에 쌓인다.
- **한글이 든 파일(slides.json, 스타일 파일)은 셸 명령(echo, heredoc)으로 쓰지 말고 파일 쓰기 도구로 쓴다.** Windows 셸에서 한글과 `\n`이 깨진다.

## 0. 처음 한 번: 설치 점검
사용자는 초보자일 수 있다. 전문 용어 없이 "지금 ○○를 설치할게요"처럼 쉬운 말로 안내하고, 설치는 Claude가 직접 실행한다.
- **파이썬이 없으면**(`python --version` / `python3 --version`이 실패) 먼저 설치한다: Windows `winget install -e --id Python.Python.3.12`, Mac `brew install python`(brew가 없으면 https://brew.sh 안내). 설치 후 터미널을 새로 열어야 인식될 수 있다.

`RUN check` — ❌가 있으면 출력된 👉 설치 명령을 사용자에게 보여 주고, 설치해도 되는지 물은 뒤 Claude가 실행한다. 다 설치한 뒤 `RUN check`로 다시 확인한다.
필요한 것: Python 3.8+, ffmpeg, yt-dlp, faster-whisper(받아쓰기), Chrome 또는 Edge.
받아쓰기 도구가 없어도 진행은 된다(화면 자막과 장면만으로 만든다). 품질이 떨어지니 설치를 권한다.

## 1. 준비
`RUN prepare "<릴스 주소 또는 영상 파일>"`
- **영상을 받지 못하면**(로그인 필요 등): 인스타에 로그인된 브라우저를 사용자에게 물어 `--cookies-browser chrome|safari|firefox|edge`를 붙여 다시 실행한다. Windows에서 chrome을 쓰려면 Chrome을 완전히 닫아야 한다. 영상 파일이 있으면 파일 경로로 대신한다.
- 다른 언어 영상도 자동 감지한다. 카드뉴스는 기본으로 한국어로 쓴다.

출력 맨 아래 `====` 블록: `WORK_DIR`, `DURATION`, `UPLOADER`, `SHEET`, `FRAMES`, `PALETTE`(영상에 많이 쓰인 색), `MY_STYLES`(등록된 내 스타일), 캡션 원문, 받아쓰기(초 단위 시각).

## 2. 영상 파악
1. 받아쓰기와 캡션을 읽는다.
2. **`SHEET`(sheet.jpg)를 반드시 열어 본다.** 칸 번호 k(왼→오, 위→아래, 0부터) × 간격(초) = 그 장면의 시각.
   - 화면에 박힌 자막·제목·UI 화면을 읽어 내용을 보충한다. 받아쓰기가 비었으면 이것이 주 재료다.
   - 슬라이드에 넣을 장면을 고른다. 확신이 없으면 `frames/all/tNNNN.jpg`(NNNN초)를 열어 확인한다.

## 3. 디자인 정하기 — 세 가지 모드
**어느 모드로 할지 먼저 정한다.**

| 모드 | 언제 | slides.json에 쓰는 것 |
|---|---|---|
| **내 스타일** | `MY_STYLES`에 `(기본)` 표시가 있을 때 기본값. 또는 "내 스타일로" | `"style": "<이름>"` |
| **섞기** | "색만 영상 따라가줘", "내 스타일인데 이번 영상 느낌으로" | `"style": {"base": "<내 스타일>", "bg": …, "accent": …, "accent2": …}` — 색만 영상에서 |
| **영상 맞춤** | 등록된 내 스타일이 없을 때 기본값. 또는 "이번엔 영상에 맞춰줘" | `"style": {"base": "<가까운 기본 묶음>", …영상에서 읽은 값}` |

사용자가 모드·스타일 이름을 말하면 그것을 따른다. 전달할 때 어떤 모드로 만들었는지 한 줄로 알린다.

### 영상 맞춤: 영상에서 읽어서 값으로 옮긴다
틀을 고르는 게 아니다. 장면 모음을 보고 **그 영상이 실제로 어떻게 생겼는지**를 값으로 옮긴다. 결과물이 매번 같으면 안 된다.

| 영상에서 볼 것 | 정하는 값 |
|---|---|
| 자막·제목 글꼴 (명조/고딕/둥근/손글씨/두꺼운 제목체) | `font`, `weight` |
| 자막 강조 방식 (색 글자/형광펜/박스/밑줄/그라데이션) | `emphasis` (+ 그라데이션이면 `accent2`) |
| 화면 속 그래픽의 모서리 (각짐 ↔ 둥글) | `radius` |
| 화면 밀도 (빽빽·큰 글씨 ↔ 여백 많음) | `scale`, `margin` |
| 글 정렬 (왼쪽/가운데) | `align` |
| 배경 밝기·대표 색·강조 색 (`PALETTE` 참고) | `bg`, `text`, `accent` |
| 분위기 (강함/차분/발랄/정보형) | `base`, `item`, `kicker`, `pattern` |
| 사람·장소가 예쁘게 잡힘 ↔ 화면 녹화 위주 | `cover`, `image_mode` |

- `bg`와 `text`는 명도 차이가 커야 한다. `accent`는 영상에서 눈에 띄는 색(자막 강조색·로고색). 영상이 무채색뿐이면 기본 묶음 색을 그대로 둔다.
- 렌더할 때 `⚠` 경고(색 대비 부족, 모르는 값)가 나오면 값을 고친다.
- 영상의 **분위기를 옮기는 것**이지 복제가 아니다. 원작자의 로고·고유 그래픽을 따라 그리지 않는다.

### 디자인 값 목록 (`style` 안에 쓴다. 안 쓴 값은 base를 따른다)
| 값 | 가능한 것 | 뜻 |
|---|---|---|
| `base` | `bold` `paper` `photo` `pop` `clean` 또는 내 스타일 이름 | 출발점 |
| `bg` `text` `accent` | `#RRGGBB` | 배경·글자·포인트 색 |
| `accent2` | `#RRGGBB` | 넣으면 accent→accent2 그라데이션 가능 |
| `keyword_color` | `#RRGGBB` | 마지막 장 키워드 색 |
| `font` | `gothic` `serif` `soft-serif` `round` `hand` `display` `retro` `tech` | 제목 글꼴 |
| `font_file` | 파일 경로 | 내 글꼴 파일(.ttf/.otf) — font보다 우선 |
| `weight` | 300~900 | 제목 굵기 |
| `tracking` | -0.08~0.1 | 제목 자간 (음수 = 좁게) |
| `scale` | 0.7~1.3 | 글자 전체 크기 |
| `title_size` | 0.6~1.4 | 본문 장 제목 크기 배율 |
| `margin` | 40~140 | 좌우 여백(px) |
| `radius` | 0~60 | 상자·사진 모서리 둥글기 |
| `emphasis` | `color` `gradient` `highlight` `box` `underline` | `*별표*` 표시 방식 |
| `title_color` | `text` `accent` `gradient` | 본문 장 제목 색 |
| `align` / `valign` | `left` `center` / `top` `center` `bottom` | 정렬 |
| `cover` | `fade` `framed` `full` | 표지 장면: 위에 깔고 아래로 녹임 / 액자 / 전체 |
| `cover_image` | 0.4~1.0 | fade일 때 장면 높이 비율 |
| `cover_kicker` | `inline` `tag` | 표지 머리말: 제목 위 / 오른쪽 위 알약 |
| `cover_divider` | true/false | 표지 제목 아래 가는 선 + @아이디 |
| `swipe` | `fill` `outline` `none` | 표지 '넘겨서 보기' 버튼 |
| `image_mode` | `shot` `full` | 본문 장면: 사진 칸 / 배경 전체 |
| `item` | `card` `line` `plain` `fill` `shadow` | 목록 모양: 상자 / 줄 / 상자 없음 / 채운 상자 / 두꺼운 테두리+그림자 |
| `bullet` | `dot` `square` `dash` `check` | 글머리표 |
| `number` | `fill` `outline` `plain` | 단계 번호 모양 |
| `kicker` | `plain` `pill` `soft` `outline` `line` | 머리말 모양 |
| `quote` | `bar` `mark` `plain` | 인용 장 모양 |
| `cta` | `box` `button` | 마지막 장: 키워드 상자 / 아이콘+버튼+아이디 |
| `cta_icon` | `bookmark` `comment` `heart` `send` `none` | button형 아이콘 |
| `button_text` | 문구 | button형 버튼 글 |
| `pattern` / `pattern_on` | `none` `glow` `grid` `dots` / `all` `cover` `content` `cta` | 배경 무늬와 넣을 곳 |
| `footer` | `full` `dots` `page` `handle` `none` | 하단 표시 |
| `handle` / `tagline` | 문구 | 아이디 / 아이디 아래 소개 한 줄 |

## 4. slides.json 쓰기
`WORK_DIR/slides.json`을 쓴다. 영상은 귀로 듣고 카드뉴스는 눈으로 읽는다. 대본을 그대로 자르지 말고 읽히는 글로 다시 쓴다.

### 구성 (6~9장)
| 순서 | type | 역할 | 규칙 |
|---|---|---|---|
| 1 | `cover` | 멈추게 하기 | 제목 18자 이내, 2~3줄(`\n`). 훅을 글로 읽히게. **image_time 필수** |
| 2 | `point` | 문제·공감 | 왜 필요한지 |
| 3~ | `point` `steps` `list` `compare` `quote` | 본문 | 장마다 제목 1개 + 본문 2줄 이내 또는 항목 3개 이내(항목 한 줄 20자 안팎) |
| 끝-1 | `point` 또는 `quote` | 정리 | 한 문장 요약 |
| 끝 | `cta` | 행동 하나 | `keyword`는 `~/.reel-skills/brand.json`의 `cta.keyword`, 없으면 "자료" |

### 원칙
- **영상·캡션에 없는 숫자·사례·주장을 새로 만들지 않는다.** 받아쓰기 오타는 문맥으로 바로잡는다.
- 한 장에 한 가지. 강조할 말은 `*별표*`(장마다 1곳 이하). 줄바꿈은 `\n`.
- **장면(`image_time`, 초)**: cover는 필수(시선을 끄는 장면). 본문은 장면이 내용을 보여 주는 장(화면 시연·결과물·전후 비교)에만 2~3장. quote·cta에는 넣지 않는다.
- **남의 릴스면** (`UPLOADER`가 사용자 본인이 아니면) cta의 `body` 또는 캡션에 `원본: @아이디`를 넣는다.
- `~/.reel-skills/profile.md`, `voice.md`가 있으면 읽고 말투를 맞춘다.
- 내 스타일로 만들 때는 그 스타일 파일의 `note`를 읽고 문구 습관(제목 형식, 마지막 장 문구)도 맞춘다.

### 형식
```json
{
  "style": "내스타일이름",
  "slides": [
    { "type": "cover", "kicker": "AI 자동화", "title": "릴스 하나로\n캐러셀까지\n*전부 자동으로*", "image_time": 22.5 },
    { "type": "point", "kicker": "01", "title": "꾸준함이 곧 *실력*", "body": "본문 한두 줄" },
    { "type": "list", "title": "Claude가 대신 하는 일", "sub": "제목 바로 아래 굵은 부제(선택)", "items": ["항목", "항목"] },
    { "type": "steps", "title": "방법은 3단계", "items": ["첫째", "둘째", "셋째"], "image_time": 25.5 },
    { "type": "compare", "title": "전과 후", "left": { "label": "전", "items": ["3시간"] }, "right": { "label": "후", "items": ["10분"] } },
    { "type": "quote", "title": "한 문장\n*요약*" },
    { "type": "cta", "keyword": "자료", "title": "댓글 남기시면\n보내드릴게요", "body": "원본: @아이디" }
  ],
  "caption": "첫 줄 훅\n\n핵심 3줄\n\nCTA\n\n#해시태그 8~12개"
}
```
슬라이드 선택 항목: `sub`(부제), `image_pos`: `"top"`(기본) `"center"` `"bottom"` 또는 0~100(장면을 위아래로 옮김), `image`: `"frames/all/t0012.jpg"`(장면 직접 지정), cta의 `button`(버튼 글, `""`이면 버튼 없음).

## 5. 이미지 만들기
`RUN render "<WORK_DIR>"` (1:1은 `--square`, 다른 스타일로 그대로 찍어 보기는 `--style <이름>`)
- `image_time`이 있는 장은 그 순간을 원본 화질로 뽑아 넣는다. 이후 slides.json은 `image` 경로로 바뀐다.
- `caption`은 `caption.txt`로 따로 저장된다.

## 6. 직접 확인 (생략 금지)
`WORK_DIR/carousel/01.png`, 글이 가장 많은 장, 장면이 들어간 장, 마지막 장을 **열어 본다.**
- 릴스에 박힌 자막이 카드 제목과 겹치면 → 그 장의 `image_pos`를 바꾸거나 다른 시각의 `image`로, 또는 `cover_image`를 줄인다.
- 장면에 벽·빈 화면만 보이면 → `image_pos`를 10~40으로 내려 본다.
- 제목이 의도와 다르게 줄바꿈되거나 글자가 너무 작아졌으면 → 문구를 줄인다(글자 크기를 억지로 키우지 않는다).
고친 뒤 `RUN render`를 다시 실행한다.

## 7. 전달
- 결과 폴더 경로, 어떤 모드·스타일로 만들었는지(영상 맞춤이면 영상의 어떤 점을 옮겼는지 한 줄), 슬라이드 표(`# | type | 제목`), 캡션 전문.
- 다른 느낌을 원하면 모드를 바꾸거나 값을 고쳐 `render`만 다시 실행한다.
- 남의 릴스를 그대로 옮겨 올리면 저작권 문제가 될 수 있다. 원작자 표기를 넣었다고 알려 준다.

---

## 내 스타일 등록 ("내 카드뉴스 스타일 등록해줘")
사용자의 **기존 카드뉴스 이미지**(폴더·zip·파일 여러 장)를 분석해 스타일 파일로 저장한다. AI를 훈련시키는 게 아니라, 디자인 값을 읽어 저장하는 것이다.

1. 이미지를 연다: 표지 1장, 본문 2~3장, 마지막 장 1장은 반드시 본다. zip이면 새 빈 폴더에 풀고 본다.
2. 위 **디자인 값 목록**의 값을 하나씩 읽어 정한다. 특히: 배경·글자·강조 색(그라데이션이면 `accent2`), 글꼴 느낌과 굵기, 정렬(위쪽/가운데), 목록 모양과 글머리표, 표지 구성(장면 위치·태그·선·아이디), 마지막 장 구성(상자/버튼·아이콘·무늬), 하단 표시, 아이디와 소개 문구.
3. `~/.reel-skills/card-styles/<이름>.json`에 쓴다. `name`, `note`(어디서 읽었는지와 문구 습관 한두 줄), 값들. 가장 가까운 기본 묶음이 있으면 `base`로 두고 다른 값만 써도 된다. 사용자가 글꼴 파일을 줬으면 같은 폴더에 복사하고 `font_file`에 파일 이름을 쓴다.
4. **원본과 같은 문구로 2~3장을 다시 만들어 나란히 비교한다**: 원본 표지·본문·마지막 장의 문구를 옮긴 slides.json을 임시 폴더에 쓰고 `RUN render`. 글자 크기(`scale`, `title_size`), 여백(`margin`), 자간(`tracking`)이 원본과 비슷해질 때까지 값을 고친다. 견본만 빨리 보려면 `RUN style demo <이름>`.
5. `RUN style default <이름>` — 기본 스타일로 지정(이후 릴스는 이 스타일로). 해제는 `RUN style default none`. 목록은 `RUN style list`.
6. 사용자에게 알린다: 비슷하게 맞춘 것(색·글꼴 느낌·구성)과 못 옮긴 것(직접 그린 일러스트, 특수 글꼴, 고유 장식). 글꼴 파일이나 로고를 주면 더 가까워진다고 안내한다.

**본인 것만 등록한다.** 남의 카드뉴스를 그대로 복제하는 용도로 쓰지 않는다. 남의 디자인은 분위기 참고까지만.

---

## 스킬 업데이트 ("스킬 업데이트해줘")
원본: https://github.com/codmsdncodusdn-web/reel-to-card
- 이 스킬 폴더가 git 저장소면(`.git` 있음) 그 폴더에서 `git pull`.
- 아니면 `https://github.com/codmsdncodusdn-web/reel-to-card/archive/refs/heads/main.zip`을 받아 풀고, 안의 파일로 이 스킬 폴더를 덮어쓴다.
- 내 스타일 파일(`~/.reel-skills/card-styles/`)은 스킬 폴더 밖에 있어 업데이트해도 그대로 남는다. 업데이트 후 새 대화를 열라고 안내한다.
