#!/usr/bin/env python3
"""測試變更追蹤功能"""

from app import N8nMonitor
import json

print("=" * 70)
print("測試變更追蹤功能")
print("=" * 70)

monitor = N8nMonitor('config.json')

# 模擬舊版本的 workflow
old_workflow = {
    "id": "test123",
    "name": "測試工作流程",
    "nodes": [
        {
            "id": "node1",
            "name": "HTTP Request",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://api.old.com"}
        },
        {
            "id": "node2",
            "name": "資料處理",
            "type": "n8n-nodes-base.set",
            "parameters": {"value1": "test"}
        }
    ]
}

# 模擬新版本的 workflow（有變更）
new_workflow = {
    "id": "test123",
    "name": "測試工作流程",
    "nodes": [
        {
            "id": "node1",
            "name": "HTTP Request",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://api.new.com"}  # 參數改變
        },
        {
            "id": "node2",
            "name": "資料轉換",  # 名稱改變
            "type": "n8n-nodes-base.set",
            "parameters": {"value1": "test"}
        },
        {
            "id": "node3",
            "name": "Slack 通知",  # 新增節點
            "type": "n8n-nodes-base.slack",
            "parameters": {"channel": "#general"}
        }
    ]
}

print("\n測試 1: 分析工作流程變更")
print("-" * 70)
changes = monitor._analyze_workflow_changes(old_workflow, new_workflow)
print("變更結果:")
print(json.dumps(changes, indent=2, ensure_ascii=False))

print("\n測試 2: 格式化變更摘要")
print("-" * 70)
summary = monitor._format_change_summary(changes)
print(summary)

print("\n測試 3: 模擬 Teams 卡片內容")
print("-" * 70)
backup_result = {
    'total_count': 10,
    'changed_count': 1,
    'changed_workflows': ['測試工作流程'],
    'workflow_changes': {
        '測試工作流程': summary
    }
}

card = monitor._create_teams_card({
    'title': 'n8n 工作流程備份完成',
    'status': 'success',
    'backup_result': backup_result
})

# 提取卡片中的文字內容
print("卡片將顯示的內容：")
for item in card['attachments'][0]['content']['body']:
    if item['type'] == 'TextBlock':
        print(f"  {item['text']}")
    elif item['type'] == 'FactSet':
        for fact in item['facts']:
            print(f"  {fact['title']}: {fact['value']}")

print("\n" + "=" * 70)
print("✓ 測試完成！")
print("=" * 70)
