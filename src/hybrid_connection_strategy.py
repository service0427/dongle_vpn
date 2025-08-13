#!/usr/bin/env python3
"""
H3 vs 익명성 트레이드오프 해결책
사이트별 적응적 연결 방식 선택
"""

class HybridConnectionManager:
    def __init__(self):
        # H3가 중요한 사이트 목록
        self.h3_critical_sites = {
            'google.com', 'youtube.com', 'gmail.com',
            'facebook.com', 'instagram.com',
            'cloudflare.com', 'fastly.com'
        }
        
        # 고위험 사이트 (완벽 익명성 필요)
        self.high_risk_sites = {
            'banking-sites.com', 'government.gov',
            'security-sensitive.com'
        }
    
    def select_connection_method(self, target_url):
        """사이트별 최적 연결 방식 선택"""
        domain = self.extract_domain(target_url)
        
        if domain in self.high_risk_sites:
            return {
                'method': 'socks5',
                'proxy': '222.101.90.78:1080',
                'reason': 'maximum_anonymity',
                'h3_support': False
            }
        elif domain in self.h3_critical_sites:
            return {
                'method': 'vpn',
                'interface': 'wg0',
                'reason': 'h3_required',
                'h3_support': True,
                'stealth_mode': True  # 추가 은닉 설정
            }
        else:
            # 기본: SOCKS5 (익명성 우선)
            return {
                'method': 'socks5',
                'proxy': '222.101.90.78:1080',
                'reason': 'default_anonymity',
                'h3_support': False
            }
    
    def extract_domain(self, url):
        """URL에서 도메인 추출"""
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()

# Playwright 사용 예시
async def create_context_with_optimal_connection(browser, target_url):
    manager = HybridConnectionManager()
    connection_info = manager.select_connection_method(target_url)
    
    if connection_info['method'] == 'socks5':
        # SOCKS5 프록시 사용
        context = await browser.new_context(
            proxy={
                'server': f"socks5://{connection_info['proxy']}"
            }
        )
        print(f"✅ SOCKS5 연결: {connection_info['reason']}")
        
    elif connection_info['method'] == 'vpn':
        # VPN 환경에서 실행 (은닉 모드)
        context = await browser.new_context(
            # VPN 환경에서는 프록시 설정 불필요
            extra_http_headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        print(f"✅ VPN 연결: H3 지원, {connection_info['reason']}")
    
    return context, connection_info

# 사용 예시
if __name__ == "__main__":
    manager = HybridConnectionManager()
    
    test_sites = [
        'https://google.com',  # H3 중요
        'https://example.com',  # 일반 사이트
        'https://banking-sites.com'  # 고위험
    ]
    
    for site in test_sites:
        info = manager.select_connection_method(site)
        print(f"{site} → {info['method']} ({info['reason']})")
