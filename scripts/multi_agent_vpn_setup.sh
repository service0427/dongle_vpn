#!/bin/bash
# 다중 에이전트 VPN 설정 (4~6개 동시 접속)

echo "=== 다중 에이전트 VPN 서버 설정 ==="

# 기본 설정
SERVER_IP="222.101.90.78"
VPN_SUBNET_BASE="10.0"
PORT_BASE=51820

# 동글 인터페이스 매핑
DONGLE1="enp0s21f0u4"
DONGLE2="enp0s21f0u3"

# 각 VPN 인터페이스 생성 (wg0 ~ wg5)
for i in {0..5}; do
    INTERFACE="wg$i"
    PORT=$((PORT_BASE + i))
    SUBNET="$VPN_SUBNET_BASE.$i.0/24"
    SERVER_ADDR="$VPN_SUBNET_BASE.$i.1/24"
    
    echo "\n[$INTERFACE] 설정 중..."
    
    # 기존 인터페이스 제거
    wg-quick down $INTERFACE 2>/dev/null
    
    # 키 생성
    PRIVATE_KEY=$(wg genkey)
    PUBLIC_KEY=$(echo $PRIVATE_KEY | wg pubkey)
    
    # 라우팅 결정 (라운드로빈)
    if [ $((i % 2)) -eq 0 ]; then
        OUT_INTERFACE=$DONGLE1
        ROUTING_TABLE=$((200 + i))
    else
        OUT_INTERFACE=$DONGLE2
        ROUTING_TABLE=$((200 + i))
    fi
    
    # WireGuard 설정 파일 생성
    cat > /etc/wireguard/$INTERFACE.conf << EOF
[Interface]
Address = $SERVER_ADDR
ListenPort = $PORT
PrivateKey = $PRIVATE_KEY

# 라우팅 설정
Table = $ROUTING_TABLE

# 시작 시 실행
PostUp = ip rule add from $SUBNET lookup $ROUTING_TABLE
PostUp = ip route add default dev $OUT_INTERFACE table $ROUTING_TABLE
PostUp = iptables -t nat -A POSTROUTING -s $SUBNET -o $OUT_INTERFACE -j MASQUERADE
PostUp = iptables -A FORWARD -i $INTERFACE -j ACCEPT
PostUp = iptables -A FORWARD -o $INTERFACE -j ACCEPT

# 종료 시 정리
PostDown = ip rule del from $SUBNET lookup $ROUTING_TABLE
PostDown = ip route flush table $ROUTING_TABLE
PostDown = iptables -t nat -D POSTROUTING -s $SUBNET -o $OUT_INTERFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i $INTERFACE -j ACCEPT
PostDown = iptables -D FORWARD -o $INTERFACE -j ACCEPT

EOF
    
    # 설정 정보 저장
    echo "  서버 IP: $SERVER_ADDR"
    echo "  포트: $PORT"
    echo "  공개키: $PUBLIC_KEY"
    echo "  라우팅: $OUT_INTERFACE (테이블 $ROUTING_TABLE)"
    
    # 인터페이스 정보 저장
    cat >> /home/proxy/vpn_interfaces.txt << EOF
$INTERFACE|$PORT|$PUBLIC_KEY|$SUBNET|$OUT_INTERFACE|$ROUTING_TABLE
EOF
    
    # 인터페이스 시작
    wg-quick up $INTERFACE
    
    echo "  ✅ $INTERFACE 활성화됨"
done

echo "\n=== 에이전트 연결 정보 ==="
echo "각 에이전트는 다음 포트 중 하나를 사용:"
for i in {0..5}; do
    echo "  - 에이전트 $((i+1)): 포트 $((PORT_BASE + i)) (10.0.$i.0/24)"
done

echo "\n=== 부하 분산 설정 ==="
echo "  - 짝수 에이전트 (0,2,4): 동글1 경유"
echo "  - 홀수 에이전트 (1,3,5): 동글2 경유"

# systemd 서비스 생성
cat > /tmp/multi-agent-vpn.service << 'EOF'
[Unit]
Description=Multi-Agent VPN Server
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/home/proxy/multi_agent_vpn_setup.sh
ExecStop=/bin/bash -c 'for i in {0..5}; do wg-quick down wg$i; done'

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/multi-agent-vpn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable multi-agent-vpn.service

echo "\n✅ 다중 에이전트 VPN 서버 준비 완료"