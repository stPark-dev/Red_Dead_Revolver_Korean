# Red Dead Revolver (PS2, USA) 한글화 — 초기 조사 (2026-11-03)

## 입력
- `Red Dead Revolver (USA).iso` SHA1 `7bbe502a1b170f80e378a566ad8ec313dba78361`, SLUS-205.00, SYSTEM.CNF VER 1.03
- ISO9660 단일 트랙, 103 files. 재빌드 라운드트립: **미확인**

## 확정 사실
| 항목 | 내용 | 근거 |
|---|---|---|
| 컨테이너 | `Dave`/`DAVE` 아카이브. hdr: magic, count, tocSize, nameSize; TOC @0x800, 16B/entry (nameOff, dataOff, usize, csize) | FRONT/BANKS 파싱 |
| 압축 | usize≠csize이면 raw deflate (zlib wbits -15) | 전 엔트리 해제 길이 일치 |
| 파일명 | `Dave`(소문자)는 비트 패킹된 이름 — **미해독**. `DAVE`는 평문 | |
| 문자열 테이블 | nlang(10) + lang offsets, nBucket(512), keys(len+ASCII+NUL), lang0: count, {hash u32, u16, fontLen+font, len+UTF-16(NUL포함), f32 sx, f32 sy, u16} | 파서가 파일 끝까지 정확히 소비 (`tools/strtbl.py`) |
| 텍스트 인코딩 | UTF-16LE (문자열 테이블·자막 모두) | |
| 컷신 자막 | UTF-16 BOM 텍스트: `mm:ss.s \t line1 \t line2 \t dur` | PERFNEW/0692 = 오프닝 대사 |
| 폰트 | 직렬화 메모리 이미지(포인터·vtable·0xCD 채움). 폰트당 **224 글리프**, 정렬된 UTF-16 코드 목록(0x20–0xFF + 반각 가나 0xFF61–0xFF9F) | FRONT/0094, 0204 |
| SLUS_205.00 | 압축/패킹된 ELF (문자열 거의 없음) — 정적 코드 분석 전 언패킹 또는 RAM 덤프 필요 | |

## 물량 (현재 하한)
- 자막: 고유 파일 73개, 701줄, 약 43,000자 (레벨 DAT 24종에 분산)
- 문자열 테이블: 고유 13종(전역 1181개 ×63사본, 215개 ×63사본, 레벨별 40개), 고유 문자열 1232개 / 약 35,500자
- 미해결: 0x0A로 시작하나 파싱 실패 2개(SHERNITE/0709, FORT/0674), 레이아웃 스크립트(`<TEXT:..>`, `<COMBODATA:..>`) 내 ASCII UI 문자열, 텍스처 그래픽 텍스트, PSS FMV
- 미추출: STREAMS.DAT(1.2GB), SWAT.DAT(304MB)

## 폰트·렌더 경로 (2026-11-03 추가, 런타임 RAM 덤프 + 정적 분석)
- 폰트 파일 = 16B 헤더(원래 기준주소, 1, 0, 이미지 크기) + 메모리 이미지. 로드 시 포인터를 (로드주소-기준주소)만큼 재배치, vtable은 ELF 내 주소로 치환 (FRONT/0094: 기준 0x188B80 → RAM 0x8368B0, 폰트 객체 RAM 0x8374B0, vtable 0x50CBA0)
- 폰트 객체: +8 글리프 수(224), +0x10 코드 목록(u16), +0x14 어드밴스 목록, +0x18 ASCII 직접 테이블(128B), +0x98 크기 변형 수(2), +0x9C.. 변형 디스크립터
- 변형 디스크립터: {텍스처 ptr, f32 1/W, f32 1/H, 글리프 테이블 ptr, u16, u16 count}. 글리프 12B = u16 위치(하위=x/2, 상위=y), u8 w, u8 h, s16×4 메트릭 — **이 형식으로 아틀라스는 최대 512×256** (오버레이로 224개 전부 확인)
- 텍스처: 4bpp + 16색 CLUT(알파 램프), PSMCT32 128×128로 스위즐 저장 → `tools/gsmem.py`로 해제 확인
- 글리프 조회 함수 0x3FC3A8: `andi a1,0xff` 후 <0x80은 테이블, ≥0x80은 코드 목록 선형 검색. 호출자 0x3FC4C8, 0x3FC860(8비트 `lb` 문자열 루프)
- **결론: 렌더러는 8비트 문자열 기반. 한글은 데이터 교체만으로 불가 → 코드 훅 필수** (2바이트 문자 해석 + 대용량/다중 페이지 글리프 공급)
- SLUS_205.00: 0x800000에 적재되는 압축 스텁 → 0x100000 이하로 해제. 코드 패치는 스텁이 실제 엔트리로 점프하는 지점을 가로채 패치 적용 루틴을 넣는 방식이 후보

## 리스크 / 다음 증거
| 조건 | 상태 | 다음 증거 |
|---|---|---|
| 한글 렌더 | **코드 훅 필수 확정** | UTF-16→8비트 변환 지점 확인, 훅 설계 PoC(1글자 표시) |
| 런타임 검증 환경 | PCSX2 v2.8.2(flatpak) + SCPH-39001, PINE IPC로 RAM 읽기 가능 (`tools/pine.py`) | 완료 |
| Dave 재패킹 + ISO 재빌드 | 미확인 | 무수정 라운드트립 |
| 파일명 디코딩 | 미해독 | 폰트/텍스처 식별에 필요 시 |
| `script_eng.txt` | 팬 FAQ 대본(2011). 게임 실제 문자열과 문구·분할·타임코드가 다름 | 번역 입력은 게임에서 추출한 원문 기준이어야 함 |

