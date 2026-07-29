from flask import Flask, request, jsonify, redirect, render_template_string
import sqlite3
import string
import random
from urllib.parse import urlparse
from datetime import datetime
import requests

try:
    import config
except ModuleNotFoundError:
    raise SystemExit("Не найден config.py. Скопируйте config.example.py в config.py и укажите свои значения.")

app = Flask(__name__)

DATABASE = config.DATABASE
ADMIN_PATH = "/" + config.ADMIN_PATH.strip("/")
RESERVED_CODES = {"api", "favicon.ico", ADMIN_PATH.strip("/")}


def get_device_type(user_agent):
    ua = user_agent.lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'Mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        return 'Tablet'
    return 'Desktop'


def get_browser(user_agent):
    ua = user_agent.lower()
    if 'edg' in ua:
        return 'Edge'
    elif 'chrome' in ua:
        return 'Chrome'
    elif 'firefox' in ua:
        return 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        return 'Safari'
    elif 'opera' in ua or 'opr' in ua:
        return 'Opera'
    return 'Other'


def get_os(user_agent):
    ua = user_agent.lower()
    if 'windows' in ua:
        return 'Windows'
    elif 'mac' in ua:
        return 'macOS'
    elif 'linux' in ua:
        return 'Linux'
    elif 'android' in ua:
        return 'Android'
    elif 'iphone' in ua or 'ipad' in ua:
        return 'iOS'
    return 'Other'


def get_geo_info(ip):
    try:
        response = requests.get(config.GEO_API_URL.format(ip=ip), timeout=2)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'country': data.get('country', 'Unknown'),
                'city': data.get('city', 'Unknown')
            }
    except Exception:
        pass
    return {'country': 'Unknown', 'city': 'Unknown'}


