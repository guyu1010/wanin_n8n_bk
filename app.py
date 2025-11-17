import requests
import json
import subprocess
import hashlib
import copy
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging
import time


class N8nMonitor:
    """n8n 工作流程監控與備份系統"""

    def __init__(self, config_path: str = 'config.json'):
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
        self.git_remote_url = config['git'].get('remote_url', 'https://github.com/guyu1010/wanin_n8n_bk_data')
        self.notifications = config.get('notifications', {})
        self.schedule_config = config.get('schedule', {
            'enabled': False,
            'interval': 600,
            'run_on_startup': True
        })

        self.headers = {
            'X-N8N-API-KEY': self.api_key,
            'Accept': 'application/json'
        }
        self.timeout = config.get('timeout', 10)
        self.max_retries = config.get('max_retries', 3)

    def setup_logging(self):
        """設定日誌系統"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('n8n_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    # ========== 健康檢查 ==========

    def check_health(self) -> Dict:
        """檢查 n8n 健康狀態"""
        try:
            response = requests.get(f"{self.n8n_url}/healthz", timeout=self.timeout)

            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }

        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': 'Connection timeout', 'timestamp': datetime.now().isoformat()}
        except requests.exceptions.ConnectionError as e:
            return {'status': 'down', 'error': str(e), 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'timestamp': datetime.now().isoformat()}

    def handle_health_change(self, health_status: Dict):
        """處理健康狀態變更"""
        current_status = health_status['status']

        if self.last_health_status != current_status:
            if current_status != 'healthy':
                self.logger.error(f"✗ n8n 服務異常: {current_status}")
                self.send_webhook_notification({
                    'title': 'n8n 服務異常',
                    'status': 'error',
                    'health_status': health_status
                })
            else:
                self.logger.info("✓ n8n 服務已恢復正常")
                self.send_webhook_notification({
                    'title': 'n8n 服務恢復',
                    'status': 'success',
                    'health_status': health_status
                })
            self.last_health_status = current_status

    # ========== 工作流程操作 ==========

    def get_all_workflows(self) -> Optional[List[Dict]]:
        """取得所有工作流程（帶重試機制）"""
        url = f"{self.n8n_url}/api/v1/workflows"

        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json()['data']
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"✗ 無法取得工作流程: {e}")
                    return None

    def get_workflow_detail(self, workflow_id: str) -> Optional[Dict]:
        """取得工作流程詳細內容"""
        try:
            response = requests.get(
                f"{self.n8n_url}/api/v1/workflows/{workflow_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def calculate_hash(self, workflow_data: Dict) -> str:
        """計算工作流程的 hash 值（僅關注功能性變更）"""
        clean_data = copy.deepcopy(workflow_data)

        # 移除不影響功能的欄位
        for field in ['updatedAt', 'createdAt', 'versionId', 'id']:
            clean_data.pop(field, None)

        # 移除 nodes 中的位置資訊
        if 'nodes' in clean_data:
            for node in clean_data['nodes']:
                node.pop('position', None)

        content = json.dumps(clean_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def _analyze_workflow_changes(self, old_workflow: Dict, new_workflow: Dict) -> Dict:
        """分析工作流程的變更"""
        changes = {'added_nodes': [], 'removed_nodes': [], 'modified_nodes': []}

        old_nodes = {node['id']: node for node in old_workflow.get('nodes', [])}
        new_nodes = {node['id']: node for node in new_workflow.get('nodes', [])}

        # 新增的節點
        for node_id, node in new_nodes.items():
            if node_id not in old_nodes:
                changes['added_nodes'].append(
                    f"{node.get('name', 'Unknown')} ({node.get('type', 'Unknown').split('.')[-1]})"
                )

        # 刪除的節點
        for node_id, node in old_nodes.items():
            if node_id not in new_nodes:
                changes['removed_nodes'].append(
                    f"{node.get('name', 'Unknown')} ({node.get('type', 'Unknown').split('.')[-1]})"
                )

        # 修改的節點
        for node_id in set(old_nodes.keys()) & set(new_nodes.keys()):
            old_node = old_nodes[node_id]
            new_node = new_nodes[node_id]
            if (old_node.get('name') != new_node.get('name') or
                old_node.get('type') != new_node.get('type') or
                old_node.get('parameters') != new_node.get('parameters')):
                changes['modified_nodes'].append(
                    f"{new_node.get('name', 'Unknown')} ({new_node.get('type', 'Unknown').split('.')[-1]})"
                )

        return changes

    def _format_change_summary(self, changes: Dict) -> str:
        """格式化變更摘要"""
        summary_parts = []

        for change_type, icon in [
            ('added_nodes', '🆕 新增'),
            ('modified_nodes', '✏️ 修改'),
            ('removed_nodes', '🗑️ 刪除')
        ]:
            nodes = changes[change_type]
            if nodes:
                preview = ', '.join(nodes[:3])
                if len(nodes) > 3:
                    preview += f" 等 {len(nodes)} 個"
                summary_parts.append(f"{icon} {len(nodes)} 個節點: {preview}")

        return '\n  '.join(summary_parts) if summary_parts else '無明顯變更'

    # ========== 敏感資訊處理 ==========

    def sanitize_workflow(self, workflow: Dict) -> Dict:
        """清理工作流程中的敏感資訊"""
        sanitized = copy.deepcopy(workflow)
        sensitive_keys = ['apiKey', 'api_key', 'password', 'token', 'secret', 'credential']

        if 'nodes' in sanitized:
            for node in sanitized['nodes']:
                if 'parameters' in node:
                    self._sanitize_dict(node['parameters'], sensitive_keys)

        return sanitized

    def _sanitize_dict(self, data: Dict, sensitive_keys: List[str]):
        """遞迴混淆字典中的敏感資訊"""
        for key in list(data.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(data[key], str) and len(data[key]) > 10:
                    data[key] = self._obfuscate_value(data[key])
            elif isinstance(data[key], str):
                obfuscated = self._obfuscate_value(data[key])
                if obfuscated != data[key]:
                    data[key] = obfuscated
            elif isinstance(data[key], dict):
                self._sanitize_dict(data[key], sensitive_keys)
            elif isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        self._sanitize_dict(item, sensitive_keys)

    def _obfuscate_value(self, value: str) -> str:
        """混淆敏感值"""
        patterns = [
            (r'=?sk-ant-[a-zA-Z0-9\-_]+', lambda v: f"{v[:10]}{'*' * 20}{v[-4:]}" if len(v) > 14 else f"{v[:6]}{'*' * (len(v) - 6)}"),
            (r'sk-[a-zA-Z0-9]{48}', lambda v: f"{v[:8]}{'*' * 35}{v[-5:]}"),
            (r'eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+', lambda v: f"{v.split('.')[0][:10]}...****...{v.split('.')[-1][-10:]}"),
            (r'gh[po]_[a-zA-Z0-9]{36}', lambda v: f"{v[:8]}{'*' * 25}{v[-5:]}")
        ]

        for pattern, obfuscator in patterns:
            if re.match(pattern, value):
                return obfuscator(value)

        return value

    def save_workflow(self, workflow: Dict) -> Path:
        """儲存工作流程到本地"""
        safe_name = "".join(c for c in workflow['name'] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name[:100] if safe_name else "unnamed_workflow"

        filename = f"{workflow['id']}_{safe_name}.json"
        workflows_dir = self.git_repo_path / 'workflows'
        workflows_dir.mkdir(parents=True, exist_ok=True)

        filepath = workflows_dir / filename
        sanitized_workflow = self.sanitize_workflow(workflow)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sanitized_workflow, f, indent=2, ensure_ascii=False)

        return filepath

    # ========== Git 操作 ==========

    def _run_git_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """執行 Git 命令"""
        return subprocess.run(
            cmd,
            cwd=self.git_repo_path,
            check=check,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

    def git_commit_and_push(self, changed_workflows: List[str]) -> bool:
        """提交變更到 Git"""
        try:
            # Git add
            result = self._run_git_command(['git', 'add', '.'], check=False)
            if result.returncode != 0 and 'ignored by one of your .gitignore files' not in result.stderr:
                self.logger.error(f"✗ Git add 失敗: {result.stderr}")
                return False

            # 檢查是否有變更
            status = self._run_git_command(['git', 'status', '--porcelain'])
            if not status.stdout.strip():
                return True

            # Commit
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_msg = f"[自動備份] {timestamp}\n\n變更的工作流程:\n" + "\n".join(f"- {name}" for name in changed_workflows)

            self._run_git_command(['git', 'commit', '-m', commit_msg])

            # Push (含重試機制)
            for retry in range(3):
                try:
                    self._run_git_command(['git', 'push'])
                    self.logger.info(f"✓ 成功推送 {len(changed_workflows)} 個工作流程到 Git")
                    return True

                except subprocess.CalledProcessError as e:
                    if 'no upstream branch' in e.stderr:
                        self._run_git_command(['git', 'push', '--set-upstream', 'origin', 'main'])
                        return True
                    elif 'rejected' in e.stderr or 'fetch first' in e.stderr:
                        # 先 pull 再重試
                        try:
                            self._run_git_command(['git', 'pull', '--no-rebase', '-X', 'theirs', 'origin', 'main'])
                            continue
                        except subprocess.CalledProcessError:
                            self.logger.warning("⚠️ Pull 失敗，重置到遠端狀態")
                            self._run_git_command(['git', 'fetch', 'origin', 'main'])
                            self._run_git_command(['git', 'reset', '--hard', 'origin/main'])
                            return False
                    elif retry < 2:
                        time.sleep(2 ** retry)
                    else:
                        raise

            return False

        except subprocess.CalledProcessError as e:
            self.logger.error(f"✗ Git 操作失敗: {e.cmd} (返回碼: {e.returncode})")
            return False
        except Exception as e:
            self.logger.error(f"✗ Git 操作發生錯誤: {e}")
            return False

    # ========== 備份流程 ==========

    def backup_workflows(self) -> Dict:
        """執行工作流程備份"""
        result = {
            'success': False,
            'changed_count': 0,
            'total_count': 0,
            'changed_workflows': [],
            'workflow_changes': {},
            'error': None
        }

        # 取得所有工作流程
        workflows = self.get_all_workflows()
        if workflows is None:
            result['error'] = '無法取得工作流程列表'
            return result

        result['total_count'] = len(workflows)

        # 載入上次的 hash 和資料
        hash_file = self.git_repo_path / '.workflow_hashes.json'
        data_file = self.git_repo_path / '.workflow_data.json'

        old_hashes = json.load(open(hash_file, 'r', encoding='utf-8')) if hash_file.exists() else {}
        old_workflows = json.load(open(data_file, 'r', encoding='utf-8')) if data_file.exists() else {}

        new_hashes = {}
        new_workflows = {}
        changed_workflows = []

        # 處理每個工作流程
        for workflow in workflows:
            detail = self.get_workflow_detail(workflow['id'])
            if detail is None:
                continue

            current_hash = self.calculate_hash(detail)
            new_hashes[workflow['id']] = current_hash
            new_workflows[workflow['id']] = detail

            # 檢查是否有變更
            if workflow['id'] not in old_hashes or old_hashes[workflow['id']] != current_hash:
                workflow_name = workflow['name']

                if workflow['id'] in old_workflows:
                    # 分析變更
                    changes = self._analyze_workflow_changes(old_workflows[workflow['id']], detail)
                    has_real_changes = any(changes[k] for k in ['added_nodes', 'modified_nodes', 'removed_nodes'])

                    if has_real_changes:
                        change_summary = self._format_change_summary(changes)
                        self.logger.info(f"📝 {workflow_name}")
                        self.logger.info(f"   {change_summary}")
                        result['workflow_changes'][workflow_name] = change_summary
                        self.save_workflow(detail)
                        changed_workflows.append(workflow_name)
                else:
                    # 新建立的工作流程
                    self.logger.info(f"📝 {workflow_name} (新建立)")
                    result['workflow_changes'][workflow_name] = "🆕 新建立的工作流程"
                    self.save_workflow(detail)
                    changed_workflows.append(workflow_name)

        # 儲存新的 hash 和資料
        with open(hash_file, 'w', encoding='utf-8') as f:
            json.dump(new_hashes, f, indent=2)

        sanitized_workflows = {wid: self.sanitize_workflow(wdata) for wid, wdata in new_workflows.items()}
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_workflows, f, indent=2, ensure_ascii=False)

        result['changed_count'] = len(changed_workflows)
        result['changed_workflows'] = changed_workflows

        # 提交到 Git
        if changed_workflows:
            if self.git_commit_and_push(changed_workflows):
                result['success'] = True
            else:
                result['error'] = 'Git 提交失敗'
        else:
            result['success'] = True

        return result

    # ========== 通知系統 ==========

    def send_webhook_notification(self, data: Dict):
        """發送 Webhook 通知"""
        webhook_config = self.notifications.get('webhook', {})
        if not webhook_config.get('enabled', False):
            return

        try:
            platform = webhook_config.get('platform', 'generic')

            if platform == 'slack':
                payload = {
                    'text': data.get('message', ''),
                    'blocks': [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': data.get('message', '')}}]
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
                payload = self._create_teams_card(data)
            else:
                payload = data

            response = requests.post(webhook_config['url'], json=payload, timeout=10)
            response.raise_for_status()

        except Exception as e:
            self.logger.error(f"✗ Webhook 發送失敗: {e}")

    def _create_teams_card(self, data: Dict) -> Dict:
        """創建 Microsoft Teams Adaptive Card"""
        status = data.get('status', 'info')
        title = data.get('title', 'n8n 監控通知')

        color_map = {'error': 'Attention', 'success': 'Good', 'info': 'Default'}
        icon_map = {'error': '⚠️', 'success': '✅', 'info': 'ℹ️'}

        card = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [{
                        "type": "TextBlock",
                        "text": f"{icon_map.get(status, 'ℹ️')} {title}",
                        "size": "Large",
                        "weight": "Bolder",
                        "color": color_map.get(status, 'Default')
                    }]
                }
            }]
        }

        body = card["attachments"][0]["content"]["body"]

        # 備份完成通知
        if 'backup_result' in data:
            result = data['backup_result']
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            body.append({
                "type": "FactSet",
                "facts": [
                    {"title": "⏰ 備份時間", "value": timestamp},
                    {"title": "📊 總流程數", "value": str(result.get('total_count', 0))},
                    {"title": "✏️ 本次變更", "value": str(result.get('changed_count', 0))}
                ]
            })

            if result.get('changed_workflows'):
                body.append({
                    "type": "TextBlock",
                    "text": "**變更的工作流程：**",
                    "weight": "Bolder",
                    "spacing": "Medium"
                })

                workflow_changes = result.get('workflow_changes', {})
                for workflow_name in result['changed_workflows']:
                    body.append({
                        "type": "TextBlock",
                        "text": f"📝 **{workflow_name}**",
                        "spacing": "Small",
                        "weight": "Bolder"
                    })

                    if workflow_name in workflow_changes:
                        for line in workflow_changes[workflow_name].split('\n'):
                            if line.strip():
                                body.append({
                                    "type": "TextBlock",
                                    "text": f"  {line.strip()}",
                                    "spacing": "None",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "wrap": True
                                })

            card["attachments"][0]["content"]["actions"] = [
                {"type": "Action.OpenUrl", "title": "開啟 n8n", "url": self.n8n_url},
                {"type": "Action.OpenUrl", "title": "查看備份", "url": self.git_remote_url}
            ]

        # 健康狀態通知
        elif 'health_status' in data:
            health = data['health_status']
            body.append({
                "type": "FactSet",
                "facts": [
                    {"title": "⏰ 時間", "value": health.get('timestamp', '')},
                    {"title": "📍 狀態", "value": health.get('status', 'unknown')}
                ]
            })

            if 'error' in health:
                body.append({
                    "type": "TextBlock",
                    "text": f"**錯誤訊息：**\n{health['error']}",
                    "wrap": True,
                    "spacing": "Medium",
                    "color": "Attention"
                })

            card["attachments"][0]["content"]["actions"] = [
                {"type": "Action.OpenUrl", "title": "檢查 n8n", "url": self.n8n_url}
            ]

        # 一般訊息
        else:
            body.append({
                "type": "TextBlock",
                "text": data.get('message', ''),
                "wrap": True
            })

        return card

    # ========== 主執行流程 ==========

    def run(self):
        """執行完整的監控與備份流程"""
        # 健康檢查
        health_status = self.check_health()
        self.handle_health_change(health_status)

        # 執行備份
        if health_status['status'] == 'healthy':
            self.logger.info("🔄 開始備份工作流程...")
            backup_result = self.backup_workflows()

            if backup_result['changed_count'] > 0:
                self.send_webhook_notification({
                    'title': 'n8n工作流程異動 - 備份完成',
                    'status': 'success',
                    'backup_result': backup_result
                })
                self.logger.info(f"✓ 備份完成 ({backup_result['changed_count']}/{backup_result['total_count']} 個變更)")
            else:
                self.logger.info(f"✓ 無變更 (共 {backup_result['total_count']} 個工作流程)")
        else:
            self.logger.warning("⚠️ 服務異常，跳過備份")

    def run_scheduled(self):
        """執行排程模式"""
        run_on_startup = self.schedule_config.get('run_on_startup', True)

        self.logger.info("=" * 50)
        self.logger.info("🚀 n8n 監控系統啟動")
        self.logger.info("⏱️  健康檢查: 每 10 分鐘 | 備份: 每小時")
        self.logger.info("=" * 50)

        # 啟動時執行
        if run_on_startup:
            try:
                self.run()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.logger.error(f"✗ 執行錯誤: {e}")

        # 排程循環
        try:
            while True:
                now = datetime.now()

                # 計算下次執行時間
                next_check = now.replace(second=0, microsecond=0)
                current_minute = now.minute
                next_minute = ((current_minute // 10) + 1) * 10

                if next_minute >= 60:
                    next_check = next_check.replace(minute=0) + timedelta(hours=1)
                else:
                    next_check = next_check.replace(minute=next_minute)

                is_backup_time = (next_minute == 0 or next_minute == 60)
                wait_seconds = (next_check - datetime.now()).total_seconds()

                task_type = "健康檢查 + 備份" if is_backup_time else "健康檢查"
                self.logger.info(f"⏰ 下次執行: {next_check.strftime('%H:%M')} [{task_type}]")

                time.sleep(wait_seconds)

                try:
                    if is_backup_time:
                        self.run()
                    else:
                        health_status = self.check_health()
                        self.handle_health_change(health_status)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"✗ 執行錯誤: {e}")

        except KeyboardInterrupt:
            self.logger.info("\n" + "=" * 50)
            self.logger.info("⛔ 監控系統已停止")
            self.logger.info("=" * 50)


if __name__ == '__main__':
    monitor = N8nMonitor('config.json')

    if monitor.schedule_config.get('enabled', False):
        monitor.run_scheduled()
    else:
        monitor.run()
