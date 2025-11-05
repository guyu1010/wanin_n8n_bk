#!/usr/bin/env python3
"""測試 Teams 通知功能"""

from app import N8nMonitor
from datetime import datetime

def test_backup_notification():
    """測試備份完成通知"""
    print("=== 測試備份完成通知 ===")

    monitor = N8nMonitor('config.json')

    # 模擬備份結果
    test_backup_result = {
        'success': True,
        'total_count': 15,
        'changed_count': 3,
        'changed_workflows': [
            '客戶自動化流程',
            '銷售報表生成',
            '每日數據同步'
        ]
    }

    monitor.send_webhook_notification({
        'title': 'n8n 工作流程備份完成',
        'status': 'success',
        'backup_result': test_backup_result
    })

    print("✓ 備份完成通知已發送到 Teams")

def test_error_notification():
    """測試錯誤通知"""
    print("\n=== 測試服務異常通知 ===")

    monitor = N8nMonitor('config.json')

    # 模擬健康檢查異常
    test_health_status = {
        'status': 'down',
        'error': 'Connection timeout - 無法連線到 n8n 服務',
        'timestamp': datetime.now().isoformat()
    }

    monitor.send_webhook_notification({
        'title': 'n8n 服務異常',
        'status': 'error',
        'health_status': test_health_status
    })

    print("✓ 服務異常通知已發送到 Teams")

def test_recovery_notification():
    """測試服務恢復通知"""
    print("\n=== 測試服務恢復通知 ===")

    monitor = N8nMonitor('config.json')

    # 模擬健康檢查恢復
    test_health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'response_time': 0.123
    }

    monitor.send_webhook_notification({
        'title': 'n8n 服務恢復',
        'status': 'success',
        'health_status': test_health_status
    })

    print("✓ 服務恢復通知已發送到 Teams")

if __name__ == '__main__':
    print("開始測試 Teams 通知功能\n")

    # 執行測試
    test_backup_notification()
    test_error_notification()
    test_recovery_notification()

    print("\n=== 測試完成 ===")
    print("請檢查你的 Teams 頻道，應該會看到 3 張卡片：")
    print("1. 綠色卡片 - 備份完成通知（包含變更的工作流程列表）")
    print("2. 紅色卡片 - 服務異常通知（包含錯誤訊息）")
    print("3. 綠色卡片 - 服務恢復通知")
