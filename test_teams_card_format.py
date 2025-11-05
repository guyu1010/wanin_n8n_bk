#!/usr/bin/env python3
"""測試 Teams Adaptive Card 格式"""

from app import N8nMonitor
import json

monitor = N8nMonitor('config.json')

# 模擬備份結果
test_data = {
    'title': 'n8n 工作流程備份完成',
    'status': 'success',
    'backup_result': {
        'total_count': 53,
        'changed_count': 3,
        'changed_workflows': [
            'AI新聞擷取&翻譯工作流',
            'prompt優化器',
            '儲存圖片'
        ]
    }
}

# 建立卡片
card = monitor._create_teams_card(test_data)

# 顯示 JSON 結構
print("=" * 60)
print("Teams Adaptive Card 格式預覽")
print("=" * 60)
print(json.dumps(card, indent=2, ensure_ascii=False))
print()
print("=" * 60)
print("檢查關鍵欄位：")
print(f"✓ 有 'attachments' 陣列: {'attachments' in card}")
print(f"✓ attachments 長度: {len(card.get('attachments', []))}")
print(f"✓ 第一個 attachment 有 'content': {'content' in card.get('attachments', [{}])[0]}")
print(f"✓ content 有 'body': {'body' in card.get('attachments', [{}])[0].get('content', {})}")
print("=" * 60)
