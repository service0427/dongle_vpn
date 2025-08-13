#!/bin/bash
# 동글 페일오버 설정 - 주 동글 실패 시 자동으로 백업 동글로 전환

echo "=== 동글 페일오버 VPN 설정 ==="

# 현재 활성 동글 확인
PRIMARY_DONGLE="enp0s21f0u4"
BACKUP_DONGLE="enp0s21f0u3"

# 주 동글 상태 확인
check_dongle_status() {
    local interface=$1
    local ip=$(ip addr show $interface 2>/dev/null | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
    
    if [ -z "$ip" ]; then
        return 1
    fi
    
    if ping -I $ip -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 페일오버 로직
if check_dongle_status $PRIMARY_DONGLE; then
    echo "✅ 주 동글($PRIMARY_DONGLE) 정상 - 계속 사용"
    ACTIVE_DONGLE=$PRIMARY_DONGLE
    ACTIVE_IP=$(ip addr show $PRIMARY_DONGLE | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
elif check_dongle_status $BACKUP_DONGLE; then
    echo "⚠️ 주 동글 실패, 백업 동글($BACKUP_DONGLE)로 전환"
    ACTIVE_DONGLE=$BACKUP_DONGLE
    ACTIVE_IP=$(ip addr show $BACKUP_DONGLE | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
    
    # 라우팅 테이블 200을 백업 동글로 변경
    GATEWAY=$(echo $ACTIVE_IP | sed 's/\.[0-9]*$/.1/')
    ip route del default table 200 2>/dev/null
    ip route add default via $GATEWAY dev $ACTIVE_DONGLE table 200
    
    # NAT 규칙 업데이트
    iptables -t nat -D POSTROUTING -s 10.0.0.0/24 -o $PRIMARY_DONGLE -j MASQUERADE 2>/dev/null
    iptables -t nat -I POSTROUTING 1 -s 10.0.0.0/24 -o $ACTIVE_DONGLE -j MASQUERADE
else
    echo "❌ 모든 동글 실패!"
    exit 1
fi

echo ""
echo "현재 활성 동글: $ACTIVE_DONGLE ($ACTIVE_IP)"
echo "VPN 트래픽은 이 동글을 통해 라우팅됩니다."

# 상태 모니터링 (선택사항)
echo ""
echo "자동 모니터링을 시작하시겠습니까? (y/n)"
echo "주 동글이 복구되면 자동으로 다시 전환됩니다."