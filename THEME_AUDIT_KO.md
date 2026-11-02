# 테마 색상 매핑 검증

대상은 `cfb6b97`에서 추가된 Ayu, GitHub Dark, GitHub Dark Dimmed, Material, One Dark Pro, Sublime Mariana, Tokyo Night, VS Code 2017, VS Code 2026의 14개 변형과, 이번 작업의 Monokai 2개 변형 및 Tokyo Night AltSynt입니다. 총 **11개 테마·17개 변형**을 검사합니다. 나머지 기존 테마는 공통 런타임의 기존 동작 유지 검사 대상입니다.

## 원본 대조 결과

색상표의 고정 revision, 포함된 부모 색상표, 구체적인 Python scope, semantic fallback, 투명도의 실제 합성 배경을 확인했습니다. 출처 URL과 checksum은 각 테마 YAML 주석에 둡니다.

| 테마 | 확인·보완한 주요 항목 |
| --- | --- |
| Ayu | 편집기 선택 영역을 원본 파란색으로 교정. 매크로·타입·클래스·인수·단어 연산자 분리. 상태바·탭·줄번호·트리의 원본 색과 투명도 적용. 현재 VS Code가 제공하는 기본 괄호색 반영. |
| GitHub Dark / Dimmed | 사이드바와 에디터 거터 분리. 탭·상태바·선택 행·글자색 교정. 원본 JS의 중복 선택색 키로 인해 실제 적용되는 VS Code 기본 선택색 `#264F78` 확인. 원본 괄호 6색 모두 보존. |
| Material | 기본/Oceanic과 Lighter의 툴바를 원본 배경으로 교정. 함수·클래스·상속 클래스·독스트링·인수·기울임을 분리. 원본 리소스의 아래쪽 2px 청록색 탭 선 적용. Lighter의 기존 가독성 보정은 명시적으로 유지. |
| One Dark Pro | 함수와 타입, 변수·인수·단어 연산자, 오류색과 선택색 교정. 원본 회색 탭 하단선 1px, 원본 기울임과 괄호 3색 순환 보존. |
| Sublime Mariana | Adaptive 사이드바·탭·상태바와 에디터를 분리. 변수·인수·클래스 참조를 추가 연결. 비활성 선택 행도 원본처럼 흰 글자 유지. |
| Tokyo Night | folke Night/Day의 상태바·TabLineSel 색과 검은 선택 탭 글자 연결. 독스트링·타입·클래스·인수·선언 키워드·괄호색 교정. |
| VS Code 2017 | Dark+/Light+의 실제 상속·Python scope 적용. 2017 당시의 일반 호출·변수 기본색과 단색 괄호 유지. 원본 파란 상태바와 활성·비활성 선택 글자색 적용. |
| VS Code 2026 | 2026 → Modern → Plus → 기본 색상표의 포함 순서와 scope 구체성을 대조. 상속된 내장 함수·타입·숫자·논리 연산자 규칙 복원. 일반 제어 키워드와 `def/class`, 기호 연산자와 단어 연산자 분리. |
| Monokai | 에디터 선택색과 비활성 트리 선택색의 잘못된 공유 교정. 원본 변수·인수·타입 참조 및 중립 괄호 연결. 라이트는 기존 사용자 변형의 공유 색상을 명시적인 새 역할로 확장. |
| Tokyo Night AltSynt | 실제 Avetis 1.0.2 원본과 대조. 변수·클래스·독스트링·일반 호출 기본색, 탭 호버 및 비활성 선택 글자 투명도 확인. |

VS Code 계열은 원본 TextMate 런타임과 Python 문법을 이용해 구체적인 scope의 최종 색을 확인했습니다. GitHub 색상표는 원본이 지정한 `@primer/primitives 7.10.0`으로 재생성해 대조했습니다. Sublime은 build 4215의 색상표·Adaptive 리소스·Python 문법을 확인했습니다. 단색 괄호를 사용하는 원본은 모든 깊이에서 같은 색을 유지하고, 3색 원본은 4–6단계에 같은 순서를 반복합니다.

## 모든 변형에 연결한 옵션

- 구문 역할 20개: 기호 연산자, 단어 연산자, 괄호/구두점, 구분자, 클래스 선언, 함수 호출, 독스트링, 타입, 상속 클래스, 선언 키워드, 언어 상수, 변수, 매개변수 선언, 클래스 참조, 괄호 깊이 1–6.
- UI 역할 15개: 줄번호, 툴바, 상태바 배경·글자, 탭의 일반/선택 글자·선택 배경·강조선·호버, 트리의 일반 글자·호버·활성 선택 배경/글자·비활성 선택 배경/글자.
- 탭 강조선은 원본에 따라 안쪽/바깥쪽 및 두께를 선택합니다. 강조선이 없는 원본은 탭 배경색으로 처리합니다.

