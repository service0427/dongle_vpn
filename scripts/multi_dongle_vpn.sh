#!/bin/bash
# 다중 동글 VPN 라우팅 관리 스크립트

# 동글 인터페이스 자동 감지
get_dongle_interfaces() {
    ip link show | grep -E "enp.*u[0-9]" | awk -F': ' '{print $2}' | cut -d':' -f1
}

# 동글별 라우팅 테이블 설정
setup_dongle_routing() {
    local interface=$1
    local table_id=$2
    local ip=$(ip addr show $interface | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
    local gateway=$(echo $ip | sed 's/\.[0-9]*$/.1/')
    
    echo "설정 중: $interface (IP: $ip, Gateway: $gateway, Table: $table_id)"
    
    # 라우팅 테이블에 경로 추가
    ip route add default via $gateway dev $interface table $table_id 2>/dev/null
    ip route add 192.168.0.0/16 dev $interface table $table_id 2>/dev/null
    
    return 0
}

# 메인 로직
echo "=== 다중 동글 VPN 라우팅 설정 ==="

# 1. 현재 연결된 동글 확인
DONGLES=$(get_dongle_interfaces)
DONGLE_COUNT=$(echo "$DONGLES" | wc -w)

echo "발견된 동글: $DONGLE_COUNT개"
echo "$DONGLES"

if [ $DONGLE_COUNT -eq 0 ]; then
    echo "❌ 연결된 동글이 없습니다"
    exit 1
fi

# 2. 옵션 선택
echo ""
echo "동글 사용 방식 선택:"
echo "1) 첫 번째 동글만 사용 (현재 방식)"
echo "2) 페일오버 (주 동글 실패 시 백업 동글 사용)"
echo "3) 로드밸런싱 (여러 동글 동시 사용)"
echo "4) 특정 동글 선택"

# 3. 각 동글의 상태 표시
TABLE_ID=200
for dongle in $DONGLES; do
    IP=$(ip addr show $dongle | grep "inet 192.168" | awk '{print $2}' | cut -d'/' -f1)
    
    # ping 테스트로 인터넷 연결 확인
    if ping -I $IP -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        STATUS="✅ 인터넷 연결됨"
    else
        STATUS="❌ 인터넷 연결 안됨"
    fi
    
    echo "  - $dongle: $IP $STATUS (Table: $TABLE_ID)"
    
    # 라우팅 테이블 설정
    setup_dongle_routing $dongle $TABLE_ID
    
    ((TABLE_ID++))
done

echo ""
echo "현재 VPN 라우팅 상태:"
ip rule show | grep "10.0.0.0/24"
echo ""
echo "권장: 인터넷이 연결된 동글을 선택하거나 페일오버 설정을 사용하세요."