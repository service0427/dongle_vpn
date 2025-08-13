# 다중 동글 VPN/SOCKS5 게이트웨이 서버 완전 설치 가이드

## 📋 개요

이 가이드는 11~20개의 USB 동글을 사용하여 다중 에이전트가 동시에 H3 트래픽을 처리할 수 있는 네트워크 게이트웨이 서버 구축 방법을 다룹니다.

### 주요 기능
- 🔄 **다중 VPN 서버** (6개 독립 인터페이스)
- 🚀 **SOCKS5 프록시** (속도 최적화)
- 🛡️ **Kill Switch** (IP 노출 방지)
- ⚖️ **자동 부하 분산** (동글간 트래픽 분산)
- 📊 **실시간 모니터링** (연결 상태 추적)
- 🔐 **유연한 인증** (임시/영구/QR 코드)

---

## 🏗️ 시스템 아키텍처

```
[클라이언트 1-6] → [VPN/SOCKS5] → [서버] → [동글 1-20] → [모바일 네트워크]
                                    ↓
                              [부하 분산]
                                    ↓
                            [Kill Switch 보호]
```

### 네트워크 구성
- **메인 라인**: eno1 (100Mbps) - 관리용, SSH 접속
- **동글 1**: enp0s21f0u4 - VPN wg0, wg2, wg4 트래픽
- **동글 2**: enp0s21f0u3 - VPN wg1, wg3, wg5 트래픽

---

## 🛠️ 1. 기본 시스템 설정

### 1.1 필수 패키지 설치

```bash
# 기본 네트워크 도구
sudo dnf update -y
sudo dnf install -y wireguard-tools iptables-services dante-server
sudo dnf install -y python3 python3-pip git curl wget

# Python 의존성
pip3 install flask qrcode pillow

# 네트워크 관리 도구
sudo dnf install -y NetworkManager-wifi NetworkManager-tui
sudo dnf install -y bind-utils net-tools tcpdump
```

### 1.2 방화벽 및 포워딩 설정

```bash
# IP 포워딩 영구 활성화
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 방화벽 설정
sudo systemctl enable iptables
sudo systemctl start iptables
```

---

## 🔧 2. WireGuard VPN 서버 설정

### 2.1 다중 VPN 인터페이스 생성

```bash
# 다중 에이전트 VPN 설정 스크립트 실행
chmod +x /home/proxy/multi_agent_vpn_setup.sh
bash /home/proxy/multi_agent_vpn_setup.sh
```

### 2.2 VPN 설정 파일들

각 VPN 인터페이스별 설정 파일이 생성됩니다:

```ini
# /etc/wireguard/wg0.conf 예시
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = [자동생성됨]
Table = 200

PostUp = ip rule add from 10.0.0.0/24 lookup 200
PostUp = ip route add default dev enp0s21f0u4 table 200
PostUp = iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o enp0s21f0u4 -j MASQUERADE

PostDown = ip rule del from 10.0.0.0/24 lookup 200
PostDown = ip route flush table 200
PostDown = iptables -t nat -D POSTROUTING -s 10.0.0.0/24 -o enp0s21f0u4 -j MASQUERADE
```

### 2.3 VPN 서비스 시작

```bash
# 모든 VPN 인터페이스 시작
for i in {0..5}; do
    sudo wg-quick up wg$i
done

# 자동 시작 설정
for i in {0..5}; do
    sudo systemctl enable wg-quick@wg$i
done
```

---

## 🔌 3. SOCKS5 프록시 설정

### 3.1 SOCKS5 서버 설정

```bash
# SOCKS5 설정 스크립트 실행
chmod +x /home/proxy/setup_socks5.sh
bash /home/proxy/setup_socks5.sh
```

### 3.2 SOCKS5 포트 구성

- **포트 1080**: 동글1 경유 (enp0s21f0u4)
- **포트 1081**: 동글2 경유 (enp0s21f0u3)
- **포트 1082**: 메인라인 경유 (eno1)

### 3.3 SOCKS5 상태 확인

```bash
# 활성 프록시 확인
ps aux | grep dante | grep -v grep

# 포트 리스닝 확인
netstat -tlnp | grep -E ':108[0-2]'
```

---

## 🛡️ 4. Kill Switch 설정

### 4.1 Kill Switch 활성화

