# 번역 검수 절차 (GPT 병행)

## 1. 검수 시트 만들기

```bash
python3 tools/review_export.py review          # review/<테이블>-NN.tsv, 시트당 최대 150줄
```

각 시트는 `id	en	ko` 세 칸입니다. 줄바꿈은 `\n`으로 적혀 있습니다.

## 2. GPT에 줄 규칙 (프롬프트에 함께 붙이기)

- `id`와 `en` 칸은 절대 바꾸지 말고 `ko` 칸만 고친다. 탭으로 구분된 3칸 형식을 유지한다.
- `{BTN_BD}`, `{ICON_2021}` 같은 중괄호 토큰은 버튼 아이콘이다. 개수와 이름을 그대로 둔다.
- `\n`(강제 줄바꿈)은 원문에 있을 때만 쓰고, 원문과 같은 개수를 유지한다.
- 용어는 `text/glossary.json`의 approved 항목을 따른다 (인명·지명 표기, 별명은 뜻으로 옮김, 서부극 말투).
- 화면 상단 안내 상자는 한 줄이 좁다: 한글 약 19자(띄어쓰기 포함 대략 20자 안팎)를 넘으면 줄이 넘어간다.
  넘어갈 때 마지막 줄에 짧은 단어 하나("봐라.", "있다.")만 남지 않게 문장 길이를 맞춘다.
- 게임 글꼴에 없는 문자는 쓰지 않는다: `…` 대신 `...`, `–` 대신 `-`.

## 3. 결과 반영

```bash
python3 tools/review_export.py --import review/swat.strtbl-01.tsv > batch.json
python3 tools/tr_merge.py batch.json --replace     # 토큰·글리프 검사 실패 시 반영 안 됨
python3 tools/wrap_audit.py                        # 줄바꿈 홀로 남는 단어 후보
python3 -m pytest -q && python3 tools/build_patch.py work/build/dev.iso
```

주의: 시트는 만든 시점의 번역을 담는다. 시트를 만든 뒤 같은 문장을 따로 고쳤다면, 예전 시트를 반영할 때 그 수정이 덮어써진다. 다른 수정이 있었으면 시트를 다시 만들어 쓴다.

검수를 마친 항목의 상태를 `distribution_eligible`로 올리는 것은 사람이 결정한다 (`tr_merge.py --state distribution_eligible`).
