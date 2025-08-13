#!/usr/bin/env python3
"""
VPN 인증 관리 시스템
- 동적 클라이언트 관리
- 임시 액세스 토큰
- 자동 만료
- QR 코드 생성
"""

import os
import json
import secrets
import subprocess
import qrcode
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import base64

class VPNAuthManager:
    def __init__(self):
        self.config_file = "/home/proxy/vpn_clients.json"
        self.clients = self.load_clients()
        
    def load_clients(self):
        """클라이언트 정보 로드"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_clients(self):
        """클라이언트 정보 저장"""
        with open(self.config_file, 'w') as f:
            json.dump(self.clients, f, indent=2)
    
    # ===== 방법 1: 사전 등록 키 (영구) =====
    def register_permanent_client(self, client_name: str, public_key: str, 
                                 allowed_ips: str = None, vpn_port: int = 51820):
        """영구 클라이언트 등록"""
        client_id = hashlib.sha256(public_key.encode()).hexdigest()[:8]
        
        # 자동 IP 할당
        if not allowed_ips:
            used_ips = [c['allowed_ips'] for c in self.clients.values()]
            for i in range(2, 255):
                test_ip = f"10.0.0.{i}/32"
                if test_ip not in used_ips:
                    allowed_ips = test_ip
                    break
        
        self.clients[client_id] = {
            'name': client_name,
            'public_key': public_key,
            'allowed_ips': allowed_ips,
            'vpn_port': vpn_port,
            'type': 'permanent',
            'created': datetime.now().isoformat(),
            'last_seen': None,
            'status': 'active'
        }
        
        # WireGuard에 추가
        self.add_to_wireguard(client_id)
        self.save_clients()
        
        print(f"✅ 영구 클라이언트 등록: {client_name} ({allowed_ips})")
        return client_id
    
    # ===== 방법 2: 임시 액세스 토큰 =====
    def create_temp_access(self, duration_hours: int = 24, vpn_port: int = 51820):
        """임시 액세스 생성"""
        # 임시 키 생성
        private_key = subprocess.run(['wg', 'genkey'], 
                                    capture_output=True, text=True).stdout.strip()
        public_key = subprocess.run(['wg', 'pubkey'], input=private_key,
                                   capture_output=True, text=True).stdout.strip()
        
        # 액세스 토큰 생성
        token = secrets.token_urlsafe(32)
        client_id = hashlib.sha256(token.encode()).hexdigest()[:8]
        
        # IP 자동 할당
        allowed_ips = self.get_next_available_ip()
        
        expires = datetime.now() + timedelta(hours=duration_hours)
        
        self.clients[client_id] = {
            'name': f'temp_{client_id}',
            'public_key': public_key,
            'private_key': private_key,  # 임시 클라이언트는 서버가 키 관리
            'allowed_ips': allowed_ips,
            'vpn_port': vpn_port,
            'type': 'temporary',
            'token': token,
            'created': datetime.now().isoformat(),
            'expires': expires.isoformat(),
            'status': 'active'
        }
        
        # WireGuard에 추가
        self.add_to_wireguard(client_id)
        self.save_clients()
        
        # 클라이언트 설정 생성
        config = self.generate_client_config(client_id)
        
        print(f"✅ 임시 액세스 생성 ({duration_hours}시간)")
        print(f"   토큰: {token}")
        print(f"   만료: {expires}")
        
        return token, config
    
    # ===== 방법 3: 동적 등록 (REST API) =====
    def dynamic_register(self, auth_token: str, device_id: str):
        """동적 클라이언트 등록 (API 인증)"""
        # 토큰 검증 (실제로는 DB나 OAuth 연동)
        if not self.verify_auth_token(auth_token):
            return None, "Invalid auth token"
        
        # 디바이스별 고유 키 생성
        client_id = hashlib.sha256(f"{device_id}{auth_token}".encode()).hexdigest()[:8]
        
        # 이미 등록된 경우 정보 반환
        if client_id in self.clients:
            return client_id, self.clients[client_id]
        
        # 새 키 생성
        private_key = subprocess.run(['wg', 'genkey'], 
                                    capture_output=True, text=True).stdout.strip()
        public_key = subprocess.run(['wg', 'pubkey'], input=private_key,
                                   capture_output=True, text=True).stdout.strip()
        
        allowed_ips = self.get_next_available_ip()
        
        self.clients[client_id] = {
            'name': f'device_{device_id}',
            'public_key': public_key,
            'allowed_ips': allowed_ips,
            'vpn_port': 51820,
            'type': 'dynamic',
            'device_id': device_id,
            'created': datetime.now().isoformat(),
            'status': 'active'
        }
        
        self.add_to_wireguard(client_id)
        self.save_clients()
        
        # 클라이언트 설정 반환
        config = {
            'private_key': private_key,
            'address': allowed_ips,
            'server_public_key': self.get_server_public_key(),
            'endpoint': '222.101.90.78:51820'
        }
        
        return client_id, config
    
    # ===== 방법 4: QR 코드 원타임 등록 =====
    def generate_qr_access(self, name: str = "QR Client"):
        """QR 코드로 원타임 액세스 생성"""
        token, config = self.create_temp_access(duration_hours=2)
        
        # QR 코드 생성
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(config)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = f"/home/proxy/qr_{token[:8]}.png"
        img.save(qr_path)
        
        print(f"✅ QR 코드 생성: {qr_path}")
        return qr_path, config
    
    # ===== 방법 5: 시간 기반 액세스 =====
    def create_scheduled_access(self, start_time: datetime, end_time: datetime):
        """특정 시간대만 사용 가능한 액세스"""
        client_id = secrets.token_hex(4)
        
        private_key = subprocess.run(['wg', 'genkey'], 
                                    capture_output=True, text=True).stdout.strip()
        public_key = subprocess.run(['wg', 'pubkey'], input=private_key,
                                   capture_output=True, text=True).stdout.strip()
        
        self.clients[client_id] = {
            'name': f'scheduled_{client_id}',
            'public_key': public_key,
            'private_key': private_key,
            'allowed_ips': self.get_next_available_ip(),
            'vpn_port': 51820,
            'type': 'scheduled',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'status': 'pending'
        }
        
        self.save_clients()
        print(f"✅ 예약 액세스 생성: {start_time} ~ {end_time}")
        return client_id
    
    # ===== 유틸리티 함수 =====
    def get_next_available_ip(self):
        """사용 가능한 다음 IP 반환"""
        used_ips = [c['allowed_ips'].split('/')[0] for c in self.clients.values()]
        for i in range(2, 255):
            test_ip = f"10.0.0.{i}"
            if test_ip not in used_ips:
                return f"{test_ip}/32"
        raise Exception("No available IPs")
    
    def add_to_wireguard(self, client_id: str):
        """WireGuard에 클라이언트 추가"""
        client = self.clients[client_id]
        vpn_interface = f"wg{client['vpn_port'] - 51820}"  # wg0, wg1, wg2...
        
        cmd = f"wg set {vpn_interface} peer {client['public_key']} allowed-ips {client['allowed_ips']}"
        subprocess.run(cmd.split(), check=True)
        
        # 설정 저장
        subprocess.run(['wg-quick', 'save', vpn_interface])
    
    def remove_from_wireguard(self, client_id: str):
        """WireGuard에서 클라이언트 제거"""
        client = self.clients[client_id]
        vpn_interface = f"wg{client['vpn_port'] - 51820}"
        
        cmd = f"wg set {vpn_interface} peer {client['public_key']} remove"
        subprocess.run(cmd.split(), check=True)
    
    def cleanup_expired(self):
        """만료된 클라이언트 정리"""
        now = datetime.now()
        expired = []
        
        for client_id, client in self.clients.items():
            if client['type'] == 'temporary':
                expires = datetime.fromisoformat(client['expires'])
                if now > expires:
                    expired.append(client_id)
            elif client['type'] == 'scheduled':
                end_time = datetime.fromisoformat(client['end_time'])
                if now > end_time:
                    expired.append(client_id)
        
        for client_id in expired:
            self.remove_from_wireguard(client_id)
            del self.clients[client_id]
            print(f"🗑️ 만료된 클라이언트 제거: {client_id}")
        
        if expired:
            self.save_clients()
    
    def generate_client_config(self, client_id: str):
        """클라이언트 설정 생성"""
        client = self.clients[client_id]
        
        config = f"""[Interface]
