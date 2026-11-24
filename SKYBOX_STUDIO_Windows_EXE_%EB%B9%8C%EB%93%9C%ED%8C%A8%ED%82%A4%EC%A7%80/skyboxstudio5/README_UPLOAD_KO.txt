SKYBOX STUDIO 수정 파일 업로드 안내

이 ZIP은 GitHub 저장소 루트에 풀어서 업로드하는 구조입니다.

1) .github/workflows/build-windows-exe.yml 을 저장소 루트의 .github/workflows/ 안에 업로드합니다.
2) SKYBOX_STUDIO_Windows_EXE_빌드패키지 폴더 안의 app.py, ui/index.html, requirements-build.txt, README_KO.md 를 기존 동명 경로에 덮어씁니다.
3) 기존 skybox_windows.exe / skybox_windows_exe 폴더는 삭제하지 않아도 됩니다.
4) GitHub Actions에서 Build SKYBOX STUDIO Windows EXE 실행 후 Artifacts의 SKYBOX-STUDIO-Windows-EXE를 다운로드합니다.

이 워크플로는 반드시 저장소 루트 .github/workflows/에 있어야 GitHub Actions가 인식합니다.
