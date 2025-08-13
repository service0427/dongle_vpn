#!/usr/bin/env python3
"""
동글 모바일 연결 활성화 스크립트
"""

import requests
import xml.etree.ElementTree as ET
import time
import json
from datetime import datetime

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def get_session_info():
    """세션 정보 획득"""
    try:
        response = requests.get("http://192.168.16.1/api/webserver/SesTokInfo", timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            session_id = root.find('SesInfo').text
            token = root.find('TokInfo').text
            log(f"세션 정보 획득 완료")
            return session_id, token
        else:
            log(f"세션 정보 획득 실패: {response.status_code}")
            return None, None
    except Exception as e:
        log(f"세션 정보 오류: {e}")
        return None, None

def get_connection_status(session_id, token):
    """현재 연결 상태 확인"""
    try:
        headers = {
            'Cookie': f'SessionID={session_id}',
            '__RequestVerificationToken': token
        }
        
        response = requests.get("http://192.168.16.1/api/monitoring/status", 
                              headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            connection_status = root.find('ConnectionStatus')
            current_network_type = root.find('CurrentNetworkType')
            signal_strength = root.find('SignalStrength')
            
            status = connection_status.text if connection_status is not None else "Unknown"
            network = current_network_type.text if current_network_type is not None else "Unknown"
            signal = signal_strength.text if signal_strength is not None else "Unknown"
            
            log(f"연결 상태: {status}")
            log(f"네트워크 타입: {network}")
            log(f"신호 강도: {signal}")
            
            return status
        else:
            log(f"상태 확인 실패: {response.status_code}")
            return None
    except Exception as e:
        log(f"상태 확인 오류: {e}")
        return None

def connect_mobile(session_id, token):
    """모바일 연결 시작"""
    try:
        headers = {
            'Cookie': f'SessionID={session_id}',
            '__RequestVerificationToken': token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # 연결 시작 요청
        connect_data = '<?xml version="1.0" encoding="UTF-8"?><request><Action>1</Action></request>'
        response = requests.post("http://192.168.16.1/api/dialup/dial", 
                               data=connect_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            log("✅ 모바일 연결 시작 요청 성공")
            return True
        else:
            log(f"❌ 모바일 연결 요청 실패: {response.status_code}")
            log(f"응답: {response.text}")
            return False
            
    except Exception as e:
        log(f"모바일 연결 오류: {e}")
        return False

def check_internet_via_dongle():
    """동글을 통한 인터넷 연결 확인"""
    import subprocess
    try:
        # 외부 IP 확인
        result = subprocess.run([
            'curl', '--interface', 'enp0s21f0u4', 
            '--connect-timeout', '10', '-s', 'http://ifconfig.me'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            external_ip = result.stdout.strip()
            log(f"🎉 동글 외부 IP: {external_ip}")
            return True, external_ip
        else:
            log("❌ 동글 인터넷 접근 실패")
            return False, None
    except Exception as e:
        log(f"인터넷 확인 오류: {e}")
        return False, None

def main():
    log("=== 동글 모바일 연결 활성화 시작 ===")
    
    # 1. 세션 정보 획득
    session_id, token = get_session_info()
    if not session_id or not token:
        log("❌ 세션 정보를 획득할 수 없습니다.")
        return
    
    # 2. 현재 상태 확인
    status = get_connection_status(session_id, token)
    
    # 3. 연결되지 않은 경우 연결 시도
    if status != "901":  # 901 = Connected
        log("모바일 연결 시작...")
        if connect_mobile(session_id, token):
            log("연결 요청 완료. 15초 대기...")
            time.sleep(15)
        else:
            log("❌ 연결 요청 실패")
            return
    else:
        log("✅ 이미 연결된 상태")
    
    # 4. 연결 후 상태 재확인
    log("연결 상태 재확인...")
    status = get_connection_status(session_id, token)
    
    # 5. 인터넷 연결 테스트
    log("인터넷 연결 테스트...")
    connected, external_ip = check_internet_via_dongle()
    
    if connected:
        log(f"🎉 성공! 동글 모바일 IP: {external_ip}")
    else:
        log("❌ 모바일 연결 후에도 인터넷 접근 불가")
        
        # 추가 진단
        log("추가 진단 정보:")
        import subprocess
        try:
            ping_result = subprocess.run([
                'ping', '-I', 'enp0s21f0u4', '-c', '2', '8.8.8.8'
            ], capture_output=True, text=True, timeout=10)
            
            if ping_result.returncode == 0:
                log("✅ 동글 ping 성공")
            else:
                log("❌ 동글 ping 실패")
                log(ping_result.stderr)
        except:
            pass

if __name__ == "__main__":
    main()