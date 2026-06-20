# PDF 순차 분할 프로그램

기능 요구사항 정본: [docs/product_spec.md](docs/product_spec.md)

Tkinter GUI에서 PDF를 열고, 썸네일을 클릭할 때마다 현재 시작 페이지부터 선택한 페이지까지를 별도 PDF로 순차 저장하는 프로그램입니다. 페이지 번호는 모두 `0`부터 시작하는 인덱스로 처리합니다.

## 설치

### 프로젝트 방식으로 설치

```powershell
python -m pip install -e .
```

### 패키지만 직접 설치

```powershell
python -m pip install Pillow PyMuPDF pypdf tkinterdnd2
```

## 실행

```powershell
python -m pdf_splitter
```

또는

```powershell
pdf-splitter
```

또는 파일을 직접 실행해도 됩니다.

```powershell
python pdf_splitter/main.py
```

## 외부 라이브러리 선택 이유

- `PyMuPDF`: PDF 페이지를 빠르게 이미지로 렌더링할 수 있어 썸네일 생성에 적합합니다.
- `pypdf`: 외부 실행 파일 없이 PDF 페이지를 읽고 지정 구간만 새 파일로 저장하기 쉽습니다.
- `Pillow`: 렌더링된 이미지를 Tkinter에서 표시 가능한 썸네일로 가공하고 `ImageTk.PhotoImage`로 연결하는 데 필요합니다.
- `tkinterdnd2`: OS 파일 관리자에서 PDF 파일을 Tkinter 창으로 드래그앤드롭해 열 수 있게 합니다.

## 사용 방법

1. `PDF 열기`를 눌러 원본 PDF를 선택하거나, PDF 파일을 앱 창에 드래그앤드롭합니다.
2. 필요하면 `저장 폴더 선택`으로 출력 폴더를 바꿉니다. 기본값은 원본 PDF와 같은 폴더입니다.
3. 썸네일을 클릭하면 현재 시작 페이지부터 클릭한 페이지까지의 저장 정보가 먼저 표시됩니다.
4. 확인을 누르면 해당 구간을 저장합니다.
5. 다음 분할은 직전 저장 구간의 다음 페이지부터 시작합니다.
6. 마지막 페이지까지 저장하면 완료 메시지가 표시됩니다.

예시:

- `3`페이지 클릭 -> `0~3` 저장
- `5`페이지 클릭 -> `4~5` 저장
- `8`페이지 클릭 -> `6~8` 저장

## 검증 명령

```powershell
python -m compileall .
python -m unittest
ruff check .
```

## 작업 완료 알림음

작업이 끝나면 지정한 WAV 파일을 재생하려면 아래 스크립트를 사용할 수 있습니다.

```powershell
.\tools\play_done_sound.ps1
```

기본 재생 파일은 `C:\Users\dolco\Music\222.wav`입니다. 다른 파일을 쓰려면 경로를 넘기면 됩니다.

```powershell
.\tools\play_done_sound.ps1 -Path C:\Users\dolco\Music\other.wav
```

Codex에게 일을 시킬 때는 프롬프트 마지막에 아래처럼 적으면 됩니다.

실행 정책 회피용으로 `.\tools\play_done_sound.cmd` 래퍼도 함께 제공합니다.

```powershell
.\tools\play_done_sound.cmd
```

```text
작업이 끝나면 .\tools\play_done_sound.cmd 를 실행해줘.
```
