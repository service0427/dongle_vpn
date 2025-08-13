#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/proxy')
from vpn_auth_manager import VPNAuthManager
from datetime import datetime, timedelta

def test_auth_methods():
    print("=== VPN 인증 관리 시스템 테스트 ===")
    manager = VPNAuthManager()
    
    # 1. 임시 액세스 테스트 (2시간)
    print("\n1. 임시 액세스 생성 (2시간):")
    token, config = manager.create_temp_access(duration_hours=2)
    print(f"   토큰: {token[:20]}...")
    print(f"   설정 생성됨")
    
    # 2. QR 코드 액세스
    print("\n2. QR 코드 액세스 생성:")
    qr_path, qr_config = manager.generate_qr_access("Test Client")
    print(f"   QR 코드: {qr_path}")
    
    # 3. 예약 액세스
    print("\n3. 예약 액세스 생성 (내일 오전 9시-오후 6시):")
    tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
    tomorrow_6pm = tomorrow_9am.replace(hour=18)
    client_id = manager.create_scheduled_access(tomorrow_9am, tomorrow_6pm)
    print(f"   클라이언트 ID: {client_id}")
    
    # 4. 현재 클라이언트 상태
    print("\n4. 등록된 클라이언트:")
    for cid, client in manager.clients.items():
        print(f"   - {client['name']}: {client['type']} ({client['status']})")
        if client['type'] == 'temporary':
            print(f"     만료: {client['expires']}")
    
    # 5. 만료된 클라이언트 정리
    print("\n5. 만료 클라이언트 정리:")
    manager.cleanup_expired()
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_auth_methods()