## PoC 진행 상황 (2026-11-03)
### 확정
- 런타임 환경: PCSX2를 Xvfb :99(소프트웨어 렌더러)에서 실행 → 사용자 데스크톱과 분리. 입력은 XTEST(:99), 메모리는 PINE.
- 타이틀 세이브스테이트 slot1(원본 ELF) — ELF 미수정 빌드의 결정적 시험용 (`tools/statetest.sh`). ELF 수정 빌드는 CRC가 달라 상태 로드 불가 → `tools/boot_to_menu.py`(타이틀 화면 이미지 감지)로 콜드부트.
- ISO 재빌드: 변경 파일은 끝에 추가+디렉터리 레코드 갱신, **이미지 끝 4MB 패딩 필수**(게임이 파일 끝 너머 선행 읽기).
- Dave 재패킹(추가 방식), strtbl 직렬화(160개 테이블 바이트 동일), 폰트 아틀라스 스위즐 왕복(6종 바이트 동일 + 시각 확인).
- 문자열 테이블 사본은 FRONT.DAT 외에 **SWAT.DAT(엔트리 47,115)** 에도 있고 타이틀 이전에 SWAT 쪽이 로드됨.
- 타이틀의 "Press START button" 등 레이아웃 텍스트는 strtbl을 거치지 않음(레이아웃 스크립트 ASCII 직접).
- UTF-16→8비트 변환: U+00A0–U+00FF는 바이트 그대로 통과(é À ÿ ¡ ° 확인), U+0152/U+AC00/U+0090은 빈칸 → **한글은 EUC-KR 바이트쌍을 U+00B0–U+00FE 두 글자로 저장**하는 방식 채택 후보.
- 언패커 스텁 `j 0x100008`(0x800020) 가로채기 → 패처가 훅을 0x1F50000에 복사, 힙 상한 `lui a0,0x1f6`(0x21A018)→0x1f5, 호출지점 패치, FlushCache. **동작 확인**(RAM에서 패치 반영, 부팅·메뉴 정상).
- 폰트 편집(217개 변형, '@' 칸에 '가' + 글리프/어드밴스) 로드 정상(크래시 없음).
### 미해결 (다음 증거)
- 0x3FC3A8 조회 함수는 **3D 책 표지 텍스트 경로만** 담당. HUD("Enter/Options")와 책 왼쪽 페이지는 **다른 렌더러** → 해당 조회 코드 미발견. 다음: RAM의 폰트 ASCII 테이블/코드목록을 오염시켜 HUD가 쓰는 폰트 객체·필드를 특정 → 그 필드를 읽는 코드 탐색.
- 초기 크래시(TLB Miss)는 키 입력 타이밍 문제였던 것으로 보이나, ELF+폰트 동시 빌드의 콜드부트 크래시 1회 미해명 → 재현 시험 필요.

## PoC3 결과 (2026-11-03) — HUD 경로 한글 표시 성공
- HUD/2D 텍스트 요소(vtable 0x502030, 레이아웃 "frontendbuttons")의 draw = 0x10E9D8. 문자열 키를 strtbl에서 찾아 **UTF-16 그대로** 0x17A078(font B 그리기)에 넘긴다.
- font B 글리프 조회: 코드 <0x100은 바이트 테이블(+0x22C), 그 이상은 정렬된 글리프 배열(+0x224, 12B, u32 code)을 **이진 탐색** → 코드 훅 없이 U+AC00 등 임의 코드 추가 가능.
- font B 파일 = 디스크립터(FRONT/0004 등, magic f32 1.02, `tools/fontb.py`) + 뒤따르는 텍스처 페이지 6장(128×128 8bpp 선형, RGBA 팔레트 흰색+알파 램프). x/y는 u8 → 페이지 ≤256×256. 페이지 인덱스 s8, 객체 내 페이지 포인터 슬롯은 +0x000~+0x17C(최대 96장 추정, 미검증).
- 동일 디스크립터(md5 77969744…) 사본 64개: FRONT 1, SWAT 3, 레벨 DAT마다 1.
- `tools/build_poc3.py`: 마지막 페이지 빈 칸(40,0)에 '가'(Noto Serif KR Bold) 추가 + "Options"→"A가B". 콜드 부팅(Xvfb :99)에서 HUD에 "A가B" 표시, TLB miss 0. 증거: work/build/poc3.iso, 스크린샷 scratchpad/poc3cold.png.
- 주의: 세이브 스테이트(타이틀)에는 font B/strtbl이 이미 RAM에 있어 디스크 변경이 반영 안 됨 → 폰트/문자열 검증은 콜드 부팅 필수.
- 남은 경로: 3D 책 텍스트(font A, 0x3FC3A8, 8비트 변환 경유 → EUC-KR 쌍 + 훅 필요), 책 왼쪽 페이지 경로 확인, 자막 경로 확인.

## PoC4 결과 (2026-11-03) — 새 텍스처 페이지 추가로 한글 표시 성공
- 책 페이지 텍스트도 font B(berrylium, 0xCAE6B0)를 쓴다. 런타임 strtbl 항목 = {hash, font*, UTF-16*, sx, sy, …}; 쓰이는 폰트는 berrylium(796), damaged(89, 0xD1B600), regulatorcondensed(41, 0xD1CDA0) 3종뿐. → **실행 파일 훅 불필요**. font A(fontbundle, 0x3FC3A8)와 EUC-KR 바이트쌍 방식은 폐기 후보(소비 텍스트 미확인).
- U+2020–2023은 font B의 버튼 아이콘 글리프(×○ 등). 번역 시 보호 토큰.
- 로더(0x179A88): 페이지를 이름 `"%s_%02d"`(.tex)로 로드, 페이지 포인터 슬롯 0x00–0xBC(**최대 48장**), 헤더 0x200–0x20C가 0이 아니면 `…s` 보조 페이지(+0xC0)도 로드.
- 아카이브 이름: 6비트 코드 + 앞 항목과의 접두사 공유(`tools/davename.py`, 문자 0=끝 1=' ' 4='(' 5=')' 6='-' 7='.' 10–19 숫자 20='_' 21–46 a–z 48='~'(추정), 56+ 접두사). TOC는 이름 정렬 → 이름으로 조회.
- `dave_patch.insert`: 이름 정렬 위치에 항목 삽입, TOC/이름 용량 부족 시 데이터 영역을 밀어 확장(WOODS.DAT 여유 2칸 등). 테스트 16개 통과.
- `tools/build_poc4.py`: berrylium_06.tex 새 페이지(128×128 8bpp, 20×21 셀)에 가~사 7자 + 디스크립터 페이지 7장. 콜드 부팅: HUD "가나다라", 책 "마바사" 표시, TLB miss 0.
- 남은 확인: (1) 자막 렌더 경로, (2) 레벨 DAT(용량 확장 포함) 인게임 로드, (3) 페이지 수 증가 시 RAM/VRAM 예산(4bpp 페이지 사용 가능성: FRONT/0000 계열은 4bpp), (4) 셀 크기·폰트 품질.

