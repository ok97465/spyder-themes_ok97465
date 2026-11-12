# 테마 검토 기준과 결과

## 수정 범위

`upstream/main`과 저장소 최초 import 이력으로 원래 포함된 13개 테마를 구분합니다.
아래 테마는 이번 검토에서 **읽기 전용**으로 유지합니다. 검토 중 적용했던 변경도
되돌렸으며 이 저장소의 작업 시작 시점과 같습니다.

`brutalism`, `catppuccin-mocha`, `dracula`, `gruvbox`, `idle`, `inkpot`,
`miami-nights`, `monokai`, `notepad++`, `obsidian`, `solarized`, `spyder`, `zenburn`.

수정 대상은 우리가 추가한 **22개 테마·33개 변형**입니다. Spyder 본체는 수정하지
않습니다. 전체 설치 시 원래 테마도 함께 빌드하지만 해당 테마의 YAML은 바꾸지 않습니다.

## 실제 프로그램 대조

설치된 VS Code 1.146.0에서 공통 Python 샘플을 열고 **45개 참고 테마를 직접 적용**했습니다.
구문색, 활성·비활성 탭, 사이드바, 버튼, 툴바, 패널 경계와 **명령 팔레트의 배경·선택 행·글자·테두리**를
확인했습니다. 빠져 있던 원본 계열의 공식 Marketplace 확장 12개도 설치했습니다.
검토 후 VS Code는 원래 `Default High Contrast`로 복원했습니다.

