# 테마 검증

테마를 수정한 뒤 YAML 색상 참조와 내보낸 파일이 일치하는지 확인합니다.
아래 명령은 이 컴퓨터의 ThemeWeaver 환경에서 실행합니다.

```sh
cd ~/codepy/spyder-themeweaver
pixi run cli export --all --theme-dir ../spyder-themes_ok97465
pixi run python ../spyder-themes_ok97465/tools/verify_port_mappings.py \
  --build-dir build
```

검증 오류가 있으면 해당 테마의 YAML을 수정하고 다시 실행합니다.
설치는 [INSTALL_KO.md](INSTALL_KO.md)를 참고합니다.