## PoC5 결과 (2026-11-03) — 인게임 자막 + 레벨 DAT(용량 확장 포함)
- 인게임 자막(튜토리얼 대사 등)은 **전역 strtbl(`swat.strtbl`, FRONT/SWAT/레벨 DAT마다 사본)** 항목이며 font B(berrylium)로 그려진다. `lvl_*_subtitles_en.txt`를 바꿔도 화면은 strtbl 문구를 표시함(파일 수정 무효과 확인).
- `tools/build_poc5.py`: FRONT/SWAT/PERFNEW의 strtbl 2개 문구 + berrylium_06 페이지. 1장 진입 후 "가나다라 마바사 … A가B …"가 **공백에서 자동 줄바꿈**되어 2줄 표시, TLB miss 0. 증거 scratchpad/p5h_sub.png.
- `grow` 변형: PERFNEW에 더미 200개를 넣어 TOC 용량 확장(28672→30720) → 1장 정상 로드·동일 표시. **아카이브 용량 확장 인게임 검증 완료**.
- 컷신(pupshow) 자막: 원본 USA 판에서도 컷신 중 자막이 **표시되지 않음**(1장 오프닝에서 확인). 로더 0x237A70은 "nosubtitles" 인자 확인 후 berrylium 폰트와 `<name>_<lang>.txt`를 연다. 표시 조건(0x2362A0 부근 객체 +0x88 등) 미해명 → 컷신 자막을 켤지는 **제품 범위 결정 사항**(코드 패치 필요 가능, 대사 파일 73개 ~43,000자).
- 화면 상단 조작 안내("Move: left analog stick")는 strtbl이 아님 → 레이아웃 스크립트 ASCII 문구 모집단(미해결 목록에 이미 있음).
- 프로필 이름 입력은 A–Z 화면 키보드 → 한글 입력 범위 밖으로 둠(영문 이름 그대로 표시).

## PoC6 결과 (2026-11-03) — 폰트 페이지 한도와 메모리 예산
- **페이지 한도 24장/폰트**: 로더가 페이지 경계 배열을 font+0x188에 개수 검사 없이 복사하는데, 그 뒤 +0x1E8부터 헤더 필드, +0x224에 글리프 배열 포인터가 있다. 43장(damaged)에서 포인터가 덮여 부팅 중 0x179DE0 TLB miss로 확인. `fontb.build`가 24장 초과를 거부(테스트 추가).
- 4bpp 페이지 지원: 헤더 +4 형식코드 0x0E=8bpp(256색), 0x10=4bpp(16색, 하위 니블 먼저). `fontb.parse_page/build_page/blank_page`, 새 페이지 생성기 `tools/fontgen.py`(테스트 25개 통과).
- 메인 힙(0x79DD80 → +4 base, +8 size 19.6MB, +0xC used; `tools/heapprobe.py`): 원본 메뉴 9.98MB 여유, **원본 1장 3.11MB 여유**. berrylium +18장(4bpp 256², 2178자, 591KB) 빌드는 1장 2.49MB 여유 → 페이지 바이트만큼 RAM 소비.
- 텍스처 예산: 추가 591KB(4bpp)는 메뉴·1장 모두 정상. 추가 1.2MB(8bpp 256² 18장) 또는 1.9MB(3폰트 4bpp)는 **메뉴에서 텍스처 깨짐**(크래시 없음). 한계는 0.6–1.2MB 사이(메뉴 기준), 레벨별 여유는 미측정.
- 없는 글리프는 게임이 **조용히 생략**한다(1장 자막에서 '험','해' 누락 확인) → 빌드 단계의 미매핑 문자 실패가 필수.
- 셀 크기 기준(대문자 높이/yoff): berrylium 22/-20, damaged 32/-36, regulatorcondensed 26/-23. 디스크립터 끝 s16은 하위 바이트=y오프셋, 상위 바이트=-1(대개)로 보임.

## 사람 결정 (2026-11-03, PoC5·PoC6 증거 기준)
- 글리프 집합: **폰트별로 번역에 실제 쓰인 음절만** 추가(4bpp 256² 페이지, 24장 한도 내). 추가 텍스처 합계 목표 ≈0.5MB 이하. 미매핑 문자는 빌드 실패.
- 범위: **게임이 표시하는 텍스트 우선**(strtbl: 메뉴·HUD·책·인게임 자막). 컷신(pupshow) 자막 활성화는 별도 후속 조사 과제.

