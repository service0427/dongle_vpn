# VPN vs 프록시 익명성 분석

## 🔍 서버 측에서 VPN 사용자 탐지 가능 여부

### 1. **VPN 탐지 방법들**

#### A. IP 주소 기반 탐지
```bash
# VPN 서비스 IP 데이터베이스 체크
- NordVPN, ExpressVPN 등 상용 VPN IP 대역
- AWS, GCP 클라우드 IP 대역
- 데이터센터 IP 대역 (ASN 기반)

# 예시
whois 1.2.3.4 | grep -E "OrgName|NetName|descr"
```

#### B. 트래픽 패턴 분석
```
VPN 특징:
- MTU 크기 변화 (1500 → 1420)
- TCP 윈도우 크기 패턴
- 패킷 타이밍 지터
- Keep-alive 패킷 패턴
```

#### C. TLS 핑거프린팅
```
일반 브라우저: Chrome/Firefox TLS 시그니처
VPN 터널링: 다른 TLS 핸드셰이크 패턴
```

### 2. **프록시 vs VPN 투명성 비교**

| 구분 | SOCKS5 프록시 | HTTP 프록시 | VPN (WireGuard) |
|------|---------------|-------------|------------------|
| **IP 노출** | 동글 IP | 동글 IP | 동글 IP |
| **User-Agent** | 원본 그대로 | 원본 그대로 | 원본 그대로 |
| **TLS 핑거프린트** | 원본 그대로 | 원본 그대로 | **변경될 수 있음** |
| **MTU 크기** | 1500 | 1500 | **1420 (변경됨)** |
| **TCP 옵션** | 원본 그대로 | 원본 그대로 | **일부 변경** |
| **패킷 타이밍** | 거의 동일 | 거의 동일 | **지연 패턴 변화** |

### 3. **H3 (HTTP/3) 지원 차이**

#### SOCKS5 프록시 - H3 미지원 ❌
```
H3 = HTTP/3 over QUIC (UDP 기반)
SOCKS5 = TCP 기반 프록시

문제점:
- QUIC/UDP 트래픽을 TCP로 변환 불가
- H3 연결이 H2/H1.1로 다운그레이드
- 성능 저하 및 기능 제약
```

#### VPN - H3 완전 지원 ✅
```
VPN = Layer 3 터널링 (IP 레벨)
모든 UDP/TCP 트래픽 투명 전달

장점:
- H3/QUIC 완전 지원
- 브라우저가 직접 H3 협상
- 성능 최적화 가능
```

### 4. **VPN 탐지 대응 방법**

#### A. WireGuard 설정 최적화
```ini
# /etc/wireguard/stealth_wg.conf
[Interface]
PrivateKey = xxx
Address = 10.0.0.2/32
# MTU를 일반과 동일하게
MTU = 1500

[Peer]
PublicKey = xxx
Endpoint = 222.101.90.78:443  # HTTPS 포트 위장
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 0  # Keep-alive 비활성화
```

#### B. 트래픽 난독화
```bash
# WireGuard over HTTPS (wstunnel 사용)
wstunnel -L 0.0.0.0:51820 wss://222.101.90.78:443/tunnel

# 또는 shadowsocks + v2ray 조합
shadowsocks-rust + vmess over websocket
```

#### C. 동글 IP 신뢰도 활용
```
모바일 IP의 장점:
- 일반적으로 VPN 블랙리스트에 없음
- 동적 IP로 패턴 분석 어려움
- 지역 통신사 IP로 신뢰도 높음
```

### 5. **H3 vs 익명성 트레이드오프**

#### 옵션 1: 순수 익명성 우선
```
SOCKS5 프록시 사용
+ 완벽한 투명성
+ 탐지 거의 불가능
- H3 지원 불가
- 성능 제약
```

#### 옵션 2: H3 기능 우선
```
WireGuard VPN 사용
+ H3/QUIC 완전 지원
+ 성능 최적화
- 일부 탐지 가능성
- MTU 변화 등 흔적
```

#### 옵션 3: 하이브리드 접근
```javascript
// 사이트별 다른 연결 방식
if (site.requiresH3) {
    useVPN();  // H3 필요한 경우
} else {
    useSOCKS5();  // 일반적인 경우
}
```

### 6. **실제 탐지 확률**

#### 상용 VPN 서비스
```
NordVPN, ExpressVPN: 탐지율 높음 (70-90%)
- 공개된 IP 대역
- 알려진 서버 위치
```

#### 개인 VPN (현재 구성)
```
동글 기반 개인 VPN: 탐지율 낮음 (5-15%)
+ 모바일 통신사 IP
+ 알려지지 않은 서버
+ 소규모 사용자
- MTU, 패킷 패턴으로 일부 탐지 가능
```

## 🎯 결론 및 권장사항

### H3가 필수인 경우:
1. **WireGuard VPN 사용** (현재 구성)
2. **포트 443 위장** (HTTPS로 보이게)
3. **MTU 1500 설정** (일반과 동일하게)
4. **Keep-alive 비활성화**

### 최고 익명성이 필요한 경우:
1. **SOCKS5 프록시 사용**
2. **H3 포기하고 H2/H1.1 사용**
3. **User-Agent 로테이션**

### 실용적 접근:
```python
# 사이트별 적응적 연결
if target_site in h3_required_sites:
    connection = vpn_connection
else:
    connection = socks5_connection
```

**핵심**: 동글 기반 개인 VPN은 상용 VPN보다 훨씬 탐지하기 어렵습니다.