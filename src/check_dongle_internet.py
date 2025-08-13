#!/usr/bin/env python3
"""
동글 인터넷 연결 상태 확인 및 APN 설정
"""

import requests
import subprocess
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def get_dongle_status():
    """동글 상태 확인"""
    try:
        # 동글 웹 인터페이스 접근
        response = requests.get("http://192.168.16.1/api/device/information", 
                              timeout=10)
        if response.status_code == 200:
            # XML 파싱
            root = ET.fromstring(response.text)
            device_name = root.find('DeviceName')
            connection_status = root.find('ConnectionStatus')
            
            log(f"장치명: {device_name.text if device_name is not None else 'Unknown'}")
            log(f"연결상태: {connection_status.text if connection_status is not None else 'Unknown'}")
            
            return True
    except Exception as e:
        log(f"동글 상태 확인 실패: {e}")
    
    return False

def check_internet_connectivity():
    """동글을 통한 인터넷 연결 확인"""
    try:
        # 동글 인터페이스를 통해 외부 접근 시도
        cmd = ["curl", "--interface", "enp0s21f0u4", 
               "--connect-timeout", "5", "-s", "http://httpbin.org/ip"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            external_ip = response.get('origin', 'Unknown')
            log(f"동글 외부 IP: {external_ip}")
            return True, external_ip
        else:
            log(f"동글 인터넷 연결 실패: {result.stderr}")
            return False, None
            
    except Exception as e:
        log(f"인터넷 연결 테스트 실패: {e}")
        return False, None

def activate_dongle_connection():
    """동글 연결 활성화 시도"""
    try:
        # 연결 활성화 API 호출
        session_info = requests.get("http://192.168.16.1/api/webserver/SesTokInfo", timeout=5)
        if session_info.status_code != 200:
            log("세션 정보 획득 실패")
            return False
            
        root = ET.fromstring(session_info.text)
        session_id = root.find('SesInfo').text
        token = root.find('TokInfo').text
        
        headers = {
            'Cookie': f'SessionID={session_id}',
            '__RequestVerificationToken': token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # 연결 시작
        connect_data = '<?xml version="1.0" encoding="UTF-8"?><request><Action>1</Action></request>'
        response = requests.post("http://192.168.16.1/api/dialup/dial", 
                               data=connect_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            log("동글 연결 활성화 요청 성공")
            return True
        else:
            log(f"동글 연결 활성화 실패: {response.status_code}")
            return False
            
    except Exception as e:
        log(f"동글 연결 활성화 오류: {e}")
        return False

def main():
    log("동글 인터넷 연결 확인 시작...")
    
    # 1. 동글 상태 확인
    if not get_dongle_status():
        log("동글에 접근할 수 없습니다.")
        return
    
    # 2. 인터넷 연결 확인
    connected, external_ip = check_internet_connectivity()
    if connected:
        log(f"✅ 동글 인터넷 연결 활성화됨! 외부 IP: {external_ip}")
        return
    
    log("❌ 동글 인터넷 연결이 비활성화 상태")
    
    # 3. 연결 활성화 시도
    log("동글 연결 활성화 시도...")
    if activate_dongle_connection():
        # 연결 활성화 후 잠시 대기
        time.sleep(5)
        
        # 다시 인터넷 연결 확인
        connected, external_ip = check_internet_connectivity()
        if connected:
            log(f"✅ 동글 연결 활성화 성공! 외부 IP: {external_ip}")
        else:
            log("❌ 연결 활성화 후에도 인터넷 접근 불가")
    else:
        log("❌ 동글 연결 활성화 실패")

if __name__ == "__main__":
    main()