def build_short_url(short_code):
    base = config.BASE_URL.rstrip('/') if config.BASE_URL else f"{request.scheme}://{request.host}"
    return f"{base}/{short_code}"


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clicks_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            referer TEXT,
            country TEXT,
            city TEXT,
            device_type TEXT,
            browser TEXT,
            os TEXT,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (short_code) REFERENCES urls (short_code)
        )
    ''')
    conn.commit()
    conn.close()


def generate_short_code(length=None):
    length = length or config.SHORT_CODE_LENGTH
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM urls WHERE short_code = ?', (code,))
        exists = cursor.fetchone()
        conn.close()
        if not exists:
            return code


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Shortener - {{ domain }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }

        body::before {
            content: '';
            position: fixed;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(0,245,255,0.1) 0%, transparent 50%);
            animation: rotate 20s linear infinite;
            pointer-events: none;
        }

        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .container {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 50px;
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            max-width: 550px;
            width: 100%;
            position: relative;
            z-index: 1;
        }

        h1 {
            font-size: 42px;
            font-weight: 700;
            background: linear-gradient(135deg, #00f5ff 0%, #ff00ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            text-align: center;
            text-shadow: 0 0 30px rgba(0,245,255,0.3);
        }

        .subtitle {
            text-align: center;
            color: rgba(255,255,255,0.5);
            font-size: 14px;
            margin-bottom: 40px;
            letter-spacing: 1px;
        }

        .form-group {
            margin-bottom: 24px;
        }

        label {
            display: block;
            margin-bottom: 10px;
            color: rgba(255,255,255,0.7);
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        input[type="text"] {
            width: 100%;
            padding: 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            font-size: 16px;
            color: #fff;
            transition: all 0.3s ease;
        }

        input[type="text"]::placeholder {
            color: rgba(255,255,255,0.3);
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #00f5ff;
            background: rgba(0,245,255,0.05);
            box-shadow: 0 0 20px rgba(0,245,255,0.2);
        }

        button {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #00f5ff 0%, #ff00ff 100%);
            color: #0f0f23;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 32px rgba(0,245,255,0.3);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 40px rgba(0,245,255,0.5);
        }

        button:active {
            transform: translateY(-1px);
        }

        .result {
            margin-top: 30px;
            padding: 24px;
            background: rgba(0,245,255,0.05);
            border-radius: 16px;
            border: 1px solid rgba(0,245,255,0.2);
            display: none;
            animation: fadeIn 0.4s ease;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .result.show {
            display: block;
        }

        .result-label {
            margin-bottom: 12px;
            font-weight: 600;
            color: #00f5ff;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .result-url {
            display: flex;
            gap: 12px;
        }

        .result-url input {
            flex: 1;
            padding: 14px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #00f5ff;
            font-weight: 600;
            font-size: 15px;
        }

        .copy-btn {
            padding: 14px 24px;
            background: linear-gradient(135deg, #00ff88 0%, #00f5ff 100%);
            color: #0f0f23;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            white-space: nowrap;
            font-weight: 700;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,255,136,0.3);
        }

        .copy-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,255,136,0.5);
        }

        .error {
            margin-top: 20px;
            padding: 16px;
            background: rgba(255,65,108,0.1);
            border: 1px solid rgba(255,65,108,0.3);
            border-radius: 12px;
            color: #ff416c;
            display: none;
            animation: shake 0.4s ease;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }

        .error.show {
            display: block;
        }

        .admin-link {
            margin-top: 30px;
            text-align: center;
        }

        .admin-link a {
            color: rgba(255,255,255,0.4);
            text-decoration: none;
            font-size: 13px;
            transition: all 0.3s ease;
        }

        .admin-link a:hover {
            color: #00f5ff;
            text-shadow: 0 0 10px rgba(0,245,255,0.5);
        }

        @media (max-width: 600px) {
            .container {
                padding: 30px 20px;
            }

            h1 {
                font-size: 32px;
            }

            .result-url {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>URL Shortener</h1>
        <p class="subtitle">{{ domain }}</p>

        <form id="shortenForm">
            <div class="form-group">
                <label for="url">Длинная ссылка</label>
                <input type="text" id="url" placeholder="https://example.com/very/long/url" required>
            </div>
            <div class="form-group">
                <label for="custom">Свой код (необязательно)</label>
                <input type="text" id="custom" placeholder="my-link">
            </div>
            <button type="submit">Сократить ссылку</button>
        </form>

        <div class="error" id="error"></div>

        <div class="result" id="result">
            <p class="result-label">Короткая ссылка создана</p>
            <div class="result-url">
                <input type="text" id="shortUrl" readonly>
                <button class="copy-btn" onclick="copyUrl()">Копировать</button>
            </div>
        </div>

        <div class="admin-link">
            <a href="{{ admin_path }}">Админ-панель</a>
        </div>
    </div>

    <script>
        document.getElementById('shortenForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const url = document.getElementById('url').value;
            const custom = document.getElementById('custom').value;
            const errorDiv = document.getElementById('error');
            const resultDiv = document.getElementById('result');

            errorDiv.classList.remove('show');
            resultDiv.classList.remove('show');

            try {
                const response = await fetch('/api/shorten', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: url,
                        custom_code: custom || undefined
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    document.getElementById('shortUrl').value = data.short_url;
                    resultDiv.classList.add('show');
                    document.getElementById('url').value = '';
                    document.getElementById('custom').value = '';
                } else {
                    errorDiv.textContent = data.error || 'Произошла ошибка';
                    errorDiv.classList.add('show');
                }
            } catch (error) {
                errorDiv.textContent = 'Ошибка соединения с сервером';
                errorDiv.classList.add('show');
            }
        });

        function copyUrl() {
            const input = document.getElementById('shortUrl');
            input.select();
            document.execCommand('copy');

            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = 'Скопировано';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, domain=config.DOMAIN, admin_path=ADMIN_PATH)


@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'error': 'URL обязателен'}), 400

    original_url = data['url']
    custom_code = data.get('custom_code')

    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url

    try:
        parsed = urlparse(original_url)
        if not parsed.netloc:
            return jsonify({'error': 'Некорректный URL'}), 400
    except Exception:
        return jsonify({'error': 'Некорректный URL'}), 400

    if custom_code:
        if len(custom_code) < 3 or len(custom_code) > 20:
            return jsonify({'error': 'Код должен быть от 3 до 20 символов'}), 400
        if custom_code in RESERVED_CODES:
            return jsonify({'error': 'Этот код зарезервирован'}), 409
        short_code = custom_code
    else:
        short_code = generate_short_code()

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO urls (short_code, original_url) VALUES (?, ?)',
            (short_code, original_url)
        )
        conn.commit()

        cursor.execute(
            'SELECT short_code, original_url, created_at FROM urls WHERE short_code = ?',
            (short_code,)
        )
        row = cursor.fetchone()
        conn.close()

        return jsonify({
            'short_url': build_short_url(row[0]),
            'short_code': row[0],
            'original_url': row[1],
            'created_at': row[2]
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({'error': 'Этот код уже занят'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/<short_code>', methods=['GET'])
def get_stats(short_code):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT short_code, original_url, created_at, clicks FROM urls WHERE short_code = ?',
        (short_code,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Ссылка не найдена'}), 404

    return jsonify({
        'short_code': row[0],
        'original_url': row[1],
        'created_at': row[2],
        'clicks': row[3]
    })


@app.route('/<short_code>')
def redirect_to_url(short_code):
    if short_code in RESERVED_CODES:
        return jsonify({'error': 'Ссылка не найдена'}), 404

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT original_url FROM urls WHERE short_code = ?', (short_code,))
    row = cursor.fetchone()

    if row:
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For') or request.remote_addr
        referer = request.headers.get('Referer', '')

        user_agent_lower = user_agent.lower()
        should_log = True

        bot_keywords = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python', 'java', 'headless']
        if any(keyword in user_agent_lower for keyword in bot_keywords):
            should_log = False

        purpose = request.headers.get('Purpose', '').lower()
        sec_purpose = request.headers.get('Sec-Purpose', '').lower()
        sec_fetch_dest = request.headers.get('Sec-Fetch-Dest', '').lower()

        if 'prefetch' in purpose or 'prefetch' in sec_purpose or sec_fetch_dest == 'empty':
            should_log = False

        if should_log:
            cursor.execute('''
                SELECT COUNT(*) FROM clicks_log
                WHERE short_code = ?
                AND ip_address = ?
                AND datetime(clicked_at) > datetime('now', '-2 seconds')
            ''', (short_code, ip_address))

            recent_clicks = cursor.fetchone()[0]

            if recent_clicks == 0:
                device_type = get_device_type(user_agent)
                browser = get_browser(user_agent)
                os_name = get_os(user_agent)
                geo = get_geo_info(ip_address)

                cursor.execute('''
                    INSERT INTO clicks_log
                    (short_code, ip_address, user_agent, referer, country, city, device_type, browser, os)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (short_code, ip_address, user_agent, referer, geo['country'], geo['city'],
                      device_type, browser, os_name))

                cursor.execute('UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?', (short_code,))

        conn.commit()
        conn.close()
        return redirect(row[0], code=302)

    conn.close()
    return jsonify({'error': 'Ссылка не найдена'}), 404


