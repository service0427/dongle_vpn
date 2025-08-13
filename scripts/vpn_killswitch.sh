#!/bin/bash
# VPN Kill Switch 설정
# VPN 연결이 끊어지면 모든 트래픽 차단

echo "=== VPN Kill Switch 설정 ==="

# 1. 기본 정책 설정
echo "1. 기본 차단 정책 설정..."

# IPv4 포워딩 활성화
echo 1 > /proc/sys/net/ipv4/ip_forward

# 기존 규칙 백업
iptables-save > /home/proxy/iptables_backup_$(date +%Y%m%d_%H%M%S).rules

# 2. Kill Switch 체인 생성
iptables -N KILLSWITCH 2>/dev/null || iptables -F KILLSWITCH

# 3. 허용할 트래픽만 정의
echo "2. 허용 규칙 설정..."

# 로컬 루프백 허용
iptables -A KILLSWITCH -i lo -j ACCEPT
iptables -A KILLSWITCH -o lo -j ACCEPT

# 이미 연결된 세션 허용
iptables -A KILLSWITCH -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# VPN 인터페이스 허용
iptables -A KILLSWITCH -i wg+ -j ACCEPT
iptables -A KILLSWITCH -o wg+ -j ACCEPT

# 로컬 네트워크 허용 (관리용)
iptables -A KILLSWITCH -s 192.168.0.0/16 -d 192.168.0.0/16 -j ACCEPT
iptables -A KILLSWITCH -s 10.0.0.0/8 -d 10.0.0.0/8 -j ACCEPT

# SSH 관리 접속 허용 (중요!)
iptables -A KILLSWITCH -p tcp --dport 22 -j ACCEPT
iptables -A KILLSWITCH -p tcp --sport 22 -j ACCEPT

# SOCKS5 프록시 포트 허용
iptables -A KILLSWITCH -p tcp --dport 1080:1082 -j ACCEPT

# VPN 포트 허용
iptables -A KILLSWITCH -p udp --dport 51820:51822 -j ACCEPT

# 동글이 활성 상태일 때만 해당 인터페이스 허용
for interface in enp0s21f0u4 enp0s21f0u3; do
    if ip link show $interface 2>/dev/null | grep -q "state UP"; then
        echo "  - $interface 허용"
        iptables -A KILLSWITCH -o $interface -m mark --mark 0x100 -j ACCEPT
    fi
done

# 4. 나머지 모든 트래픽 차단 (Kill Switch)
echo "3. Kill Switch 활성화..."
iptables -A KILLSWITCH -j LOG --log-prefix "KILLSWITCH-DROP: " --log-level 4
iptables -A KILLSWITCH -j DROP

# 5. FORWARD 체인에 KILLSWITCH 적용
iptables -I FORWARD -j KILLSWITCH

# 6. VPN 클라이언트가 본인 IP를 사용하지 못하도록 차단
echo "4. IP 노출 방지 규칙..."

# VPN 서브넷에서 메인 IP로 직접 나가는 것 차단
iptables -t nat -I POSTROUTING -s 10.0.0.0/24 -o eno1 ! -d 192.168.0.0/16 -j DROP
iptables -t nat -I POSTROUTING -s 10.1.0.0/24 -o eno1 ! -d 192.168.0.0/16 -j DROP

echo "=== Kill Switch 설정 완료 ==="
echo ""
echo "현재 규칙:"
iptables -L KILLSWITCH -n -v
echo ""
echo "⚠️  주의사항:"
echo "  - VPN이 끊어지면 자동으로 모든 외부 트래픽이 차단됩니다"
echo "  - SSH 관리 접속은 유지됩니다"
echo "  - 동글 IP 토글 시에도 연결이 유지됩니다"