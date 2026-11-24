from __future__ import annotations
import os, sys, json, re, shutil, zipfile, tempfile, subprocess, time, random
from pathlib import Path
from datetime import datetime

try:
    import webview
except ImportError:
    print('pywebview가 설치되지 않았습니다. install.bat을 먼저 실행하세요.')
    input('Enter를 누르면 종료합니다...')
    raise SystemExit(1)

# In a PyInstaller one-file build, bundled resources live in sys._MEIPASS,
# while user data must remain beside the EXE so it survives app updates.
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR
DATA_DIR = APP_DIR / 'data'
SKY_DIR = DATA_DIR / 'Skyboxes'
BACKUP_DIR = DATA_DIR / 'Backups'
CONFIG_FILE = DATA_DIR / 'settings.json'
for p in (SKY_DIR, BACKUP_DIR): p.mkdir(parents=True, exist_ok=True)

FACE_ALIASES = {'bk':'bk','back':'bk','dn':'dn','bottom':'dn','ft':'ft','front':'ft','lf':'lf','left':'lf','rt':'rt','right':'rt','up':'up','top':'up'}
REQUIRED = ['bk','dn','ft','lf','rt','up']

def face_of(filename: str):
    stem = Path(filename).stem.lower()
    # Prefer face suffixes separated by underscore/hyphen; supports sky512_bk.tex and bk.tex
    m = re.search(r'(?:^|[_\-\.])(bk|back|dn|bottom|ft|front|lf|left|rt|right|up|top)$', stem)
    if not m:
        m = re.search(r'(?:sky\d*[_-]?)(bk|dn|ft|lf|rt|up)$', stem)
    return FACE_ALIASES.get(m.group(1)) if m else None

def safe_name(s: str):
    s = re.sub(r'[\\/:*?"<>|]+', '_', (s or '').strip()).strip(' .')
    return (s[:64] or 'my_skybox')

