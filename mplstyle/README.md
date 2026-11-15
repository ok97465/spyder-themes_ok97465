# Matplotlib 스타일

이 저장소의 다크 테마 33개에 맞춰 사용할 수 있는 Matplotlib 스타일
27개입니다. 기존 VS Code Modern에 26개를 추가했습니다. 테마의 배경 색조와
강조색을 바탕으로, Spyder 배경보다 조금 밝은 figure와 axes를 사용합니다.
데이터 기본 6~8색, 글자, 눈금, 격자, 범례, 오류 막대, 박스 플롯과 저장
배경을 함께 설정합니다. 크기·글꼴·간격은 기존 Modern 스타일과 같습니다.

각 `.mplstyle`은 독립 파일이므로 다른 스타일 파일을 함께 복사할 필요가 없습니다.
VS Code Modern의 기존 파일은 그대로 유지합니다.

## 테마 선택

| Spyder 다크 테마 | 스타일 파일 | 배색 특징 |
| --- | --- | --- |
| Brutalism | [brutalism-dark.mplstyle](brutalism-dark.mplstyle) | 따뜻한 회색, 금색·살구·세이지 |
| Carbonfox | [carbonfox-dark.mplstyle](carbonfox-dark.mplstyle) | 중성 회색, 선명한 파랑·분홍·초록 |
| Catppuccin Mocha | [catppuccin-mocha-dark.mplstyle](catppuccin-mocha-dark.mplstyle) | 보랏빛 배경과 파스텔 |
| Dracula | [dracula-dark.mplstyle](dracula-dark.mplstyle) | 청회색, 밝은 초록·분홍·보라 |
| Flexoki | [flexoki-dark.mplstyle](flexoki-dark.mplstyle) | 먹색, 차분한 흙빛·청록 |
| GitHub Dark | [github-dark.mplstyle](github-dark.mplstyle) | 짙은 남색, 파랑·살구·민트 |
| GitHub Dark Dimmed | [github-dark-dimmed.mplstyle](github-dark-dimmed.mplstyle) | 밝아진 슬레이트 배경, 부드러운 강조색 |
| Gruvbox | [gruvbox-dark.mplstyle](gruvbox-dark.mplstyle) | 따뜻한 회갈색, 노랑·초록·빨강 |
| Horizon | [horizon-dark.mplstyle](horizon-dark.mplstyle) | 청회색, 장미색·살구·청록 |
| Inkpot | [inkpot-dark.mplstyle](inkpot-dark.mplstyle) | 보랏빛 회색, 청보라·연주황·청록 |
| Kanagawa Dragon | [kanagawa-dragon-dark.mplstyle](kanagawa-dragon-dark.mplstyle) | 따뜻한 먹색, 채도를 낮춘 자연색 |
| Material | [material-dark.mplstyle](material-dark.mplstyle) | 푸른 회색, 밝은 파스텔 |
| Miami Nights | [miami-nights-dark.mplstyle](miami-nights-dark.mplstyle) | 보랏빛 배경, 네온 강조색 |
| Modus | [modus-dark.mplstyle](modus-dark.mplstyle) | 검정에 가까운 배경, 강한 대비 |
| Monokai | [monokai-dark.mplstyle](monokai-dark.mplstyle) | 올리브 회색, 라임·분홍·주황 |
| Nightfox | [nightfox-dark.mplstyle](nightfox-dark.mplstyle) | 짙은 남색, 차분한 파랑·옥색 |
| Nordfox | [nordfox-dark.mplstyle](nordfox-dark.mplstyle) | 차가운 청회색, 절제된 파스텔 |
| Obsidian | [obsidian-dark.mplstyle](obsidian-dark.mplstyle) | 차가운 회색, 초록·주황·청보라 |
| One Dark Pro | [one-dark-pro-dark.mplstyle](one-dark-pro-dark.mplstyle) | 청회색, 파랑·황토·보라 |
| PaperColor | [papercolor-dark.mplstyle](papercolor-dark.mplstyle) | 중성 회색, 선명한 터미널 계열 색 |
| Solarized | [solarized-dark.mplstyle](solarized-dark.mplstyle) | 푸른 녹색 배경, 따뜻한 글자색 |
| Spyder | [spyder-dark.mplstyle](spyder-dark.mplstyle) | 남색, 밝은 파랑·보라·노랑 |
| Sublime Mariana | [sublime-mariana-dark.mplstyle](sublime-mariana-dark.mplstyle) | 슬레이트 배경, 부드러운 주황·청록 |
| Tokyo Night | [tokyonight-dark.mplstyle](tokyonight-dark.mplstyle) | 남보라색 배경, 파랑·보라·분홍 |
| VS Code High Contrast | [vscode-high-contrast-dark.mplstyle](vscode-high-contrast-dark.mplstyle) | 검정에 가까운 배경, 밝은 글자와 축 |
| VS Code Modern | [vscode-modern-dark.mplstyle](vscode-modern-dark.mplstyle) | 중성 회색, 파랑·살구·청록 |
| Zenburn | [zenburn-dark.mplstyle](zenburn-dark.mplstyle) | 중성 회색, 낮은 채도의 따뜻한 색 |

