from __future__ import annotations
import os, sys, json, re, shutil, zipfile, subprocess, time, random
import urllib.request, urllib.error, uuid, ctypes
from pathlib import Path
from datetime import datetime

try:
    import webview
except ImportError:
    print('pywebview가 설치되지 않았습니다. 빌드된 EXE를 사용하거나 pywebview를 설치하세요.')
    input('Enter를 누르면 종료합니다...')
    raise SystemExit(1)

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR))
DATA_DIR = APP_DIR / 'data'
SKY_DIR = DATA_DIR / 'Skyboxes'
BACKUP_DIR = DATA_DIR / 'Backups'
CONFIG_FILE = DATA_DIR / 'settings.json'
for p in (SKY_DIR, BACKUP_DIR):
    p.mkdir(parents=True, exist_ok=True)

# 공개 GitHub 저장소의 licenses.json을 매 실행마다 확인합니다.
LICENSE_URL = 'https://raw.githubusercontent.com/seoho11/SKYBOX-STUDIO-LICENSE/main/licenses.json'
LICENSE_TIMEOUT_SECONDS = 10


def _license_message(text: str, title: str = 'SKYBOX STUDIO - 인증') -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:
        print(text)
        try:
            input('Enter를 누르면 종료합니다...')
        except Exception:
            pass


def _device_id_file() -> Path:
    base = os.environ.get('LOCALAPPDATA')
    if base:
        root = Path(base) / 'SKYBOX_STUDIO'
    else:
        root = Path.home() / '.skybox_studio'
    root.mkdir(parents=True, exist_ok=True)
    return root / 'device_id.txt'


def get_or_create_device_id() -> str:
    path = _device_id_file()
    try:
        value = path.read_text(encoding='utf-8').strip()
        if re.fullmatch(r'[0-9a-fA-F-]{36}', value):
            return value.lower()
    except Exception:
        pass
    value = str(uuid.uuid4())
    path.write_text(value, encoding='utf-8')
    return value


def check_license_at_startup() -> tuple[bool, str, str]:
    device_id = get_or_create_device_id()
    # CDN 캐시로 이전 ON/OFF 값이 오래 보이지 않도록 요청별 쿼리 문자열을 붙입니다.
    url = f'{LICENSE_URL}?v={time.time_ns()}'
    request = urllib.request.Request(url, headers={'User-Agent': 'SKYBOX-STUDIO-License-Check/1.0', 'Cache-Control': 'no-cache'})
    try:
        with urllib.request.urlopen(request, timeout=LICENSE_TIMEOUT_SECONDS) as response:
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            return False, device_id, '인증 목록 파일 크기가 너무 큽니다. 관리자에게 문의하세요.'
        data = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(data, dict) or not isinstance(data.get('users', {}), dict):
            raise ValueError('licenses.json 형식이 올바르지 않습니다.')
        admins = data.get('admins', [])
        if not isinstance(admins, list):
            raise ValueError('admins 항목은 배열이어야 합니다.')
        # 관리자 ID는 users의 OFF 설정과 관계없이 허용합니다.
        if device_id in admins:
            return True, device_id, '관리자 PC 인증 완료'
        users = data.get('users', {})
        status = users.get(device_id, False)
        allowed = status is True or (isinstance(status, dict) and status.get('enabled') is True)
        if allowed:
            return True, device_id, '사용 승인 완료'
        return False, device_id, '이 PC는 아직 승인되지 않았거나 사용 권한이 중지되었습니다.'
    except urllib.error.HTTPError as exc:
        return False, device_id, f'인증 목록을 불러오지 못했습니다. (HTTP {exc.code})\n인터넷 연결과 GitHub 저장소를 확인하세요.'
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, device_id, 'GitHub 인증 서버에 연결할 수 없습니다.\n인터넷 연결을 확인한 뒤 다시 실행하세요.'
    except Exception as exc:
        return False, device_id, f'인증 목록을 확인하는 중 오류가 발생했습니다.\n{exc}'


FACE_ALIASES = {'bk':'bk','back':'bk','dn':'dn','bottom':'dn','ft':'ft','front':'ft','lf':'lf','left':'lf','rt':'rt','right':'rt','up':'up','top':'up'}
REQUIRED = ['bk','dn','ft','lf','rt','up']


