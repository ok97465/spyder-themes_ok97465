# 테마 설치

개인 커스텀 Spyder(`spyder6_ok97465`)용 테마를 빌드해 Anaconda `base`에 설치합니다. ThemeWeaver와 Pixi가 준비된 환경을 기준으로 합니다.

검증·미리보기 스크립트는 `.tools/`에 둡니다. 현재 인접 ThemeWeaver는
`theme.yaml`이 있는 폴더만 테마로 내보내므로 `mplstyle/` 같은 일반 폴더는
자동으로 제외합니다. 이 필터가 없는 이전 ThemeWeaver에서는 일반 폴더 때문에
전체 내보내기가 중단될 수 있으므로 현재 인접 버전을 사용합니다.

인접 ThemeWeaver의 선택적 UI·메뉴·Switcher 색 내보내기를 사용합니다. 현재 커스텀 Spyder의
비활성 dock 탭과 도움말 프레임은 `COLOR_BACKGROUND_4`를 직접 사용하므로,
비활성 탭 배경 역할과 이 색을 함께 맞춥니다. 이번 툴바·탭·버튼 개선에는
Spyder 본체 수정이 필요하지 않습니다. 메뉴·Switcher 역할도 ThemeWeaver에서
QSS와 리소스로 내보내므로 Spyder 본체 수정 없이 적용됩니다. 색상 이식 기준과 화면 검증은
[테마 검증](THEME_AUDIT_KO.md)을 참고하세요.

```bash
cd ~/codepy/spyder-themeweaver
pixi run export-all --theme-dir ../spyder-themes_ok97465
pixi run package
/Users/ok97465/anaconda3/bin/python -m pip install \
  --no-deps --force-reinstall \
  dist/spyder_themes/dist/spyder_themes-*.whl
```

wheel 파일이 여러 개라면 이번에 생성된 파일명을 지정합니다.

설치 후 커스텀 Spyder를 재시작하고 **환경설정 → 모양**에서 테마를 선택합니다. 테마 수정 후에도 같은 명령으로 다시 설치합니다.

갱신할 때 설정 파일을 삭제할 필요는 없습니다. 커스텀 Spyder는 패키지의 기본색을
읽고 직접 수정한 구문 색상만 설정에 저장합니다. 이 동작에는 인접
`spyder6_ok97465`의 모양 설정 저장·현재 셀 강조 갱신 수정도 필요합니다.

이전 버전에서 저장된 기본색이 남아 새 색이 적용되지 않는 경우에만 한 번
**환경설정 → 모양 → 해당 테마 선택 → 색상 초기화 아이콘**
(툴팁: **Reset customized colors to defaults**)을 사용합니다. 선택한 테마의
구문 색상 수정은 초기화되며 다른 설정은 유지됩니다. 이후에는 테마 패키지를
다시 설치하고 Spyder를 재시작하면 됩니다. 직접 수정해 둔 색은 갱신 후에도
우선 적용되므로, 그 색을 패키지 기본값으로 되돌릴 때도 같은 초기화를 사용합니다.
