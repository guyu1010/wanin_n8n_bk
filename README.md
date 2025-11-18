# n8n 監控與備份系統

自動化的 n8n 工作流程監控、備份與版本控制系統。

## 功能特色

- ⏰ **定時執行** - 健康檢查每 10 分鐘，備份每小時自動執行
- 🔍 **健康監控** - 自動偵測 n8n 服務狀態，異常時發送通知
- 💾 **智能備份** - 只備份有功能性變更的工作流程（過濾位置等非功能性變更）
- 🔍 **變更追蹤** - 自動分析並顯示節點的新增、修改、刪除
- 📢 **Teams 通知** - 精美的 Adaptive Card 卡片通知（透過 Power Automate）
- 🔄 **Git 版本控制** - 自動提交並推送到 GitLab/GitHub（支援 master 分支）
- 🔒 **資訊保護** - 自動過濾敏感資訊（API Key、Token、密碼等）
- 📊 **日誌管理** - 自動輪替日誌檔，保留 60 天記錄

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
    "repo_path": "./backup",
    "remote_url": "http://your-gitlab-server/path/to/repo.git"
  },
  "timeout": 10,
  "max_retries": 3,
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

### 3. 設定 Git 認證並 clone 備份 Repository

```bash
# 設定 Git credential helper（記住帳密）
git config --global credential.helper store

# 設定使用者資訊
git config --global user.name "your-name"
git config --global user.email "your-email@company.com"

# Clone 備份 repository
git clone http://your-gitlab-server/path/to/repo.git backup
```

### 4. 執行程式

```bash
# 單次執行模式（手動測試用）
python3 app.py

# 排程模式（背景持續運行）
# 確保 config.json 中 schedule.enabled = true
python3 app.py
```

## 運作模式

### 排程模式（預設）
當 `config.json` 中 `schedule.enabled = true` 時：
- **健康檢查**: 每 10 分鐘執行一次（00, 10, 20, 30, 40, 50 分）
- **完整備份**: 每小時整點執行（00 分）
- **服務監控**: 健康狀態變更時發送 Teams 通知
- **開機執行**: 啟動時立即執行一次完整檢查（可透過 `run_on_startup` 設定）

### 單次執行模式
當 `schedule.enabled = false` 時：
- 執行一次健康檢查 + 備份
- 適合手動測試或搭配外部排程工具（如 cron）

## 通知範例

### 備份完成通知

Teams 卡片將顯示：

```
✅ n8n工作流程異動 - 備份完成

⏰ 備份時間: 2024-11-18 15:00:00
📊 總流程數: 53
✏️ 本次變更: 3

變更的工作流程：

📝 客戶自動化流程
  🆕 新增 1 個節點: Slack 通知 (slack)
  ✏️ 修改 2 個節點: HTTP Request (httpRequest), 資料處理 (set)
  🗑️ 刪除 1 個節點: 舊處理器 (function)
```

### 服務異常通知

```
⚠️ n8n 服務異常

⏰ 時間: 2024-11-18 15:30:00
📍 狀態: timeout
錯誤訊息: Connection timeout
```

## 配置說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `n8n.url` | n8n 服務網址 | 必填 |
| `n8n.api_key` | n8n API 金鑰（在 n8n Settings > API 中建立） | 必填 |
| `git.repo_path` | 本地 Git 備份路徑 | `./backup` |
| `git.remote_url` | GitLab/GitHub 遠端 repository URL | 必填 |
| `timeout` | API 請求逾時秒數 | `10` |
| `max_retries` | API 請求失敗重試次數 | `3` |
| `schedule.enabled` | 啟用排程模式 | `false` |
| `schedule.run_on_startup` | 啟動時立即執行一次 | `true` |
| `notifications.webhook.enabled` | 啟用 Webhook 通知 | `false` |
| `notifications.webhook.platform` | 通知平台（支援 teams, slack, discord） | `teams` |
| `notifications.webhook.url` | Webhook URL | - |

## Teams Webhook 設定（透過 Power Automate）

1. 在 Power Automate 建立 Flow
2. 觸發器：選擇「**When a HTTP request is received**」
3. 動作：選擇「**Post adaptive card in a chat or channel**」
   - 在 Request Body JSON Schema 中加入接收格式
   - 設定要發送的 Teams 頻道