원본에 구별이 없는 역할은 같은 색을 명시적으로 연결합니다. 일반 Qt 텍스트와 변수 탐색기 표는 가독성 보정이 필요한 경우 기존 보정을 유지하고, 트리·탭·상태바는 별도 원본 색으로 연결합니다. Sublime의 명시되지 않은 거터 글자색은 기존 Qt 기본 `#808080`을 호환 기본값으로 유지합니다.

## 검증 방법

ThemeWeaver 환경에서 실행합니다.

```sh
pixi run cli export --theme ayu github-dark github-dark-dimmed material \
  one-dark-pro sublime-mariana tokyonight vscode-2017 vscode-2026 \
  monokai tokyo-night-altsynt --theme-dir ../spyder-themes_ok97465

pixi run python ../spyder-themes_ok97465/tools/verify_port_mappings.py \
  --build-dir build --report /tmp/theme-port-coverage.json
```

검증 도구는 실제 Spyder 소비 코드에서 필수 옵션을 읽습니다. 중복 YAML 키, 색상·참조·변형 선언, 모든 새 역할의 누락, 원본 팔레트와 생성된 Python 팔레트의 불일치, CSS/QSS 및 라이선스 파일 누락을 검사합니다. 별도의 Qt 회귀 검사는 원본 내·외측 탭 선, 로컬 독 탭 스타일, 트리 호버·선택 글자색, 단어 연산자·6단계 괄호·테마 전환과 기존 테마 fallback을 검증합니다.

현재 검증 결과는 **17개 변형의 구조·참조·source/export 대조 오류 0개**, **PyQt5·PySide6 각각 회귀 58개 통과**입니다. Qt 검사는 실제 위젯 픽셀로 트리 호버와 로컬 독 탭 호버, 독 탭 및 문서 모드 파일 탭의 안쪽 2px 선도 확인합니다. 생성 wheel의 전체 카탈로그 및 11개 포트의 팔레트·메타데이터·원본 라이선스 일치도 확인합니다. 설치된 전체 17개 변형의 실제 Spyder 위젯 렌더링과 Qt 리소스 로딩도 통과했습니다.

실제 Spyder 위젯 미리보기는 설치된 패키지와 보완된 Spyder 코드로 생성합니다. 개인 설정과 분리된 임시 설정을 사용합니다.

```sh
QT_QPA_PLATFORM=offscreen QT_API=pyqt5 \
  /path/to/spyder/python tools/render_port_previews.py \
  --out-dir /tmp/theme-port-previews
```

## 대비 검사와 표현 범위

구조·참조·export 검증과 대비 권고를 구분합니다. 원본의 흐린 주석, 선택색, 아이콘·줄번호, UI 밝기 순서는 Spyder의 엄격한 대비 규칙을 만족하지 않는 경우가 있습니다. 해당 값은 원본을 보존하며, 이를 검사 통과로 보고하지 않습니다. Qt 전용 그룹 배경 등 보정값은 YAML 주석으로 구별합니다.

아래 수치는 ThemeWeaver의 변형별 71개 대비 규칙 중 **통과 / 미달**입니다. 미달 항목에는 원본 색상 및 Qt 그룹 배경·밝기 순서 제약이 포함됩니다. 새 역할의 구조·참조 검증 결과와는 별도입니다.

| 테마 | 다크 | 라이트 |
| --- | --- | --- |
| Ayu | 53 / 18 | 43 / 28 |
| GitHub Dark | 69 / 2 | — |
| GitHub Dark Dimmed | 65 / 6 | — |
| Material | 52 / 19 | 48 / 23 |
| Monokai | 65 / 6 | 71 / 0 |
| One Dark Pro | 62 / 9 | — |
| Sublime Mariana | 63 / 8 | — |
| Tokyo Night AltSynt | 61 / 10 | — |
| Tokyo Night | 60 / 11 | 51 / 20 |
| VS Code 2017 | 66 / 5 | 71 / 0 |
| VS Code 2026 | 66 / 5 | 68 / 3 |

이 포트는 로컬 Python 구문·문맥을 이용합니다. 외부 라이브러리 타입을 판별하는 Pylance 전체 기능은 포함하지 않습니다. 매개변수 역할은 선언부에 적용하고, 클래스 참조는 선언·상속 문맥으로 확인되는 이름에 적용합니다. 불완전한 구문은 AST 기반 역할이 기본 강조로 돌아가며, 3,000블록 또는 200,000자를 넘는 파일에서는 입력 지연을 막기 위해 문서 문맥 분석을 생략합니다. Qt/Spyder의 위젯 배치와 OS 창 장식은 각 원본 프로그램과 다릅니다.