Nightfox·Nordfox는 설치된 **Nightfox Theme Collections 1.0.7**을 별도로 직접 적용해
툴바, 활성·비활성 탭, pane 경계, 버튼과 명령 팔레트를 확인했습니다. 이 대조 후에는
작업 시작 시 선택되어 있던 `modus-vivendi`로 복원했습니다. 두 테마는 nvim 원본이
아닌 [VS Code 이식본](https://github.com/nuromirg/nightfox-vscode/tree/ed72c227cd94a9698ad463aad8d496fcc0441b2d)을
기준으로 하며, 설치된 JSON과 고정 revision의 SHA-256이 일치합니다.

Sublime Text **Build 4215**에서도 **Adaptive UI + Monokai / Mariana**를 번갈아 적용하고
코드·탭·명령 팔레트·검색 버튼을 확인했습니다. Mariana는 VS Code 이식본보다 **설치된
Sublime Text의 리소스와 실제 화면을 우선**합니다. 원래 포함된 Monokai는 검토만 하며
YAML을 수정하지 않습니다. Sublime 선택도 원래 Adaptive + Monokai로 복원했습니다.

Vim·Emacs·Sublime 기반 테마의 VS Code 확장은 별도 이식본입니다. Folke Tokyo Night와
Enkia의 VS Code Tokyo Night, 개인 Catppuccin·Dracula 변형과 공식 배색은 완전히 같지
않습니다. 참고 확장으로 기존 개인 구문색을 덮어쓰지 않고 각 YAML의 원본·변형 정책을
따릅니다. Brutalism·Ciaran Inkpot·Jupyter Miami Nights는 정확히 대응하는 VS Code 확장을
확인하지 못했으며 이름만 비슷한 확장을 동일 원본으로 취급하지 않습니다.

## 반영한 수정

- 비활성 탭·도움말: 현재 Spyder가 둘 다 `COLOR_BACKGROUND_4`를 사용하므로
  `COLOR_TAB_BACKGROUND`와 같은 보완색을 사용합니다. 테마의 중성색·종이색 계열 안에서
  얇은 경계와 탭 글자가 보이도록 조정합니다.
- 활성 프레임: `COLOR_ACCENT_3`가 코드·패널 배경과 거의 같던 추가 테마를 보완합니다.
  Rosé Pine Dawn은 비활성 무테두리 의도를 유지하면서 포커스는 식별할 수 있게 합니다.
- 메뉴·명령 팔레트: 메뉴 선택색을 프레임 포커스색과 독립시킵니다. 원본 메뉴·quick input
  색과 알파 합성을 확인해 불투명 Qt 색으로 옮깁니다. Switcher는 글자를 `COLOR_TEXT_1`로
  HTML에 넣으므로 원본의 독립된 선택 글자색을 적용할 수 없는 경우 선택 배경을 보완합니다.
- 버튼: 일반·호버·누름·비활성 상태를 실제 Qt에서 확인합니다. Mariana는 Adaptive의
  흰색 오버레이를 기준으로 기본 `#3F4347`, 호버 `#55595D`, 누름 `#616468`, 글자
  `#EAEBEC`로 수정했습니다. 원본처럼 누를 때 밝아집니다.
- 구문 매핑: Flexoki의 내장 함수는 원본 주황색·굵게, Python `self/cls`와 상속 클래스
  참조는 일반 글자색으로 수정했습니다. Carbonfox storage는 키워드 보라색으로, Modus
  괄호 순환은 `rainbow-0`부터 시작하도록 바로잡았습니다. 원본 구문색을 일괄 재색칠하지 않습니다.

Mariana 명령 팔레트는 Adaptive의 배경 `#1D2227`, 선택 행 `#3F4347`, 입력창 `#303841`을
사용합니다. 실제 검색 패널과 일반 대화상자는 바탕이 달라 버튼 합성색이 조금 다릅니다.
Qt에는 대화상자 기준의 불투명 색을 사용합니다. Sublime의 macOS 메뉴는 OS가 그리므로
Qt 메뉴색을 Adaptive의 동일 역할을 그대로 복제한 값이라고 주장하지 않습니다.

VS Code High Contrast는 검정·흰색 코드/툴바 바탕과 native 대비색을 유지합니다. Dark
비활성 pane은 `#6FC3DF`, 포커스는 `#F38518`; Light는 `#0F4A85`와 `#006BBD`입니다.
도움말·탭은 Qt 보완색을 쓰며 HC 메뉴와 Switcher에는 원본의 선택 윤곽선도 표시합니다.
Switcher는 선택 배경을 유지하면서 Dark `#F38518`, Light `#006BBD`의 1px 윤곽선으로
선택 행을 구분합니다. 실제 목록에서 네 면의 픽셀과 3:1 이상의 경계 대비를 확인합니다.

## Spyder 수정 없이 적용

인접 ThemeWeaver의 선택적 역할로 QSS와 Qt 리소스를 함께 생성합니다.
역할을 선언하지 않은 기존 테마의 스타일은 변경하지 않습니다.

| 역할 | 사용처 |
| --- | --- |
| `COLOR_PANE_BORDER` / `COLOR_EDITOR_BORDER` / `COLOR_SIDEBAR_BORDER` | 비활성 콘텐츠 프레임 |
| `COLOR_ACCENT_3` | 활성 프레임 |
| `COLOR_TAB_*` | 탭 배경·글자·호버·선택 강조선 |
| `COLOR_BUTTON_*` | 버튼 배경·글자·호버·누름·테두리 |
| `COLOR_MENU_*` | 메뉴 일반·선택 배경/글자와 1px 테두리 |
| `COLOR_MENU_SELECTED_BORDER` | 필요한 테마의 메뉴 선택 윤곽선 |
| `COLOR_SWITCHER_*` | 실제 Spyder Switcher 배경·선택 행·입력창·테두리 |
| `COLOR_SWITCHER_SELECTED_BORDER` | 필요한 테마의 Switcher 선택 윤곽선 |

Switcher QSS는 개별 선택자로 출력합니다. 쉼표로 묶인 자손 선택자의 공백을 qstylizer가
없애 실제 목록에 적용되지 않던 문제를 ThemeWeaver에서 처리했습니다. 테스트 위젯에
임시 색을 주입하거나 Spyder를 수정하지 않습니다.

## 검증

최종 wheel을 별도 경로에 고정해 검증한 결과 **31/31개 변형**, 실제 위젯 상태·픽셀
**1,091개 검사**, UI 글자·아이콘 대비 **558쌍**이 통과했습니다. 원래 13개 테마의
소스와 기존 설치 기준 패키지 파일 **5,643개**가 동일한지도 확인했습니다.
실제 프로그램과 Qt 화면을 나란히 둔 로컬 결과는
[화면 비교 보고서](.artifacts/theme-review-2026-11-13/index.html)에서 볼 수 있습니다.

Nightfox·Nordfox의 별도 결과는
[실제 Qt 화면·상태별 캡처](.artifacts/nightfox-nordfox-review/spyder/index.html)와
[원본·내보내기 검증](.artifacts/nightfox-nordfox-review/source-verification.json)에 있습니다.
두 변형의 원본 색·서식 132개, 위젯·상태 픽셀 검사 70개, UI 글자·아이콘 대비
36쌍과 공유 역할 대비 6개를 통과했습니다. 검증한 wheel을 Anaconda `base`에 설치하고
[설치 파일 12,849개 일치](.artifacts/nightfox-nordfox-review/install-verification.json)를
확인했습니다. 테마 목록 등록을 제외한 기존 테마 파일 12,408개는 동일하며, 이 개수에서
Python bytecode와 macOS `.DS_Store`는 제외합니다.
툴바는 원본 title bar 배경, 활성 pane은 원본의 파랑, 비활성 pane은 원본 경계색을
사용합니다. 비활성 탭과 Help 프레임이 공유하는 색은 각 테마의 청회색 안에서 밝기를
보완하고, Nordfox 메뉴·Switcher·트리 선택 배경은 `#48586B`로 소폭 어둡게 했습니다.
구문색과 italic 주석, 활성 탭, 기본·호버 버튼색은 VS Code 원본을 유지합니다.

`COLOR_ERROR_1`은 중지 아이콘과 Dependencies 셀 배경에 함께 쓰입니다. 두 테마는
Dependencies 글자에 원본의 밝은 ANSI 흰색을 쓰고 오류·경고 셀 배경을 같은 색조의
어두운 색으로 보완했습니다. 셀 글자는 4.5:1 이상입니다. Nordfox의 공유 오류색은
원본 툴바 위에서 약 2.72:1이므로 이 중지 아이콘까지 3:1이라고 주장하지 않습니다.
일반 오류·경고 아이콘의 `ICON_4/5`는 원본색을 유지합니다. Spyder 본체나 ThemeWeaver
코드를 추가로 수정하지 않고 기존 YAML 역할만 사용했습니다.

일반 UI 글자는 4.5:1, 일반 툴바 아이콘은 3:1을 확인합니다. 메뉴 일반·선택 글자와
Switcher 일반 행·선택 행·입력창도 포함합니다. 일반 프레임의 1.4:1은 이 저장소의 얇은
경계 시각 점검 기준이며 접근성 인증 기준은 아닙니다. HC는 주요 경계에 3:1을 확인합니다.
명시적 무테두리는 비활성 대비 하한을 강제하지 않되 실제 색과 활성 포커스는 확인합니다.

원본의 흐린 주석·줄 번호·일부 구문색은 대비 참고값으로 보고합니다. 이를 전부 4.5:1로
바꾸면 원본을 훼손하므로 UI 필수 검사와 구분합니다. 기존 13개 테마의 발견 사항은
수정 사유로 자동 적용하지 않습니다. 예를 들어 기존 Solarized Light의 Help 경계는
약 1.397:1이지만 사용자 요청대로 원래 색을 유지합니다.

실제 CodeEditor의 Python 추가 역할 20개·서식, 툴바·탭·버튼 상태별 픽셀, 편집기/콘솔
포커스 전환, 실제 `QMenu`와 실제 Spyder `Switcher`를 격리된 설정으로 확인합니다.
개인 프로젝트나 콘솔을 실행하지 않습니다. 다음은 개별 추가 테마의 재검증 예입니다.

```sh
python .tools/render_port_previews.py --themes vscode-high-contrast sublime-mariana \
  --ui-states --pane-borders --out-dir .artifacts/custom-theme-review-final

cd ../spyder-themeweaver
pixi run cli export --theme vscode-high-contrast sublime-mariana \
  --theme-dir ../spyder-themes_ok97465
pixi run python ../spyder-themes_ok97465/.tools/verify_port_mappings.py \
  --build-dir build --themes vscode-high-contrast sublime-mariana
```

로컬 `native-vscode-review/`·`native-sublime-review/`에는 실제 프로그램 화면이,
`custom-theme-review-final/`에는 실제 Qt 상태별·메뉴·Switcher 화면이 있습니다. 모두
`.artifacts/` 아래에 둡니다. 기준 소스·색상 상속·합성값은 원본 검사 JSON과 YAML 주석에
보존하며, 원래 13개 테마의 소스 불변과 설치 파일 불변도 별도로 확인합니다.
