"""Real frozen CLI/resource/HTTP gate. Stdlib only; no Vite, model claims or mocks.

Windows taskkill is test cleanup, NOT application-native crash containment.
The supplied home must be cargo's copied resource directory (or the installed one).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--python-module', action='store_true', help='Diagnostic source CLI, NOT a frozen-binary pass')
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = {'checks': [], 'platform': sys.platform, 'executable': str(args.executable), 'execution_mode': 'source-cli' if args.python_module else 'frozen',
              'limitations': ['No Windows WebView GUI assertion; CLI/resource HTTP gate only.',
                              'No bundled model/encode/export/offline installer certification.',
                              'taskkill test cleanup does not prove native crash containment.']}
    def check(name, condition):
        result['checks'].append({'name': name, 'passed': bool(condition)})
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)
        if not condition:
            raise AssertionError(name)
    def stop(process):
        if process.poll() is None:
            if sys.platform == 'win32':
                cleanup = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                         capture_output=True, text=True, timeout=20)
                print('cleanup:', cleanup.returncode, cleanup.stdout, cleanup.stderr, flush=True)
                if cleanup.returncode != 0 and process.poll() is None:
                    raise RuntimeError('Failed to clean up smoke process tree')
            else:
                process.send_signal(signal.SIGTERM)
            process.wait(timeout=20)
    def start(home, data, receipt, instance, port):
        env = os.environ.copy()
        env.update(CUTTING_EDGE_HOME=str(home), CUTTING_EDGE_DATA_DIR=str(data),
                   CUTTING_EDGE_DESKTOP_INSTANCE_ID=instance, CUTTING_EDGE_DESKTOP_READY_FILE=str(receipt))
        command = [str(args.executable.absolute())]
        if args.python_module:
            command += ['-m', 'app']
            env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2]/'backend')
        with (args.output/f'{instance}.log').open('wb') as log:
            return subprocess.Popen(command + ['--serve-frontend', '--host', '127.0.0.1',
                                     '--port', str(port)], env=env, cwd=home.parent,
                                    stdout=log, stderr=subprocess.STDOUT)
    # Disable proxies even if the CI machine has proxy environment variables.
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(base, route, headers=None):
        req = urllib.request.Request(base+route, headers=headers or {})
        try:
            with http.open(req, timeout=5) as response:
                return response.status, {k.lower():v for k,v in response.headers.items()}, response.read()
        except urllib.error.HTTPError as error:
            return error.code, {k.lower():v for k,v in error.headers.items()}, error.read()
    try:
        with tempfile.TemporaryDirectory(prefix='ce-desktop-') as temp:
            root = Path(temp)
            home = root/'نصب با فاصله'  # frozen/runtime paths must survive Unicode and spaces
            home.mkdir()
            for name in ['frontend', 'models', 'binaries']:
                if (args.home/name).exists():
                    shutil.copytree(args.home/name, home/name)
            shutil.copyfile(args.home/'bundle-status.json', home/'bundle-status.json')
            # Copy only the exact mapped resources, NOT an executable/dependency cache.
            check('mapped frontend exists', (home/'frontend'/'index.html').is_file())
            check('resource staging manifest exists', (home/'bundle-status.json').is_file())
            (home/'not-public.txt').write_text('private install resource', encoding='utf-8')
            data = root/'داده محلی'
            receipt = root/'startup'/'123-456.json'
            with socket.socket() as reserve:
                reserve.bind(('127.0.0.1', 0))
                port = reserve.getsockname()[1]
            base = f'http://127.0.0.1:{port}'
            for index in range(2):
                instance = f'123-{456+index}'
                receipt = root/'startup'/f'{instance}.json'
                process = start(home, data, receipt, instance, port)
                try:
                    deadline = time.monotonic()+60
                    while not receipt.exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(.1)
                    check(f'launch {index}: live process with receipt', receipt.exists() and process.poll() is None)
                    proof = json.loads(receipt.read_text(encoding='utf-8'))
                    check(f'launch {index}: matching identity/resource proof', proof == {
                        'version':1, 'instance_id':instance, 'origin':base, 'home':str(home), 'frontend_ready':True})
                    # Receipt is published at the end of lifespan, before uvicorn
                    # announces its inherited listener; retry real HTTP within deadline.
                    while True:
                        try:
                            status, headers, body = request(base, '/')
                            break
                        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                            print('awaiting inherited listener:', error, flush=True)
                            if time.monotonic() >= deadline:
                                raise
                            time.sleep(.1)
                    check(f'launch {index}: built React without Vite', status == 200 and b'type="module"' in body)
                    check(f'launch {index}: same-origin CSP', "connect-src 'self'" in headers.get('content-security-policy',''))
                    status, _, body = request(base, '/api/v1/health')
                    check(f'launch {index}: real healthy API', status == 200 and json.loads(body)['offline'] is True)
                    check(f'launch {index}: resource home preserved', json.loads(body)['models_dir'] == str(home/'models'))
                    status, _, body = request(base, '/api/v1/system/diagnostics')
                    check(f'launch {index}: actual local database/profile', status == 200 and json.loads(body)['paths'] == {
                        'data_dir':str(data), 'home_dir':str(home)})
                    check(f'launch {index}: foreign origin rejected', request(base, '/api/v1/health', {'Origin':'https://untrusted.example'})[0] == 403)
                    check(f'launch {index}: foreign Host rejected', request(base, '/api/v1/health', {'Host':'untrusted.example'})[0] == 403)
                    check(f'launch {index}: install files not exposed', request(base, '/not-public.txt')[0] == 404)
                    check(f'launch {index}: API misses not React HTML', request(base, '/api/v1/nonexistent')[0] == 404)
                finally:
                    stop(process)
            with socket.socket() as decoy:
                decoy.bind(('127.0.0.1', 0))
                decoy.listen()
                occupied = decoy.getsockname()[1]
                receipt = root/'conflict.json'
                process = start(home, data, receipt, '999-111', occupied)
                try:
                    code = process.wait(timeout=40)
                    check('occupied port fails closed', code != 0 and not receipt.exists())
                finally:
                    stop(process)
            shutil.rmtree(home/'frontend')
            receipt = root/'missing.json'
            process = start(home, data, receipt, '999-222', port)
            try:
                code = process.wait(timeout=40)
                check('missing frontend fails closed', code != 0 and not receipt.exists())
            finally:
                stop(process)
            logs = data/'logs'/'backend.jsonl'
            check('startup errors written to local log', logs.is_file() and 'desktop.frontend.missing' in logs.read_text(encoding='utf-8') and 'desktop.listener.failed' in logs.read_text(encoding='utf-8'))
            shutil.copyfile(logs, args.output/'backend.jsonl')
    finally:
        (args.output/'smoke.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
