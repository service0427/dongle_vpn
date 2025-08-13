#!/bin/bash
echo "=== VPN 트래픽을 동글로 라우팅하는 정교한 설정 ==="

# 1. 동글이 실제로 인터넷에 연결되어 있는지 확인
echo "1. 동글 인터넷 연결 확인..."
if ping -I enp0s21f0u4 -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "✅ 동글 인터넷 연결 확인됨"
else
    echo "❌ 동글 인터넷 연결 실패 - 중단"
    exit 1
fi

# 2. VPN 트래픽을 위한 별도 라우팅 테이블 생성 (테이블 200)
echo "2. VPN 전용 라우팅 테이블 설정..."
ip route add default via 192.168.16.1 dev enp0s21f0u4 table 200 2>/dev/null
ip route add 192.168.16.0/24 dev enp0s21f0u4 src 192.168.16.100 table 200 2>/dev/null

# 3. VPN 클라이언트 트래픽만 동글로 라우팅 (WireGuard 인터페이스 제외)
echo "3. 정책 기반 라우팅 설정..."
# VPN 클라이언트에서 나오는 트래픽 중 VPN 서버 자체로 가지 않는 트래픽만
ip rule add from 10.0.0.0/24 not to 222.101.90.78 lookup 200 priority 100 2>/dev/null

# 4. iptables NAT 설정 (VPN 클라이언트 트래픽을 동글로)
echo "4. NAT 규칙 설정..."
# VPN 클라이언트 트래픽이 동글로 나갈 때 SNAT
iptables -t nat -I POSTROUTING 1 -s 10.0.0.0/24 ! -d 10.0.0.0/24 -o enp0s21f0u4 -j SNAT --to-source 192.168.16.100 2>/dev/null

echo "5. 설정 확인..."
echo "라우팅 룰:"
ip rule show | grep "lookup 200"
echo "라우팅 테이블 200:"
ip route show table 200
echo "NAT 규칙:"
iptables -t nat -L POSTROUTING -n | grep "10.0.0.0/24"

echo "=== 설정 완료 ==="
echo "이제 VPN 클라이언트에서 ifconfig.me를 확인해보세요."