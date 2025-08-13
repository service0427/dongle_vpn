# VPN 동시 다중 접속 테스트 가이드

## 동시 접속 가능 여부: ✅ YES

VPN은 다음과 같이 동시 다중 접속이 가능합니다:

### 1. 같은 VPN 서버에 여러 클라이언트
```
wg0 (포트 51820)
├── 클라이언트 A (10.0.0.2)
├── 클라이언트 B (10.0.0.3)
├── 클라이언트 C (10.0.0.4)
└── 클라이언트 D (10.0.0.5)
```
현재 wg0에 이미 7개 피어가 연결되어 있음!

### 2. 다른 포트로 분산
```
클라이언트 1 → wg0 (51820) → 동글1
클라이언트 2 → wg1 (51821) → 동글2
클라이언트 3 → wg2 (51822) → 동글1
클라이언트 4 → wg3 (51823) → 동글2
클라이언트 5 → wg4 (51824) → 동글1
클라이언트 6 → wg5 (51825) → 동글2
```

### 3. 실제 테스트 방법

#### 클라이언트 1 설정 (agent1.conf):
```ini
[Interface]
PrivateKey = [생성된_개인키_1]
Address = 10.0.0.2/32
DNS = 8.8.8.8

[Peer]
PublicKey = OTzHXdIyACJ8qtOWM75mExDgsQdu+3ORuu34PtaqgzM=
Endpoint = 222.101.90.78:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

#### 클라이언트 2 설정 (agent2.conf):
```ini
[Interface]
PrivateKey = [생성된_개인키_2]
Address = 10.0.0.3/32
DNS = 8.8.8.8

[Peer]
PublicKey = OTzHXdIyACJ8qtOWM75mExDgsQdu+3ORuu34PtaqgzM=
Endpoint = 222.101.90.78:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

### 4. 동시 접속 테스트 명령어

**터미널 1:**
```bash
wg-quick up ./agent1.conf
curl ifconfig.me
```

**터미널 2:**
```bash
wg-quick up ./agent2.conf
curl ifconfig.me
```

**터미널 3:**
```bash
wg-quick up ./agent3.conf
curl ifconfig.me
```

### 5. 부하 분산 상태

현재 서버는 자동으로 부하를 분산합니다:
- **동글1 (enp0s21f0u4)**: wg0, wg2, wg4 트래픽
- **동글2 (enp0s21f0u3)**: wg1, wg3, wg5 트래픽

### 6. 제한사항

- 각 클라이언트는 고유한 개인키/공개키 쌍 필요
- 각 클라이언트는 고유한 IP 주소 필요
- 서버는 모든 피어의 공개키를 알아야 함

### 7. 현재 연결 상태 확인

```bash
# 서버에서 실행
wg show

# 연결된 피어 수 확인
wg show all dump | grep -c peer

# 각 인터페이스별 연결 수
for i in {0..5}; do 
    echo "wg$i: $(wg show wg$i dump | grep -c peer) peers"
done
```

## 결론

✅ **동시 다중 접속 완벽 지원**
- 같은 VPN 서버에 여러 클라이언트 동시 접속 가능
- 6개 독립 VPN 인터페이스로 최대 수백 개 동시 연결 가능
- 자동 부하 분산으로 안정적인 연결 유지