```bash
# Kill Switch 설정
chmod +x /home/proxy/vpn_killswitch.sh
sudo bash /home/proxy/vpn_killswitch.sh
```

### 4.2 Kill Switch 규칙

- VPN 연결 실패 시 모든 외부 트래픽 자동 차단
- SSH 관리 접속은 항상 유지 (포트 22)
- 로컬 네트워크 통신 허용
- SOCKS5/VPN 포트 허용

---

## 🤖 5. 자동화 시스템 설정

### 5.1 에이전트 연결 관리자

```bash
# 에이전트 자동 할당 시스템
chmod +x /home/proxy/agent_connection_manager.py
python3 /home/proxy/agent_connection_manager.py
```

### 5.2 VPN 인증 관리 시스템

```bash
# VPN 인증 시스템 시작
chmod +x /home/proxy/vpn_auth_manager.py
python3 /home/proxy/vpn_auth_manager.py &

# API 서버 테스트
curl -X POST http://localhost:5000/api/vpn/temp \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

### 5.3 네트워크 게이트웨이 서버

```bash
# 통합 게이트웨이 서버 시작
chmod +x /home/proxy/network_gateway_server.py
python3 /home/proxy/network_gateway_server.py &
```

---

## 📊 6. 모니터링 및 관리

### 6.1 VPN 연결 상태 확인

```bash
# 모든 VPN 인터페이스 상태
wg show

# 특정 인터페이스 상세 정보
wg show wg0

# 연결된 클라이언트 수
wg show all dump | grep peer | wc -l
```

### 6.2 트래픽 모니터링

```bash
# 실시간 대역폭 모니터링
iftop -i eno1

# 인터페이스별 통계
vnstat -l -i enp0s21f0u4

# 동글 상태 확인
for i in enp0s21f0u4 enp0s21f0u3; do
    echo "$i: $(ip addr show $i | grep 'inet ' | awk '{print $2}')"
done
```

### 6.3 에이전트 상태 모니터링

```python
# Python을 통한 에이전트 모니터링
from agent_connection_manager import AgentConnectionManager
manager = AgentConnectionManager()
manager.monitor_agents()
```

---

## 👥 7. 클라이언트 연결 가이드

### 7.1 VPN 클라이언트 설정

#### 자동 클라이언트 생성
```bash
# 새 에이전트용 VPN 설정 생성
python3 -c "
from agent_connection_manager import AgentConnectionManager
manager = AgentConnectionManager()
result = manager.assign_agent('agent_001', 'TestAgent')
print(result['config'])
"
```

#### 수동 클라이언트 설정 예시
```ini
[Interface]
PrivateKey = [클라이언트_개인키]
Address = 10.0.0.2/32
DNS = 8.8.8.8

[Peer]
PublicKey = [서버_공개키]
Endpoint = 222.101.90.78:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

### 7.2 SOCKS5 프록시 사용

#### Playwright 예시
```javascript
const { chromium } = require('playwright');

// 동글1 경유
const browser1 = await chromium.launch({
  proxy: { server: 'socks5://222.101.90.78:1080' }
});

// 동글2 경유
const browser2 = await chromium.launch({
  proxy: { server: 'socks5://222.101.90.78:1081' }
});
```

#### cURL 예시
```bash
# 동글1 경유
curl --socks5 222.101.90.78:1080 ifconfig.me

# 동글2 경유
curl --socks5 222.101.90.78:1081 ifconfig.me
```

---

## 🔄 8. 운영 및 유지보수

### 8.1 일상 관리 명령어

```bash
# 시스템 상태 체크
systemctl status wg-quick@wg0
systemctl status dante-server

# 로그 확인
journalctl -u wg-quick@wg0 -f
tail -f /home/proxy/gateway.log

# 재시작
sudo systemctl restart wg-quick@wg0
sudo systemctl restart dante-server
```

### 8.2 동글 IP 토글

```bash
# 동글 IP 변경 (자동)
python3 -c "
from network_gateway_server import NetworkGatewayServer
server = NetworkGatewayServer()
server.toggle_dongle_ip('dongle1')
"

# 수동 재연결
sudo nmcli device disconnect enp0s21f0u4
sleep 3
sudo nmcli device connect enp0s21f0u4
```

### 8.3 백업 및 복원