## 제품 파이프라인 1차 (2026-11-03)
### 추출·번역
- `tools/extract_strtbl.py` → `text/strtbl_src.jsonl`: 전 아카이브 strtbl을 (테이블, 키) 단위로 병합(사본 간 차이 0, 차이 시 실패). 키↔엔트리는 **ELF 해시(대소문자 구분)** 로 전수 매핑(`strtbl.elf_hash`). 백업/Xbox 테이블 7사본 제외 기록(`*.excluded.json`).
- 아이콘 글리프 º¼½¾(원형 버튼), †‡•‣(막대형)는 `{BTN_BA}`…`{ICON_2023}` 토큰(`tools/textcodec.py`, 리터럴 중괄호는 이중화). '…'(U+2026)·'–'(U+2013)는 어느 폰트에도 글리프가 없어 원본에서도 생략됨 → 번역에서 사용 금지(검사).
- 범위: 게임 도달 테이블의 비어 있지 않은 고유 문구 1,245개(약 36,400자) **전부 초벌 번역 완료**(state=needs_review, `text/strtbl_ko.jsonl`, 동일 원문은 `same_as` 연결). `tools/translation.py`가 원문 변경·토큰·상태·same_as·글리프 없는 문자 검사, `tools/tr_merge.py`가 덮어쓰기 금지 병합.
- 용어/말투: `text/glossary.json` — 인명 음역, 별명은 뜻 번역(“돼지” 조시 등), 서부풍 말투(악당·레드 반말, 주민 해요체, 안내 하세요체), 장소 번역(술집·총포상·잡화점·보안관 사무소) **사용자 승인**. 개별 용어 다수는 proposed.

### 레이아웃(.swui)
- 화면 요소는 레이아웃이 `<FONT:..>`로 폰트를 정하고 `<TEXT|TEXTBOX|READOUT:..:REF>`, `<BUTTON|COMBO:x,y,z:LABEL:..>`, `<COMBODATA:LABEL:..>`, `<LOOKUPDATA:..>`로 문구를 참조한다. REF가 strtbl 키면 번역문, 아니면 **리터럴이 그대로** 표시.
- **레이아웃 폰트가 strtbl 항목 폰트보다 우선**(책 제목 profile_cur_lgnd: 항목 berrylium, 실제 regulatorcondensed). → 글리프 계획은 항목 폰트 ∪ 레이아웃 폰트(`tools/swui.py`, `tools/extract_layout.py` → `text/layout_refs.json`, LOOKUP 열→요소 매핑 `text/layout_map.json`).
- **리터럴을 swat.strtbl의 새 키로 추가하면 리터럴이 번역문으로 해석됨**(PoC7: Enter/Accept/Back/Begin → 선택/확인/뒤로/시작 표시). `text/layout_ko.json`(124개: 버튼, 설정 화면, 장 제목 'Chapter N', 멀티 모드/레벨명 등) → `strtbl.add_entries`.
- SWAT 전용 `lvl_frontend.strtbl`은 **로드되지 않음**(키 'Chapter 1' 번역이 화면에 반영 안 됨) → 해당 레이아웃 참조는 리터럴로 처리. `lvl_tng.strtbl`(구 훈련 프로토타입)도 미도달 추정, 미번역.
- 추가 폰트: steelfish(장 제목), narrow_lables·woodcut_small(멀티 포스터), courier18(일지), bosshealth, arial14 → `build_patch.FONTS`에 셀/yoff 설정, 글리프가 적으면 작은 페이지(32/64/128) 자동 선택.

### 빌드·런타임 QA (dev 정책, work/build/dev.iso, 배포 불가 표시)
- `tools/build_patch.py`: 원본 SHA1 확인 → 번역 선택(dev: 미번역은 원문 유지 / release: 전부 distribution_eligible 요구) → 폰트별 필요 한글 산출(미매핑 문자는 빌드 실패) → 63개 아카이브의 strtbl·폰트 사본 전부 갱신 + 페이지 삽입 → manifest.
- 현재 새 글리프: berrylium 727, regulatorcondensed 261, damaged 180, bosshealth 34, narrow_lables 36, courier18 15, steelfish 2, arial14 2 / 페이지 합계 473KB(예산 600KB, 591KB 검증치 이하).
- 콜드부트 확인(TLB miss 0): 메인 메뉴·설정·화면 설정·소리 설정·프로필·책(진행 중인 플레이어/제1장/과녁 한가운데/본문)·1장 인게임 자막·HUD 안내·일시정지 메뉴 한글 표시. 1장 힙 여유 2.68MB(원본 3.11MB).
- **컷신 자막: 소리 설정의 '자막' 옵션(기본 '끔')을 켜면 표시됨** → `lvl_*_pupshow_*_en.txt`(UTF-16, 시간·2줄·지속시간) 내용이 그대로 출력. 이전 "USA판 컷신 자막 미표시" 판단은 옵션 기본값 때문이었음 → 범위 재결정 필요.
- 남은 영어: 타이틀 "Press START button"(strtbl 미경유), 메모리 카드 메시지("Memory card (8MB)… is not formatted…", 출처 미확인), 저널 포스터 그래픽("Ugly Chris' Gang / LOCKED / Frontier Battles"), 프로필 "New Player"(그래픽 추정), 멀티 포스터 P-1~4/CPU/N/A(의도적 유지).

## 컷신 자막 (2026-11-04)
- 사람 결정: 컷신 자막(소리 설정 '자막' 옵션으로 표시)을 다음 범위로 포함("계속 진행해보자", 컷신 자막 우선 권고에 대한 응답).
- 파일: `lvl_*_pupshow_*_en.txt` 74개(레벨 DAT·SWAT.DAT에 사본, 사본 간 동일). UTF-16LE+BOM, CRLF, `시간\t줄1\t줄2\t지속`. 쉼표가 든 칸은 스프레드시트식 따옴표 → **게임이 따옴표를 제거**("Hey Pa, where did you get that?"가 따옴표 없이 표시, qa4). 일부 파일은 끝에 홀수 바이트 1개·공백/탭 줄이 붙어 있음 → 그대로 보존(`tools/pupshow.py`, 74개 전부 바이트 왕복 일치).
- 기준선 `text/pupshow_src.jsonl`(`tools/extract_pupshow.py`): 309큐, 15,294자. SWAT.DAT에만 있는 8개 파일(52큐: jailnew, msn, msncyn_02/03, mansroof_04, royal_01, royfinal_02, traingood, barfight_02)은 reach=swat-only(해당 레벨 DAT에 사본 없음 → 미도달 추정, strtbl과 같은 정책으로 번역은 포함).
- 번역 `text/pupshow_ko.jsonl`: 309큐 전부 초벌(needs_review). 줄 구분(`\n`)은 원문 2줄 구조 유지(화자 2명이 한 큐를 나누는 경우 있음). 따옴표·탭·3줄 이상은 `pupshow.with_text`가 거부.
- 빌드: `build_patch`가 자막 번역을 같은 글리프 계획(berrylium)에 합류, 파일을 큐 단위로 재작성(번역 없는 큐는 원본 바이트 유지). **줄 폭 검사**: 각 줄 폭(글리프 w 합 + 공백 8)이 도달 가능한 원문 최대 줄 폭(600)을 넘으면 빌드 실패. berrylium 새 글리프 727→807(페이지 수 7장 그대로, 추가 바이트 0).
- 런타임 확인(qa5b, dev 빌드): 소리 설정 '자막' 켬 → 1장 오프닝 컷신(perfnew_01)과 이어지는 인게임 자막이 한글 2줄로 표시, 쉼표 포함 문장의 따옴표 없음, 줄 폭 화면 안. TLB miss 없음. 자간이 영문보다 넓으나 판독 가능.
- 주의: 자막 옵션을 바꾸고 확인하면 메모리 카드 미포맷 안내가 뜬다 → **No → "Are you sure?"에서 Yes**(포맷하지 않음)로 넘김.

