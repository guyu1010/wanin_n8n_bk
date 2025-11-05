# n8n 監控系統部署指南

## 📋 功能概述

這個監控系統提供：
- ⏰ **內建排程器** - 不需要設定 cron job
- 🔍 **健康監控** - 自動偵測 n8n 服務狀態
- 💾 **自動備份** - 偵測變更並備份到 Git
- 📢 **Teams 通知** - 精美的 Adaptive Card 通知

---

## 🚀 快速開始

### 方法 1：直接執行（測試用）

```bash
cd /home/user/wanin_n8n_bk
python3 app.py
```

程式會根據 `config.json` 的設定：
- 如果 `schedule.enabled = true`：持續運行，定期執行監控
- 如果 `schedule.enabled = false`：執行一次後結束

停止程式：按 `Ctrl+C`

---

### 方法 2：作為系統服務運行（推薦）

#### 步驟 1：安裝服務

```bash
# 複製服務文件到 systemd 目錄
sudo cp n8n-monitor.service /etc/systemd/system/

# 重新載入 systemd
sudo systemctl daemon-reload

# 啟用服務（開機自動啟動）
sudo systemctl enable n8n-monitor

# 啟動服務
sudo systemctl start n8n-monitor
```

#### 步驟 2：檢查服務狀態

```bash
# 查看服務狀態
sudo systemctl status n8n-monitor

# 查看即時日誌
sudo journalctl -u n8n-monitor -f

# 查看最近的日誌
sudo journalctl -u n8n-monitor -n 50
```

#### 步驟 3：管理服務

```bash
# 停止服務
sudo systemctl stop n8n-monitor

# 重新啟動服務
sudo systemctl restart n8n-monitor

# 停用服務（取消開機自啟）
sudo systemctl disable n8n-monitor
```

---

## ⚙️ 配置說明

### config.json 完整範例

```json
{
  "n8n": {
    "url": "http://103.130.125.54:5678",
    "api_key": "你的_n8n_API_金鑰"
  },
  "git": {
    "repo_path": "./backup"
  },
  "timeout": 10,
  "max_retries": 3,
  "schedule": {
    "enabled": true,
    "interval": 600,
    "run_on_startup": true
  },
  "notifications": {
    "webhook": {
      "enabled": true,
      "platform": "teams",
      "url": "你的_Teams_Webhook_URL"
    }
  }
}
```

### 設定說明

#### n8n 設定
- `url`: n8n 服務的網址
- `api_key`: n8n API 金鑰（在 n8n 設定中取得）

#### git 設定
- `repo_path`: 備份 repository 的本地路徑
  - 相對路徑：`./backup`（推薦）
  - 絕對路徑：`/opt/n8n/backup`

#### 排程設定
- `enabled`: 是否啟用排程模式
  - `true`: 持續運行，定期執行
  - `false`: 執行一次後結束
- `interval`: 執行間隔（秒）
  - `300`: 5 分鐘
  - `600`: 10 分鐘（推薦）
  - `1800`: 30 分鐘
  - `3600`: 1 小時
- `run_on_startup`: 啟動時是否立即執行
  - `true`: 立即執行一次（推薦）
  - `false`: 等待第一個間隔後才執行

#### 通知設定
- `enabled`: 是否啟用通知
- `platform`: 通知平台
  - `teams`: Microsoft Teams
  - `slack`: Slack
  - `discord`: Discord
- `url`: Webhook URL

---

## 🔐 安全設定

### 1. Git 認證設定

**使用 SSH Key（推薦）**

```bash
# 生成 SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# 查看公鑰
cat ~/.ssh/id_ed25519.pub

# 將公鑰加入到 GitHub: Settings > SSH and GPG keys

# 設定 Git remote 為 SSH
cd backup
git remote set-url origin git@github.com:guyu1010/wanin_n8n_bk_data.git
```

**或使用 Personal Access Token**

```bash
# 在 GitHub 建立 Token: Settings > Developer settings > Personal access tokens
# 權限: repo (完整權限)

# 第一次推送時會要求輸入：
#   Username: 你的 GitHub 帳號
#   Password: Personal Access Token (不是密碼！)

# 設定記住認證
git config --global credential.helper store
```

### 2. 保護敏感資訊

**不要將 config.json 提交到 Git**

```bash
# .gitignore 已包含 backup/ 目錄
# 確保不會誤提交備份資料
```

**使用環境變數（可選）**