## 별도 파일을 만들지 않은 테마

배경과 데이터 배색이 가까운 경우 공유할 스타일을 골랐습니다.
원본 테마를 정확히 재현하는 별칭은 아니며, 플롯에 어울리는 공통 배색입니다.

| Spyder 다크 테마 | 사용할 스타일 | 통합 이유 |
| --- | --- | --- |
| Ayu | [github-dark.mplstyle](github-dark.mplstyle) | 짙은 남색 배경과 파랑·주황·보라·노랑 조합이 가까움 |
| IDLE | [dracula-dark.mplstyle](dracula-dark.mplstyle) | 초록·하늘색·주황·보라 강조색이 많이 겹침 |
| Notepad++ | [vscode-modern-dark.mplstyle](vscode-modern-dark.mplstyle) | 파랑·살구·보라 중심의 VS Code 계열 배색 |
| Tokyo Night AltSynt | [tokyonight-dark.mplstyle](tokyonight-dark.mplstyle) | 배경과 기본 글자색이 같고 데이터색도 비슷한 범위 |
| VS Code 2017 | [vscode-modern-dark.mplstyle](vscode-modern-dark.mplstyle) | 핵심 구문색이 Modern과 같음 |
| VS Code 2026 | [github-dark.mplstyle](github-dark.mplstyle) | 파랑·라일락·살구·빨강이 GitHub 계열과 겹침 |

Alabaster와 Rosé Pine Dawn은 라이트 전용이므로 대상에서 제외했습니다.
고대비 테마인 Modus와 VS Code High Contrast는 배경이 비슷하지만 데이터
배색 차이가 있어 둘 다 유지합니다. GitHub Dimmed도 배경 밝기와 강조색의
차이가 커 별도로 유지합니다.

## 원하는 때 적용

그림을 생성하기 전에 실행합니다. 상대 경로는 현재 작업 디렉터리를 기준으로
하므로 Spyder에서 여러 프로젝트를 오갈 때는 절대 경로가 편합니다.

```python
import matplotlib.pyplot as plt

plt.style.use([
    "default",
    "/Users/ok97465/codepy/spyder-themes_ok97465/mplstyle/vscode-modern-dark.mplstyle",
])

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [2, 1, 4], label="Signal")
ax.legend()
plt.show()
```

`default`를 먼저 적용하면 이전 스타일에서 지정했던 설정이 남는 것을
줄일 수 있습니다. 이후 생성할 그림을 Matplotlib 기본값으로 돌리려면
`plt.style.use("default")`를 실행합니다. 이미 생성한 그림은 다시 그립니다.

일부 코드에서만 사용하려면 다음처럼 범위를 제한합니다.

```python
with plt.style.context(["default", "/absolute/path/vscode-modern-dark.mplstyle"]):
    fig, ax = plt.subplots()
    ax.scatter([1, 2, 3], [2, 1, 4])
    plt.show()
```

## 이름으로 불러오기 (선택)

`matplotlib.get_configdir()` 아래 `stylelib/`에 스타일 파일을 복사하거나
심볼릭 링크로 연결하면 `plt.style.use(["default", "vscode-modern-dark"])`로
불러올 수 있습니다. 이 저장소 파일은 제자리에 두어도 됩니다.
이미 실행 중인 콘솔에서 파일을 등록했다면 `plt.style.reload_library()`를 실행합니다.

## 미리보기

