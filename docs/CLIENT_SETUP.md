# WireGuard 클라이언트 설정 가이드

## 빠른 설정 (복사해서 사용)

### 1. 설정 파일 생성
```bash
cat > /tmp/wg-client.conf << 'EOF'
[Interface]
PrivateKey = [당신의_개인키]
Address = 10.0.0.4/32
DNS = 8.8.8.8

[Peer]
PublicKey = OTzHXdIyACJ8qtOWM75mExDgsQdu+3ORuu34PtaqgzM=
Endpoint = 222.101.90.78:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
```

### 2. WireGuard 설치 및 연결
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y wireguard-tools

# CentOS/Rocky
sudo dnf install -y wireguard-tools

# 설정 파일 이동
sudo mv /tmp/wg-client.conf /etc/wireguard/wg0.conf
sudo chmod 600 /etc/wireguard/wg0.conf

# 연결
sudo wg-quick up wg0
```

### 3. 연결 확인
```bash
# VPN 터널 확인
ping -c 2 10.0.0.1

# 외부 IP 확인 (222.101.90.78이어야 함)
curl ifconfig.me
```

## 자주 발생하는 문제와 해결

### ❌ "RTNETLINK answers: Operation not permitted"
```bash
# 해결: 권한 부여
sudo modprobe wireguard
sudo sysctl -w net.ipv4.ip_forward=1
```

### ❌ "Unable to access interface: Operation not permitted"
```bash
# 해결: Docker/컨테이너인 경우
--cap-add=NET_ADMIN --device /dev/net/tun
```

### ❌ 핸드셰이크 실패
```bash
# 시간 동기화 확인
date
sudo ntpdate -s time.google.com

# 방화벽 확인 (클라이언트 측)
sudo iptables -L -n | grep 51820
sudo ufw allow 51820/udp  # Ubuntu
```

### ❌ DNS 작동 안함
```bash
# resolvconf 설치
sudo apt install resolvconf
sudo systemctl enable --now systemd-resolved

# 또는 수동 DNS 설정
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

## Playwright와 통합

### Python 예제
```python
import subprocess
import time

def start_wireguard():
    """WireGuard VPN 시작"""
    try:
        subprocess.run(['sudo', 'wg-quick', 'up', 'wg0'], check=True)
        time.sleep(2)  # 연결 대기
        
        # 연결 확인
        result = subprocess.run(['sudo', 'wg', 'show'], 
                              capture_output=True, text=True)
        if "latest handshake" in result.stdout:
            print("✅ VPN 연결됨")
            return True
    except:
        print("❌ VPN 연결 실패")
    return False

def stop_wireguard():
    """WireGuard VPN 중지"""
    subprocess.run(['sudo', 'wg-quick', 'down', 'wg0'])

# Playwright 사용
from playwright.sync_api import sync_playwright

if start_wireguard():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://ifconfig.me")
        ip = page.content()
        print(f"현재 IP: {ip}")  # 222.101.90.78이어야 함
        browser.close()
    stop_wireguard()
```

## 연결 테스트 스크립트

```bash
#!/bin/bash
# 저장: test-connection.sh

echo "1. WireGuard 상태..."
sudo wg show wg0

echo -e "\n2. 네트워크 테스트..."
ping -c 1 10.0.0.1 && echo "✅ VPN 서버 연결됨" || echo "❌ VPN 서버 연결 실패"

echo -e "\n3. 외부 IP 확인..."
EXTERNAL_IP=$(curl -s ifconfig.me)
if [ "$EXTERNAL_IP" = "222.101.90.78" ]; then
    echo "✅ VPN 통해 연결 중 ($EXTERNAL_IP)"
else
    echo "❌ VPN 미연결 (현재 IP: $EXTERNAL_IP)"
fi

echo -e "\n4. DNS 테스트..."
nslookup google.com 8.8.8.8 &>/dev/null && echo "✅ DNS 작동" || echo "❌ DNS 실패"
```

## 중요 체크 포인트

1. ✅ 개인키가 올바른가?
2. ✅ 서버 공개키: `OTzHXdIyACJ8qtOWM75mExDgsQdu+3ORuu34PtaqgzM=`
3. ✅ 서버 주소: `222.101.90.78:51820`
4. ✅ 클라이언트 IP: `10.0.0.4/32`
5. ✅ sudo 권한으로 실행했는가?

## 디버깅 명령어

```bash
# 상세 로그 확인
sudo wg-quick up wg0 2>&1 | tee wireguard.log

# 커널 로그
sudo dmesg | grep wireguard

# 네트워크 인터페이스
ip addr show wg0

# 라우팅 테이블
ip route show table all | grep wg0
```