## 타이틀 "Press START button" 조사 (2026-11-04, 미해결)
- 화면 문구는 SWAT.DAT `logo01.pck`(Flash 계열 UI 무비, ActionScript 바이트코드: 상수 풀 `theText,_alpha,pulse,_global,xboxButtons,loadNow,text,"Press START","Press START button"`)에서 온다. 텍스트 필드 초기값 오프셋 75152, 상수 풀 75445/75457. → SWAT.DAT가 부팅 시 사용됨(SWAT 전용 strtbl이 미로드인 것과 별개).
- PoC A: swat.strtbl에 키 "Press START button" 추가 → 변화 없음(영문 유지). swat_ps2.strtbl의 같은 키는 이미 한글인데도 영문 → strtbl 조회 경로 아님으로 추정.
- PoC B/C: logo01.pck 세 곳을 같은 길이 UTF-8 한글 / ASCII 표식(AAA/BBB/CCC)으로 교체 → 둘 다 **문구가 사라짐**. 그때 EE RAM에 무비 문자열이 아예 없음 → 수정된 pck가 로드 거부된 것으로 보임(문자열 해시·체크섬 등 무결성 검사 가능성). 미해결 가설: pck 내부 이름 해시(`fe f7 03 ff` 등) 또는 블록 체크섬. 다음 단계 후보: pck 로더(ELF) 역분석, 또는 범위 제외 결정.
- **사람 결정 (2026-11-04)**: 타이틀 "Press START button"은 **영어로 두고 예외 처리**(사용자: "타이틀은 영어로 두고 예외 처리해"). 릴리스 범위·주장에서 제외 항목으로 명시.
- "New Player": strtbl 키·레이아웃 문구가 아니라 ELF의 **기본 프로필 이름** 리터럴(0x5171B3, profile_* 키 이름들 사이). 이름 입력은 A–Z 화면 키보드이고 메모리 카드에 저장되는 사용자 문자열 → 기존 결정(프로필 이름은 영문 유지)에 포함해 영어로 둠.

## 남은 영어의 공통 출처: 플래시 계열 무비(.pck) (2026-11-04)
- 메모리 카드 안내("Memory card (8MB) (for PlayStation®2) in MEMORY CARD slot 1 is not formatted. Do you want to format it? / Yes / No / Press ✕ to confirm selection"): 안내가 떠 있을 때 EE RAM에 원문 문자열(ASCII·UTF-16)이 없고, **글자당 u32, 코드=ASCII−32(글리프 번호)** 배열(0x142E90C 등, 제어코드 04 03 05 포함)만 있다. 디스크 전체 파일(아카이브 압축 해제 포함)에서 그 배열·원문 모두 검색 안 됨 → 무비 내부의 압축/비트 패킹 데이터에서 런타임 생성으로 추정.
- 일지 포스터("Ugly Chris' Gang / LOCKED / Frontier Battles"): FRONT.DAT `j01_01_mainmenu.pck` 안 문자열.
- 타이틀 문구: SWAT.DAT `logo01.pck`(위 절). 수정 시 로드 거부.
- pck 무비마다 자체 글꼴 표(문자 ' '..'_' 96자, 글리프 번호=코드−32)를 내장 → 한글화하려면 ① pck 형식(압축·재배치 포인터) 해독 ② 내장 글꼴에 한글 글리프 추가 또는 font B로 우회 ③ 로드 거부(무결성 검사) 해제가 모두 필요. strtbl·레이아웃과 별개의 대형 과제.
- FRONT.DAT의 pck: j01_01_mainmenu, j10_01_generic, memoryicon, popups_01_ingame(“Slot 1-A” 등 메모리 카드 팝업 추정). SWAT.DAT에 j02~j19 일지 페이지 무비 다수.
- **사람 결정 (2026-11-04)**: pck 무비 속 영어(타이틀 문구·메모리 카드 메시지·일지 포스터 문구)는 **예외로 두고 영어 유지**(사용자: "예외로 둡니다"). "New Player"는 프로필 이름 정책으로 영어 유지.