@app.route('/api/urls', methods=['GET'])
def list_urls():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT short_code, original_url, created_at, clicks FROM urls ORDER BY created_at DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()

    urls = []
    for row in rows:
        urls.append({
            'short_code': row[0],
            'original_url': row[1],
            'created_at': row[2],
            'clicks': row[3]
        })

    return jsonify({'urls': urls})


def admin_panel():
    with open('admin_panel.html', 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), domain=config.DOMAIN)


app.add_url_rule(ADMIN_PATH, 'admin_panel', admin_panel)


@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM urls')
    total_urls = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(clicks) FROM urls')
    total_clicks = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(DISTINCT ip_address) FROM clicks_log')
    unique_ips = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM clicks_log WHERE device_type = "Desktop"')
    desktop_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM clicks_log WHERE device_type = "Mobile"')
    mobile_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'total_urls': total_urls,
        'total_clicks': total_clicks,
        'unique_ips': unique_ips,
        'desktop_count': desktop_count,
        'mobile_count': mobile_count
    })


@app.route('/api/admin/logs/<short_code>', methods=['GET'])
def admin_logs(short_code):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT created_at FROM urls WHERE short_code = ?', (short_code,))
    url_row = cursor.fetchone()
    if not url_row:
        conn.close()
        return jsonify({'logs': []})

    created_at = datetime.strptime(url_row[0], '%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        SELECT ip_address, user_agent, referer, country, city,
               device_type, browser, os, clicked_at
        FROM clicks_log
        WHERE short_code = ?
        ORDER BY clicked_at DESC
    ''', (short_code,))

    rows = cursor.fetchall()
    conn.close()

    logs = []
    for row in rows:
        clicked_at = datetime.strptime(row[8], '%Y-%m-%d %H:%M:%S')
        time_diff = clicked_at - created_at

        total_seconds = int(time_diff.total_seconds())
        if total_seconds < 60:
            time_since = f"{total_seconds} сек"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            time_since = f"{minutes} мин"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            time_since = f"{hours} ч {minutes} мин"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            time_since = f"{days} дн {hours} ч"

        logs.append({
            'ip_address': row[0],
            'user_agent': row[1],
            'referer': row[2],
            'country': row[3],
            'city': row[4],
            'device_type': row[5],
            'browser': row[6],
            'os': row[7],
            'clicked_at': row[8],
            'time_since_created': time_since
        })

    return jsonify({'logs': logs})


@app.route('/api/admin/delete/<short_code>', methods=['DELETE'])
def admin_delete(short_code):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM urls WHERE short_code = ?', (short_code,))
    exists = cursor.fetchone()
    if not exists:
        conn.close()
        return jsonify({'error': 'Ссылка не найдена'}), 404

    cursor.execute('DELETE FROM clicks_log WHERE short_code = ?', (short_code,))
    cursor.execute('DELETE FROM urls WHERE short_code = ?', (short_code,))
    conn.commit()
    conn.close()

    return jsonify({'status': 'deleted'})


@app.route('/api/admin/delete-all-links', methods=['DELETE'])
def admin_delete_all_links():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM urls')
    links_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM clicks_log')
    logs_count = cursor.fetchone()[0]

    cursor.execute('DELETE FROM clicks_log')
    cursor.execute('DELETE FROM urls')

    conn.commit()
    conn.close()

    return jsonify({'status': 'deleted', 'deleted_links': links_count, 'deleted_logs': logs_count})


@app.route('/api/admin/delete-zero-clicks', methods=['DELETE'])
def admin_delete_zero_clicks():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM urls WHERE clicks = 0')
    zero_clicks_count = cursor.fetchone()[0]

    cursor.execute('SELECT short_code FROM urls WHERE clicks = 0')
    zero_clicks_codes = [row[0] for row in cursor.fetchall()]

    if zero_clicks_codes:
        placeholders = ','.join(['?' for _ in zero_clicks_codes])
        cursor.execute(f'DELETE FROM clicks_log WHERE short_code IN ({placeholders})', zero_clicks_codes)

    cursor.execute('DELETE FROM urls WHERE clicks = 0')

    conn.commit()
    conn.close()

    return jsonify({'status': 'deleted', 'deleted_links': zero_clicks_count})


init_db()

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=False)