```bash
# 설정 백업
tar -czf vpn_backup_$(date +%Y%m%d).tar.gz \
  /etc/wireguard/ \
  /home/proxy/*.py \
  /home/proxy/*.json \
  /home/proxy/*.md

# 방화벽 규칙 백업
iptables-save > /home/proxy/iptables_backup_$(date +%Y%m%d).rules
```

---

## ⚠️ 9. 문제 해결

### 9.1 일반적인 문제들

#### VPN 연결 실패
```bash
# 인터페이스 상태 확인
ip link show wg0

# 라우팅 테이블 확인
ip route show table 200

# 방화벽 규칙 확인
iptables -L -n -v
```

#### SOCKS5 연결 실패
```bash
# 포트 점유 확인
netstat -tlnp | grep 1080

# dante 로그 확인
tail -f /var/log/dante_dongle1.log
```

#### 동글 연결 문제
```bash
# USB 디바이스 확인
lsusb

# 네트워크 인터페이스 확인
ip link show | grep enp

# NetworkManager 상태
nmcli device status
```

### 9.2 성능 최적화

#### 대역폭 부족 시
```bash
# 기가비트 이더넷 어댑터 추가 필요
# QoS 설정으로 임시 해결
tc qdisc add dev enp0s21f0u4 root handle 1: htb default 30
tc class add dev enp0s21f0u4 parent 1: classid 1:1 htb rate 50mbit
```

#### CPU 사용률 높을 시
```bash
# WireGuard 대신 SOCKS5 사용
# OpenVPN 대신 WireGuard 사용
```

---

## 📈 10. 성능 벤치마크

### 10.1 속도 테스트

```bash
# 직접 연결 vs VPN vs SOCKS5 비교
iperf3 -c speedtest.net -t 30  # 직접
# VPN 연결 후
iperf3 -c speedtest.net -t 30  # VPN
# SOCKS5 경유
tsocks iperf3 -c speedtest.net -t 30  # SOCKS5
```

### 10.2 예상 성능

| 연결 방식 | 지연시간 | 대역폭 효율 | CPU 사용률 |
|-----------|----------|-------------|------------|
| 직접 연결 | 기준 | 100% | 최소 |
| SOCKS5 | +0-5ms | 95-100% | 5-10% |
| WireGuard | +10-20ms | 70-80% | 20-30% |

---

## 🔒 11. 보안 고려사항

### 11.1 VPN vs SOCKS5 익명성

- **SOCKS5**: 완벽한 투명성, 탐지 불가
- **VPN**: 일부 패킷 패턴 변화, 동글 기반이라 탐지 어려움

### 11.2 권장 사용법

```python
# H3가 필요한 사이트: VPN
if site_requires_h3:
    use_vpn_connection()
else:
    use_socks5_proxy()  # 완벽한 익명성
```

---

## 📞 12. 문의 및 지원

### 파일 구조
```
/home/proxy/
├── multi_agent_vpn_setup.sh          # VPN 서버 자동 설정
├── setup_socks5.sh                   # SOCKS5 프록시 설정
├── vpn_killswitch.sh                 # Kill Switch 설정
├── network_gateway_server.py         # 통합 게이트웨이 관리
├── agent_connection_manager.py       # 에이전트 자동 할당
├── vpn_auth_manager.py               # VPN 인증 시스템
├── hybrid_connection_strategy.py     # 하이브리드 연결 전략
├── COMPLETE_SETUP_GUIDE.md          # 이 문서
└── 설정 파일들 (.conf, .json)
```

### 주요 포트
- **SSH**: 22
- **VPN**: 51820-51825 (UDP)
- **SOCKS5**: 1080-1082 (TCP)
- **API**: 5000 (HTTP)

---

## 🎯 13. 최종 체크리스트

- [ ] 기본 패키지 설치 완료
- [ ] WireGuard VPN 서버 6개 인터페이스 활성화
- [ ] SOCKS5 프록시 3개 포트 활성화
- [ ] Kill Switch 설정 완료
- [ ] 에이전트 관리 시스템 실행
- [ ] VPN 인증 시스템 실행
- [ ] 모니터링 시스템 설정
- [ ] 클라이언트 테스트 완료
- [ ] 백업 설정 완료

**🎉 설치 완료! 이제 4-6개 에이전트가 동시에 다중 동글을 통해 H3 트래픽을 안전하고 효율적으로 처리할 수 있습니다.**