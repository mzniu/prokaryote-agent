"""
技能树服务 - 桥接 SkillEvolutionCoordinator 和 SkillTreeManager
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_daemon_config() -> Dict:
    """加载守护进程配置"""
    config_path = PROJECT_ROOT / "prokaryote_agent" / "daemon_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _resolve_path(relative_path: str) -> Path:
    """解析相对路径为绝对路径"""
    p = Path(relative_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def get_coordinator():
    """获取技能协调器实例"""
    from prokaryote_agent.specialization.skill_coordinator import (
        SkillEvolutionCoordinator
    )
    config = _load_daemon_config()
    spec = config.get('specialization', {})
    general_path = _resolve_path(
        spec.get('general_tree_path',
                  './prokaryote_agent/specialization/domains/general_tree.json')
    )
    domain_path = _resolve_path(
        spec.get('skill_tree_path',
                  './prokaryote_agent/specialization/domains/legal_tree.json')
    )
    return SkillEvolutionCoordinator(
        str(general_path), str(domain_path),
        enable_ai_optimization=False  # Web 查询不触发 AI
    )


def get_tree_stats() -> Dict[str, Any]:
    """获取双树统计"""
    coord = get_coordinator()
    return coord.get_stats()


def get_general_tree() -> Dict[str, Any]:
    """获取通用技能树"""
    config = _load_daemon_config()
    spec = config.get('specialization', {})
    path = _resolve_path(
        spec.get('general_tree_path',
                  './prokaryote_agent/specialization/domains/general_tree.json')
    )
    with open(path, 'r', encoding='utf-8') as f:
        tree = json.load(f)

    # 添加 id 到每个技能
    for skill_id, skill in tree.get('skills', {}).items():
        skill['id'] = skill_id

    return tree


def get_domain_tree() -> Dict[str, Any]:
    """获取专业技能树"""
    config = _load_daemon_config()
    spec = config.get('specialization', {})
    path = _resolve_path(
        spec.get('skill_tree_path',
                  './prokaryote_agent/specialization/domains/legal_tree.json')
    )
    with open(path, 'r', encoding='utf-8') as f:
        tree = json.load(f)

    for skill_id, skill in tree.get('skills', {}).items():
        skill['id'] = skill_id

    return tree


def get_skill_registry() -> Dict[str, Any]:
    """获取已学技能注册表"""
    path = PROJECT_ROOT / "prokaryote_agent" / "skills" / "library" / "skill_registry.json"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'skills': {}}


def update_skill_priority(tree_type: str, skill_id: str,
                          priority: float) -> Dict:
    """更新技能优先级"""
    tree = get_general_tree() if tree_type == 'general' else get_domain_tree()
    skills = tree.get('skills', {})
    if skill_id not in skills:
        return {'success': False, 'error': f'技能 {skill_id} 不存在'}

    skills[skill_id]['priority_boost'] = priority

    # 保存
    config = _load_daemon_config()
    spec = config.get('specialization', {})
    key = 'general_tree_path' if tree_type == 'general' else 'skill_tree_path'
    path = _resolve_path(spec.get(key, ''))

    # 移除临时 id 字段再保存
    for sid, s in skills.items():
        s.pop('id', None)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    return {'success': True}


def unlock_skill(tree_type: str, skill_id: str) -> Dict:
    """手动解锁技能"""
    tree = get_general_tree() if tree_type == 'general' else get_domain_tree()
    skills = tree.get('skills', {})
    if skill_id not in skills:
        return {'success': False, 'error': f'技能 {skill_id} 不存在'}

    skills[skill_id]['unlocked'] = True

    config = _load_daemon_config()
    spec = config.get('specialization', {})
    key = 'general_tree_path' if tree_type == 'general' else 'skill_tree_path'
    path = _resolve_path(spec.get(key, ''))

    for sid, s in skills.items():
        s.pop('id', None)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    return {'success': True, 'message': f'已解锁 {skill_id}'}


def add_custom_skill(tree_type: str,
                     skill_data: Dict) -> Dict:
    """添加自定义技能"""
    tree = get_general_tree() if tree_type == 'general' else get_domain_tree()
    skills = tree.get('skills', {})

    skill_id = skill_data.get('id')
    if not skill_id:
        return {'success': False, 'error': '缺少技能 ID'}
    if skill_id in skills:
        return {'success': False, 'error': f'技能 {skill_id} 已存在'}

    # 构建技能数据
    new_skill = {
        'name': skill_data.get('name', skill_id),
        'category': skill_data.get('category', 'knowledge_acquisition'),
        'tier': skill_data.get('tier', 'basic'),
        'level': 0,
        'max_level': skill_data.get('max_level', 20),
        'proficiency': 0.0,
        'unlocked': skill_data.get('unlocked', False),
        'prerequisites': skill_data.get('prerequisites', []),
        'description': skill_data.get('description', ''),
    }
    skills[skill_id] = new_skill

    config = _load_daemon_config()
    spec = config.get('specialization', {})
    key = 'general_tree_path' if tree_type == 'general' else 'skill_tree_path'
    path = _resolve_path(spec.get(key, ''))

    # 清理临时字段
    for sid, s in skills.items():
        s.pop('id', None)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    return {'success': True, 'skill_id': skill_id}


def reload_skill(skill_id: str) -> Dict[str, Any]:
    """
    热重载指定技能（不重启服务器）

    Args:
        skill_id: 技能ID

    Returns:
        操作结果
    """
    from prokaryote_agent.skills.skill_base import SkillLibrary
    library_path = (
        PROJECT_ROOT / "prokaryote_agent" / "skills" / "library"
    )

    # 检查技能文件是否存在
    skill_file = library_path / f"{skill_id}.py"
    if not skill_file.exists():
        return {
            'success': False,
            'error': f'技能文件不存在: {skill_id}.py'
        }

    try:
        library = SkillLibrary(str(library_path))
        reloaded = library.reload_skill(skill_id)
        if reloaded:
            return {
                'success': True,
                'message': f'技能 {skill_id} 已热重载',
                'skill_name': reloaded.metadata.name if reloaded.metadata else skill_id,
            }
        else:
            return {
                'success': False,
                'error': f'重载失败: 技能 {skill_id} 无法加载',
            }
    except Exception as e:
        logger.exception(f"热重载技能失败: {skill_id}")
        return {
            'success': False,
            'error': f'重载异常: {str(e)}',
        }


def reload_all_skills() -> Dict[str, Any]:
    """
    热重载所有已注册技能

    Returns:
        操作结果，包含成功/失败的技能列表
    """
    from prokaryote_agent.skills.skill_base import SkillLibrary
    library_path = (
        PROJECT_ROOT / "prokaryote_agent" / "skills" / "library"
    )

    try:
        library = SkillLibrary(str(library_path))
        results = {'reloaded': [], 'failed': []}

        for skill_id in list(library.registry.keys()):
            reloaded = library.reload_skill(skill_id)
            if reloaded:
                results['reloaded'].append(skill_id)
            else:
                results['failed'].append(skill_id)

        return {
            'success': True,
            'message': f'重载完成: {len(results["reloaded"])} 成功, '
                       f'{len(results["failed"])} 失败',
            **results,
        }
    except Exception as e:
        logger.exception("批量热重载失败")
        return {'success': False, 'error': str(e)}
