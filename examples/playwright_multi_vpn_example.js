// 하나의 클라이언트에서 여러 Playwright 인스턴스 실행
const { chromium } = require('playwright');

async function createAgent(vpnPort, agentName) {
    // 각 에이전트가 다른 VPN 포트 사용
    const browser = await chromium.launch({
        proxy: {
            server: `socks5://222.101.90.78:${1080 + vpnPort}` // 또는 VPN 연결 후
        },
        headless: true
    });
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // IP 확인
    await page.goto('https://ifconfig.me');
    const ip = await page.textContent('body');
    console.log(`${agentName}: ${ip}`);
    
    return { browser, page, name: agentName };
}

async function main() {
    // 4~6개 에이전트 동시 실행
    const agents = await Promise.all([
        createAgent(0, 'Agent1'), // VPN wg0 또는 SOCKS5 1080
        createAgent(1, 'Agent2'), // VPN wg1 또는 SOCKS5 1081  
        createAgent(0, 'Agent3'), // VPN wg0 (같은 VPN 다중 접속)
        createAgent(1, 'Agent4'), // VPN wg1 (같은 VPN 다중 접속)
        createAgent(0, 'Agent5'), // VPN wg0
        createAgent(1, 'Agent6')  // VPN wg1
    ]);
    
    console.log(`✅ ${agents.length}개 에이전트 동시 실행 중`);
    
    // 각 에이전트가 독립적으로 작업
    await Promise.all(agents.map(async (agent) => {
        // H3 관련 작업 수행
        await agent.page.goto('https://target-site.com');
        // ... 작업 진행
    }));
}

main();