#!/usr/bin/env python3
"""
다중 에이전트 VPN + 프록시 시스템
각 에이전트는 독립적인 VPN과 SOCKS5 프록시를 가짐
"""

import os
import json
import subprocess
from datetime import datetime

class MultiAgentVPNProxy:
    def __init__(self):
        self.config_file = "/home/proxy/agent_vpn_config.json"
        self.agents = []
        self.load_config()
    
    def load_config(self):
        """기존 설정 로드 또는 초기화"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.agents = json.load(f)
        else:
            # 기본 설정
            self.agents = [
                {
                    "id": "agent1",
                    "vpn_port": 51820,
                    "vpn_subnet": "10.0.0.0/24",
                    "vpn_ip": "10.0.0.1",
                    "interface": "enp0s21f0u4",
                    "interface_ip": "192.168.16.100",
                    "socks_port": 1080,
                    "routing_table": 200,
                    "status": "active"
                },
                {
                    "id": "agent2", 
                    "vpn_port": 51821,
                    "vpn_subnet": "10.1.0.0/24",
                    "vpn_ip": "10.1.0.1",
                    "interface": "enp0s21f0u3",
                    "interface_ip": "192.168.14.100",
                    "socks_port": 1081,
                    "routing_table": 201,
                    "status": "ready"
                },
                {
                    "id": "agent3",
                    "vpn_port": 51822,
                    "vpn_subnet": "10.2.0.0/24", 
                    "vpn_ip": "10.2.0.1",
                    "interface": "eno1",
                    "interface_ip": "222.101.90.78",
                    "socks_port": 1082,
                    "routing_table": 202,
                    "status": "ready"
                }
            ]
            self.save_config()
    
    def save_config(self):
        """설정 저장"""
        with open(self.config_file, 'w') as f:
            json.dump(self.agents, f, indent=2)
    
    def generate_vpn_config(self, agent):
        """에이전트별 VPN 설정 생성"""
        config = f"""[Interface]
# {agent['id']} VPN 서버
Address = {agent['vpn_ip']}/24
ListenPort = {agent['vpn_port']}
PrivateKey = PRIVATE_KEY_{agent['id'].upper()}

# 라우팅 설정
Table = {agent['routing_table']}
PostUp = ip rule add from {agent['vpn_subnet']} lookup {agent['routing_table']} priority {100 + agent['routing_table']}
PostUp = ip route add default via {agent['interface_ip'].rsplit('.', 1)[0]}.1 dev {agent['interface']} table {agent['routing_table']}
PostUp = echo 1 > /proc/sys/net/ipv4/ip_forward
PostUp = iptables -A FORWARD -i %i -j ACCEPT
PostUp = iptables -A FORWARD -o %i -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -s {agent['vpn_subnet']} -o {agent['interface']} -j MASQUERADE
PostUp = iptables -A INPUT -i %i -j ACCEPT

PreDown = ip rule del from {agent['vpn_subnet']} lookup {agent['routing_table']} priority {100 + agent['routing_table']}
PreDown = iptables -D FORWARD -i %i -j ACCEPT
PreDown = iptables -D FORWARD -o %i -j ACCEPT
PreDown = iptables -t nat -D POSTROUTING -s {agent['vpn_subnet']} -o {agent['interface']} -j MASQUERADE
PreDown = iptables -D INPUT -i %i -j ACCEPT

# 클라이언트는 추후 추가
"""
        return config
    
    def setup_agent_vpn(self, agent_id):
        """특정 에이전트의 VPN 설정"""
        agent = next((a for a in self.agents if a['id'] == agent_id), None)
        if not agent:
            print(f"❌ 에이전트 {agent_id}를 찾을 수 없습니다")
            return False
        
        print(f"설정 중: {agent['id']}")
        print(f"  - VPN 포트: {agent['vpn_port']}")
        print(f"  - 출구 인터페이스: {agent['interface']} ({agent['interface_ip']})")
        print(f"  - SOCKS5 프록시 포트: {agent['socks_port']}")
        
        # VPN 설정 파일 생성
        config_file = f"/etc/wireguard/wg-{agent['id']}.conf"
        config = self.generate_vpn_config(agent)
        
        # 개인키 생성
        private_key = subprocess.run(['wg', 'genkey'], capture_output=True, text=True).stdout.strip()
        public_key = subprocess.run(['wg', 'pubkey'], input=private_key, capture_output=True, text=True).stdout.strip()
        
        config = config.replace(f"PRIVATE_KEY_{agent['id'].upper()}", private_key)
        
        # 설정 저장
        with open(f"/tmp/wg-{agent['id']}.conf", 'w') as f:
            f.write(config)
        
        subprocess.run(['sudo', 'mv', f"/tmp/wg-{agent['id']}.conf", config_file])
        
        print(f"  - 공개키: {public_key}")
        
        # 라우팅 테이블 추가
        rt_tables = "/etc/iproute2/rt_tables"
        table_entry = f"{agent['routing_table']} {agent['id']}_route\n"
        
        with open(rt_tables, 'r') as f:
            if table_entry not in f.read():
                subprocess.run(['sudo', 'bash', '-c', f'echo "{table_entry}" >> {rt_tables}'])
        
        agent['public_key'] = public_key
        agent['status'] = 'configured'
        self.save_config()
        
        return True
    
    def start_socks_proxy(self, agent_id):
        """SOCKS5 프록시 시작"""
        agent = next((a for a in self.agents if a['id'] == agent_id), None)
        if not agent:
            return False
        
        # SSH 동적 포트 포워딩을 사용한 SOCKS5 프록시
        # 또는 dante-server, microsocks 등 사용 가능
        print(f"SOCKS5 프록시 시작: 포트 {agent['socks_port']}")
        
        # 예: microsocks 사용
        cmd = f"microsocks -i {agent['interface_ip']} -p {agent['socks_port']}"
        # subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return True
    
    def status(self):
        """전체 시스템 상태"""
        print("\n=== 다중 에이전트 VPN/프록시 상태 ===")
        for agent in self.agents:
            print(f"\n{agent['id']}:")
            print(f"  VPN: {agent['vpn_port']} → {agent['interface']} ({agent['interface_ip']})")
            print(f"  SOCKS5: localhost:{agent['socks_port']}")
            print(f"  상태: {agent['status']}")
            
            # 실제 연결 확인
            try:
                result = subprocess.run(['wg', 'show', f"wg-{agent['id']}"], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    print(f"  ✅ VPN 활성")
                else:
                    print(f"  ⭕ VPN 비활성")
            except:
                print(f"  ⭕ VPN 미설정")

def main():
    manager = MultiAgentVPNProxy()
    
    print("=== 다중 에이전트 VPN/프록시 관리자 ===")
    print("1. 전체 상태 보기")
    print("2. 에이전트 VPN 설정")
    print("3. SOCKS5 프록시 시작")
    print("4. 자동 설정 (모든 에이전트)")
    
    manager.status()
    
    # 자동 설정 예시
    print("\n모든 에이전트 설정을 시작하시겠습니까? (y/n)")
    
if __name__ == "__main__":
    main()