# 하나의 클라이언트에서 다중 VPN 사용 방법

## 방법 1: SOCKS5 프록시로 간단하게

```javascript
// VPN 없이 SOCKS5로만 처리
const agents = [
    { proxy: 'socks5://222.101.90.78:1080' }, // 동글1
    { proxy: 'socks5://222.101.90.78:1081' }, // 동글2
    { proxy: 'socks5://222.101.90.78:1080' }, // 동글1 (재사용)
    { proxy: 'socks5://222.101.90.78:1081' }, // 동글2 (재사용)
];
```

## 방법 2: 네임스페이스로 VPN 분리

```bash
# 각 VPN을 다른 네임스페이스에서 실행
sudo ip netns add vpn1
sudo ip netns add vpn2

# 각 네임스페이스에서 VPN 연결
sudo ip netns exec vpn1 wg-quick up /etc/wireguard/agent1.conf
sudo ip netns exec vpn2 wg-quick up /etc/wireguard/agent2.conf

# Playwright를 각 네임스페이스에서 실행
sudo ip netns exec vpn1 node agent1.js &
sudo ip netns exec vpn2 node agent2.js &
```

## 방법 3: Docker 컨테이너 (가장 깔끔)

```yaml
# docker-compose.yml
version: '3'
services:
  agent1:
    image: mcr.microsoft.com/playwright:focal
    environment:
      - VPN_CONFIG=/etc/wireguard/wg0.conf
    volumes:
      - ./configs/agent1.conf:/etc/wireguard/wg0.conf
      - ./scripts:/app
    command: node /app/agent.js
    
  agent2:
    image: mcr.microsoft.com/playwright:focal  
    environment:
      - VPN_CONFIG=/etc/wireguard/wg0.conf
    volumes:
      - ./configs/agent2.conf:/etc/wireguard/wg0.conf
      - ./scripts:/app
    command: node /app/agent.js
```

## 결론: SOCKS5가 가장 간단

**하나의 클라이언트에서 4~6개 Playwright 실행 시:**

1. **SOCKS5 프록시** (✅ 추천)
   - 설정 간단
   - VPN 클라이언트 불필요
   - 각 Playwright가 다른 프록시 사용

2. **VPN 다중 연결**
   - 네임스페이스나 Docker 필요
   - 설정 복잡
   - 보안은 더 강화

현재 서버에 SOCKS5가 이미 설정되어 있으므로, 
**SOCKS5 프록시로 바로 사용 가능합니다!**