4. 複製 HTTP POST URL 到 `config.json` 的 `notifications.webhook.url`

程式會自動將備份結果和服務狀態轉換為 Adaptive Card 格式發送。

## 檔案結構

```
.
├── app.py                    # 主程式
├── config.json               # 設定檔（包含 n8n 和 GitLab 設定）
├── requirements.txt          # Python 依賴套件清單
├── n8n-monitor.service       # systemd 服務檔案（Linux 部署用）
├── .gitignore                # Git 忽略清單
├── README.md                 # 說明文件
├── DEPLOY_LINUX.md           # Linux 部署詳細指南（已整合至 README）
├── backup/                   # 備份目錄（獨立的 Git repository）
│   ├── workflows/            # 工作流程 JSON 檔案
│   ├── .workflow_hashes.json # 功能性變更 Hash 記錄
│   ├── .workflow_data.json   # 完整工作流程資料（用於變更比對）
│   └── README.md             # 備份說明（由第一次推送建立）
├── n8n_monitor.log           # 當前日誌檔案
└── n8n_monitor.log.YYYY-MM-DD # 歷史日誌檔案（自動輪替，保留 60 天）
```

## 技術規格

- **語言**: Python 3.7+
- **依賴**: requests
- **備份格式**: JSON
- **版本控制**: Git
- **執行頻率**: 健康檢查每 10 分鐘，備份每小時
- **日誌管理**: 自動輪替，保留 60 天

---

# Linux 伺服器部署指南

## 前置準備

### 系統需求
- Ubuntu/Debian 或 CentOS/RHEL Linux
- Python 3.8+
- Git 已安裝
- 可連接到 n8n 伺服器和 GitLab

### 檢查環境
```bash
python3 --version  # 檢查 Python 版本
git --version      # 檢查 Git 版本
pip3 --version     # 檢查 pip 版本
```

## 完整部署步驟

### 步驟 1: 上傳檔案到伺服器

將以下檔案上傳到伺服器（例如 `~/n8n/n8nbk_python`）：
- `app.py`
- `config.json`
- `requirements.txt`
- `n8n-monitor.service`
- `.gitignore`

### 步驟 2: 修改設定檔

編輯 `config.json`，設定正式環境參數：
```json
{
  "n8n": {
    "url": "http://your-production-n8n:5678",
    "api_key": "your_production_api_key"
  },
  "git": {
    "repo_path": "./backup",
    "remote_url": "http://your-gitlab-server/path/to/repo.git"
  },
  "notifications": {
    "webhook": {
      "enabled": true,
      "url": "your_teams_webhook_url"
    }
  }
}
```

### 步驟 3: 安裝 Python 依賴

```bash
cd ~/n8n/n8nbk_python

# 方式 A: 直接安裝
pip3 install -r requirements.txt

# 方式 B: 使用虛擬環境（建議）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 步驟 4: 設定 Git 認證

#### 方式 A: Credential Store（推薦，較簡單）

```bash
# 1. 設定 Git credential helper
git config --global credential.helper store

# 2. 設定使用者資訊
git config --global user.name "your-username"
git config --global user.email "your-email@company.com"

# 3. 刪除舊的 backup 目錄（如果存在）
cd ~/n8n/n8nbk_python
rm -rf backup

# 4. 從 GitLab clone 現有 repository
git clone http://your-gitlab-server/path/to/repo.git backup
# 第一次會要求輸入帳號密碼，輸入後會自動記住

# 5. 確認 clone 成功
cd backup
git status
git remote -v
```

**重要提醒**：
- 第一次 `git clone` 或 `git push` 時會要求輸入 GitLab 帳號和密碼
- 輸入後會自動儲存在 `~/.git-credentials`
- 之後程式執行時就不需要再輸入了

#### 方式 B: SSH Key（較安全）

```bash
# 1. 生成 SSH key
ssh-keygen -t ed25519 -C "backup@yourcompany.com"
# 按 Enter 使用預設路徑

# 2. 顯示公鑰
cat ~/.ssh/id_ed25519.pub

