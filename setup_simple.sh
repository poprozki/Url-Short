#!/bin/bash

APP_DIR="/var/www/shortener"
LOG_DIR="/var/log/url-shortener"

echo "Настройка URL Shortener без gunicorn..."

systemctl stop url-shortener 2>/dev/null

echo "Создание service файла..."
cat > /etc/systemd/system/url-shortener.service << EOF
[Unit]
Description=URL Shortener Flask Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/output.log
StandardError=append:$LOG_DIR/error.log

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
echo "Логи: $LOG_DIR/output.log, $LOG_DIR/error.log"
