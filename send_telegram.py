import urllib.request
import urllib.parse
import json
import sys
import os

def _load_env():
    """Load .env file into os.environ."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())

_load_env()

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
API = f'https://api.telegram.org/bot{TOKEN}'

def send_message(text, parse_mode='HTML'):
    """Send a text message."""
    if not TOKEN or not CHAT_ID:
        raise RuntimeError('TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured in .env')
    data = urllib.parse.urlencode({
        'chat_id': CHAT_ID,
        'parse_mode': parse_mode,
        'text': text
    }).encode()
    req = urllib.request.Request(f'{API}/sendMessage', data=data)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def send_photo(photo_path, caption=''):
    """Send a photo with optional caption."""
    if not TOKEN or not CHAT_ID:
        raise RuntimeError('TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured in .env')
    boundary = '----FormBoundary7MA4YWxkTrZu0gW'

    with open(photo_path, 'rb') as f:
        photo_data = f.read()

    body = []
    body.append(f'--{boundary}'.encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"')
    body.append(b'')
    body.append(CHAT_ID.encode())
    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="photo"; filename="{os.path.basename(photo_path)}"'.encode())
    body.append(b'Content-Type: image/png')
    body.append(b'')
    body.append(photo_data)
    if caption:
        body.append(f'--{boundary}'.encode())
        body.append(b'Content-Disposition: form-data; name="caption"')
        body.append(b'')
        body.append(caption.encode())
        body.append(f'--{boundary}'.encode())
        body.append(b'Content-Disposition: form-data; name="parse_mode"')
        body.append(b'')
        body.append(b'HTML')
    body.append(f'--{boundary}--'.encode())

    body_bytes = b'\r\n'.join(body)

    req = urllib.request.Request(
        f'{API}/sendPhoto',
        data=body_bytes,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        send_message(' '.join(sys.argv[1:]))
    else:
        print('Usage: python send_telegram.py "message"')
