#!/usr/bin/env python3
"""測試配置讀取和排程器初始化"""

from app import N8nMonitor

print("=" * 60)
print("測試配置讀取...")
print("=" * 60)

monitor = N8nMonitor('config.json')

print(f"✓ n8n URL: {monitor.n8n_url}")
print(f"✓ Git 備份路徑: {monitor.git_repo_path}")
print(f"✓ 請求 timeout: {monitor.timeout} 秒")
print(f"✓ 最大重試次數: {monitor.max_retries}")
print()
print("排程設定:")
print(f"  - 啟用: {monitor.schedule_config.get('enabled')}")
print(f"  - 執行時間: 每小時的 00 分和 30 分")
print(f"  - 啟動時執行: {monitor.schedule_config.get('run_on_startup')}")
print()
print("通知設定:")
print(f"  - 啟用: {monitor.notifications['webhook'].get('enabled')}")
print(f"  - 平台: {monitor.notifications['webhook'].get('platform')}")
print()
print("=" * 60)
print("配置讀取成功！")
print("=" * 60)
print()
print("提示：")
print("  - 要測試單次執行，將 config.json 中的 'enabled' 改為 false")
print("  - 要啟動排程模式，執行: python3 app.py")
print("  - 排程模式會持續運行，按 Ctrl+C 可停止")