# 3. 將公鑰加到 GitLab
# GitLab > Settings > SSH Keys > 貼上公鑰

# 4. Clone repository（使用 SSH URL）
cd ~/n8n/n8nbk_python
rm -rf backup
git clone git@your-gitlab-server:path/to/repo.git backup
```

### 步驟 5: 測試執行

```bash
cd ~/n8n/n8nbk_python

# 測試執行（按 Ctrl+C 停止）
python app.py

# 或使用 venv
venv/bin/python app.py

# 檢查是否正常：
# ✓ 可以連接到 n8n
# ✓ 可以取得工作流程
# ✓ 可以推送到 GitLab
```

### 步驟 6: 設定為系統服務

#### 6.1 修改 service 檔案路徑

編輯 `n8n-monitor.service`，根據實際路徑修改：

```ini
[Service]
User=wadmin                                    # 改成實際使用者
WorkingDirectory=/home/wadmin/n8n/n8nbk_python # 改成實際路徑
ExecStart=/home/wadmin/n8n/n8nbk_python/venv/bin/python /home/wadmin/n8n/n8nbk_python/app.py
```

**如果使用 venv**，ExecStart 要用 venv 中的 python：
```ini
ExecStart=/home/wadmin/n8n/n8nbk_python/venv/bin/python /home/wadmin/n8n/n8nbk_python/app.py
```

**如果沒用 venv**，直接用系統 python：
```ini
ExecStart=/usr/bin/python3 /home/wadmin/n8n/n8nbk_python/app.py
```

#### 6.2 註冊並啟動服務

```bash
# 1. 複製 service 檔案到系統目錄
sudo cp ~/n8n/n8nbk_python/n8n-monitor.service /etc/systemd/system/

# 2. 重新載入 systemd
sudo systemctl daemon-reload

# 3. 啟用服務（開機自動啟動）
sudo systemctl enable n8n-monitor

# 4. 啟動服務
sudo systemctl start n8n-monitor

# 5. 查看服務狀態
sudo systemctl status n8n-monitor

# 6. 查看即時日誌（按 Ctrl+C 停止查看）
sudo journalctl -u n8n-monitor -f
```

## 常見問題排除

### Git 推送失敗

**症狀**: `git push` 時出現 `rejected` 或 `fetch first` 錯誤

**解決方式 1**: 先拉取再推送
```bash
cd ~/n8n/n8nbk_python/backup
git pull origin master --allow-unrelated-histories -X theirs
git push -u origin master
```

**解決方式 2**: 重新 clone（最簡單）
```bash
cd ~/n8n/n8nbk_python
rm -rf backup
git clone http://your-gitlab-server/path/to/repo.git backup
```

### 合併衝突

**症狀**: `git pull` 時出現 `CONFLICT` 訊息

**解決方式**:
```bash
# 取消合併
git merge --abort

# 重新 pull 並使用遠端版本
git pull origin master --allow-unrelated-histories -X theirs

# 推送
git push -u origin master
```

### 服務無法啟動

**檢查方式**:
```bash
# 查看詳細錯誤
sudo journalctl -u n8n-monitor -n 50 --no-pager

# 檢查檔案權限
ls -la ~/n8n/n8nbk_python/

# 手動執行測試
cd ~/n8n/n8nbk_python
python app.py
```

**常見原因**:
1. service 檔案中的路徑不正確
2. Python 路徑錯誤（檢查 `which python3` 或 venv 路徑）
3. 檔案權限問題（確保使用者有權限執行）
4. config.json 設定錯誤

## 服務管理指令

```bash
# 查看服務狀態
sudo systemctl status n8n-monitor

# 啟動服務
sudo systemctl start n8n-monitor

# 停止服務
sudo systemctl stop n8n-monitor

# 重新啟動服務
sudo systemctl restart n8n-monitor

# 查看即時日誌
sudo journalctl -u n8n-monitor -f

# 查看最近 100 行日誌
sudo journalctl -u n8n-monitor -n 100

# 查看今天的日誌
sudo journalctl -u n8n-monitor --since today

# 查看程式產生的日誌檔
tail -f ~/n8n/n8nbk_python/n8n_monitor.log
```