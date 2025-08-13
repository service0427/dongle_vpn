#!/usr/bin/env python3
"""
터미널에서 실행 가능한 동글 IP 토글 스크립트
"""

import requests
import sys
import json
import argparse
from datetime import datetime

API_BASE = "http://localhost:5000/api"

def print_status(message, status="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{status}] {message}")

def check_api_server():
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def list_clients():
    """클라이언트 목록 조회"""
    try:
        response = requests.get(f"{API_BASE}/clients")
        if response.status_code == 200:
            clients = response.json()
            if not clients:
                print_status("등록된 클라이언트가 없습니다")
                return
            
            print_status("등록된 클라이언트 목록:")
            print("-" * 60)
            for client_id, info in clients.items():
                status = "🟢 활성" if info['status'] == 'active' else "🔴 비활성"
                ip = info.get('ip', 'N/A')
                print(f"ID: {client_id:<15} IP: {ip:<15} {status}")
            print("-" * 60)
        else:
            print_status("클라이언트 목록을 가져올 수 없습니다", "ERROR")
    except Exception as e:
        print_status(f"오류 발생: {e}", "ERROR")

def toggle_client(client_id):
    """클라이언트 IP 토글"""
    try:
        print_status(f"클라이언트 '{client_id}' IP 토글 중...")
        response = requests.post(f"{API_BASE}/clients/{client_id}/toggle")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                new_ip = data['new_ip']
                if new_ip:
                    print_status(f"✅ 클라이언트 '{client_id}' 새 IP: {new_ip}", "SUCCESS")
                else:
                    print_status(f"🔴 클라이언트 '{client_id}' IP 비활성화됨", "SUCCESS")
            else:
                print_status(f"토글 실패: {data.get('error', '알 수 없는 오류')}", "ERROR")
        else:
            print_status(f"API 호출 실패 (상태코드: {response.status_code})", "ERROR")
    except Exception as e:
        print_status(f"토글 중 오류 발생: {e}", "ERROR")

def add_client(client_id, public_key):
    """새 클라이언트 추가"""
    try:
        print_status(f"클라이언트 '{client_id}' 추가 중...")
        data = {"public_key": public_key}
        response = requests.post(f"{API_BASE}/clients/{client_id}", json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print_status(f"✅ 클라이언트 '{client_id}' 추가됨, IP: {result['assigned_ip']}", "SUCCESS")
            else:
                print_status(f"추가 실패: {result.get('error', '알 수 없는 오류')}", "ERROR")
        else:
            print_status(f"API 호출 실패 (상태코드: {response.status_code})", "ERROR")
    except Exception as e:
        print_status(f"클라이언트 추가 중 오류 발생: {e}", "ERROR")

def show_wireguard_status():
    """WireGuard 상태 조회"""
    try:
        response = requests.get(f"{API_BASE}/wireguard/status")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_status("현재 WireGuard 상태:")
                print(data['status'])
            else:
                print_status(f"상태 조회 실패: {data.get('error')}", "ERROR")
    except Exception as e:
        print_status(f"상태 조회 중 오류 발생: {e}", "ERROR")

def main():
    parser = argparse.ArgumentParser(description="동글 IP 토글 도구")
    parser.add_argument('action', choices=['list', 'toggle', 'add', 'status'], 
                       help="실행할 작업")
    parser.add_argument('--client-id', '-c', help="클라이언트 ID")
    parser.add_argument('--public-key', '-k', help="공개키 (add 시 필요)")
    
    args = parser.parse_args()
    
    print_status("동글 IP 토글 도구 시작")
    
    # API 서버 상태 확인
    if not check_api_server():
        print_status("❌ API 서버에 연결할 수 없습니다. 서버를 먼저 시작해주세요:", "ERROR")
        print_status("python3 /home/proxy/dongle_api.py")
        sys.exit(1)
    
    if args.action == 'list':
        list_clients()
    
    elif args.action == 'toggle':
        if not args.client_id:
            print_status("--client-id 옵션이 필요합니다", "ERROR")
            sys.exit(1)
        toggle_client(args.client_id)
    
    elif args.action == 'add':
        if not args.client_id or not args.public_key:
            print_status("--client-id 및 --public-key 옵션이 필요합니다", "ERROR")
            sys.exit(1)
        add_client(args.client_id, args.public_key)
    
    elif args.action == 'status':
        show_wireguard_status()

if __name__ == "__main__":
    main()