```bash
# 建立 .env 檔案
export N8N_API_KEY="your_api_key"
export N8N_URL="http://your-n8n-url"
export TEAMS_WEBHOOK="your_webhook_url"

# 在 app.py 中讀取環境變數（需要自行修改程式碼）
```

---

## 📊 監控與除錯

### 查看日誌

**本地日誌檔案**
```bash
tail -f n8n_monitor.log
```

**系統日誌（systemd 服務）**
```bash
# 即時查看
sudo journalctl -u n8n-monitor -f

# 查看今天的日誌
sudo journalctl -u n8n-monitor --since today

# 查看特定時間範圍
sudo journalctl -u n8n-monitor --since "2025-11-05 10:00" --until "2025-11-05 12:00"

# 只顯示錯誤
sudo journalctl -u n8n-monitor -p err
```

### 常見問題排查

#### 1. 服務無法啟動

```bash
# 檢查服務狀態
sudo systemctl status n8n-monitor

# 檢查配置檔語法
python3 -c "import json; json.load(open('config.json'))"

# 手動執行測試
python3 app.py
```

#### 2. Git 推送失敗

```bash
# 檢查 Git 認證
cd backup
git push

# 查看 remote URL
git remote -v

# 測試 SSH 連線（如果使用 SSH）
ssh -T git@github.com
```

#### 3. Teams 通知失敗

```bash
# 測試通知功能
python3 test_teams_notification.py

# 檢查 webhook URL 是否正確
# 確認 Power Automate Flow 是否啟用
```

---

## 🔄 更新與維護

### 更新程式碼

```bash
# 停止服務
sudo systemctl stop n8n-monitor

# 更新程式碼
git pull

# 重新啟動服務
sudo systemctl start n8n-monitor
```

### 備份配置

```bash
# 定期備份 config.json
cp config.json config.json.backup
```

### 清理日誌

```bash
# 清理本地日誌（保留最近 7 天）
find . -name "n8n_monitor.log*" -mtime +7 -delete

# 清理系統日誌
sudo journalctl --vacuum-time=7d
```

---

## 📈 效能調校

### 調整執行頻率

根據你的需求調整 `interval`：

- **頻繁變更**（多人協作）: `300` 秒（5 分鐘）
- **一般使用**: `600` 秒（10 分鐘）
- **低頻變更**: `1800` 秒（30 分鐘）

### 減少網路請求

如果 n8n 有大量 workflows：

```json
{
  "timeout": 30,
  "max_retries": 5
}
```

---

## 🆘 支援與幫助

### 測試工具

```bash
# 測試配置讀取
python3 test_config.py

# 測試 Teams 通知
python3 test_teams_notification.py

# 測試排程器（30秒間隔）
python3 test_scheduler.py
```

### 日誌位置

- 本地日誌: `./n8n_monitor.log`
- 系統日誌: `journalctl -u n8n-monitor`
- 備份記錄: `./backup/.workflow_hashes.json`

---

## 📝 進階設定

### 自訂服務使用者

編輯 `n8n-monitor.service`：

```ini
[Service]
User=your_username
Group=your_group
```

### 環境變數設定

在 `n8n-monitor.service` 中加入：

```ini
[Service]
Environment="N8N_API_KEY=your_key"
Environment="LOG_LEVEL=DEBUG"
```

### 多實例部署

如果有多個 n8n 實例：

```bash
# 複製目錄
cp -r /home/user/wanin_n8n_bk /home/user/wanin_n8n_bk_prod

# 修改配置檔
vi /home/user/wanin_n8n_bk_prod/config.json

# 複製並重新命名服務文件
cp n8n-monitor.service /etc/systemd/system/n8n-monitor-prod.service

# 修改服務文件中的路徑
sudo vi /etc/systemd/system/n8n-monitor-prod.service
```

---

## ✅ 檢查清單

部署前確認：

- [ ] config.json 設定正確
- [ ] Git 認證已設定（SSH 或 Token）
- [ ] backup/ 目錄已 clone
- [ ] Teams Webhook 已建立並測試
- [ ] 執行 `python3 test_config.py` 確認配置
- [ ] 執行 `python3 test_teams_notification.py` 測試通知

生產環境：

- [ ] 以 systemd 服務運行
- [ ] 設定開機自動啟動
- [ ] 定期檢查日誌
- [ ] 定期測試備份還原
- [ ] 監控磁碟空間

---

## 📞 聯絡資訊

如有問題，請檢查：
1. 日誌檔案 `n8n_monitor.log`
2. 系統日誌 `journalctl -u n8n-monitor`
3. GitHub Issues: https://github.com/guyu1010/wanin_n8n_bk/issues
