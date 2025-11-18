#!/usr/bin/env python3
"""诊断脚本 - 检查工作流状态"""
import json
import requests
from pathlib import Path

# 读取配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

n8n_url = config['n8n']['url'].rstrip('/')
api_key = config['n8n']['api_key']
repo_path = Path(config['git']['repo_path'])

headers = {
    'X-N8N-API-KEY': api_key,
    'Accept': 'application/json'
}

print("=" * 70)
print("n8n 工作流状态诊断")
print("=" * 70)

# 1. 检查 n8n API 返回的工作流
print("\n【1】n8n API 返回的工作流：")
print("-" * 70)
try:
    response = requests.get(f"{n8n_url}/api/v1/workflows", headers=headers, timeout=10)
    response.raise_for_status()
    workflows = response.json()['data']

    print(f"总数: {len(workflows)} 个\n")
    for i, w in enumerate(workflows, 1):
        active_status = "✓ 启用" if w.get('active') else "✗ 停用"
        print(f"{i}. {w['name']}")
        print(f"   ID: {w['id']}")
        print(f"   状态: {active_status}")
        print(f"   更新时间: {w.get('updatedAt', 'N/A')}")
        print()

except Exception as e:
    print(f"✗ 错误: {e}")
    workflows = []

# 2. 检查备份记录
print("\n【2】备份记录 (.workflow_data.json)：")
print("-" * 70)
data_file = repo_path / '.workflow_data.json'
if data_file.exists():
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            old_workflows = json.load(f)

        print(f"总数: {len(old_workflows)} 个\n")
        for i, (wid, wdata) in enumerate(old_workflows.items(), 1):
            print(f"{i}. {wdata.get('name', 'Unknown')}")
            print(f"   ID: {wid}")
            print()
    except Exception as e:
        print(f"✗ 读取错误: {e}")
        old_workflows = {}
else:
    print("✗ 文件不存在 (首次运行)")
    old_workflows = {}

# 3. 检查本地备份文件
print("\n【3】本地备份文件 (workflows/ 目录)：")
print("-" * 70)
workflows_dir = repo_path / 'workflows'
if workflows_dir.exists():
    json_files = list(workflows_dir.glob('*.json'))
    print(f"总数: {len(json_files)} 个\n")
    for i, filepath in enumerate(sorted(json_files), 1):
        print(f"{i}. {filepath.name}")
else:
    print("✗ 目录不存在")

# 4. 比对分析
print("\n【4】比对分析：")
print("-" * 70)

if workflows:
    current_ids = {w['id'] for w in workflows}
    old_ids = set(old_workflows.keys())

    # 新增的
    new_ids = current_ids - old_ids
    if new_ids:
        print(f"\n🆕 新增的工作流 ({len(new_ids)} 个):")
        for w in workflows:
            if w['id'] in new_ids:
                print(f"  - {w['name']} (ID: {w['id']})")

    # 删除的
    deleted_ids = old_ids - current_ids
    if deleted_ids:
        print(f"\n🗑️ 已删除的工作流 ({len(deleted_ids)} 个):")
        for wid in deleted_ids:
            wname = old_workflows[wid].get('name', 'Unknown')
            print(f"  - {wname} (ID: {wid})")

    # 相同的
    same_ids = current_ids & old_ids
    if same_ids:
        print(f"\n✓ 未变更的工作流 ({len(same_ids)} 个):")
        for w in workflows:
            if w['id'] in same_ids:
                print(f"  - {w['name']} (ID: {w['id']})")

    if not new_ids and not deleted_ids:
        print("\n✓ n8n 和备份记录一致，无变更")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
