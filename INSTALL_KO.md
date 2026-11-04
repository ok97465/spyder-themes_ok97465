# 테마 설치

개인 커스텀 Spyder(`spyder6_ok97465`)용 테마를 빌드해 Anaconda `base`에 설치합니다. ThemeWeaver와 Pixi가 준비된 환경을 기준으로 합니다.

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