## 멀티플레이(쇼다운) 런타임 QA (2026-11-04)
- 경로: 메인 메뉴 ← 왼쪽 포스터(SHOWDOWN) → 참가(1P) → 슬롯 2에 CPU → START → 레벨 포스터 → ✕ 시작(`tools/to_showdown.py`, 메뉴 입력은 3초 간격 필요).
- 한글 확인: 참가 화면 버튼 안내(선택/뒤로/팀/설정), 캐릭터 이름(애니 스토크스, 잭 스위프트, “제비족” 핸콕, 치킨), 설정 오버레이, 쇼다운 설정(게임 모드·현상금 한도·파워업), 레벨 포스터(트윈 록스/고대의 거석, 시작/뒤로/무작위/설정), 로딩 "불러오는 중..." · "START 버튼을 누르세요", 대전 중 "R1 버튼으로 부활", 무기 이름.
- **코드 참조 문구**: ELF가 `sprintf` 후 키로 조회하는 문구가 있음 → `text/code_literals.json`(근거 필수)에 등록하면 swat.strtbl 새 키로 번역(`build_patch.merge_code_literals`, 테스트). PoC로 "Player 1 Paused" → "플레이어 1 일시정지" 확인. 등록: Player 1~4 Paused, First One/Team to $N Wins!(N=3000…20000), N Minute Timed Battle!(1~15분).
- 영어로 남는 것: 상대 이름표 "Player 2"(이름 버퍼를 직접 그림, 조회 안 함 → 이름 분류로 유지), 로딩 화면 그림 "CONTROLLER"·"CARD COLORS"·"MULTIPLAYER GAME MODES"(텍스처 그래픽 텍스트, 미조사).
- 품질 메모: 포스터 위 큰 "START 버튼을 누르세요"는 narrow_lables(12px 셀)를 약 1.9배 확대해 그려 흐림.

## 그림 글자: 로딩 화면 IPU (2026-11-04)

- 멀티 로딩 화면은 **SWAT.DAT의 `mpload_<모드>_<NN>.ipu`** (EE 메모리에 이름 형식 `mpload_%s_%02d`, 옆에 `mpscreens`). 512×448 IPU(PS2 MPEG-2 인트라) 한 프레임, 모든 파일 flags=0(8비트 DC, 선형 qscale, B14 VLC, 지그재그). 실제 화면(STUD VS HOLD'EM, CONTROLLER, CARD COLORS)과 디코드 결과 일치.
- `mpscreens.txt`(SWAT): gen 3, hunt/sun/noon/stud/hold/duel 2, none 1 → 도달 이미지 고유 8장: gen_01 CONTROLLER, gen_02 PROFILES & OPTIONS, gen_03 MULTIPLAYER GAME MODES, (hold/hunt/stud/sun)_01 STUD VS HOLD'EM, _02 CARD COLORS, (duel/noon)_01 DUELING CONTROLS, _02 DUELING PHASES, none_01 NO RULES. 03~06(WEAPON POWER UPS, GLOBAL POWER-UPS, HOLD'EM RULES, STUD POKER, HIGH NOON)은 개수 밖 → 미도달 추정(미확인). `_0`/`_1`(한 자리) 7개는 `%02d`로 못 만드는 이름 → 제외(구버전 도안).
- 기타 IPU 그림 글자: `coolscreen.ipu`("LOADING", 멀티 레벨 DAT), `gameover.ipu`("GAME OVER", 멀티 레벨 DAT), `lvl_core_map.ipu`(지도 라벨 Jail Cell/Supply Room/Core/Lounge, CORE.DAT). SWAT 전용 levelselect_bg2(COMING SOON)·mainmenu·jr_*·rockstarpresents·showdown 로고는 미조사/로고.
- `tools/ipu.py`: 비트스트림 파서/빌더(게임 IPU 63개 전부 바이트 왕복 일치), 디코더(FFmpeg 대비 Y 최대 1 차이), 인코더, `replace_region`(글자 영역에 닿는 매크로블록만 재인코딩, 나머지는 계수 그대로 → 보호 영역 픽셀 불변). 테스트 `tests/test_ipu.py`.
- PoC: gen_01을 인페인팅(OpenCV Telea, 박스 내 어두운 무채색 픽셀) + Noto Serif CJK KR Black으로 한글 라벨 → 재인코딩 51,123B(원본 59,102B). 검증용 ISO(hunt/gen 슬롯 전부 교체)에서 로딩 화면에 한글 "조작법" 그림 정상 표시(scratchpad gt2/ingame_controller_ko.png). 엔진이 우리 인코더 출력 IPU를 그대로 디코드함.
- **범위 결정(2026-11-04, 사용자: A)**: mpscreens 기준 도달 8장 + coolscreen + gameover + lvl_core_map. 미도달 추정 03~06(5장)과 SWAT 전용 기타 IPU는 범위 밖(제외, 근거: mpscreens 개수).
- 제품 빌드 반영: `text/gfx_ko.json`(이미지별 src_sha1·별칭·박스·문구·글꼴·색, state needs_review) → `tools/gfxtext.py` → `build_patch.gfx_plan`(모든 사본이 src_sha1과 같아야 함, release는 distribution_eligible 필요, 문구가 박스를 벗어나면 실패). dev.iso: 이미지 11종, 사본 132개 교체(coolscreen 62, gameover 62, core_map 2, mpload 16).
- 런타임 확인: 제품 빌드에서 카드 색깔(mpload_*_02) 한글 표시, PoC에서 조작법(gen_01) 표시. 나머지 9종은 정적 검증(디코드·미리보기)만 — 로딩 이미지가 무작위라 화면 도달 미확인. coolscreen(LOADING)·gameover·코어 지도는 표시 시점 미확인.

## swui 버튼 배치 (2026-11-04, 사용자 보고: 멀티 설정 목록 배치 불균일·'즐겨 쓰는 캐릭터' 칸 넘침)