PrivateKey = {client.get('private_key', 'YOUR_PRIVATE_KEY')}
Address = {client['allowed_ips']}
DNS = 8.8.8.8

[Peer]
PublicKey = {self.get_server_public_key()}
Endpoint = 222.101.90.78:{client['vpn_port']}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25"""
        
        return config
    
    def get_server_public_key(self):
        """서버 공개키 조회"""
        result = subprocess.run(['wg', 'show', 'wg0', 'public-key'],
                              capture_output=True, text=True)
        return result.stdout.strip()
    
    def verify_auth_token(self, token: str) -> bool:
        """인증 토큰 검증 (실제로는 DB나 OAuth 연동)"""
        # 예시: 간단한 토큰 검증
        valid_tokens = ['master_token_123', 'api_key_456']
        return token in valid_tokens

# ===== REST API 서버 =====
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
auth_manager = VPNAuthManager()

@app.route('/api/vpn/register', methods=['POST'])
def api_register():
    """동적 VPN 등록 API"""
    data = request.json
    auth_token = data.get('auth_token')
    device_id = data.get('device_id')
    
    client_id, config = auth_manager.dynamic_register(auth_token, device_id)
    
    if client_id:
        return jsonify({
            'success': True,
            'client_id': client_id,
            'config': config
        })
    else:
        return jsonify({
            'success': False,
            'error': config
        }), 401

@app.route('/api/vpn/temp', methods=['POST'])
def api_temp_access():
    """임시 액세스 생성 API"""
    data = request.json
    hours = data.get('hours', 24)
    
    token, config = auth_manager.create_temp_access(hours)
    
    return jsonify({
        'success': True,
        'token': token,
        'config': config
    })

def cleanup_loop():
    """백그라운드 정리 작업"""
    import time
    while True:
        time.sleep(300)  # 5분마다
        auth_manager.cleanup_expired()

def main():
    print("=== VPN 인증 관리 시스템 ===")
    print("1. 영구 클라이언트 등록")
    print("2. 임시 액세스 생성 (24시간)")
    print("3. QR 코드 액세스 생성")
    print("4. API 서버 시작")
    
    # 백그라운드 정리 작업 시작
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    
    # 예시 실행
    manager = VPNAuthManager()
    
    # 임시 액세스 생성 예시
    token, config = manager.create_temp_access(24)
    print(f"\n임시 설정:\n{config}")

if __name__ == "__main__":
    main()