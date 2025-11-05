# n8n 監控與備份系統

自動化的 n8n 工作流程監控、備份與版本控制系統。

## 功能特色

- ⏰ **定時執行** - 每小時 00 分和 30 分自動執行
- 🔍 **健康監控** - 自動偵測 n8n 服務狀態
- 💾 **智能備份** - 只備份有變更的工作流程
- 🔍 **變更追蹤** - 自動分析並顯示節點的新增、修改、刪除
- 📢 **Teams 通知** - 精美的 Adaptive Card 卡片通知
- 🔄 **Git 版本控制** - 自動提交並推送到 GitHub
- 🔒 **資訊保護** - 自動過濾敏感資訊（API Key、Token 等）

## 快速開始

### 1. 安裝依賴

```bash
pip3 install requests
```

### 2. 設定配置

編輯 `config.json`：

```json
{
  "n8n": {
    "url": "http://your-n8n-url:5678",
    "api_key": "your_n8n_api_key"
  },
  "git": {
    "repo_path": "./backup"
  },
  "schedule": {
    "enabled": true,
    "run_on_startup": true
  },
  "notifications": {
    "webhook": {
      "enabled": true,
      "platform": "teams",
      "url": "your_teams_webhook_url"
    }
  }
}
```

### 3. 初始化備份 Repository

```bash
git clone https://github.com/your-username/backup-repo.git backup
```

### 4. 執行程式

```bash
python3 app.py
```

## 通知範例

Teams 卡片將顯示：

```
✅ n8n 工作流程備份完成

⏰ 備份時間: 2025-11-05 15:00:00
📊 總流程數: 53
✏️ 本次變更: 3

變更的工作流程：

📝 客戶自動化流程
  🆕 新增 1 個節點: Slack 通知 (slack)
  ✏️ 修改 2 個節點: HTTP Request (httpRequest), 資料處理 (set)
  🗑️ 刪除 1 個節點: 舊處理器 (function)
```

## 系統服務部署

### 方式一：systemd 服務（推薦）

```bash
sudo cp n8n-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable n8n-monitor
sudo systemctl start n8n-monitor
```

### 方式二：直接執行

```bash
python3 app.py
```

## 配置說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `n8n.url` | n8n 服務網址 | - |
| `n8n.api_key` | n8n API 金鑰 | - |
| `git.repo_path` | Git 備份路徑 | `./backup` |
| `schedule.enabled` | 啟用排程模式 | `true` |
| `schedule.run_on_startup` | 啟動時立即執行 | `true` |
| `notifications.webhook.enabled` | 啟用 Webhook 通知 | `false` |
| `notifications.webhook.platform` | 通知平台 | `teams` |

## Teams Webhook 設定

1. 在 Power Automate 建立 Flow
2. 觸發器：選擇「**When a HTTP request is received**」
3. 動作：選擇「**Post adaptive card in a chat or channel**」
4. 複製 HTTP POST URL 到 `config.json`

詳細步驟請參考：[TEAMS_SETUP_GUIDE.md](TEAMS_SETUP_GUIDE.md)

## 檔案結構

```
.
├── app.py                    # 主程式
├── config.json               # 設定檔
├── n8n-monitor.service       # systemd 服務文件
├── backup/                   # 備份目錄（獨立 Git repo）
│   ├── workflows/            # 工作流程 JSON 檔案
│   ├── .workflow_hashes.json # Hash 記錄
│   └── .workflow_data.json   # 完整資料（用於變更比對）
└── n8n_monitor.log           # 日誌檔案
```

## 技術規格

- **語言**: Python 3.7+
- **依賴**: requests
- **備份格式**: JSON
- **版本控制**: Git
- **執行頻率**: 每半小時（00 分、30 分）

## 授權

MIT License

## 貢獻

歡迎提交 Issue 和 Pull Request！