- 원인: `multioption_menu.swui`의 `<BUTTON:x,...>` x가 영어 폭에 맞춰 손으로 정한 왼쪽 끝(23/12/8/15 → 영어 중심 ≈48). 번역문 폭이 달라 왼쪽 끝이 들쭉날쭉. 'Hold'(누르고 있기)는 조작 하위 메뉴의 값 칸(86)을 거의 채워 화살표와 겹침, 'Favorite' 하위 메뉴 제목은 열 구분선에 닿음.
- 글꼴 헤더: u32 +8 = 자간(berrylium 1, regulatorcondensed 3), +12 = 공백 폭(14). 폭 = Σ(w+자간) + 공백×14.
- 조치: `text/swui_layout.json`(파일별 글꼴·배율·중심 x·라벨, 근거) → `build_patch.swui_recenter`가 번역문 폭으로 BUTTON/COMBO x를 다시 계산(FRONT·SWAT 사본 동일 확인). multioption_menu(중심 48), multioption_controls(값 칸 중심 49). 번역 축약: Favorite '주 캐릭터', Hold '누르기'.
- 확인(qa_opt2): 목록이 제목 축에 정렬, 조작 하위 메뉴 값이 화살표와 겹치지 않음, '주 캐릭터' 제목이 열 안에 들어감.
- 전체 swui 정적 점검(`scratchpad/swui_audit.txt`): 대부분 왼쪽 정렬 목록이고 한글 폭이 영어보다 좁아 문제 없음. 예/아니요 쌍(continue·warning·warningfrontend·profile)은 영어 단어 기준 x라 '아니요'(영어 'NO'보다 넓음)가 한쪽으로 쏠림 → 처음엔 라벨별 영어 중심 유지(keep_center)였으나 1장 '그만두기' 확인창에서 쌍이 오른쪽으로 쏠림(qa_l1/warn.png) → `mode: group`(영어 단어 사이 간격 유지, 쌍 전체를 영어 쌍의 중심에 배치)으로 교체. 1장 일시정지 → 그만두기 확인창에서 예/아니요 쌍이 상자 중앙(중심 534 vs 상자 527px) 확인(qa_l1b/warn.png), 아니요로 복귀. continue(재도전)·warningfrontend·profile은 같은 규칙, 화면 미확인.

## 상단 HUD 안내 줄바꿈 (2026-11-04)

- 관찰(dev.iso, 1장 튜토리얼): `swat_ps2.strtbl/Perfnew_Nav_Tutorial_2`가 줄바꿈되며 "스틱"만 둘째 줄에 남음.
- 측정: 상단 안내 상자는 띄어쓰기 단위로 앞에서부터 채워 줄바꿈한다. 표시 중인 문자열(EE RAM의 문자열 테이블 사본, UTF-16LE)을 PINE으로 폭을 아는 시험 문자열로 바꿔 가며 확인: 비확대 폭 464는 한 줄, 469는 줄바꿈 → 한계 [464, 468] (berrylium, sx 0.8, 폭 = Σ(글자폭 + 자간 1) + 공백 14).
- 하단 인물 대사 상자: 대사가 떠 있는 순간을 세이브스테이트(슬롯 4)로 잡고, 매번 불러온 뒤 같은 방식으로 측정 → 567 한 줄, 572 줄바꿈 → 한계 [567, 571]. 한 단어가 상자보다 길면 글자 단위로 끊김.
- 점검: berrylium sx 0.8 문자열 중 464/468 폭에서 한국어만 마지막 줄이 상자 폭 20% 미만으로 남는 것 34개. 33개를 고쳐 쓴 뒤, 사용자가 31개를 직접 다듬은 문안으로 교체(전부 needs_review 유지).
- 보류: `Sher70_DuelTutorial_2c` — 2/2a/2b/2c/2d가 단계를 하나씩 늘려 보여 주는 연속 문장이라, 사용자 문안(네 단계를 한 번에 나열, "표적 지정")을 넣으면 2d와 내용이 겹치고 용어("조준점 찍기")가 갈림. 미변경: `Sher70_DuelTutorial_26_combined`(칸 맞춤 범례, 표시 화면 미확인), `HOWTOGATGUN_10`(원문에 미사용 표기).
- 확인: 재빌드 후 게임에서 카메라 안내가 한 줄, 이어지는 START/플레이어 설정 안내는 두 줄로 고르게 표시.
- 한계: 문자열별 표시 상자가 매핑되지 않아 빌드 검사로 강제하지 않음. 점검 스크립트는 QA 보조 수단.
- 2차 점검(하단 상자 567/571 포함, 4개 폭 모두): 한국어에서만 홀로 남는 문장 18개 + 연속 문장 `Sher70_DuelTutorial_29b1`(29a1과 앞부분을 맞춤)을 고쳐 씀. 기준은 464 이하로 한 줄, 또는 두 상자 모두에서 고르게 두 줄.
- 남은 항목: 사용자 문안 6개(Draw_And_Holster2, Perfnew_Dummy_1/2, TIP_PigJosh_A/D, Traingood_More_Bandits)는 하단 상자에서는 문제없고 상단 상자에 나올 때만 끝 단어가 떨어짐. 음성 대사(Dummy·Draw·Bandits)는 하단 상자일 가능성이 높으나 TIP_*의 표시 상자는 미확인.
- 표시 상자 확인(1장 훈련장, 세이브스테이트 6·7): 아버지 음성 대사("훈련장에 온 걸 환영한다", "제법 잘 쏘는구나", `Perfnew_Dummy_1`)도 **상단 상자**에 표시됨. 음성 대사는 하단 상자라는 가정은 틀림. 하단 상자는 레벨 도입부 레터박스 구간 대사에서만 확인.
- 이에 따라 사용자 문안 6개(Perfnew_Dummy_1/2, Draw_And_Holster2, TIP_PigJosh_A/D, Traingood_More_Bandits)를 표현을 최소로 바꿔 464 이하로 줄임. `Perfnew_Dummy_1`은 상태 7에서 RAM의 문자열을 새 문안으로 바꾼 뒤 과녁을 맞혀 한 줄 표시를 확인.
- 남은 점검 대상(4개 폭 기준): `Sher70_DuelTutorial_26_combined`, `HOWTOGATGUN_10` 2개뿐.

## 1장 런타임 QA (2026-11-04, 세이브스테이트 5~10)

