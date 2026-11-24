# SKYBOX STUDIO — Windows 단일 EXE 빌드

이 프로젝트는 A형 모던 대시보드 UI를 사용하는 SKYBOX STUDIO 재구현판입니다.
이 환경은 Linux이므로 Windows EXE를 직접 생성·실행 검증할 수 없습니다. 대신 GitHub의 Windows 빌드 서버에서 단일 EXE를 생성하도록 설정했습니다.

## EXE 받는 방법
1. GitHub에 새 저장소를 만듭니다.
2. 이 ZIP의 압축을 풀고 파일 전체를 저장소에 업로드합니다. `.github/workflows/build-windows-exe.yml` 경로도 반드시 포함해야 합니다.
3. 저장소의 **Actions** 탭을 엽니다.
4. 왼쪽에서 **Build SKYBOX STUDIO Windows EXE**를 선택합니다.
5. **Run workflow**를 누르고 초록색 완료 표시가 나올 때까지 기다립니다.
6. 완료된 실행 항목 아래 **Artifacts**에서 `SKYBOX-STUDIO-Windows-EXE`를 다운로드합니다.
7. ZIP을 풀면 `SKYBOX STUDIO.exe`가 있습니다.

## 실행 시 참고
- 단일 EXE이며 Python을 별도로 설치할 필요가 없습니다.
- 첫 실행 PC에 Microsoft Edge WebView2 Runtime이 없으면 해당 런타임 설치가 필요할 수 있습니다. 따라서 모든 PC에서 무조건 완전 무설치라고 보장할 수는 없습니다.
- 사용자 스카이박스와 백업/설정은 EXE와 같은 위치의 `data` 폴더에 저장됩니다. EXE를 다른 폴더로 옮길 때 `data` 폴더도 함께 옮기세요.
- Roblox 적용 기능은 Roblox 업데이트에 따라 경로/파일 구조가 바뀌면 동작하지 않을 수 있습니다. 중요한 파일을 먼저 백업하세요.
- 이 프로그램은 원본의 소스코드를 수정한 것이 아니라 확인 가능한 UI/기능을 바탕으로 재구현한 버전입니다.

## 포함 기능
- TEX 6면 파일 또는 ZIP 가져오기 및 6면 검사
- 스카이박스 목록, 삭제
- 일반 적용 및 랜덤 적용
- Roblox 버전 폴더 탐색
- 적용 전 기존 TEX 파일 백업
- Roblox 종료/적용 후 실행 설정
- 색상 테마 설정
