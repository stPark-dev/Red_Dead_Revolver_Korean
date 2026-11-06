# 레드 데드 리볼버 한글패치 (Red Dead Revolver Korean Patch)

<p align="center"><img src="cover_ko.png" alt="레드 데드 리볼버 한글판 표지" width="360"></p>

PS2 북미판 **Red Dead Revolver (SLUS-20500)** 를 한국어로 옮기는 팬 번역 프로젝트입니다.
게임 이미지를 직접 고치지 않고, 원본 ISO에서 매번 같은 결과를 만들어 내는 빌드 스크립트와 번역 데이터를 관리합니다.

> **현재 상태: 베타 v0.9.0-beta.1 공개 (검수 전).** 받기: [돈골's 한글팩](https://hangul.dongolpack.workers.dev/resources/red-dead-revolver/). 번역은 모두 초벌(`needs_review`)이라 정식 배포 기준(검수 완료)은 아직 충족하지 않습니다. 자세한 내용은 아래 [진행 상황](#진행-상황-2026-11-06)을 보세요.

## 진행 상황 (2026-11-06)

### 배포 상태: **베타 공개, 정식 배포 불가**

2026-11-06 사용자 결정으로 검수 전 번역을 베타(`--policy beta`)로 공개했습니다. 정식판은 아래 기준을 채운 뒤 `--policy release`로 냅니다.

| 판단 기준 | 상태 |
|---|---|
| 번역 검수 | 번역 2,201개(문자열 1,630 · 자막 417 · 레이아웃 143 · 그림 글자 11) 모두 `needs_review`. 배포 빌드(`--policy release`)는 검수를 마친(`distribution_eligible`) 번역만 받도록 되어 있어, 지금은 빌드가 의도대로 중단됨 |
| 진행을 막는 결함 | 알려진 결함 없음. 21장 크래시(아카이브 이름표 인코딩)는 수정했고, 현상금 사냥꾼 모드 20개 장과 멀티플레이 맵 26종(2인용 13 · 4인용 13)을 모두 로딩·경기 진입까지 확인 (에뮬레이터 예외 0) |
| 범위 결정 | 영어로 남는 화면 일부(아래 표)는 아직 결정이 필요함 |
| 배포 형식 | 배포 묶음(xdelta + Windows·Linux 적용 스크립트 + 안내) 준비됨. 베타 v0.9.0-beta.1 공개 (결과 SHA1 `2ea61e20…`) |
| 실기 확인 | PCSX2에서만 확인. 실제 PS2 확인은 하지 않음 |

### 진행률 (대략)

| 영역 | 진행률 | 내용 |
|---|---|---|
| 번역 초벌 | 100% | 문자열 1,630 · 컷신·동영상 자막 417 · 레이아웃 문구 143 · 그림 글자 11 |
| 기술 작업 | 약 90% | 문자열·자막·폰트·그림 글자 재삽입, 재현 가능한 빌드, 크래시 수정. 남은 것은 아래 미해결 항목 |
| 런타임 확인 | 약 60% | 메뉴·설정·책, 1장, 현상금 사냥꾼 20개 장(레벨 진입·HUD·재도전·게임 오버), 자막 표시, 멀티플레이 맵 26종 확인. 스토리 모드 전체 진행은 아직 |
| 번역 검수 | 약 2% | 검수 시트(문자열·자막·레이아웃·그림 글자 전체)와 반영 도구, GPT 검수 절차 준비 완료 (`docs/review.md`) |
| 배포 준비 | 약 80% | 베타·정식 빌드 검증, 배포 묶음 생성(`tools/package_release.py`), Linux·Windows(wine) 적용 검증, 배포처 등록 |
| **전체** | **약 72%** | |

### 남은 작업

1. **번역 검수** — `tools/review_export.py`로 만든 시트를 GPT로 검수해 `tools/review_apply.py`로 반영하고, 끝난 항목을 `distribution_eligible`로 올리기 (사람이 결정)
2. **영어로 남는 화면의 범위 결정**

   | 화면 | 출처 | 한글화하려면 |
   |---|---|---|
   | 타이틀 "Press START", 메모리 카드 안내 | 플래시 계열 무비(.pck) | 무비 형식 해독·내장 글꼴 교체 (대형 작업) |
   | 상점, 무기 선택, 장 시작 메뉴 | `shop*.pck`, `weaponselection.pck`, `startchpmenu.pck` | 위와 같음 |
   | 보스·동료 체력바 이름 (Katie, Slade, Megan …) | 레벨 적 데이터의 이름 (스크립트 식별자와 공용) | 실행 파일 훅 필요 |
   | "COMPLETED" 도장, "Story Mode", 캐릭터 소개 이름 | 그림 글자 | 그림 교체 |

3. **런타임 확인 마무리** — 스토리 모드 진행 중 컷신 자막, 실기(가능하면)
4. **정식판** — 검수 완료 후 `--policy release` 빌드로 배포 묶음을 만들어 공개. 베타 제보 반영
5. Windows 적용 스크립트를 실제 Windows에서 확인 (지금은 wine으로만 확인)
6. 보류 중인 문구 결정: `Sher70_DuelTutorial_2c`

## 패치 적용 방법

[돈골's 한글팩](https://hangul.dongolpack.workers.dev/resources/red-dead-revolver/)에서 배포 zip(`RedDeadRevolver-Korean-Patch-v<버전>.zip`)을 받아 완전히 풉니다. zip 안의 `읽어주세요.txt`에도 같은 안내가 있습니다.

### 1. 원본 ISO

패치는 북미판 **SLUS-20500** ISO 한 가지에만 맞습니다. 적용 스크립트가 SHA1을 확인하며, 다른 판이면 아무 파일도 만들지 않습니다.

```
7bbe502a1b170f80e378a566ad8ec313dba78361  Red Dead Revolver (USA).iso
```

### 2. 적용

- **Windows**: 원본 ISO를 `한글패치_적용.bat` 위에 끌어다 놓습니다(또는 원본 ISO를 같은 폴더에 넣고 더블클릭). 함께 든 `tools/xdelta3decode.exe`(xdelta 3.2.2 공식 배포본)를 씁니다.
- **Linux / macOS**: `xdelta3`를 설치하고(`sudo apt install xdelta3`, `brew install xdelta`) 실행합니다.

  ```bash
  sh apply.sh "Red Dead Revolver (USA).iso"
  ```

- **다른 도구**: `patch/RDR-ko.xdelta`는 표준 xdelta3(VCDIFF)라 xdelta UI·Delta Patcher로도 적용됩니다.

원본 ISO는 바뀌지 않고, 같은 폴더에 한글판 ISO(`RedDeadRevolver_KR_v<버전>.iso`, 약 2.4GB)가 새로 생깁니다.

### 3. 실행

- PCSX2 등 에뮬레이터에서 한글판 ISO를 엽니다.
- 자막은 게임 안 **설정 → 소리 설정 → 자막**을 켜야 보입니다.
- 기존 세이브(메모리 카드)는 그대로 쓸 수 있습니다.

### 배포 묶음 만들기 (개발자용)

```bash
python3 tools/build_patch.py work/build/beta.iso --policy beta      # 정식판은 --policy release (검수 완료 번역만)
python3 tools/package_release.py work/build/beta.iso 0.9.0-beta.1 \
    --decoder <xdelta3-3.2.2-windows-x86_64/xdelta3decode.exe> --decoder-license <xdelta LICENSE>
```

- 베타·정식 빌드는 `text/`·`tools/`에 커밋 안 된 변경이 있으면 거부하고, 빌드 기록에 커밋을 남깁니다.
- `package_release.py`는 xdelta를 만든 뒤 다시 적용해 결과 SHA1이 빌드와 같은지 확인하고, `work/dist/`에 zip과 `.sha256`을 만듭니다. 묶음 틀은 `release/`에 있습니다.
- 개발 빌드(`--policy dev`)로는 배포 묶음을 만들지 않습니다.

## 이 저장소에 없는 것

게임 ROM·ISO, PS2 BIOS, 게임에서 추출한 데이터는 포함하지 않으며 앞으로도 올리지 않습니다.
빌드하려면 직접 소유한 게임 디스크에서 만든 ISO가 필요합니다.

## 한국어화 범위

| 대상 | 방식 |
|---|---|
| 메뉴·HUD·튜토리얼·대사 (문자열 테이블) | 번역 후 재삽입, 한글 글리프를 폰트 페이지로 추가 |
| 컷신·동영상(PSS) 자막 | 자막 파일 번역 (2줄 구성 유지, 원문 최대 폭 초과 시 빌드 실패) |
| 메뉴 레이아웃 문구 | 문자열 테이블 키로 추가해 번역, 버튼 위치 재계산 |
| 로딩 화면 등 그림 글자 (IPU) | 글자 영역만 지우고 한글로 다시 그려 재인코딩 |

영어로 두는 것(현재 결정): 타이틀의 "Press START", 플래시 계열 무비(.pck) 속 문구, 프로필 이름. 그 밖에 아직 영어로 남은 화면은 위 [남은 작업](#남은-작업)을 보세요.

자막은 게임의 소리 설정에서 "자막"을 켜야 보입니다.

## 준비물

- 원본 ISO: `orig/Red Dead Revolver (USA).iso` (SHA1 `7bbe502a1b170f80e378a566ad8ec313dba78361`)
- 폰트: 저장소 상위 폴더의 `../fonts/`에 Noto Serif KR(Bold, Black), Noto Sans KR(Bold) `.otf`
- Python 3, `numpy`, `opencv-python`, `Pillow`, `pytest`
- (선택) 런타임 확인용: PCSX2, Xvfb, `python-xlib`

## 빌드와 테스트

```bash
python3 -m pytest -q                         # 단위 테스트
python3 tools/build_patch.py work/build/dev.iso                    # 개발 빌드
python3 tools/build_patch.py out.iso --policy release              # 배포 빌드 (검수 완료 번역만 허용)
```

빌드는 원본 ISO의 SHA1을 확인하고, 글리프가 없는 글자가 하나라도 있으면 실패합니다.
결과 ISO 옆에 번역 수·추가 글리프·교체 파일을 담은 `*.manifest.json`이 생성됩니다.

## 폴더 구성

- `tools/` — 아카이브(Dave)·문자열 테이블·폰트·IPU 이미지 처리, 빌드, 에뮬레이터 조작 스크립트
- `tests/` — 단위 테스트
- `text/` — 원문 기준선(`*_src.jsonl`)과 번역(`*_ko.jsonl`, `layout_ko.json`, `gfx_ko.json`), 용어집
- `docs/survey.md` — 조사 기록, 결정 사항, 검증 결과
- `hook/` — PoC 단계 코드

## 번역 참여

번역은 `text/strtbl_ko.jsonl`(한 줄에 한 항목)에 있습니다. `{BTN_BD}` 같은 토큰은 버튼 아이콘이므로 그대로 두세요.
화면 상단 안내 상자는 한 줄 폭이 좁아(berrylium 기준 약 464), 마지막 줄에 짧은 단어만 남지 않도록 문장 길이를 맞춰 주세요.

## 고지

이 프로젝트는 Rockstar Games 및 Take-Two Interactive와 관계없는 비공식 팬 번역입니다. 게임의 모든 권리는 원 저작권자에게 있습니다.
