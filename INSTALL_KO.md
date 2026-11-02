# Spyder 테마를 Anaconda base에 설치하기

이 문서는 이 컴퓨터의 테마 소스를 ThemeWeaver로 빌드한 뒤, 생성된 `spyder_themes` 패키지를 Anaconda `base` 환경에 설치하는 방법을 설명합니다.

현재 저장소에는 테마 YAML 파일만 있고 Pixi 빌드 설정은 없습니다. 따라서 빌드 명령은 별도의 ThemeWeaver 저장소에서 실행하고, `--theme-dir`로 이 저장소를 지정합니다.

## 사용 경로

| 용도 | 경로 |
| --- | --- |
| 테마 소스 저장소 | `/Users/ok97465/codepy/spyder-themes_ok97465` |
| ThemeWeaver 빌드 저장소 | `/Users/ok97465/codepy/spyder-themeweaver` |
| Anaconda base의 Python | `/Users/ok97465/anaconda3/bin/python` |

이 컴퓨터에는 Git, Pixi, Anaconda가 설치되어 있다는 전제로 진행합니다. 각 단계가 오류 없이 끝난 뒤 다음 단계로 진행하세요.

## 1. ThemeWeaver 준비하기 — 처음 한 번

```bash
git clone https://github.com/spyder-ide/spyder-themeweaver.git ~/codepy/spyder-themeweaver
cd ~/codepy/spyder-themeweaver
pixi install
```

이미 해당 경로에 ThemeWeaver를 받아 두었다면 `git clone`은 생략합니다.

## 2. 현재 테마 내보내기 및 패키징

```bash
cd ~/codepy/spyder-themeweaver
pixi run export-all --theme-dir ../spyder-themes_ok97465
pixi run package
```

- `export-all`: 이 테마 저장소의 전체 테마를 읽어 ThemeWeaver의 `build/`에 내보냅니다.
- `package`: `build/`의 테마로 설치 가능한 wheel과 소스 배포 파일을 만듭니다. 테마 내보내기는 수행하지 않으므로 반드시 `export-all`을 먼저 실행합니다.

기본 wheel 생성 위치는 다음과 같습니다. 경로는 ThemeWeaver 저장소 기준입니다.

```text
dist/spyder_themes/dist/spyder_themes-*.whl
```

## 3. Anaconda base에 설치하기

ThemeWeaver 저장소에서 실행합니다.

```bash
/Users/ok97465/anaconda3/bin/python -m pip install \
  --no-deps --force-reinstall \
  dist/spyder_themes/dist/spyder_themes-*.whl
```

- base의 Python 경로를 직접 지정하므로 `conda activate base`는 필요 없습니다.
- `--force-reinstall`: 기존 패키지와 버전이 같아도 새로 빌드한 테마로 다시 설치합니다.
- `--no-deps`: 다른 의존성 패키지는 변경하지 않고 테마 패키지만 설치합니다.

위 명령은 base에 설치된 기존 `spyder_themes` 패키지를 교체합니다. wheel 파일이 여러 버전 남아 있다면 `*.whl` 대신 이번에 생성된 파일명을 정확히 지정하세요.

## 4. 설치 확인 및 Spyder 재시작

```bash
/Users/ok97465/anaconda3/bin/python -m pip show spyder-themes
```

출력의 `Location`이 `/Users/ok97465/anaconda3/lib/python.../site-packages` 아래인지 확인합니다.

설치가 끝나면 실행 중인 Spyder를 완전히 종료하고 다시 실행한 뒤, 환경설정의 모양/테마 항목에서 설치한 테마를 선택합니다.

`Sublime Mariana / dark`와 `Monokai / dark`는 Sublime Text의 Adaptive 조합을 기준으로 합니다. 괄호와 연산자, 함수와 클래스, 독스트링의 세부 색상 및 상태바·탭·트리의 독립 색상은 `/Users/ok97465/codepy/spyder6_ok97465`의 보완된 Spyder 코드가 함께 필요합니다. 해당 저장소의 `spyder.sh`로 실행하면 이 코드가 사용됩니다. 일반 Spyder에서도 테마는 로드되지만 일부 구문·UI 색상은 공통 항목으로 표시됩니다. Monokai의 라이트 버전은 기존 Spyder용 사용자 변형입니다.

`Tokyo Night AltSynt / dark`는 Avetis의 VS Code 테마를 별도로 옮긴 것입니다. 변수·매개변수·클래스 참조와 중첩 괄호 색상도 위 Spyder 포크에서 지원합니다. 기존 `Tokyo Night`는 folke의 Night/Day 테마입니다.

## 테마 수정 후 다시 설치하기

이 저장소의 YAML 파일을 수정한 뒤 아래 명령을 순서대로 실행하면 됩니다.

```bash
cd ~/codepy/spyder-themeweaver
pixi run export-all --theme-dir ../spyder-themes_ok97465
pixi run package
/Users/ok97465/anaconda3/bin/python -m pip install \
  --no-deps --force-reinstall \
  dist/spyder_themes/dist/spyder_themes-*.whl
```

재설치 후에도 Spyder를 완전히 종료하고 다시 실행합니다.

## 참고

- [ThemeWeaver 공식 빌드 안내](https://github.com/spyder-ide/spyder-themeweaver#quick-start)
- [Spyder Python 패키지 생성 안내](https://github.com/spyder-ide/spyder-themeweaver#spyder-python-package-python-package)
