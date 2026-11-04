# 레드 데드 리볼버 한글패치 (Red Dead Revolver Korean Patch)

<p align="center"><img src="cover_ko.png" alt="레드 데드 리볼버 한글판 표지" width="360"></p>

PS2 북미판 **Red Dead Revolver (SLUS-20500)** 를 한국어로 옮기는 팬 번역 프로젝트입니다.
게임 이미지를 직접 고치지 않고, 원본 ISO에서 매번 같은 결과를 만들어 내는 빌드 스크립트와 번역 데이터를 관리합니다.

> **현재 상태: 개발 중.** 번역은 모두 검토 대기(`needs_review`) 상태이며, 배포용 패치는 아직 없습니다.

## 이 저장소에 없는 것

게임 ROM·ISO, PS2 BIOS, 게임에서 추출한 데이터는 포함하지 않으며 앞으로도 올리지 않습니다.
빌드하려면 직접 소유한 게임 디스크에서 만든 ISO가 필요합니다.

## 한국어화 범위

| 대상 | 방식 |
|---|---|
| 메뉴·HUD·튜토리얼·대사 (문자열 테이블) | 번역 후 재삽입, 한글 글리프를 폰트 페이지로 추가 |
| 컷신 자막 | 자막 파일 번역 (2줄 구성 유지) |
| 메뉴 레이아웃 문구 | 문자열 테이블 키로 추가해 번역, 버튼 위치 재계산 |
| 로딩 화면 등 그림 글자 (IPU) | 글자 영역만 지우고 한글로 다시 그려 재인코딩 |

영어로 두는 것: 타이틀의 "Press START", 플래시 계열 무비(.pck) 속 문구, 프로필 이름.

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
