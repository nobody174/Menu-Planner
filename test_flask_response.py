import subprocess
import time
import requests

print('[STARTING] Flask server...')
import os
cwd = os.getcwd()
print(f'[CWD] Current working directory: {cwd}')
proc = subprocess.Popen(['python', 'pi-deployment/flask_app.py'],
                       cwd=cwd,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       text=True)

time.sleep(6)

try:
    print('[REQUEST] Getting http://localhost:5000/shopping')
    response = requests.get('http://localhost:5000/shopping', timeout=5)
    html = response.text
    print(f'[OK] Got {len(html)} bytes')

    if 'og fisk' in html:
        print('[OK] HTML contains "og fisk" - NEW VERSION IS BEING SERVED!')
    else:
        print('[ERROR] HTML missing "og fisk" - OLD VERSION!')

    if 'Handleliste for denne uken' in html:
        print('[OK] HTML contains "Handleliste for denne uken" - NEW!')
    else:
        print('[ERROR] HTML missing text - OLD!')

    # Show first 1000 chars
    print('\nFirst 1000 chars of HTML response:')
    print(html[:1000])

finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        pass
    print('\n[DONE]')

    # Show Flask log
    import time
    time.sleep(0.5)
    try:
        with open('logs/flask_app.log', 'r', encoding='utf-8') as f:
            log_content = f.read()
            print('\n===== FLASK LOG (last 2000 chars) =====')
            print(log_content[-2000:])
    except Exception as e:
        print(f'Could not read log: {e}')
