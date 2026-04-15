# PDF 변환 스킬

HWP/HWPX 파일을 PDF로 변환하고, PDF를 이미지(PNG)로 변환하는 스킬.

## 트리거
- 사용자가 HWP/HWPX → PDF 변환을 요청할 때
- PDF를 이미지로 변환할 때
- 문서를 시각적으로 비교/확인할 때

## HWP/HWPX → PDF 변환

한글 COM 자동화를 사용한다. **주의**: `Visible` 설정을 하지 않고, `Open()` 시 format 파라미터를 빈 문자열로 전달해야 정상 동작한다.

```python
import win32com.client
import os, time

MAX_RETRIES = 2

def convert_hwp_to_pdf(hwp_paths):
    """HWP/HWPX 파일 목록을 PDF로 변환. 변환된 PDF 경로 리스트 반환."""
    if not hwp_paths:
        return []

    results = []
    hwp = None

    try:
        hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
        hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')

        for hwp_path in hwp_paths:
            pdf_path = hwp_path.rsplit('.', 1)[0] + '.pdf'

            # PDF가 이미 존재하면 스킵
            if os.path.exists(pdf_path):
                results.append(pdf_path)
                continue

            converted = False
            for attempt in range(MAX_RETRIES + 1):
                try:
                    hwp.Open(hwp_path, "", "forceopen:true")  # format은 빈 문자열!
                    hwp.HAction.GetDefault("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
                    hwp.HParameterSet.HFileOpenSave.filename = pdf_path
                    hwp.HParameterSet.HFileOpenSave.Format = "PDF"
                    hwp.HAction.Execute("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
                    hwp.Clear(1)
                    converted = True
                    break
                except Exception as e:
                    try: hwp.Clear(1)
                    except: pass
                    if attempt < MAX_RETRIES:
                        wait = 2 ** attempt
                        print(f'  [재시도] PDF 변환 ({os.path.basename(hwp_path)}) {attempt + 1}/{MAX_RETRIES} ({wait}초 후)...')
                        time.sleep(wait)
                    else:
                        print(f'  [실패] PDF 변환 ({os.path.basename(hwp_path)}): {e}')
            results.append(pdf_path if converted else None)

    except Exception as e:
        print(f'  [실패] 한글 프로그램 초기화: {e}')

    finally:
        try:
            if hwp: hwp.Quit()
        except: pass

    return results
```

## PDF → 이미지(PNG) 변환

PyMuPDF(fitz)를 사용한다.

```python
import fitz

def pdf_to_images(pdf_path, dpi=200):
    """PDF의 각 페이지를 PNG 이미지로 변환. 이미지 경로 리스트 반환."""
    doc = fitz.open(pdf_path)
    images = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for i in range(doc.page_count):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat)
        out_path = pdf_path.rsplit('.', 1)[0] + f'_p{i+1}.png'
        pix.save(out_path)
        images.append(out_path)
    doc.close()
    return images
```

## 통합 함수: HWPX → 이미지

```python
def hwpx_to_images(hwpx_path, dpi=200):
    """HWPX 파일을 PDF로 변환 후 각 페이지를 PNG 이미지로 변환."""
    pdf_paths = convert_hwp_to_pdf([os.path.abspath(hwpx_path)])
    if pdf_paths and pdf_paths[0]:
        return pdf_to_images(pdf_paths[0], dpi=dpi)
    return []
```

## PDF 텍스트 추출

PyMuPDF로 PDF에서 텍스트를 추출한다.

```python
import fitz

def extract_text_from_pdf(pdf_path):
    """PDF 전체 텍스트 추출."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text
```

### 공문번호 추출 예시

```python
import re

def extract_gongmun_number(pdf_path):
    """PDF에서 공문번호 추출 (시행기관명-번호(날짜) 패턴). 없으면 None."""
    text = extract_text_from_pdf(pdf_path)
    match = re.search(
        r'시행\s*(.+?-\d+)\s*\(\s*(\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.)\s*\)',
        text
    )
    if match:
        inst_num = match.group(1).strip()
        date_str = re.sub(r'\s+', ' ', match.group(2).strip())
        return f"{inst_num}({date_str})"
    return None
```

## PDF 특정 페이지만 이미지 변환

첫 페이지 등 특정 페이지만 변환할 때 사용.

```python
import fitz, tempfile, os

def pdf_page_to_image(pdf_path, page_num=0, dpi=200):
    """PDF 특정 페이지를 PNG로 변환. 임시 파일 경로 반환."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    doc.close()

    fd, tmp_path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    pix.save(tmp_path)
    return tmp_path
```

## 재시도 로직

PDF 변환/이미지 변환 등에서 실패 시 지수 백오프로 재시도한다.

```python
import time

MAX_RETRIES = 2

def with_retry(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """함수 실행을 최대 max_retries회 재시도 (지수 백오프)."""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f'  [재시도] {attempt + 1}/{max_retries} ({wait}초 후)...')
                time.sleep(wait)
            else:
                raise
```

## 의존성
- `win32com.client` (pywin32) - HWP COM 자동화
- `fitz` (PyMuPDF) - PDF → 이미지, 텍스트 추출
- 한글 프로그램 설치 필수 (HWPFrame.HwpObject COM)
