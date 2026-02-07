"""
进化服务 - 系统状态和进化控制
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_system_status() -> Dict[str, Any]:
    """获取系统运行状态"""
    status_file = PROJECT_ROOT / "prokaryote_agent" / "daemon_status.json"

    status = {
        'running': False,
        'pid': None,
        'started_at': None,
        'last_check': None,
        'evolution_count': 0,
        'current_generation': 0,
        'domain': 'unknown',
    }

    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            status.update(data)

            # 检查进程是否还活着
            pid = status.get('pid')
            if pid:
                try:
                    os.kill(pid, 0)
                    status['running'] = True
                except (OSError, ProcessLookupError):
                    status['running'] = False
        except Exception as e:
            logger.warning("读取状态文件失败: %s", e)

    return status


def get_daemon_config() -> Dict[str, Any]:
    """获取守护进程配置"""
    config_path = PROJECT_ROOT / "prokaryote_agent" / "daemon_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def update_daemon_config(updates: Dict[str, Any]) -> Dict:
    """更新守护进程配置"""
    config_path = PROJECT_ROOT / "prokaryote_agent" / "daemon_config.json"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 深度合并更新
    _deep_merge(config, updates)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return {'success': True, 'message': '配置已更新'}


def _deep_merge(base: Dict, update: Dict):
    """深度合并字典"""
    for key, value in update.items():
        if (key in base and isinstance(base[key], dict)
                and isinstance(value, dict)):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_evolution_logs(limit: int = 100,
                       offset: int = 0) -> Dict[str, Any]:
    """获取进化日志"""
    log_file = PROJECT_ROOT / "prokaryote_agent" / "log" / "daemon.log"
    lines = []

    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            # 倒序，最新的在前
            all_lines.reverse()
            total = len(all_lines)
            selected = all_lines[offset:offset + limit]

            for line in selected:
                line = line.strip()
                if not line:
                    continue
                lines.append(_parse_log_line(line))

        except Exception as e:
            logger.warning("读取日志失败: %s", e)
            total = 0
    else:
        total = 0

    return {
        'total': total,
        'offset': offset,
        'limit': limit,
        'lines': lines,
    }


def _parse_log_line(line: str) -> Dict[str, str]:
    """解析日志行"""
    # 格式: 2026-02-07 16:36:01,209 - module - LEVEL - message
    parts = line.split(' - ', 3)
    if len(parts) >= 4:
        return {
            'timestamp': parts[0].strip(),
            'module': parts[1].strip(),
            'level': parts[2].strip(),
            'message': parts[3].strip(),
        }
    return {
        'timestamp': '',
        'module': '',
        'level': 'INFO',
        'message': line,
    }


def get_knowledge_list(domain: str = None,
                       query: str = None) -> List[Dict]:
    """获取知识列表"""
    try:
        from prokaryote_agent.knowledge import get_knowledge_base
        kb = get_knowledge_base()

        if query:
            items = kb.search(query, limit=50)
        else:
            items = kb.list_all(domain=domain, limit=50)

        result = []
        for item in items:
            if hasattr(item, '__dict__'):
                result.append({
                    'id': getattr(item, 'id', ''),
                    'title': getattr(item, 'title', ''),
                    'domain': getattr(item, 'domain', ''),
                    'category': getattr(item, 'category', ''),
                    'keywords': getattr(item, 'keywords', []),
                    'quality_score': getattr(item, 'quality_score', 0),
                    'created_at': getattr(item, 'created_at', ''),
                })
            elif isinstance(item, dict):
                result.append(item)
        return result
    except Exception as e:
        logger.warning("获取知识列表失败: %s", e)
        return []


def get_knowledge_detail(knowledge_id: str) -> Dict:
    """获取知识详情"""
    try:
        from prokaryote_agent.knowledge import get_knowledge_base
        kb = get_knowledge_base()
        item = kb.get(knowledge_id)
        if item:
            if hasattr(item, '__dict__'):
                from dataclasses import asdict
                return asdict(item)
            return item
        return {'error': '未找到'}
    except Exception as e:
        return {'error': str(e)}