Spyder에서 `../.tools/preview_mplstyle.py`를 열고 F5로 실행합니다.
Plots 창을 사용하려면 Spyder의 그래픽 백엔드는 Inline으로 설정합니다.
스크립트는 작업 디렉터리와 관계없이 이 폴더의 스타일을 찾습니다.
F5의 기본 스타일은 Modern입니다. 다른 스타일은 Spyder의 실행 옵션에
`--style /absolute/path/gruvbox-dark.mplstyle`을 지정하거나 IPython 콘솔에서
다음처럼 실행합니다.

```python
%run /Users/ok97465/codepy/spyder-themes_ok97465/.tools/preview_mplstyle.py --style /Users/ok97465/codepy/spyder-themes_ok97465/mplstyle/gruvbox-dark.mplstyle
```

터미널에서 그림을 저장할 수도 있습니다 (저장소 루트에서 실행).

```bash
MPLBACKEND=Agg python .tools/preview_mplstyle.py \
  --style mplstyle/gruvbox-dark.mplstyle \
  --save-dir .artifacts/mplstyle-gruvbox-dark --no-show
```

총 12가지 예제를 세 그림으로 만듭니다: 선과 범례, 산점도, 겹친 히스토그램,
그룹 막대, 오류 막대와 신뢰 구간, 로그 축, 히트맵과 컬러바, 등고선,
박스 플롯, 바이올린 플롯, 원형 그래프, 주석과 수식.

모든 스타일의 렌더링·대비·저장 배경을 한 번에 검증하려면 다음을 실행합니다.
이 검증에는 Matplotlib, NumPy, Pillow가 필요합니다.

```bash
python .tools/verify_mplstyles.py
```

`.artifacts/mplstyle-gallery/`에 스타일별 PNG·SVG, 전체 비교 이미지
`contact-sheet-01.png`부터 `contact-sheet-03.png`, 검사 결과 `validation.json`을
저장합니다. 파일 이름을 선택해서 검사할 수도 있습니다.

```bash
python .tools/verify_mplstyles.py --styles gruvbox-dark solarized-dark
```

검증 기준은 본문·범례 글자 대비 7:1 이상, 눈금 4.5:1 이상, 데이터색과
축 테두리 3:1 이상입니다. 격자는 데이터보다 약하게 표시합니다. 이 수치는
불투명한 기본색과 배경의 대비이며, 투명도·선 굵기·색각에 따른 식별성 전체를
보장하지 않습니다. 많은 계열을 겹쳐 그릴 때는 마커와 선 모양도 함께 사용합니다.

## 개별 지정이 필요한 부분

- `violinplot`의 collection 색, 주석 화살표 색, 원형 그래프 내부 비율 글자에는
  전용 스타일 설정이 없습니다. 미리보기 스크립트에서 필요한 지정법을 보여 줍니다.
- `image.cmap`은 순차형 `viridis`입니다. 양수·음수의 차이를 표현하는 데이터는
  예제처럼 발산형 컬러맵을 직접 선택합니다.
- 코드에서 `color="black"`, `facecolor="white"` 등을 명시하거나 다른 라이브러리가
  스타일을 다시 설정하면 해당 설정이 우선합니다.
- PNG/SVG는 어두운 배경을 유지합니다. 밝은 보고서용 그림은 밝은 스타일로
  다시 생성하는 편이 좋습니다.

2026-11-15에 Matplotlib 3.10.6에서 27개 스타일 전부의 12종 예제(총 324개
subplot)를 렌더링하고 PNG 81개와 SVG 81개의 배경·불투명도를 확인했습니다.
대비 검사 최솟값은 본문 7.830:1, 범례 7.020:1, 눈금 4.537:1,
데이터색 3.166:1, 축 테두리 3.011:1입니다.

커스텀 Spyder 6.2.0a3의 Inline Plots 창에서는 Modern을 처음 검증한 뒤,
Solarized·Monokai·Kanagawa Dragon·GitHub Dimmed의 예제를 직접 실행하고
27개 스타일의 전체 비교 이미지 세 장을 확인했습니다. 화면 확인에는
설치된 PyQt5 / Qt 5.15.2를 사용했습니다. PySide6 / Qt 6.9.2는
화면 자동화의 접근성 조회 중 충돌하여 시각 검증에서 제외했습니다.
