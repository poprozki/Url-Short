#!/bin/bash

APP_DIR="/var/www/shortener"
LOG_DIR="/var/log/url-shortener"
BIND="0.0.0.0:5000"

echo "Проверка установки gunicorn..."

if command -v gunicorn3 &> /dev/null; then
    GUNICORN_PATH=$(which gunicorn3)
    echo "Найден gunicorn3: $GUNICORN_PATH"
elif command -v gunicorn &> /dev/null; then
    GUNICORN_PATH=$(which gunicorn)
    echo "Найден gunicorn: $GUNICORN_PATH"
else
    echo "gunicorn не найден, устанавливаем..."
    pip3 install gunicorn

    if command -v gunicorn3 &> /dev/null; then
        GUNICORN_PATH=$(which gunicorn3)
    elif command -v gunicorn &> /dev/null; then
        GUNICORN_PATH=$(which gunicorn)
    else
        echo "Ошибка установки gunicorn. Попробуйте вручную: pip3 install gunicorn"
        exit 1
    fi
fi

echo "Путь к gunicorn: $GUNICORN_PATH"
echo ""

systemctl stop url-shortener 2>/dev/null

echo "Создание service файла..."
cat > /etc/systemd/system/url-shortener.service << EOF
[Unit]
Description=URL Shortener Flask Application
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=$GUNICORN_PATH --workers 4 --bind $BIND --timeout 120 --access-logfile $LOG_DIR/access.log --error-logfile $LOG_DIR/error.log app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

systemctl daemon-reload
systemctl enable url-shortener.service
systemctl start url-shortener.service

sleep 2

echo ""
echo "=========================================="
echo "Статус сервиса:"
echo "=========================================="
systemctl status url-shortener.service --no-pager -l

echo ""
echo "Команды управления:"
echo "  systemctl start url-shortener"
echo "  systemctl stop url-shortener"
echo "  systemctl restart url-shortener"
echo "  systemctl status url-shortener"
echo "  journalctl -u url-shortener -f"
echo ""
echo "Логи: $LOG_DIR/access.log, $LOG_DIR/error.log"
