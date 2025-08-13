#!/usr/bin/env python3
"""
동글 IP 토글 API 서버
WireGuard 클라이언트의 IP 할당을 동적으로 관리
"""

from flask import Flask, request, jsonify
import subprocess
import json
import os
import socket
import threading
import time
from datetime import datetime

app = Flask(__name__)

# 설정
WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"
CLIENT_DATA_FILE = "/home/proxy/clients.json"
BASE_IP = "10.0.0"
START_IP = 10  # 10.0.0.10부터 시작

class WireGuardManager:
    def __init__(self):
        self.clients = self.load_clients()
    
    def load_clients(self):
        """클라이언트 정보 로드"""
        if os.path.exists(CLIENT_DATA_FILE):
            with open(CLIENT_DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def save_clients(self):
        """클라이언트 정보 저장"""
        with open(CLIENT_DATA_FILE, 'w') as f:
            json.dump(self.clients, f, indent=2)
    
    def get_next_available_ip(self):
        """사용 가능한 다음 IP 주소 반환"""
        used_ips = set()
        for client in self.clients.values():
            if 'ip' in client:
                ip_num = int(client['ip'].split('.')[-1])
                used_ips.add(ip_num)
        
        for i in range(START_IP, 255):
            if i not in used_ips:
                return f"{BASE_IP}.{i}"
        
        raise Exception("사용 가능한 IP가 없습니다")
    
    def add_client(self, client_id, public_key):
        """새 클라이언트 추가"""
        ip = self.get_next_available_ip()
        
        self.clients[client_id] = {
            'public_key': public_key,
            'ip': ip,
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'last_toggle': datetime.now().isoformat()
        }
        
        self.save_clients()
        self.update_wireguard_config()
        return ip
    
    def toggle_client_ip(self, client_id):
        """클라이언트 IP 토글"""
        if client_id not in self.clients:
            return None, "클라이언트를 찾을 수 없습니다"
        
        client = self.clients[client_id]
        
        if client['status'] == 'active':
            # IP 비활성화
            client['status'] = 'inactive'
            client['old_ip'] = client['ip']
            client['ip'] = None
        else:
            # 새 IP 할당
            new_ip = self.get_next_available_ip()
            client['status'] = 'active'
            client['ip'] = new_ip
        
        client['last_toggle'] = datetime.now().isoformat()
        self.save_clients()
        self.update_wireguard_config()
        
        return client['ip'], f"클라이언트 {client_id} IP 토글 완료"
    
    def update_wireguard_config(self):
        """WireGuard 설정 파일 업데이트"""
        try:
            # 기본 인터페이스 설정 읽기
            with open(WG_CONFIG_PATH, 'r') as f:
                lines = f.readlines()
            
            # [Interface] 섹션만 유지
            interface_lines = []
            in_interface = False
            
            for line in lines:
                if line.strip().startswith('[Interface]'):
                    in_interface = True
                elif line.strip().startswith('[Peer]'):
                    break
                
                if in_interface:
                    interface_lines.append(line)
            
            # 활성 클라이언트 Peer 섹션 추가
            peer_sections = []
            for client_id, client in self.clients.items():
                if client['status'] == 'active' and client.get('ip'):
                    peer_sections.extend([
                        f"\n# 클라이언트: {client_id}\n",
                        "[Peer]\n",
                        f"PublicKey = {client['public_key']}\n",
                        f"AllowedIPs = {client['ip']}/32\n"
                    ])
            
            # 파일 쓰기
            with open(WG_CONFIG_PATH, 'w') as f:
                f.writelines(interface_lines)
                f.writelines(peer_sections)
            
            # WireGuard 재시작
            subprocess.run(['sudo', 'systemctl', 'restart', 'wg-quick@wg0'], check=True)
            return True
            
        except Exception as e:
            print(f"WireGuard 설정 업데이트 실패: {e}")
            return False

# WireGuard 매니저 인스턴스
wg_manager = WireGuardManager()

@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """모든 클라이언트 목록 조회"""
    return jsonify(wg_manager.clients)

@app.route('/api/clients/<client_id>/toggle', methods=['POST'])
def toggle_client(client_id):
    """클라이언트 IP 토글"""
    try:
        new_ip, message = wg_manager.toggle_client_ip(client_id)
        return jsonify({
            'success': True,
            'client_id': client_id,
            'new_ip': new_ip,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/clients/<client_id>', methods=['POST'])
def add_client(client_id):
    """새 클라이언트 추가"""
    try:
        data = request.get_json()
        if not data or 'public_key' not in data:
            return jsonify({'error': 'public_key가 필요합니다'}), 400
        
        ip = wg_manager.add_client(client_id, data['public_key'])
        return jsonify({
            'success': True,
            'client_id': client_id,
            'assigned_ip': ip,
            'message': f'클라이언트 {client_id} 추가 완료',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/wireguard/status', methods=['GET'])
def wireguard_status():
    """WireGuard 상태 조회"""
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True)
        return jsonify({
            'success': True,
            'status': result.stdout,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("동글 IP 토글 API 서버 시작...")
    print(f"클라이언트 데이터: {CLIENT_DATA_FILE}")
    print(f"WireGuard 설정: {WG_CONFIG_PATH}")
    app.run(host='0.0.0.0', port=5000, debug=True)