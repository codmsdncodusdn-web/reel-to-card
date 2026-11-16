# reel-to-card — 릴스 주소 하나로 카드뉴스 만들기

인스타그램 릴스 주소를 넣으면 클로드가 영상을 분석해서 **4:5(1080×1350) 카드뉴스 이미지와 캡션 초안**을 만들어 주는 Claude Code 스킬입니다.

- 영상 내려받기 → 받아쓰기 → 장마다 문구 쓰기 → 영상 장면 넣기 → 이미지 저장까지 한 번에
- 기존 카드뉴스 이미지를 보여주면 **내 계정 스타일**로 등록해서 계속 그 톤으로 제작
- 스타일을 등록하지 않으면 릴스마다 영상 분위기에 맞춰 디자인
- API 키 불필요. Windows·Mac 지원 (제작자는 Windows에서 확인)

## 준비물

- 클로드 유료 플랜 (Claude Code를 쓸 수 있는 플랜)
- 컴퓨터 (Windows 또는 Mac), 크롬 브라우저

나머지 프로그램(Python, ffmpeg, yt-dlp, faster-whisper)은 설치 과정에서 클로드가 알아서 설치합니다.

## 설치

클로드 데스크톱 앱의 **Code 탭**(또는 터미널의 Claude Code)에 아래 문장을 그대로 붙여넣으세요.

```
https://github.com/codmsdncodusdn-web/reel-to-card 에 있는 클로드 스킬을 내 스킬 폴더(~/.claude/skills/reel-to-card)에 설치해줘.
git이 없으면 zip 파일로 내려받아서 풀어줘.
설치가 끝나면 그 스킬의 설치 점검(check)을 실행하고, 없는 프로그램은 쉬운 말로 설명하면서 설치해줘.
```

설치가 끝나면 **새 대화**를 열어야 스킬이 인식됩니다.

<details>
<summary>직접 설치하기</summary>

```bash
git clone https://github.com/codmsdncodusdn-web/reel-to-card ~/.claude/skills/reel-to-card
```

git이 없으면 이 페이지의 **Code → Download ZIP**으로 받아 압축을 풀고, 폴더 이름을 `reel-to-card`로 바꿔 `~/.claude/skills/` 안에 넣으세요.
(Windows: `C:\Users\내이름\.claude\skills\reel-to-card`)

</details>

## 사용

```
/reel-to-card https://www.instagram.com/reel/여기에주소/
```

결과는 작업 폴더의 `카드뉴스/<릴스코드>/carousel/` 안에 `01.png, 02.png …`로 저장되고, 캡션은 `caption.txt`에 저장됩니다.

고치고 싶은 곳은 이어서 말로 하면 됩니다. 예) "3번 장 제목 더 짧게", "표지 장면 바꿔줘", "1:1로도 만들어줘"

## 내 스타일 등록

내 카드뉴스 이미지 5~10장을 폴더에 모아 두고 이렇게 말합니다.

```
"내카드뉴스" 폴더에 있는 이미지로 내 카드뉴스 스타일을 등록해줘. 이름은 mystyle로 하고 기본 스타일로 지정해줘.
```

| 방식 | 이렇게 말하면 | 결과 |
|---|---|---|
| 내 스타일 | "내 스타일로 만들어줘" | 항상 내 계정 톤 |
| 섞기 | "색만 영상에 맞춰줘" | 내 글꼴·구성 + 그 영상의 색 |
| 영상 맞춤 | "이번엔 영상 분위기에 맞춰줘" | 릴스마다 다른 디자인 |

## 업데이트

```
reel-to-card 스킬을 GitHub 최신 버전으로 업데이트해줘.
```

## 꼭 지켜주세요

다른 사람의 릴스를 참고할 때는 **그대로 옮기지 말고 내 경험과 내 말로 다시 써서** 올려 주세요. 남의 영상 내용과 장면을 그대로 올리면 저작권 문제가 생길 수 있습니다. 다른 사람 릴스로 만들면 마지막 장에 `원본: @아이디`가 자동으로 들어갑니다. 가장 좋은 사용법은 내가 올린 릴스를 카드뉴스로 한 번 더 쓰는 것입니다.

## 만든 사람

[@platformtree_](https://www.instagram.com/platformtree_/)
