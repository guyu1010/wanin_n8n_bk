#!/usr/bin/env python3
"""測試排程時間計算邏輯"""

from datetime import datetime, timedelta

def calculate_next_run(now):
    """計算下一個執行時間（每小時的 00 分或 30 分）"""
    next_run = now.replace(second=0, microsecond=0)

    # 決定下一個執行時間點
    if now.minute < 30:
        # 下一個執行時間是本小時的 30 分
        next_run = next_run.replace(minute=30)
    else:
        # 下一個執行時間是下一小時的 00 分
        next_run = next_run.replace(minute=0)
        next_run = next_run + timedelta(hours=1)

    # 如果計算出的時間已經過去（可能剛好在整點或半點），則跳到下一個時間點
    if next_run <= now:
        if next_run.minute == 0:
            next_run = next_run.replace(minute=30)
        else:
            next_run = next_run.replace(minute=0) + timedelta(hours=1)

    return next_run

# 測試各種時間點
test_cases = [
    "2025-11-05 14:00:00",  # 整點
    "2025-11-05 14:15:00",  # 15分
    "2025-11-05 14:29:59",  # 29分59秒
    "2025-11-05 14:30:00",  # 半點
    "2025-11-05 14:45:00",  # 45分
    "2025-11-05 14:59:59",  # 59分59秒
    "2025-11-05 23:45:00",  # 跨日測試
]

print("=" * 70)
print("排程時間計算測試")
print("=" * 70)
print("規則：每小時的 00 分和 30 分執行")
print()

for test_time_str in test_cases:
    now = datetime.strptime(test_time_str, "%Y-%m-%d %H:%M:%S")
    next_run = calculate_next_run(now)
    wait_seconds = (next_run - now).total_seconds()
    wait_minutes = int(wait_seconds // 60)

    print(f"現在時間: {now.strftime('%H:%M:%S')}")
    print(f"  → 下次執行: {next_run.strftime('%H:%M:%S')}")
    print(f"  → 等待時間: {wait_minutes} 分 {int(wait_seconds % 60)} 秒")
    print()

print("=" * 70)
print("測試完成！")
print()
print("執行時間表：")
print("00:00, 00:30, 01:00, 01:30, 02:00, 02:30, ...")
print("每天共執行 48 次（每半小時一次）")
print("=" * 70)
