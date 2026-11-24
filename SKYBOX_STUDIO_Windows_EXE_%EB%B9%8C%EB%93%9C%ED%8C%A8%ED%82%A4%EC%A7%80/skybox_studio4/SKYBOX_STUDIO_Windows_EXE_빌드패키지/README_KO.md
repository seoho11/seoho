# SKYBOX STUDIO — Rebuilt (A Dashboard)

원본 `Skybox Studio.exe`에 내장된 UI/문구/기능 식별자와 동봉된 `Skyboxes` 안내 파일을 기준으로 새로 작성한 독립 재구현판입니다. 원본 실행 파일은 수정하거나 덮어쓰지 않습니다.

## 포함 기능
- 대시보드형 UI (홈 / 스카이박스 / 설정 / 도움말)
- TEX 6면 파일 또는 ZIP 가져오기 및 6면 검증
- 중복 이름 자동 처리 (`이름2`, `이름3` ...)
- 등록된 세트 목록 / 유효성 검사 / 삭제
- 일반 적용 및 랜덤 적용
- Roblox 버전 폴더 검색
- Roblox `content/sky` 적용 폴더를 사용자가 직접 선택
- SkyboxFix `.bat` 파일을 직접 선택하고 TEX 복사 후 자동 실행
- 경로 설정을 `data/settings.json`에 저장
- 적용 전 Roblox 종료 옵션, 적용 후 Roblox 실행 옵션
- 덮어쓰기 전 원본 TEX 파일 백업
- 이전 랜덤 세트 제외 옵션
- 색상 테마 설정 저장

## 실행
1. Windows 10/11에 Python 3.10 이상 설치 (설치 시 PATH 옵션 활성화)
2. `install.bat` 실행
3. `start.bat` 실행

## EXE 만들기
GitHub Actions의 `Build SKYBOX STUDIO Windows EXE` 워크플로를 실행하면 단일 `SKYBOX STUDIO.exe`가 생성됩니다. 사용자 설정과 백업은 EXE와 같은 위치의 `data` 폴더에 저장됩니다.

## 파일 위치
프로그램 폴더의 `data/Skyboxes`에 세트별 폴더로 저장됩니다. 각 폴더에는 다음 여섯 면의 TEX 파일이 있어야 합니다.
`bk, dn, ft, lf, rt, up`
파일명 예: `sky512_bk.tex`, `sky512_dn.tex`, `sky512_ft.tex`, `sky512_lf.tex`, `sky512_rt.tex`, `sky512_up.tex`.

## 적용 동작 및 주의
- 적용 대상은 설정에서 사용자가 직접 지정한 Roblox `content/sky` 폴더입니다. 경로를 지정하지 않으면 적용을 중단합니다.
- TEX 6개 복사가 끝난 뒤 설정에서 선택한 `SkyboxFix.bat`를 해당 BAT 파일의 폴더를 작업 폴더로 하여 실행합니다. BAT 종료 코드가 0이 아니거나 180초 안에 끝나지 않으면 오류를 표시합니다.
- 적용 전 대상 폴더에 이미 존재하는 동일 파일은 `data/Backups` 아래에 복사합니다.
- `적용 전 Roblox 종료`가 켜져 있으면 Roblox 프로세스를 강제 종료합니다. 저장하지 않은 게임 작업이 있다면 먼저 종료하세요.
- Roblox 업데이트로 내부 파일명/경로가 바뀌면 적용이 실패할 수 있습니다. 이 경우 수동으로 임의 파일을 덮어쓰지 마세요.
- BAT 파일은 사용자가 직접 선택한 파일만 실행합니다. 출처를 신뢰할 수 있는 SkyboxFix BAT인지 확인한 뒤 지정하세요.
- 이 패키지는 Python 소스 프로젝트입니다. 현재 환경에서는 Windows용 EXE 빌드 및 실제 Roblox 적용 테스트를 수행하지 못했습니다.

## 원본과의 관계
원본 ZIP에는 `.csproj`/소스 코드가 없고, Windows 실행 파일과 WebView2 런타임 데이터만 있었습니다. 실행 파일 안의 HTML UI와 문자열, 동봉된 안내 TXT를 분석해 기능을 재구현했습니다. 따라서 원본 내부의 모든 세부 동작과 1:1 동일하다고 보장하지 않습니다.
