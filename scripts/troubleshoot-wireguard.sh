#!/bin/bash
echo "=== WireGuard 연결 문제 해결 스크립트 ==="
echo ""

# 1. 기본 연결 테스트
echo "1. 서버 연결 테스트..."
if ping -c 1 222.101.90.78 &>/dev/null; then
    echo "   ✅ 서버 IP 접근 가능"
else
    echo "   ❌ 서버 IP 접근 불가 - 네트워크 확인 필요"
    exit 1
fi

# 2. UDP 포트 테스트
echo "2. UDP 51820 포트 테스트..."
if timeout 2 bash -c "</dev/udp/222.101.90.78/51820" 2>/dev/null; then
    echo "   ✅ UDP 포트 열림"
else
    echo "   ⚠️  UDP 포트 확인 불가 (방화벽 가능성)"
fi

# 3. WireGuard 모듈 확인
echo "3. WireGuard 커널 모듈..."
if lsmod | grep wireguard &>/dev/null; then
    echo "   ✅ WireGuard 모듈 로드됨"
else
    echo "   ❌ WireGuard 모듈 없음 - 설치 필요"
    echo "   실행: sudo apt install wireguard-tools"
fi

# 4. 인터페이스 확인
echo "4. WireGuard 인터페이스..."
if ip link show wg0 &>/dev/null; then
    echo "   ✅ wg0 인터페이스 존재"
    
    # IP 확인
    if ip addr show wg0 | grep "10.0.0.4" &>/dev/null; then
        echo "   ✅ IP 주소 설정됨 (10.0.0.4)"
    else
        echo "   ❌ IP 주소 없음"
    fi
    
    # 핸드셰이크 확인
    HANDSHAKE=$(sudo wg show wg0 latest-handshakes 2>/dev/null | grep -v "0$" | wc -l)
    if [ "$HANDSHAKE" -gt 0 ]; then
        echo "   ✅ 핸드셰이크 성공"
    else
        echo "   ❌ 핸드셰이크 실패"
    fi
else
    echo "   ❌ wg0 인터페이스 없음"
    echo "   실행: sudo wg-quick up wg0"
fi

# 5. DNS 확인
echo "5. DNS 해석 테스트..."
if nslookup google.com 8.8.8.8 &>/dev/null || host google.com &>/dev/null; then
    echo "   ✅ DNS 작동"
else
    echo "   ⚠️  DNS 확인 불가"
fi

# 6. 라우팅 확인
echo "6. 라우팅 테이블..."
if ip route | grep "default dev wg0" &>/dev/null; then
    echo "   ✅ 기본 라우트가 WireGuard로 설정됨"
elif ip route | grep "0.0.0.0/1 dev wg0" &>/dev/null; then
    echo "   ✅ WireGuard 라우팅 설정됨"
else
    echo "   ⚠️  WireGuard 라우팅 확인 필요"
fi

echo ""
echo "=== 디버그 명령어 ==="
echo "sudo wg show         # WireGuard 상태"
echo "sudo wg-quick down wg0 && sudo wg-quick up wg0  # 재연결"
echo "sudo journalctl -xe | grep wg  # 로그 확인"