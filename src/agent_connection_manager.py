#!/usr/bin/env python3
"""
동적 에이전트 연결 관리 시스템
- 4~6개 에이전트 동시 접속 관리
- 자동 부하 분산
- 연결 상태 모니터링
"""

import os
import json
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import threading

class AgentConnectionManager:
    def __init__(self):
        self.config_file = "/home/proxy/agent_connections.json"
        self.agents = {}
        self.vpn_interfaces = [
            {"interface": "wg0", "port": 51820, "subnet": "10.0.0", "dongle": "enp0s21f0u4"},
            {"interface": "wg1", "port": 51821, "subnet": "10.0.1", "dongle": "enp0s21f0u3"},
            {"interface": "wg2", "port": 51822, "subnet": "10.0.2", "dongle": "enp0s21f0u4"},
            {"interface": "wg3", "port": 51823, "subnet": "10.0.3", "dongle": "enp0s21f0u3"},
            {"interface": "wg4", "port": 51824, "subnet": "10.0.4", "dongle": "enp0s21f0u4"},
            {"interface": "wg5", "port": 51825, "subnet": "10.0.5", "dongle": "enp0s21f0u3"},
        ]
        self.load_agents()
        
    def load_agents(self):
        """에이전트 정보 로드"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.agents = json.load(f)
        else:
            self.agents = {}
    
    def save_agents(self):
        """에이전트 정보 저장"""
        with open(self.config_file, 'w') as f:
            json.dump(self.agents, f, indent=2)
    
    def assign_agent(self, agent_id: str, agent_name: str = None) -> Dict:
        """새 에이전트에 VPN 인터페이스 자동 할당"""
        
        # 사용 가능한 인터페이스 찾기
        used_interfaces = [agent['interface'] for agent in self.agents.values()]
        available = None
        
        for vpn in self.vpn_interfaces:
            if vpn['interface'] not in used_interfaces:
                available = vpn
                break
        
        if not available:
            # 가장 오래된 비활성 에이전트 제거
            self.cleanup_inactive_agents()
            return self.assign_agent(agent_id, agent_name)  # 재시도
        
        # 키 생성
        private_key = subprocess.run(['wg', 'genkey'], 
                                    capture_output=True, text=True).stdout.strip()
        public_key = subprocess.run(['wg', 'pubkey'], input=private_key,
                                   capture_output=True, text=True).stdout.strip()
        
        # IP 할당
        next_ip = self.get_next_ip(available['subnet'])
        
        # 에이전트 등록
        self.agents[agent_id] = {
            'name': agent_name or f'agent_{agent_id[:8]}',
            'interface': available['interface'],
            'port': available['port'],
            'public_key': public_key,
            'private_key': private_key,
            'ip_address': f"{next_ip}/32",
            'dongle': available['dongle'],
            'created': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'status': 'active',
            'traffic': {'rx': 0, 'tx': 0}
        }
        
        # WireGuard에 피어 추가
        self.add_peer_to_wireguard(agent_id)
        self.save_agents()
        
        # 클라이언트 설정 생성
        config = self.generate_agent_config(agent_id)
        
        print(f"✅ 에이전트 {agent_name} 할당됨:")
        print(f"   인터페이스: {available['interface']}")
        print(f"   포트: {available['port']}")
        print(f"   IP: {next_ip}")
        print(f"   동글: {available['dongle']}")
        
        return {
            'agent_id': agent_id,
            'config': config,
            'connection_info': {
                'server': '222.101.90.78',
                'port': available['port'],
                'ip': next_ip
            }
        }
    
    def get_next_ip(self, subnet: str) -> str:
        """서브넷에서 다음 사용 가능한 IP 찾기"""
        used_ips = []
        for agent in self.agents.values():
            if agent['ip_address'].startswith(subnet):
                used_ips.append(int(agent['ip_address'].split('.')[3].split('/')[0]))
        
        for i in range(2, 254):
            if i not in used_ips:
                return f"{subnet}.{i}"
        
        raise Exception(f"No available IPs in subnet {subnet}")
    
    def add_peer_to_wireguard(self, agent_id: str):
        """WireGuard에 피어 추가"""
        agent = self.agents[agent_id]
        cmd = f"wg set {agent['interface']} peer {agent['public_key']} allowed-ips {agent['ip_address']}"
        subprocess.run(cmd.split(), check=True)
    
    def remove_peer_from_wireguard(self, agent_id: str):
        """WireGuard에서 피어 제거"""
        agent = self.agents[agent_id]
        cmd = f"wg set {agent['interface']} peer {agent['public_key']} remove"
        subprocess.run(cmd.split(), check=True)
    
    def generate_agent_config(self, agent_id: str) -> str:
        """에이전트용 WireGuard 설정 생성"""
        agent = self.agents[agent_id]
        
        # 서버 공개키 가져오기
        result = subprocess.run(['wg', 'show', agent['interface'], 'public-key'],
                              capture_output=True, text=True)
        server_public_key = result.stdout.strip()
        
        config = f"""[Interface]