class Bridge:
    def __init__(self):
        self.settings = self._load_settings()
        self.last_random = ''

    def _load_settings(self):
        defaults = {'autoClose': True, 'autoLaunch': True, 'excludePrevious': True, 'accent':'#5687F5', 'bg':'#111827', 'text':'#E8EEF9'}
        try:
            if CONFIG_FILE.exists(): defaults.update(json.loads(CONFIG_FILE.read_text(encoding='utf-8')))
        except Exception: pass
        return defaults

    def _save(self):
        CONFIG_FILE.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_status(self):
        sets = self.get_skyboxes()
        ver = self._roblox_version()
        return {'skyboxes': sets, 'count': len(sets), 'robloxVersion': ver or '설치 경로를 찾을 수 없음', 'robloxFound': bool(ver), 'skyboxPath': str(SKY_DIR), 'settings': self.settings}

    def get_skyboxes(self):
        result=[]
        for folder in sorted([p for p in SKY_DIR.iterdir() if p.is_dir()], key=lambda p:p.name.lower()):
            files=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower()=='.tex']
            faces={face_of(p.name) for p in files}
            missing=[f for f in REQUIRED if f not in faces]
            result.append({'name':folder.name,'files':[{'name':p.name,'size':p.stat().st_size} for p in files], 'isValid':not missing, 'missing':missing})
        return result

    def _extract_files(self, paths):
        collected=[]
        for raw in paths:
            p=Path(raw)
            if p.suffix.lower()=='.zip':
                with zipfile.ZipFile(p) as z:
                    for info in z.infolist():
                        if info.is_dir() or Path(info.filename).suffix.lower()!='.tex': continue
                        name=Path(info.filename).name
                        collected.append((name,z.read(info)))
            elif p.suffix.lower()=='.tex': collected.append((p.name,p.read_bytes()))
        # dedupe by face, reject ambiguous/incomplete set
        by_face={}
        for name,data in collected:
            face=face_of(name)
            if face and face not in by_face: by_face[face]=(name,data)
        missing=[f for f in REQUIRED if f not in by_face]
        if missing: raise ValueError('6면 TEX 파일을 찾지 못했습니다. 누락: '+', '.join(missing))
        if len(by_face)!=6: raise ValueError('서로 다른 6면 파일이 필요합니다.')
        return [by_face[k] for k in REQUIRED]

    def select_files(self):
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=('TEX and ZIP (*.tex;*.zip)', 'All files (*.*)'))
        return list(result or [])

    def import_skybox(self, name, paths):
        files=self._extract_files(paths)
        base=safe_name(name)
        final=base; n=2
        while (SKY_DIR/final).exists(): final=f'{base}{n}'; n+=1
        dest=SKY_DIR/final; dest.mkdir(parents=True)
        try:
            for fname,data in files: (dest/Path(fname).name).write_bytes(data)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True); raise
        return {'ok':True,'name':final,'message':f'{final} 등록 완료'}

    def delete_skybox(self, name):
        target=SKY_DIR/safe_name(name)
        if not target.exists() or not target.is_dir(): raise ValueError('해당 스카이박스를 찾을 수 없습니다.')
        shutil.rmtree(target)
        return {'ok':True,'message':f'{name} 삭제 완료'}

    def _roblox_roots(self):
        local=os.environ.get('LOCALAPPDATA')
        if not local: return []
        base=Path(local)/'Roblox'/'Versions'
        if not base.exists(): return []
        dirs=[p for p in base.iterdir() if p.is_dir() and (p/'RobloxPlayerBeta.exe').exists()]
        return sorted(dirs, key=lambda p:(p/'RobloxPlayerBeta.exe').stat().st_mtime, reverse=True)

    def _roblox_version(self):
        roots=self._roblox_roots()
        return roots[0].name if roots else None

    def _stop_roblox(self):
        subprocess.run(['taskkill', '/F', '/IM', 'RobloxPlayerBeta.exe'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(['taskkill', '/F', '/IM', 'Windows10Universal.exe'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(1.2)

    def _roblox_running(self):
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq RobloxPlayerBeta.exe', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, encoding='utf-8', errors='replace', check=False
            )
            return 'RobloxPlayerBeta.exe' in (result.stdout or '')
        except Exception:
            return False

    def apply(self, mode, selected_name):
        sets = [s for s in self.get_skyboxes() if s['isValid']]
        if not sets:
            raise ValueError('적용 가능한 스카이박스가 없습니다. 6면 TEX 세트를 먼저 등록하세요.')

        if mode == 'random':
            pool = sets
            if self.settings.get('excludePrevious') and len(sets) > 1:
                pool = [s for s in sets if s['name'] != self.last_random] or sets
            chosen = random.choice(pool)
        else:
            chosen = next((s for s in sets if s['name'] == selected_name), None)
            if not chosen:
                raise ValueError('스카이박스를 선택하세요.')

        # Roblox의 content/sky 폴더에서 사용하는 표준 6면 파일명으로 통일한다.
        face_targets = {
            'bk': 'sky512_bk.tex',
            'dn': 'sky512_dn.tex',
            'ft': 'sky512_ft.tex',
            'lf': 'sky512_lf.tex',
            'rt': 'sky512_rt.tex',
            'up': 'sky512_up.tex',
        }
        source_dir = SKY_DIR / chosen['name']
        source_by_face = {}
        for src in source_dir.iterdir():
            if src.is_file() and src.suffix.lower() == '.tex':
                face = face_of(src.name)
                if face:
                    if face in source_by_face:
                        raise ValueError(f'{face} 면에 해당하는 TEX 파일이 중복되어 있습니다: {src.name}')
                    source_by_face[face] = src

        missing = [face for face in REQUIRED if face not in source_by_face]
        if missing:
            raise ValueError('적용할 TEX 파일이 부족합니다. 누락된 면: ' + ', '.join(missing))

        roots = self._roblox_roots()
        if not roots:
            raise ValueError('Roblox 설치 버전을 찾을 수 없습니다. Roblox를 설치한 뒤 다시 시도하세요.')
        version = roots[0]
        target = version / 'content' / 'sky'
        if not target.is_dir():
            raise ValueError(f'Roblox sky 폴더를 찾을 수 없습니다: {target}')

        if self._roblox_running():
            if self.settings.get('autoClose'):
                self._stop_roblox()
                if self._roblox_running():
                    raise RuntimeError('Roblox를 종료하지 못했습니다. 게임을 완전히 종료한 뒤 다시 적용하세요.')
            else:
                raise RuntimeError('Roblox가 실행 중입니다. 설정에서 "적용 전 Roblox 자동 종료"를 켜거나 게임을 종료하세요.')

        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup = BACKUP_DIR / f'{version.name}_{stamp}'
        backup.mkdir(parents=True, exist_ok=False)
        staged = []
        backed_up = []
        installed = []
        try:
            # 먼저 원본 6개를 백업하고, 모든 새 파일을 임시 파일로 준비한다.
            for face in REQUIRED:
                dest_name = face_targets[face]
                dest = target / dest_name
                if dest.exists():
                    shutil.copy2(dest, backup / dest_name)
                    backed_up.append(dest_name)

                temp = target / (dest_name + '.skybox_tmp')
                if temp.exists():
                    temp.unlink()
                shutil.copy2(source_by_face[face], temp)
                if not temp.is_file() or temp.stat().st_size == 0:
                    raise IOError(f'{dest_name} 임시 파일 검증에 실패했습니다.')
                staged.append((temp, dest, dest_name))

            # 임시 파일이 모두 준비된 뒤에만 실제 파일을 교체한다.
            for temp, dest, dest_name in staged:
                os.replace(str(temp), str(dest))
                installed.append(dest_name)

            # 실제 대상 파일을 다시 확인한다.
            for face in REQUIRED:
                dest_name = face_targets[face]
                dest = target / dest_name
                expected_size = source_by_face[face].stat().st_size
                if not dest.is_file() or dest.stat().st_size != expected_size:
                    raise IOError(f'{dest_name} 적용 후 검증에 실패했습니다.')

        except Exception as e:
            # 부분 적용이 발생하면 기존 파일은 백업본으로 복구하고 새로 생긴 파일은 제거한다.
            rollback_errors = []
            for dest_name in reversed(installed):
                dest = target / dest_name
                saved = backup / dest_name
                try:
                    if saved.exists():
                        shutil.copy2(saved, dest)
                    elif dest.exists():
                        dest.unlink()
                except Exception as rollback_error:
                    rollback_errors.append(f'{dest_name}: {rollback_error}')
            for temp, _, _ in staged:
                try:
                    if temp.exists():
                        temp.unlink()
                except Exception:
                    pass
            detail = f'적용 중 오류가 발생했습니다: {e}\n백업 위치: {backup}'
            if rollback_errors:
                detail += '\n복구 중 추가 오류: ' + '; '.join(rollback_errors)
            raise RuntimeError(detail) from e

        if mode == 'random':
            self.last_random = chosen['name']

        launch_message = ''
        if self.settings.get('autoLaunch'):
            exe = version / 'RobloxPlayerBeta.exe'
            try:
                subprocess.Popen([str(exe)], cwd=str(version))
            except Exception as e:
                launch_message = f' (파일 적용은 완료됐지만 Roblox 자동 실행은 실패: {e})'

        return {
            'ok': True,
            'name': chosen['name'],
            'message': f'{chosen["name"]} 적용 완료 · Roblox 표준 6면 파일 교체 및 검증 완료{launch_message}',
            'backup': str(backup),
            'target': str(target),
            'files': [face_targets[f] for f in REQUIRED],
        }

    def open_folder(self):
        os.startfile(str(SKY_DIR))
        return {'ok':True,'message':'스카이박스 폴더를 열었습니다.'}

    def save_settings(self, data):
        for key in ('autoClose','autoLaunch','excludePrevious','accent','bg','text'):
            if key in data: self.settings[key]=data[key]
        self._save(); return {'ok':True,'settings':self.settings}

    def reset_settings(self):
        self.settings={'autoClose':True,'autoLaunch':True,'excludePrevious':True,'accent':'#5687F5','bg':'#111827','text':'#E8EEF9'}
        self._save(); return self.settings

    def close(self):
        try: webview.windows[0].destroy()
        except Exception: pass

if __name__=='__main__':
    try:
        bridge=Bridge()
        ui_file = RESOURCE_DIR/'ui'/'index.html'
        if not ui_file.exists():
            raise FileNotFoundError(f'UI 파일을 찾을 수 없습니다: {ui_file}')
        webview.create_window('SKYBOX STUDIO', ui_file.resolve().as_uri(), js_api=bridge, width=1180, height=780, min_size=(900,620), background_color='#0B1020')
        webview.start(debug=False)
    except Exception:
        import traceback
        log = APP_DIR/'startup_error.log'
        log.write_text(traceback.format_exc(), encoding='utf-8')
        print('프로그램 시작 중 오류가 발생했습니다.')
        print(f'오류 기록: {log}')
        traceback.print_exc()
        input('Enter를 누르면 종료합니다...')
