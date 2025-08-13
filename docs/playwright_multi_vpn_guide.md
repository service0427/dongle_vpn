# Playwright 다중 VPN 활용 가이드

## 방법 1: Docker 컨테이너 (가장 간단)

```yaml
# docker-compose.yml
version: '3'
services:
  playwright-agent1:
    image: mcr.microsoft.com/playwright:focal
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./agent1-vpn.conf:/etc/wireguard/wg0.conf
    command: |
      sh -c "wg-quick up wg0 && node agent1.js"
    
  playwright-agent2:
    image: mcr.microsoft.com/playwright:focal
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./agent2-vpn.conf:/etc/wireguard/wg0.conf
    command: |
      sh -c "wg-quick up wg0 && node agent2.js"
```

## 방법 2: VMware/VirtualBox

### VM별 설정:
- **VM1**: Windows/Linux → VPN1 (동글1)
- **VM2**: Windows/Linux → VPN2 (동글2)
- **VM3**: Windows/Linux → VPN3 (메인라인)

### 장점:
- 완전한 격리
- OS별 독립적인 네트워크 스택
- 각 VM이 다른 IP 대역 사용

## 방법 3: 프록시 체인 (VPN 없이)

서버에서 SOCKS5 프록시만 운영하고, 클라이언트는 프록시 연결:

```javascript
// Playwright with proxy
const browser = await chromium.launch({
  proxy: {
    server: 'socks5://222.101.90.78:1080', // 동글1 프록시
  }
});

// 또는 다른 에이전트
const browser2 = await chromium.launch({
  proxy: {
    server: 'socks5://222.101.90.78:1081', // 동글2 프록시
  }
});
```

## 방법 4: 브라우저 프로필 분리

```javascript
// 각 브라우저 컨텍스트에 다른 프록시
const context1 = await browser.newContext({
  proxy: { server: 'socks5://server:1080' }
});

const context2 = await browser.newContext({
  proxy: { server: 'socks5://server:1081' }
});
```

## 권장 아키텍처

### 서버 측:
```
WireGuard VPN 서버 (다중 포트)
  ├── 포트 51820 → 동글1 라우팅
  ├── 포트 51821 → 동글2 라우팅
  └── 포트 51822 → 메인라인 라우팅

SOCKS5 프록시 서버 (다중 포트)
  ├── 포트 1080 → 동글1 경유
  ├── 포트 1081 → 동글2 경유
  └── 포트 1082 → 메인라인 경유
```

### 클라이언트 측:
```
옵션 1: Docker 컨테이너별 VPN
옵션 2: VM별 VPN
옵션 3: SOCKS5 프록시만 사용 (VPN 없이)
```

## 최적 선택:

**개발/테스트**: Docker 컨테이너 + VPN
**프로덕션**: SOCKS5 프록시 (관리 간단)
**보안 중시**: VM + VPN (완전 격리)