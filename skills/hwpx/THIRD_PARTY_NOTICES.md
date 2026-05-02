# Third-Party Notices

이 스킬은 다음 오픈소스 프로젝트의 알고리즘과 아이디어를 참조·이식하여 사용합니다.
각 원저작자와 라이선스 전문을 아래에 명시합니다.

---

## 1. rhwp — HWPX/HWP Viewer and Editor (Rust + WebAssembly)

- **저장소**: https://github.com/edwardkim/rhwp
- **저작권**: Copyright (c) 2025-2026 Edward Kim
- **라이선스**: MIT License

### 참조·이식 범위

다음 알고리즘·패턴을 Python으로 재작성하여 본 스킬에 포함하였습니다. 원본 소스 코드
자체는 포함하지 않으며, 설계 의도·상수·제어 흐름을 참고한 독립 구현입니다.

| 스킬 내 파일 | 참조한 rhwp 파일 | 이식 내용 |
|--------------|-------------------|-----------|
| `scripts/table_calc.py` | `src/document_core/table_calc/{tokenizer,parser,evaluator}.rs` | 3-layer 수식 엔진 (토크나이저/파서/평가기). SUM/AVG/MIN/MAX/COUNT/IF + 단항 수학 함수 + 셀 참조(A1, A1:B5, ?1, A?, above·below·left·right) |
| `scripts/hwpx_helpers.py` — `local_name()`, `xpath_local()` | `src/parser/hwpx/utils.rs:10-18` | 네임스페이스 prefix 무관 XPath 패턴 |
| `scripts/hwpx_helpers.py` — `utf16_len()`, `tab_aware_offset()` | `src/parser/hwpx/section.rs:299-322` | UTF-16 코드유닛 + 탭 8-unit 오프셋 규칙 |
| `scripts/hwpx_helpers.py` — `read_zip_entry_limited()`, 상수 | `src/parser/hwpx/reader.rs:19-26` | zip bomb 방어 상한 (XML 32MB / BinData 64MB) |
| `scripts/verify_hwpx.py` | 동상 | zip bomb 상한 체크 통합 |
| `scripts/hwpx_modifier.py` — `collect_all_fields()` | `src/document_core/queries/field_query.rs` + `src/parser/hwpx/section.rs::parse_ctrl_field_begin` | `<hp:fieldBegin>` 파싱 패턴 |

### 라이선스 전문 (MIT License)

```
MIT License

Copyright (c) 2025-2026 Edward Kim

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. jkf87/hwpx-skill

- **저장소**: https://github.com/jkf87/hwpx-skill
- **역할**: 본 스킬의 최초 기반(base fork). 이후 독자적으로 확장됨.
- **변경 사항 요약**: `README.md` 참조.

---

## 문의

추가 고지·수정 요청이 있으면 이슈로 알려주세요.