- 훈련장 안내(무기 뽑기, 조준 커서, 과녁 조준·사격·명중, 재장전, 허수아비 오른손·왼발·왼손·오른발)는 모두 상단 상자에 한글로 정상 표시. 오른발 단계는 자동 조준이 맞히지 못해 중단.
- 훈련 건너뛰기 → 본 전투에서 쓰러짐 → **그림 글자 "게임 오버"(gameover.ipu)와 "불러오는 중..."(coolscreen.ipu)를 게임 화면에서 확인** → 스토리 메뉴로 복귀. 1장(체크포인트 전)에서는 재도전 창(continue.swui)이 나오지 않음. 재도전 창 확인은 체크포인트가 있는 이후 구간이 필요.
- 방법 메모: 세이브스테이트 이후 고친 문장은 RAM의 문자열 테이블 사본을 새 문안으로 덮어 확인(새 문안이 더 짧을 때만). 조준은 화면에서 과녁(붉은 원)·부위 표식(흰 반짝임)과 조준점(주황/붉은 십자) 색을 찾아 오른쪽 스틱을 짧게 눌러 맞춤.

## 아카이브 이름표 사슬 제한: 21장 크래시·레벨 로딩 지연 (2026-11-05)

- 증상(현상금 사냥꾼 모드 순회): 모든 장에서 캐릭터 소개 영상(로딩 화면)이 약 2분 지속(원본 약 10초). 21장 '종착역'은 컷신(PSS/DIEGOCAR.PSS) 시작에서 `Jump to unaligned address (PC 0xc9f0acbb)` / `Jump to unmapped recLUT page` 또는 정지(RAM 변화 없음). 2장도 컷신 뒤 검은 화면.
- 배제한 가설(각각 콜드부트로 21장 실행): ISO 끝 추가 배치(디스크 탐색) → 원래 순서 재배치(`iso9660.replace_all`)해도 동일 / 아카이브 데이터 순서 → 원본 순서 재배치(`dave_patch.repack`)해도 동일 / 메인 힙 부족 → 로딩 중에도 3.4MB 여유 / 글꼴 페이지 크기(256²) → 128²로도 동일 / 재압축 → 우리 deflate가 원본과 바이트 동일.
- 이분 탐색: TRAIN.DAT 원본 복원 → 여전히 실패, **SWAT.DAT 원본 복원 → 정상**. SWAT.DAT 안에서는 자막만·그래픽만은 무관, 글꼴 하나(arial14, 글자 2개 추가)만 바꿔도 로딩 지연. 내용 변경 없이 위치만 밀기 → 정상. **빈 항목 하나 추가만으로**: 이름순 맨 뒤 → 로딩 지연, 맨 앞(모든 번호가 밀림) → 지연+크래시.
- 원인: `davename.encode`가 접두사 공유를 끝없이 이어 붙임(SWAT.DAT 최장 사슬 7965). 원본 아카이브 64개는 모두 **전체 이름 사이 간격이 최대 32**(32칸째에서 공유 가능해도 전체 이름 저장). 게임은 이름을 풀 때 전체 이름까지 최대 32항목만 거슬러 오르는 것으로 보이며, 넘으면 조회 실패 → 느린 대체 경로·엉뚱한 리소스.
- 수정: `davename.MAX_CHAIN = 32`(테스트 2개). 콜드부트 21장: 로딩 원본 수준, 컷신·플레이·재도전·게임 오버·불러오는 중·메뉴 복귀 정상, 에뮬레이터 예외 0.
- 함께 남긴 변경(원인은 아니었으나 원본 구조 보존): ISO 파일 순서 유지 재배치(이미지 2.94→2.36GB), 아카이브 데이터를 원본 순서로 재배치(배치 규칙은 원본 64개를 바이트 동일 재현).
- 영향: 이 수정 이전의 세이브스테이트·순회 관찰(로딩 시간, 2장 검은 화면 등)은 무효 → 새 빌드로 재순회.

## 보스 체력바 이름 (2026-11-05, 미해결)

- 현상금 사냥꾼 7장 "Katie"/"Slade", 13장 "Ted"/"Tony" 등 체력바 이름이 영어. 출처는 레벨 `lvl_*_var_*.enm`의 `Name` 필드이며 같은 문자열을 스크립트(actb/stateb)가 액터 식별자로 씀 → 값 직접 변경 불가.
- PoC: swat.strtbl에 키 'Katie'/'Slade' 추가(FRONT·SWAT·SHERNITE 사본 모두 반영 확인) → 화면은 영어 그대로. 체력바는 strtbl 조회를 거치지 않음(키 'Red'/'Scrooge'의 존재는 다른 소비자). PoC 항목은 되돌림.
- 한글화하려면 체력바 그리기 코드의 이름 인자를 가로채는 실행 파일 훅이 필요 → 범위·투자 결정 대상.

## 동영상(PSS) 자막 모집단 추가 (2026-11-05)

- 자막을 켠 순회(받은 세이브는 소리 설정 → 자막이 '끔'이었음)에서 3장 'How much for the lot?', 14장 'My fathers, I have news.'가 영어로 표시. 출처는 SWAT.DAT의 `<동영상>_en.txt`(PSS/SHER7001.PSS ↔ `sher7001_en.txt`). 형식은 레벨 컷신 자막과 같아 기존 파서로 바이트 왕복 일치(17개 파일).
- `tools/extract_pupshow.py`: 대상 = `lvl_*_pupshow_*_en.txt` + 디스크에 있는 PSS 이름과 일치하는 `<name>_en.txt`(17개). 키 기반 `lvl_*_subtitles_en.txt`(strtbl로 대체됨)와 짝 없는 파일(testsubtitles, jail01, jailnew01, station, wartrain01, 03_uglystreetfight_open 1, 02_bounty_open01_01, 1)은 제외. 동영상 자막은 SWAT.DAT에만 있어도 reach=game.
- 기준선 309 → 417큐(+108, 5,133자, 기존 기록 변경 0). 초벌 번역 108줄(15줄은 다른 컷신의 같은 문장 번역 재사용), 폭 제한(600) 초과 1줄 단축. 콜드부트 3장 동영상 자막 6줄 한글 표시·2줄 안에 맞음 확인.
- 자막을 켠 20개 장 순회: 레벨 컷신 자막 한글 정상(줄바꿈·잘림 없음), 에뮬레이터 예외 0.
