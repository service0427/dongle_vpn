# VPN 대역폭 오버헤드 분석

## 🔴 VPN은 통신량을 증가시킵니다!

### 1. **VPN 오버헤드 구성**

```
원본 데이터: 1000 bytes
↓
+ VPN 헤더: 20-40 bytes
+ 암호화 패딩: 16-32 bytes  
+ UDP/TCP 헤더: 8-20 bytes
+ Keep-alive 패킷: 주기적 추가
= 총 전송량: 1044-1092 bytes (4~9% 증가)
```

### 2. **실제 오버헤드 비교**

| 프로토콜 | 오버헤드 | 1GB 전송 시 | 설명 |
|---------|---------|------------|------|
| **직접 연결** | 0% | 1.00 GB | 오버헤드 없음 |
| **SOCKS5** | 1-2% | 1.01-1.02 GB | 헤더만 추가 |
| **WireGuard** | 4-6% | 1.04-1.06 GB | 최소 암호화 |
| **OpenVPN** | 10-20% | 1.10-1.20 GB | 무거운 암호화 |
| **IPSec** | 15-25% | 1.15-1.25 GB | 엔터프라이즈급 |

### 3. **WireGuard 상세 분석**

```
패킷 구조:
[IP Header: 20 bytes]
[UDP Header: 8 bytes]
[WireGuard Header: 16 bytes]
[Encrypted Payload: N bytes]
[Auth Tag: 16 bytes]

총 오버헤드: 60 bytes per packet
MTU 1420 기준: 4.2% 오버헤드
```

### 4. **실제 시나리오 (20개 동글)**

```
시나리오: 각 동글이 10Mbps 사용

직접 연결:
- 20 x 10Mbps = 200Mbps

SOCKS5 경유:
- 20 x 10.2Mbps = 204Mbps (2% 증가)

WireGuard VPN:
- 20 x 10.5Mbps = 210Mbps (5% 증가)
- + Keep-alive 트래픽: 추가 1-2Mbps
- 총: 211-212Mbps

OpenVPN:
- 20 x 12Mbps = 240Mbps (20% 증가!)
```

### 5. **숨겨진 오버헤드**

#### A. Keep-alive 패킷
```bash
# WireGuard PersistentKeepalive=25
매 25초마다 각 피어당 32 bytes 전송
20개 클라이언트 = 20 x 32 x (60/25) = 1536 bytes/min
```

#### B. 재전송 오버헤드
```
VPN 터널 내 패킷 손실 시:
- 원본 재전송
- VPN 레이어 재전송
= 이중 재전송 발생
```

#### C. MTU 문제
```
일반 이더넷 MTU: 1500
VPN 후 MTU: 1420 (WireGuard)

→ 패킷 분할 증가
→ 더 많은 헤더 필요
→ 추가 5-10% 오버헤드
```

## 📊 실측 테스트 명령어

```bash
# 1. 직접 연결 테스트
iperf3 -c 8.8.8.8 -t 30

# 2. SOCKS5 경유
tsocks iperf3 -c 8.8.8.8 -t 30

# 3. VPN 경유
wg-quick up wg0
iperf3 -c 8.8.8.8 -t 30

# 오버헤드 계산
echo "scale=2; (vpn_bytes - direct_bytes) / direct_bytes * 100" | bc
```

## 🎯 최적화 방법

### 1. **MTU 최적화**
```bash
# MTU 자동 탐지
ping -M do -s 1472 8.8.8.8

# WireGuard MTU 설정
wg set wg0 mtu 1420
```

### 2. **압축 활용 (OpenVPN만)**
```
# OpenVPN 설정
comp-lzo adaptive
push "comp-lzo adaptive"
```

### 3. **불필요한 암호화 제거**
```
# 내부망 전용
cipher none
auth none
```

## 💡 결론

### VPN vs SOCKS5 대역폭 사용량:

| 구분 | 1GB 데이터 전송 시 실제 사용량 |
|------|------------------------------|
| **직접 연결** | 1.00 GB |
| **SOCKS5** | 1.01-1.02 GB (✅ 최소) |
| **WireGuard** | 1.05-1.10 GB |
| **OpenVPN** | 1.15-1.25 GB |

### 20개 동글 시나리오:
- **100Mbps 이더넷**: 둘 다 병목
- **1Gbps 이더넷**: 
  - SOCKS5: 거의 풀 성능
  - VPN: 5-20% 성능 저하

### 📌 권장사항:

1. **속도가 중요하면**: SOCKS5
2. **보안이 중요하면**: WireGuard (OpenVPN 피하기)
3. **대역폭 제한 있으면**: SOCKS5 필수

**답변: VPN은 동일 데이터 전송 시 5-20% 더 많은 대역폭을 사용합니다!**