PrivateKey = {agent['private_key']}
Address = {agent['ip_address']}
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
Endpoint = 222.101.90.78:{agent['port']}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25"""
        
        return config
    
    def get_agent_status(self, agent_id: str) -> Dict:
        """에이전트 상태 조회"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        
        # WireGuard 통계 조회
        result = subprocess.run(['wg', 'show', agent['interface'], 'dump'],
                              capture_output=True, text=True)
        
        for line in result.stdout.split('\n'):
            parts = line.split('\t')
            if len(parts) > 3 and parts[0] == agent['public_key']:
                agent['last_handshake'] = parts[4] if parts[4] != '0' else 'Never'
                agent['traffic']['rx'] = int(parts[5])
                agent['traffic']['tx'] = int(parts[6])
                break
        
        return agent
    
    def monitor_agents(self):
        """에이전트 상태 모니터링"""
        print("\n=== 에이전트 상태 ===")
        print(f"{'ID':<15} {'이름':<15} {'인터페이스':<10} {'IP':<15} {'상태':<10} {'RX(MB)':<10} {'TX(MB)':<10}")
        print("-" * 95)
        
        for agent_id, agent in self.agents.items():
            status = self.get_agent_status(agent_id)
            if status:
                rx_mb = status['traffic']['rx'] / (1024*1024)
                tx_mb = status['traffic']['tx'] / (1024*1024)
                print(f"{agent_id[:12]:<15} {status['name']:<15} {status['interface']:<10} "
                      f"{status['ip_address']:<15} {status['status']:<10} "
                      f"{rx_mb:<10.2f} {tx_mb:<10.2f}")
    
    def cleanup_inactive_agents(self, threshold_minutes: int = 30):
        """비활성 에이전트 정리"""
        now = datetime.now()
        to_remove = []
        
        for agent_id, agent in self.agents.items():
            last_seen = datetime.fromisoformat(agent['last_seen'])
            if (now - last_seen).total_seconds() > threshold_minutes * 60:
                to_remove.append(agent_id)
        
        for agent_id in to_remove:
            print(f"🗑️ 비활성 에이전트 제거: {agent_id}")
            self.remove_peer_from_wireguard(agent_id)
            del self.agents[agent_id]
        
        if to_remove:
            self.save_agents()
    
    def get_load_balance_info(self) -> Dict:
        """부하 분산 정보 조회"""
        dongle_load = {}
        
        for agent in self.agents.values():
            dongle = agent['dongle']
            if dongle not in dongle_load:
                dongle_load[dongle] = {'count': 0, 'traffic': 0}
            
            dongle_load[dongle]['count'] += 1
            dongle_load[dongle]['traffic'] += agent['traffic']['rx'] + agent['traffic']['tx']
        
        return dongle_load

def main():
    manager = AgentConnectionManager()
    
    print("=== 에이전트 연결 관리자 ===")
    print("명령어:")
    print("  add <agent_id> <name> - 새 에이전트 추가")
    print("  status - 모든 에이전트 상태")
    print("  load - 부하 분산 정보")
    print("  cleanup - 비활성 에이전트 정리")
    print("  monitor - 실시간 모니터링")
    
    # 테스트용 에이전트 추가
    test_id = hashlib.sha256(f"test_{time.time()}".encode()).hexdigest()[:16]
    result = manager.assign_agent(test_id, "TestAgent1")
    print(f"\n테스트 에이전트 설정:\n{result['config']}")
    
    # 상태 확인
    manager.monitor_agents()
    
    # 부하 분산 정보
    load_info = manager.get_load_balance_info()
    print("\n=== 부하 분산 상태 ===")
    for dongle, info in load_info.items():
        print(f"{dongle}: {info['count']}개 에이전트, {info['traffic']/(1024*1024):.2f} MB 트래픽")

if __name__ == "__main__":
    main()