def face_of(filename: str):
    stem = Path(filename).stem.lower()
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
        defaults = {'autoClose': True, 'autoLaunch': True, 'excludePrevious': True,
                    'accent':'#5687F5', 'bg':'#111827', 'text':'#E8EEF9',
                    'robloxSkyPath':'', 'skyboxFixBat':''}
        try:
            if CONFIG_FILE.exists():
                defaults.update(json.loads(CONFIG_FILE.read_text(encoding='utf-8')))
        except Exception:
            pass
        return defaults

    def _save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_status(self):
        sets = self.get_skyboxes()
        ver = self._roblox_version()
        return {'skyboxes': sets, 'count': len(sets), 'robloxVersion': ver or '설치 경로를 찾을 수 없음',
                'robloxFound': bool(ver), 'skyboxPath': str(SKY_DIR), 'settings': self.settings}

    def get_skyboxes(self):
        result = []
        for folder in sorted([p for p in SKY_DIR.iterdir() if p.is_dir()], key=lambda p:p.name.lower()):
            files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower()=='.tex']
            faces = {face_of(p.name) for p in files}
            missing = [f for f in REQUIRED if f not in faces]
            result.append({'name':folder.name,'files':[{'name':p.name,'size':p.stat().st_size} for p in files], 'isValid':not missing, 'missing':missing})
        return result

    def _extract_files(self, paths):
        collected = []
        for raw in paths:
            p = Path(raw)
            if p.suffix.lower()=='.zip':
                with zipfile.ZipFile(p) as z:
                    for info in z.infolist():
                        if info.is_dir() or Path(info.filename).suffix.lower()!='.tex':
                            continue
                        collected.append((Path(info.filename).name,z.read(info)))
            elif p.suffix.lower()=='.tex':
                collected.append((p.name,p.read_bytes()))
        by_face = {}
        for name,data in collected:
            face = face_of(name)
            if face and face not in by_face:
                by_face[face] = (name,data)
        missing = [f for f in REQUIRED if f not in by_face]
        if missing:
            raise ValueError('6면 TEX 파일을 찾지 못했습니다. 누락: '+', '.join(missing))
        return [by_face[k] for k in REQUIRED]

    def select_files(self):
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True,
            file_types=('TEX and ZIP (*.tex;*.zip)', 'All files (*.*)'))
        return list(result or [])

    def select_sky_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return str(result[0]) if result else ''

    def select_fix_bat(self):
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False,
            file_types=('Batch files (*.bat)', 'All files (*.*)'))
        return str(result[0]) if result else ''

    def import_skybox(self, name, paths):
        files = self._extract_files(paths)
        base = safe_name(name); final = base; n = 2
        while (SKY_DIR/final).exists():
            final = f'{base}{n}'; n += 1
        dest = SKY_DIR/final; dest.mkdir(parents=True)
        try:
            for fname,data in files:
                (dest/Path(fname).name).write_bytes(data)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True); raise
        return {'ok':True,'name':final,'message':f'{final} 등록 완료'}

    def delete_skybox(self, name):
        target = SKY_DIR/safe_name(name)
        if not target.exists() or not target.is_dir():
            raise ValueError('해당 스카이박스를 찾을 수 없습니다.')
        shutil.rmtree(target)
        return {'ok':True,'message':f'{name} 삭제 완료'}

    def _roblox_roots(self):
        local = os.environ.get('LOCALAPPDATA')
        if not local:
            return []
        base = Path(local)/'Roblox'/'Versions'
        if not base.exists():
            return []
        dirs = [p for p in base.iterdir() if p.is_dir() and (p/'RobloxPlayerBeta.exe').exists()]
        return sorted(dirs, key=lambda p:(p/'RobloxPlayerBeta.exe').stat().st_mtime, reverse=True)

    def _roblox_version(self):
        roots = self._roblox_roots()
        return roots[0].name if roots else None

    def _stop_roblox(self):
        subprocess.run(['taskkill','/F','/IM','RobloxPlayerBeta.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(['taskkill','/F','/IM','Windows10Universal.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(1.0)

    def apply(self, mode, selected_name):
        sets = [s for s in self.get_skyboxes() if s['isValid']]
        if not sets:
            raise ValueError('적용 가능한 스카이박스가 없습니다. 6면 TEX 세트를 먼저 등록하세요.')
        if mode=='random':
            pool = sets
            if self.settings.get('excludePrevious') and len(sets)>1:
                pool = [s for s in sets if s['name']!=self.last_random] or sets
            chosen = random.choice(pool); self.last_random = chosen['name']
        else:
            chosen = next((s for s in sets if s['name']==selected_name), None)
            if not chosen:
                raise ValueError('스카이박스를 선택하세요.')

        raw_target = (self.settings.get('robloxSkyPath') or '').strip()
        raw_bat = (self.settings.get('skyboxFixBat') or '').strip()
        if not raw_target:
            raise ValueError('설정에서 Roblox content\\sky 폴더 경로를 먼저 지정하세요.')
        if not raw_bat:
            raise ValueError('설정에서 SkyboxFix BAT 파일 경로를 먼저 지정하세요.')
        target = Path(raw_target).expanduser()
        bat = Path(raw_bat).expanduser()
        if not target.exists() or not target.is_dir():
            raise ValueError(f'지정한 Roblox sky 폴더를 찾을 수 없습니다: {target}')
        if not bat.exists() or not bat.is_file() or bat.suffix.lower()!='.bat':
            raise ValueError(f'지정한 SkyboxFix BAT 파일을 찾을 수 없습니다: {bat}')

        roots = self._roblox_roots()
        if self.settings.get('autoClose'):
            self._stop_roblox()
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = BACKUP_DIR/f'{safe_name(target.parent.parent.name)}_{stamp}'
        backup.mkdir(parents=True, exist_ok=True)
        source = SKY_DIR/chosen['name']; copied = []
        try:
            for src in source.iterdir():
                if src.is_file() and src.suffix.lower()=='.tex':
                    face = face_of(src.name)
                    if not face:
                        continue
                    dest = target/f'sky512_{face}.tex'
                    if dest.exists():
                        shutil.copy2(dest, backup/dest.name)
                    shutil.copy2(src,dest); copied.append(dest.name)
            if len(copied)!=6:
                raise RuntimeError(f'복사된 TEX 파일이 6개가 아닙니다: {len(copied)}개')
        except Exception as e:
            raise RuntimeError(f'TEX 파일 적용 중 오류: {e}\n백업 위치: {backup}')

        try:
            result = subprocess.run(['cmd.exe','/d','/c','call',str(bat)], cwd=str(bat.parent),
                                  capture_output=True, text=True, timeout=180, check=False)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or '').strip()[-1200:]
                raise RuntimeError(f'BAT 종료 코드 {result.returncode}. {detail}')
        except subprocess.TimeoutExpired:
            raise RuntimeError('SkyboxFix BAT 실행 시간이 180초를 초과해 중단했습니다. TEX 파일은 복사되었으며 원본 백업은 보관되어 있습니다.')
        except Exception as e:
            raise RuntimeError(f'TEX 파일은 복사했지만 SkyboxFix 실행에 실패했습니다: {e}\n백업 위치: {backup}')

        if self.settings.get('autoLaunch'):
            version = roots[0] if roots else target.parent.parent
            exe = version/'RobloxPlayerBeta.exe'
            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(version))
        return {'ok':True,'name':chosen['name'],
                'message':f'{chosen["name"]} 적용 완료 · TEX 6개 복사 및 SkyboxFix 실행 완료',
                'backup':str(backup),'target':str(target),'bat':str(bat)}

    def open_folder(self):
        os.startfile(str(SKY_DIR))
        return {'ok':True,'message':'스카이박스 폴더를 열었습니다.'}

    def save_settings(self, data):
        keys = ('autoClose','autoLaunch','excludePrevious','accent','bg','text','robloxSkyPath','skyboxFixBat')
        for key in keys:
            if key in data:
                self.settings[key] = data[key]
        self._save(); return {'ok':True,'settings':self.settings}

    def reset_settings(self):
        self.settings = {'autoClose':True,'autoLaunch':True,'excludePrevious':True,
                       'accent':'#5687F5','bg':'#111827','text':'#E8EEF9',
                       'robloxSkyPath':'','skyboxFixBat':''}
        self._save(); return self.settings

    def close(self):
        try:
            webview.windows[0].destroy()
        except Exception:
            pass


if __name__ == '__main__':
    allowed, current_device_id, license_reason = check_license_at_startup()
    if not allowed:
        _license_message(
            f'{license_reason}\n\n이 PC의 등록 ID:\n{current_device_id}\n\n위 ID를 관리자에게 전달해 승인을 요청하세요.',
            'SKYBOX STUDIO - 사용 승인 필요'
        )
        raise SystemExit(0)

    bridge = Bridge()
    webview.create_window('SKYBOX STUDIO', str(RESOURCE_DIR/'ui'/'index.html'), js_api=bridge,
                          width=1180, height=780, min_size=(900,620), background_color='#0B1020')
    webview.start(debug=False)
