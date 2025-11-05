#!/usr/bin/env python3
"""測試排程器功能（短間隔測試）"""

import json
import sys
import os

# 建立測試用的 config
test_config = {
    "n8n": {
        "url": "http://103.130.125.54:5678",
        "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkM2U3OTU1YS1mZDJkLTQ4ODctODBkOC1mYTA1M2EwMGY4M2YiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYyMjQ3NzU2fQ.uXm_N0l_47mgUgzAq_Uw8fqcuJan2brOaSr-CexSjcA"
    },
    "git": {
        "repo_path": "./backup"
    },
    "timeout": 10,
    "max_retries": 3,
    "schedule": {
        "enabled": True,
        "interval": 30,  # 測試用：30 秒（實際使用建議 600 秒）
        "run_on_startup": True
    },
    "notifications": {
        "webhook": {
            "enabled": False  # 測試時關閉通知
        }
    }
}

# 儲存測試配置
with open('config_test.json', 'w', encoding='utf-8') as f:
    json.dump(test_config, f, indent=2, ensure_ascii=False)

print("=" * 60)
print("🧪 排程器測試模式")
print("=" * 60)
print("測試配置：")
print(f"  - 執行間隔: 30 秒")
print(f"  - 啟動時執行: 是")
print(f"  - 通知功能: 關閉")
print()
print("你將會看到：")
print("  1. 立即執行第一次監控")
print("  2. 每 30 秒自動執行一次")
print()
print("按 Ctrl+C 可以停止測試")
print("=" * 60)
print()

# 執行監控
from app import N8nMonitor

try:
    monitor = N8nMonitor('config_test.json')
    monitor.run_scheduled()
except KeyboardInterrupt:
    print("\n\n測試完成！")
finally:
    # 清理測試配置檔
    if os.path.exists('config_test.json'):
        os.remove('config_test.json')
        print("已清理測試配置檔")
