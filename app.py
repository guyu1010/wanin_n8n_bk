import requests
import json
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging
import time

class N8nMonitor:
    def __init__(self, config_path: str = 'config.json'):
        """初始化監控系統"""
        self.load_config(config_path)
        self.setup_logging()
        self.last_health_status = None
        
    def load_config(self, config_path: str):
        """載入設定檔"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.n8n_url = config['n8n']['url'].rstrip('/')
        self.api_key = config['n8n']['api_key']
        self.git_repo_path = Path(config['git']['repo_path'])

        # 通知設定
        self.notifications = config.get('notifications', {})

        # 排程設定
        self.schedule_config = config.get('schedule', {
            'enabled': False,
            'interval': 600,
            'run_on_startup': True
        })

        # HTTP 請求設定
        self.headers = {
            'X-N8N-API-KEY': self.api_key,
            'Accept': 'application/json'
        }
        self.timeout = config.get('timeout', 10)
        self.max_retries = config.get('max_retries', 3)
    
    def setup_logging(self):
        """設定日誌"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('n8n_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_health(self) -> Dict:
        """檢查 n8n 健康狀態"""
        try:
            # 方法 1: 使用 n8n 的 healthz endpoint
            health_url = f"{self.n8n_url}/healthz"
            response = requests.get(health_url, timeout=self.timeout)
            
            if response.status_code == 200:
                self.logger.info("✓ n8n 服務正常運行")
                return {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                self.logger.warning(f"n8n 回應異常: HTTP {response.status_code}")
                return {
                    'status': 'unhealthy',
                    'error': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except requests.exceptions.Timeout:
            self.logger.error("✗ n8n 連線逾時")
            return {
                'status': 'timeout',
                'error': 'Connection timeout',
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"✗ 無法連線到 n8n: {e}")
            return {
                'status': 'down',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"✗ 健康檢查發生錯誤: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_all_workflows(self) -> Optional[List[Dict]]:
        """取得所有工作流程(帶重試機制)"""
        url = f"{self.n8n_url}/api/v1/workflows"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                workflows = response.json()['data']
                self.logger.info(f"成功取得 {len(workflows)} 個工作流程")
                return workflows
            except Exception as e:
                self.logger.warning(f"取得工作流程失敗 (嘗試 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                else:
                    self.logger.error("已達最大重試次數")
                    return None
    
    def get_workflow_detail(self, workflow_id: str) -> Optional[Dict]:
        """取得工作流程詳細內容"""
        url = f"{self.n8n_url}/api/v1/workflows/{workflow_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"取得工作流程 {workflow_id} 失敗: {e}")
            return None
    
    def calculate_hash(self, workflow_data: Dict) -> str:
        """計算工作流程的 hash 值"""
        # 移除時間戳記等不影響邏輯的欄位
        clean_data = {k: v for k, v in workflow_data.items()
                     if k not in ['updatedAt', 'createdAt']}
        content = json.dumps(clean_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def _analyze_workflow_changes(self, old_workflow: Dict, new_workflow: Dict) -> Dict:
        """分析工作流程的變更"""
        changes = {
            'added_nodes': [],
            'removed_nodes': [],
            'modified_nodes': []
        }

        old_nodes = {node['id']: node for node in old_workflow.get('nodes', [])}
        new_nodes = {node['id']: node for node in new_workflow.get('nodes', [])}

        for node_id, node in new_nodes.items():
            if node_id not in old_nodes:
                changes['added_nodes'].append(f"{node.get('name', 'Unknown')} ({node.get('type', 'Unknown').split('.')[-1]})")

        for node_id, node in old_nodes.items():
            if node_id not in new_nodes:
                changes['removed_nodes'].append(f"{node.get('name', 'Unknown')} ({node.get('type', 'Unknown').split('.')[-1]})")

        for node_id in set(old_nodes.keys()) & set(new_nodes.keys()):
            old_node = old_nodes[node_id]
            new_node = new_nodes[node_id]
            if (old_node.get('name') != new_node.get('name') or
                old_node.get('type') != new_node.get('type') or
                old_node.get('parameters') != new_node.get('parameters')):
                changes['modified_nodes'].append(f"{new_node.get('name', 'Unknown')} ({new_node.get('type', 'Unknown').split('.')[-1]})")

        return changes

    def _format_change_summary(self, changes: Dict) -> str:
        """格式化變更摘要為簡潔文字"""
        summary_parts = []

        if changes['added_nodes']:
            summary_parts.append(f"🆕 新增 {len(changes['added_nodes'])} 個節點: {', '.join(changes['added_nodes'][:3])}")
            if len(changes['added_nodes']) > 3:
                summary_parts[-1] += f" 等 {len(changes['added_nodes'])} 個"

        if changes['modified_nodes']:
            summary_parts.append(f"✏️ 修改 {len(changes['modified_nodes'])} 個節點: {', '.join(changes['modified_nodes'][:3])}")
            if len(changes['modified_nodes']) > 3:
                summary_parts[-1] += f" 等 {len(changes['modified_nodes'])} 個"

        if changes['removed_nodes']:
            summary_parts.append(f"🗑️ 刪除 {len(changes['removed_nodes'])} 個節點: {', '.join(changes['removed_nodes'][:3])}")
            if len(changes['removed_nodes']) > 3:
                summary_parts[-1] += f" 等 {len(changes['removed_nodes'])} 個"

        return '\n  '.join(summary_parts) if summary_parts else '無明顯變更'

    def sanitize_workflow(self, workflow: Dict) -> Dict:
        """清理工作流程中的敏感資訊"""
        import copy
        sanitized = copy.deepcopy(workflow)

        # 清理節點中的敏感參數
        sensitive_keys = ['apiKey', 'api_key', 'password', 'token', 'secret', 'credential']

        if 'nodes' in sanitized:
            for node in sanitized['nodes']:
                if 'parameters' in node:
                    for key in list(node['parameters'].keys()):
                        # 檢查是否為敏感欄位
                        if any(sensitive in key.lower() for sensitive in sensitive_keys):
                            node['parameters'][key] = "***REMOVED***"
                        # 遞迴清理巢狀結構
                        elif isinstance(node['parameters'][key], dict):
                            self._sanitize_dict(node['parameters'][key], sensitive_keys)

        return sanitized

    def _obfuscate_value(self, value: str) -> str:
        """簡單混淆敏感值（保留前後部分，中間用 * 代替）"""
        import re

        # Anthropic API keys: sk-ant-xxx
        if re.match(r'=?sk-ant-[a-zA-Z0-9\-_]+', value):
            # 保留前10個字元和後4個字元
            if len(value) > 14:
                prefix = value[:10]
                suffix = value[-4:]
                return f"{prefix}{'*' * 20}{suffix}"
            return value[:6] + '*' * (len(value) - 6)

        # OpenAI API keys: sk-xxx
        if re.match(r'sk-[a-zA-Z0-9]{48}', value):
            return value[:8] + '*' * 35 + value[-5:]

        # JWT tokens
        if re.match(r'eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+', value):
            parts = value.split('.')
            if len(parts) >= 2:
                return f"{parts[0][:10]}...****...{parts[-1][-10:]}"

        # GitHub tokens
        if re.match(r'gh[po]_[a-zA-Z0-9]{36}', value):
            return value[:8] + '*' * 25 + value[-5:]

        return value

    def _sanitize_dict(self, data: Dict, sensitive_keys: List[str]):
        """遞迴混淆字典中的敏感資訊"""
        for key in list(data.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                # 只混淆字串值
                if isinstance(data[key], str) and len(data[key]) > 10:
                    data[key] = self._obfuscate_value(data[key])
            elif isinstance(data[key], str):
                # 檢查字串值是否包含敏感模式
                obfuscated = self._obfuscate_value(data[key])
                if obfuscated != data[key]:
                    data[key] = obfuscated
            elif isinstance(data[key], dict):
                self._sanitize_dict(data[key], sensitive_keys)
            elif isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        self._sanitize_dict(item, sensitive_keys)

    def save_workflow(self, workflow: Dict) -> Path:
        """儲存工作流程到本地"""
        # 清理檔名中的特殊字元
        safe_name = "".join(c for c in workflow['name'] if c.isalnum() or c in (' ', '-', '_')).strip()

        # 如果清理後是空字串，使用預設名稱
        if not safe_name:
            safe_name = "unnamed_workflow"
            self.logger.warning(f"工作流程 ID {workflow['id']} 的名稱無法清理，使用預設名稱")

        # 限制檔名長度，避免過長
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
            self.logger.info(f"檔名過長，已截斷至 100 字元")

        filename = f"{workflow['id']}_{safe_name}.json"

        workflows_dir = self.git_repo_path / 'workflows'
        workflows_dir.mkdir(parents=True, exist_ok=True)

        filepath = workflows_dir / filename

        # 簡單混淆敏感資訊後儲存
        sanitized_workflow = self.sanitize_workflow(workflow)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sanitized_workflow, f, indent=2, ensure_ascii=False)

        return filepath
    
    def git_commit_and_push(self, changed_workflows: List[str]) -> bool:
        """提交變更到 Git（含重試機制）"""
        try:
            self.logger.info("=" * 50)
            self.logger.info("開始執行 Git 操作")

            # 確保在 git repo 目錄，執行 git add
            self.logger.info(f"執行: git add . (在目錄: {self.git_repo_path})")
            result = subprocess.run(['git', 'add', '.'],
                         cwd=self.git_repo_path, check=True,
                         capture_output=True, text=True, encoding='utf-8')

            # 檢查是否有變更
            self.logger.info("檢查 git status...")
            status = subprocess.run(['git', 'status', '--porcelain'],
                                  cwd=self.git_repo_path, check=True,
                                  capture_output=True, text=True, encoding='utf-8')

            if not status.stdout.strip():
                self.logger.info("沒有需要提交的變更")
                return True

            self.logger.info(f"偵測到變更檔案:\n{status.stdout}")

            # 建立 commit message
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_msg = f"[自動備份] {timestamp}\n\n變更的工作流程:\n"
            commit_msg += "\n".join(f"- {name}" for name in changed_workflows)

            # 執行 commit
            self.logger.info("執行: git commit")
            subprocess.run(['git', 'commit', '-m', commit_msg],
                         cwd=self.git_repo_path, check=True,
                         capture_output=True, text=True, encoding='utf-8')
            self.logger.info("✓ Commit 成功")

            # 執行 push（含重試機制）
            max_push_retries = 3
            for retry in range(max_push_retries):
                try:
                    self.logger.info(f"執行: git push (嘗試 {retry + 1}/{max_push_retries})")
                    push_result = subprocess.run(['git', 'push'],
                                 cwd=self.git_repo_path, check=True,
                                 capture_output=True, text=True, encoding='utf-8')

                    if push_result.stdout:
                        self.logger.info(f"Push 輸出: {push_result.stdout}")
                    if push_result.stderr:
                        self.logger.info(f"Push 訊息: {push_result.stderr}")

                    self.logger.info(f"✓ 成功提交並推送 {len(changed_workflows)} 個工作流程到 Git")
                    self.logger.info("=" * 50)
                    return True

                except subprocess.CalledProcessError as e:
                    # 如果是第一次 push，需要設定 upstream
                    if 'no upstream branch' in e.stderr:
                        self.logger.info("偵測到首次推送，執行: git push --set-upstream origin main")
                        push_result = subprocess.run(['git', 'push', '--set-upstream', 'origin', 'main'],
                                     cwd=self.git_repo_path, check=True,
                                     capture_output=True, text=True, encoding='utf-8')
                        self.logger.info("✓ 成功推送到遠端")
                        return True

                    # 如果被拒絕（遠端有更新），先 pull 再 push
                    elif 'rejected' in e.stderr or 'fetch first' in e.stderr:
                        self.logger.warning("⚠️ 推送被拒絕，遠端有更新")
                        self.logger.info("執行: git pull (使用 merge 策略，衝突時優先採用遠端版本)")

                        try:
                            # 使用 merge 策略，衝突時自動選擇遠端版本
                            pull_result = subprocess.run([
                                'git', 'pull', '--no-rebase',
                                '-X', 'theirs',  # 衝突時選擇遠端版本
                                'origin', 'main'
                            ], cwd=self.git_repo_path, check=True,
                               capture_output=True, text=True, encoding='utf-8')

                            self.logger.info("✓ 成功拉取並合併遠端變更")

                            # 繼續下一輪重試
                            continue

                        except subprocess.CalledProcessError as pull_error:
                            self.logger.error(f"✗ Pull 失敗: {pull_error.stderr}")

                            # 如果 merge 也失敗，嘗試重置到遠端狀態
                            self.logger.warning("⚠️ 嘗試重置到遠端最新狀態")
                            try:
                                subprocess.run(['git', 'fetch', 'origin', 'main'],
                                             cwd=self.git_repo_path, check=True,
                                             capture_output=True, text=True, encoding='utf-8')
                                subprocess.run(['git', 'reset', '--hard', 'origin/main'],
                                             cwd=self.git_repo_path, check=True,
                                             capture_output=True, text=True, encoding='utf-8')
                                self.logger.info("✓ 已重置到遠端最新狀態")
                                return False  # 本次推送放棄，下次會重新備份
                            except subprocess.CalledProcessError:
                                self.logger.error("✗ 無法重置到遠端狀態")
                                return False

                    # 其他錯誤
                    elif retry < max_push_retries - 1:
                        wait_time = 2 ** retry  # 指數退避: 1s, 2s, 4s
                        self.logger.warning(f"Push 失敗，{wait_time} 秒後重試...")
                        time.sleep(wait_time)
                    else:
                        # 最後一次重試失敗
                        raise

            # 如果所有重試都失敗
            self.logger.error("已達最大重試次數，推送失敗")
            return False

        except subprocess.CalledProcessError as e:
            self.logger.error("=" * 50)
            self.logger.error(f"✗ Git 操作失敗")
            self.logger.error(f"指令: {e.cmd}")
            self.logger.error(f"返回碼: {e.returncode}")
            if e.stdout:
                self.logger.error(f"標準輸出: {e.stdout}")
            if e.stderr:
                self.logger.error(f"錯誤輸出: {e.stderr}")
            self.logger.error("=" * 50)
            return False
        except Exception as e:
            self.logger.error(f"✗ Git 操作發生未預期錯誤: {e}")
            return False
    
    def backup_workflows(self) -> Dict:
        """執行工作流程備份"""
        self.logger.info("=" * 50)
        self.logger.info("開始備份工作流程")

        result = {
            'success': False,
            'changed_count': 0,
            'total_count': 0,
            'changed_workflows': [],
            'workflow_changes': {},  # 新增：儲存每個 workflow 的變更詳情
            'error': None
        }

        # 取得所有工作流程
        workflows = self.get_all_workflows()
        if workflows is None:
            result['error'] = '無法取得工作流程列表'
            return result

        result['total_count'] = len(workflows)

        # 載入上次的 hash 和完整資料
        hash_file = self.git_repo_path / '.workflow_hashes.json'
        data_file = self.git_repo_path / '.workflow_data.json'
        old_hashes = {}
        old_workflows = {}

        if hash_file.exists():
            with open(hash_file, 'r', encoding='utf-8') as f:
                old_hashes = json.load(f)

        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                old_workflows = json.load(f)

        new_hashes = {}
        new_workflows = {}
        changed_workflows = []

        # 處理每個工作流程
        for workflow in workflows:
            detail = self.get_workflow_detail(workflow['id'])
            if detail is None:
                continue

            # 計算 hash
            current_hash = self.calculate_hash(detail)
            new_hashes[workflow['id']] = current_hash
            new_workflows[workflow['id']] = detail

            # 檢查是否有變更
            if workflow['id'] not in old_hashes or old_hashes[workflow['id']] != current_hash:
                workflow_name = workflow['name']
                self.logger.info(f"偵測到變更: {workflow_name} (ID: {workflow['id']})")

                # 分析變更（如果有舊版本）
                if workflow['id'] in old_workflows:
                    changes = self._analyze_workflow_changes(old_workflows[workflow['id']], detail)
                    change_summary = self._format_change_summary(changes)
                    self.logger.info(f"  {change_summary}")
                    result['workflow_changes'][workflow_name] = change_summary
                else:
                    # 新建立的 workflow
                    result['workflow_changes'][workflow_name] = "🆕 新建立的工作流程"
                    self.logger.info(f"  🆕 新建立的工作流程")

                self.save_workflow(detail)
                changed_workflows.append(workflow_name)

        # 儲存新的 hash 和資料
        with open(hash_file, 'w', encoding='utf-8') as f:
            json.dump(new_hashes, f, indent=2)

        # 儲存 workflow 資料時也要 sanitize（避免敏感資訊外洩）
        sanitized_workflows = {}
        for workflow_id, workflow_data in new_workflows.items():
            sanitized_workflows[workflow_id] = self.sanitize_workflow(workflow_data)

        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_workflows, f, indent=2, ensure_ascii=False)

        result['changed_count'] = len(changed_workflows)
        result['changed_workflows'] = changed_workflows

        # 如果有變更,提交到 Git
        if changed_workflows:
            if self.git_commit_and_push(changed_workflows):
                result['success'] = True
            else:
                result['error'] = 'Git 提交失敗'
        else:
            self.logger.info("沒有偵測到工作流程變更")
            result['success'] = True

        return result
    
    def send_webhook_notification(self, data: Dict):
        """發送 Webhook 通知 (Slack, Discord, Teams, etc.)"""
        webhook_config = self.notifications.get('webhook', {})
        if not webhook_config.get('enabled', False):
            return

        try:
            # 根據不同平台格式化訊息
            platform = webhook_config.get('platform', 'generic')

            if platform == 'slack':
                payload = {
                    'text': data.get('message', ''),
                    'blocks': [
                        {
                            'type': 'section',
                            'text': {'type': 'mrkdwn', 'text': data.get('message', '')}
                        }
                    ]
                }
            elif platform == 'discord':
                payload = {
                    'content': data.get('message', ''),
                    'embeds': [{
                        'title': data.get('title', 'n8n 監控通知'),
                        'description': data.get('message', ''),
                        'color': 15158332 if data.get('status') == 'error' else 3066993
                    }]
                }
            elif platform == 'teams':
                # 建立完整的 Adaptive Card 結構
                payload = self._create_teams_card(data)
            else:  # generic
                payload = data

            response = requests.post(
                webhook_config['url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            self.logger.info("✓ Webhook 通知已發送")

        except Exception as e:
            self.logger.error(f"發送 Webhook 失敗: {e}")

    def _create_teams_card(self, data: Dict) -> Dict:
        """創建 Microsoft Teams Adaptive Card"""
        status = data.get('status', 'info')
        title = data.get('title', 'n8n 監控通知')

        # 根據狀態設定顏色和圖示
        if status == 'error':
            color = 'Attention'  # 紅色
            icon = '⚠️'
        elif status == 'success':
            color = 'Good'  # 綠色
            icon = '✅'
        else:
            color = 'Default'  # 灰色
            icon = 'ℹ️'

        # 基本卡片結構
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"{icon} {title}",
                                "size": "Large",
                                "weight": "Bolder",
                                "color": color
                            }
                        ]
                    }
                }
            ]
        }

        body = card["attachments"][0]["content"]["body"]

        # 根據不同的通知類型添加內容
        if 'backup_result' in data:
            # 備份完成通知
            result = data['backup_result']
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 添加時間和統計資訊
            body.append({
                "type": "FactSet",
                "facts": [
                    {"title": "⏰ 備份時間", "value": timestamp},
                    {"title": "📊 總流程數", "value": str(result.get('total_count', 0))},
                    {"title": "✏️ 本次變更", "value": str(result.get('changed_count', 0))}
                ]
            })

            # 如果有變更，顯示變更列表和詳情
            if result.get('changed_workflows'):
                body.append({
                    "type": "TextBlock",
                    "text": "**變更的工作流程：**",
                    "weight": "Bolder",
                    "spacing": "Medium"
                })

                workflow_changes = result.get('workflow_changes', {})
                for workflow_name in result['changed_workflows']:
                    # 顯示工作流程名稱
                    body.append({
                        "type": "TextBlock",
                        "text": f"📝 **{workflow_name}**",
                        "spacing": "Small",
                        "weight": "Bolder"
                    })

                    # 顯示變更摘要（如果有）
                    if workflow_name in workflow_changes:
                        change_summary = workflow_changes[workflow_name]
                        # 將多行摘要分開顯示
                        for line in change_summary.split('\n'):
                            if line.strip():
                                body.append({
                                    "type": "TextBlock",
                                    "text": f"  {line.strip()}",
                                    "spacing": "None",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "wrap": True
                                })

            # 添加連結按鈕
            card["attachments"][0]["content"]["actions"] = [
                {
                    "type": "Action.OpenUrl",
                    "title": "開啟 n8n",
                    "url": self.n8n_url
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "查看備份",
                    "url": "https://github.com/guyu1010/wanin_n8n_bk_data"
                }
            ]

        elif 'health_status' in data:
            # 健康狀態變更通知
            health = data['health_status']

            body.append({
                "type": "FactSet",
                "facts": [
                    {"title": "⏰ 時間", "value": health.get('timestamp', '')},
                    {"title": "📍 狀態", "value": health.get('status', 'unknown')}
                ]
            })

            # 如果有錯誤訊息
            if 'error' in health:
                body.append({
                    "type": "TextBlock",
                    "text": f"**錯誤訊息：**\n{health['error']}",
                    "wrap": True,
                    "spacing": "Medium",
                    "color": "Attention"
                })

            # 添加連結按鈕
            card["attachments"][0]["content"]["actions"] = [
                {
                    "type": "Action.OpenUrl",
                    "title": "檢查 n8n",
                    "url": self.n8n_url
                }
            ]
        else:
            # 一般訊息
            message = data.get('message', '')
            body.append({
                "type": "TextBlock",
                "text": message,
                "wrap": True
            })

        return card

    def handle_health_change(self, health_status: Dict):
        """處理健康狀態變更"""
        current_status = health_status['status']

        # 如果狀態改變,發送通知
        if self.last_health_status != current_status:
            if current_status != 'healthy':
                # n8n 出現問題
                self.logger.error(f"n8n 服務異常: {current_status}")
                self.send_webhook_notification({
                    'title': 'n8n 服務異常',
                    'status': 'error',
                    'health_status': health_status
                })
            else:
                # n8n 恢復正常
                self.logger.info("n8n 服務已恢復正常")
                self.send_webhook_notification({
                    'title': 'n8n 服務恢復',
                    'status': 'success',
                    'health_status': health_status
                })

            self.last_health_status = current_status
    
    def run(self):
        """執行完整的監控與備份流程"""
        self.logger.info("開始執行 n8n 監控與備份")
        
        # 1. 檢查健康狀態
        health_status = self.check_health()
        self.handle_health_change(health_status)
        
        # 2. 如果 n8n 正常,執行備份
        if health_status['status'] == 'healthy':
            backup_result = self.backup_workflows()

            if backup_result['changed_count'] > 0:
                self.send_webhook_notification({
                    'title': 'n8n 工作流程備份完成',
                    'status': 'success',
                    'backup_result': backup_result
                })
        else:
            self.logger.warning("由於 n8n 服務異常,跳過備份作業")
        
        self.logger.info("監控與備份流程結束")
        self.logger.info("=" * 50)

    def run_scheduled(self):
        """執行排程模式 - 在每小時的 00 分和 30 分執行"""
        run_on_startup = self.schedule_config.get('run_on_startup', True)

        self.logger.info("=" * 50)
        self.logger.info("🚀 n8n 監控系統啟動（排程模式）")
        self.logger.info("⏱️  執行時間: 每小時的 00 分和 30 分")
        self.logger.info(f"🔄 啟動時執行: {'是' if run_on_startup else '否'}")
        self.logger.info("=" * 50)

        # 如果設定為啟動時執行，立即執行一次
        if run_on_startup:
            self.logger.info("⚡ 立即執行第一次監控...")
            try:
                self.run()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.logger.error(f"執行時發生錯誤: {e}")

        # 進入排程循環
        try:
            while True:
                # 計算下次執行時間（每小時的 00 分或 30 分）
                now = datetime.now()
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

                # 計算需要等待的秒數
                wait_seconds = (next_run - datetime.now()).total_seconds()

                self.logger.info(f"⏰ 下次執行時間: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (等待 {int(wait_seconds)} 秒)")
                time.sleep(wait_seconds)

                # 執行監控與備份
                try:
                    self.run()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"執行時發生錯誤: {e}")

        except KeyboardInterrupt:
            self.logger.info("\n")
            self.logger.info("=" * 50)
            self.logger.info("⛔ 收到中斷訊號，正在停止監控系統...")
            self.logger.info("=" * 50)

if __name__ == '__main__':
    import sys

    monitor = N8nMonitor('config.json')

    # 檢查是否啟用排程模式
    if monitor.schedule_config.get('enabled', False):
        monitor.run_scheduled()
    else:
        # 單次執行模式（兼容舊版使用方式）
        monitor.run()