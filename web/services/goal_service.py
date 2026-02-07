"""
进化目标服务 - 桥接 EvolutionGoalManager
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _get_goal_manager():
    """获取目标管理器"""
    from prokaryote_agent.goal_manager import EvolutionGoalManager
    goal_file = PROJECT_ROOT / "evolution_goals.md"
    mgr = EvolutionGoalManager(str(goal_file))
    mgr.load_goals()
    return mgr


def get_all_goals() -> List[Dict[str, Any]]:
    """获取所有目标"""
    mgr = _get_goal_manager()
    result = []
    for goal in mgr.goals.values():
        result.append({
            'id': goal.id,
            'title': goal.title,
            'description': goal.description,
            'status': goal.status.value,
            'priority': goal.priority.value,
            'category': goal.category,
            'acceptance_criteria': goal.acceptance_criteria,
            'dependencies': goal.dependencies,
            'capabilities': goal.capabilities,
            'created_at': str(goal.created_at),
            'completed_at': str(goal.completed_at) if goal.completed_at else None,
        })
    return result


def get_goal_stats() -> Dict[str, Any]:
    """获取目标统计"""
    mgr = _get_goal_manager()
    return mgr.get_statistics()


def update_goal_status(goal_id: str, status: str) -> Dict:
    """更新目标状态"""
    from prokaryote_agent.goal_manager import GoalStatus
    mgr = _get_goal_manager()
    if goal_id not in mgr.goals:
        return {'success': False, 'error': f'目标 {goal_id} 不存在'}

    goal = mgr.goals[goal_id]
    try:
        goal.status = GoalStatus(status)
        mgr._save_goals()
        return {'success': True}
    except ValueError:
        return {'success': False, 'error': f'无效状态: {status}'}


def create_goal(title: str, description: str = "",
                priority: str = "medium",
                acceptance_criteria: List[str] = None) -> Dict:
    """创建新目标 - 追加到 evolution_goals.md"""
    goal_file = PROJECT_ROOT / "evolution_goals.md"

    # 构建 Markdown 内容
    priority_marks = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '',
        'low': '🟢',
    }
    mark = priority_marks.get(priority, '')
    line = f"- [ ] {mark}{title}".strip()

    lines = [f"\n{line}"]
    if description:
        lines.append(f"  {description}")
    if acceptance_criteria:
        for c in acceptance_criteria:
            lines.append(f"  - {c}")

    content = '\n'.join(lines) + '\n'

    with open(goal_file, 'a', encoding='utf-8') as f:
        f.write(content)

    return {'success': True, 'message': f'已添加目标: {title}'}


def delete_goal(goal_id: str) -> Dict:
    """删除目标 - 从文件中移除"""
    mgr = _get_goal_manager()
    if goal_id not in mgr.goals:
        return {'success': False, 'error': f'目标 {goal_id} 不存在'}

    goal = mgr.goals[goal_id]
    goal_file = PROJECT_ROOT / "evolution_goals.md"
    content = goal_file.read_text(encoding='utf-8')

    # 尝试移除目标行
    import re
    # 移除 "- [ ] title" 或 "- [x] title"
    escaped_title = re.escape(goal.title.strip())
    pattern = rf'- \[.\] .*?{escaped_title}.*?\n(?:  .*\n)*'
    new_content = re.sub(pattern, '', content, count=1)

    goal_file.write_text(new_content, encoding='utf-8')
    return {'success': True}
