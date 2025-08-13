#!/usr/bin/env python3
"""
네트워크 게이트웨이 서버
- SOCKS5 프록시 상시 운영
- VPN Kill Switch (IP 노출 방지)
- 동글 IP 토글 관리
- 트래픽 모니터링
"""

import os
import json
import asyncio
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import socket
import struct

class NetworkGatewayServer:
    def __init__(self):
        self.config_file = "/home/proxy/gateway_config.json"
        self.log_file = "/home/proxy/gateway.log"
        self.dongles = {}
        self.vpn_clients = {}
        self.proxies = {}
        self.load_config()
        
    def log(self, message: str, level: str = "INFO"):
        """로깅"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
    
    def load_config(self):
        """설정 로드"""
        default_config = {
            "dongles": {
                "dongle1": {
                    "interface": "enp0s21f0u4",
                    "ip": "192.168.16.100",
                    "gateway": "192.168.16.1",
                    "socks_port": 1080,
                    "vpn_port": 51820,
                    "routing_table": 200,
                    "status": "active",
                    "ip_toggle_enabled": True,
                    "failover_dongle": "dongle2"
                },
                "dongle2": {
                    "interface": "enp0s21f0u3", 
                    "ip": "192.168.14.100",
                    "gateway": "192.168.14.1",
                    "socks_port": 1081,
                    "vpn_port": 51821,
                    "routing_table": 201,
                    "status": "active",
                    "ip_toggle_enabled": True,
                    "failover_dongle": "dongle1"
                }
            },
            "main_line": {
                "interface": "eno1",
                "ip": "222.101.90.78",
                "socks_port": 1082,
                "vpn_port": 51822,
                "routing_table": 202,
                "status": "active"
            },
            "kill_switch": {
                "enabled": True,
                "block_on_vpn_failure": True,
                "allowed_ips": ["10.0.0.0/8", "192.168.0.0/16"]
            },
            "monitoring": {
                "health_check_interval": 30,
                "traffic_logging": True,
                "alert_on_failure": True
            }
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """설정 저장"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_kill_switch(self):
        """Kill Switch 설정 - VPN 실패 시 트래픽 차단"""
        self.log("Kill Switch 설정 중...")
        
        # 기본 DROP 정책
        rules = [
            # 로컬 트래픽 허용
            "iptables -A FORWARD -s 10.0.0.0/8 -d 10.0.0.0/8 -j ACCEPT",
            "iptables -A FORWARD -s 192.168.0.0/16 -d 192.168.0.0/16 -j ACCEPT",
            
            # VPN 인터페이스 트래픽 허용
            "iptables -A FORWARD -i wg+ -j ACCEPT",
            "iptables -A FORWARD -o wg+ -j ACCEPT",
            
            # 동글 인터페이스가 활성화된 경우만 허용
            "iptables -A FORWARD -m mark --mark 0x100 -j ACCEPT",
            
            # 나머지는 DROP (Kill Switch)
            "iptables -A FORWARD -j DROP"
        ]
        
        for rule in rules:
            subprocess.run(rule.split(), check=False)
        
        self.log("Kill Switch 활성화됨")
    
    def start_socks5_proxy(self, name: str, config: dict):
        """SOCKS5 프록시 시작"""
        port = config['socks_port']
        interface_ip = config['ip']
        
        self.log(f"SOCKS5 프록시 시작: {name} (포트 {port})")
        
        # dante-server 설정 생성
        dante_config = f"""
logoutput: /var/log/dante_{name}.log
internal: 0.0.0.0 port = {port}
external: {interface_ip}

socksmethod: none
clientmethod: none

client pass {{
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error connect disconnect
}}

socks pass {{
    from: 0.0.0.0/0 to: 0.0.0.0/0
    protocol: tcp udp
    log: error connect disconnect
}}
"""
        
        config_file = f"/tmp/dante_{name}.conf"
        with open(config_file, 'w') as f:
            f.write(dante_config)
        
        # dante 서버 시작
        cmd = f"danted -f {config_file} -D"
        subprocess.Popen(cmd.split())
        
        self.proxies[name] = {
            'port': port,
            'pid': None,
            'status': 'running'
        }
        
        return True
    
    def toggle_dongle_ip(self, dongle_name: str):
        """동글 IP 토글"""
        if dongle_name not in self.config['dongles']:
            self.log(f"동글 {dongle_name}을 찾을 수 없음", "ERROR")
            return False
        
        dongle = self.config['dongles'][dongle_name]
        interface = dongle['interface']
        
        self.log(f"동글 {dongle_name} IP 토글 시작...")
        
        # 1. 현재 연결된 VPN 클라이언트 보호
        self.protect_vpn_clients(dongle_name)
        
        # 2. 동글 재연결 (IP 변경)
        self.reconnect_dongle(interface)
        
        # 3. 새 IP 확인 및 라우팅 업데이트
        time.sleep(5)  # IP 할당 대기
        new_ip = self.get_interface_ip(interface)
        
        if new_ip:
            dongle['ip'] = new_ip
            self.update_routing(dongle_name)
            self.log(f"동글 {dongle_name} 새 IP: {new_ip}")
            
            # 4. VPN 클라이언트 복구
            self.restore_vpn_clients(dongle_name)
            return True
        else:
            self.log(f"동글 {dongle_name} IP 할당 실패", "ERROR")
            # 페일오버 실행
            self.failover_dongle(dongle_name)
            return False
    
    def protect_vpn_clients(self, dongle_name: str):
        """VPN 클라이언트 보호 (IP 토글 중)"""
        # 임시로 페일오버 동글로 라우팅
        dongle = self.config['dongles'][dongle_name]
        failover = dongle.get('failover_dongle')
        
        if failover and failover in self.config['dongles']:
            failover_dongle = self.config['dongles'][failover]
            table_id = dongle['routing_table']
            
            # 라우팅 테이블 임시 변경
            cmd = f"ip route replace default via {failover_dongle['gateway']} dev {failover_dongle['interface']} table {table_id}"
            subprocess.run(cmd.split())
            
            self.log(f"VPN 클라이언트 임시 보호: {dongle_name} → {failover}")
    
    def restore_vpn_clients(self, dongle_name: str):
        """VPN 클라이언트 복구"""
        dongle = self.config['dongles'][dongle_name]
        table_id = dongle['routing_table']
        
        # 원래 라우팅으로 복구
        cmd = f"ip route replace default via {dongle['gateway']} dev {dongle['interface']} table {table_id}"
        subprocess.run(cmd.split())
        
        self.log(f"VPN 클라이언트 복구: {dongle_name}")
    
    def reconnect_dongle(self, interface: str):
        """동글 재연결 (IP 변경)"""
        # NetworkManager를 통한 재연결
        subprocess.run(['nmcli', 'device', 'disconnect', interface], check=False)
        time.sleep(2)
        subprocess.run(['nmcli', 'device', 'connect', interface], check=False)
    
    def get_interface_ip(self, interface: str) -> Optional[str]:
        """인터페이스 IP 조회"""
        try:
            result = subprocess.run(
                ['ip', 'addr', 'show', interface],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '192.168' in line:
                    return line.split()[1].split('/')[0]
        except:
            pass
        return None
    
    def update_routing(self, dongle_name: str):
        """라우팅 업데이트"""
        dongle = self.config['dongles'][dongle_name]
        table_id = dongle['routing_table']
        
        # 라우팅 테이블 업데이트
        cmds = [
            f"ip route flush table {table_id}",
            f"ip route add default via {dongle['gateway']} dev {dongle['interface']} table {table_id}",
            f"ip route add 192.168.0.0/16 dev {dongle['interface']} table {table_id}"
        ]
        
        for cmd in cmds:
            subprocess.run(cmd.split(), check=False)
    
    def failover_dongle(self, failed_dongle: str):
        """동글 페일오버"""
        dongle = self.config['dongles'][failed_dongle]
        failover = dongle.get('failover_dongle')
        
        if failover and failover in self.config['dongles']:
            self.log(f"페일오버 실행: {failed_dongle} → {failover}")
            
            # VPN 트래픽을 백업 동글로 라우팅
            failover_dongle = self.config['dongles'][failover]
            table_id = dongle['routing_table']
            
            cmd = f"ip route replace default via {failover_dongle['gateway']} dev {failover_dongle['interface']} table {table_id}"
            subprocess.run(cmd.split())
            
            dongle['status'] = 'failed'
            failover_dongle['status'] = 'primary'
            self.save_config()
    
    async def health_check_loop(self):
        """헬스체크 루프"""
        while True:
            await asyncio.sleep(self.config['monitoring']['health_check_interval'])
            
            # 동글 상태 확인
            for name, dongle in self.config['dongles'].items():
                if self.check_dongle_health(dongle['interface']):
                    if dongle['status'] == 'failed':
                        self.log(f"동글 {name} 복구됨")
                        dongle['status'] = 'active'
                else:
                    if dongle['status'] == 'active':
                        self.log(f"동글 {name} 실패 감지", "WARNING")
                        self.failover_dongle(name)
    
    def check_dongle_health(self, interface: str) -> bool:
        """동글 헬스체크"""
        ip = self.get_interface_ip(interface)
        if not ip:
            return False
        
        # ping 테스트
        result = subprocess.run(
            ['ping', '-I', ip, '-c', '1', '-W', '2', '8.8.8.8'],
            capture_output=True
        )
        return result.returncode == 0
    
    def start(self):
        """서버 시작"""
        self.log("네트워크 게이트웨이 서버 시작...")
        
        # 1. Kill Switch 설정
        if self.config['kill_switch']['enabled']:
            self.setup_kill_switch()
        
        # 2. SOCKS5 프록시 시작
        for name, dongle in self.config['dongles'].items():
            if dongle['status'] == 'active':
                self.start_socks5_proxy(name, dongle)
        
        # 메인라인 프록시
        self.start_socks5_proxy('mainline', self.config['main_line'])
        
        # 3. 헬스체크 시작
        asyncio.create_task(self.health_check_loop())
        
        self.log("서버 준비 완료")
        self.log(f"SOCKS5 프록시 포트:")
        self.log(f"  - 동글1: 1080")
        self.log(f"  - 동글2: 1081")
        self.log(f"  - 메인라인: 1082")
        self.log(f"VPN 포트:")
        self.log(f"  - 동글1: 51820")
        self.log(f"  - 동글2: 51821")
        self.log(f"  - 메인라인: 51822")

def main():
    server = NetworkGatewayServer()
    server.start()
    
    # 이벤트 루프 실행
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        server.log("서버 종료")

if __name__ == "__main__":
    main()