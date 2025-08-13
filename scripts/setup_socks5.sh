#!/bin/bash
# SOCKS5 프록시 서버 설정 (microsocks 사용)

echo "=== SOCKS5 프록시 서버 설정 ==="

# microsocks 설치 확인
if ! command -v microsocks &> /dev/null; then
    echo "microsocks 설치 중..."
    cd /tmp
    git clone https://github.com/rofl0r/microsocks.git
    cd microsocks
    make
    sudo cp microsocks /usr/local/bin/
    cd /home/proxy
fi

# 각 인터페이스별 SOCKS5 프록시 시작
start_proxy() {
    local name=$1
    local interface=$2
    local port=$3
    local ip=$4
    
    echo "프록시 시작: $name (포트 $port)"
    
    # 기존 프로세스 종료
    pkill -f "microsocks.*-p $port" 2>/dev/null
    
    # 새 프록시 시작
    if [ "$ip" != "" ]; then
        nohup microsocks -i 0.0.0.0 -p $port -b $ip > /home/proxy/socks5_${name}.log 2>&1 &
        echo "  ✅ $name 프록시 시작됨 (PID: $!)"
        echo $! > /home/proxy/socks5_${name}.pid
    else
        echo "  ❌ $name IP 없음"
    fi
}

# 동글1 프록시
DONGLE1_IP=$(ip addr show enp0s21f0u4 2>/dev/null | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
start_proxy "dongle1" "enp0s21f0u4" 1080 "$DONGLE1_IP"

# 동글2 프록시
DONGLE2_IP=$(ip addr show enp0s21f0u3 2>/dev/null | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
start_proxy "dongle2" "enp0s21f0u3" 1081 "$DONGLE2_IP"

# 메인라인 프록시
MAIN_IP=$(ip addr show eno1 | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d'/' -f1)
start_proxy "mainline" "eno1" 1082 "$MAIN_IP"

echo ""
echo "=== SOCKS5 프록시 상태 ==="
echo "활성 프록시:"
ps aux | grep microsocks | grep -v grep

echo ""
echo "사용 가능한 프록시:"
echo "  - socks5://$(hostname -I | awk '{print $1}'):1080  # 동글1"
echo "  - socks5://$(hostname -I | awk '{print $1}'):1081  # 동글2"  
echo "  - socks5://$(hostname -I | awk '{print $1}'):1082  # 메인라인"

# systemd 서비스 생성
cat > /tmp/socks5-proxy.service << 'EOF'
[Unit]
Description=SOCKS5 Proxy Service
After=network.target

[Service]
Type=forking
ExecStart=/home/proxy/setup_socks5.sh
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/socks5-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable socks5-proxy.service

echo ""
echo "자동 시작 설정 완료: systemctl start socks5-proxy"