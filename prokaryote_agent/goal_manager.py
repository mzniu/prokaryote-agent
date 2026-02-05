"""
EvolutionGoalManager - 进化目标管理器

负责解析 evolution_goals.md 文件，管理进化目标的状态。
"""
import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class GoalStatus(Enum):
    """目标状态"""
    PENDING = "pending"           # 待执行
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    SKIPPED = "skipped"           # 跳过


class GoalPriority(Enum):
    """目标优先级"""
    CRITICAL = "critical"   # 关键
    HIGH = "high"           # 高
    MEDIUM = "medium"       # 中
    LOW = "low"             # 低


@dataclass
class EvolutionGoal:
    """进化目标"""
    id: str
    title: str
    description: str = ""
    status: GoalStatus = GoalStatus.PENDING
    priority: GoalPriority = GoalPriority.MEDIUM
    category: str = ""
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)  # 关联的能力ID
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_ready(self, completed_goals: set) -> bool:
        """检查目标是否可以执行（依赖已满足）"""
        return all(dep in completed_goals for dep in self.dependencies)


class EvolutionGoalManager:
    """进化目标管理器"""
    
    def __init__(self, goal_file: str = None):
        """
        初始化目标管理器
        
        Args:
            goal_file: 目标文件路径，默认为 evolution_goals.md
        """
        if goal_file is None:
            goal_file = "evolution_goals.md"
        
        self.goal_file = Path(goal_file)
        self.goals: Dict[str, EvolutionGoal] = {}
        self._loaded = False
    
    def load_goals(self) -> List[EvolutionGoal]:
        """从文件加载目标"""
        if not self.goal_file.exists():
            print(f"⚠️  目标文件不存在: {self.goal_file}")
            return []
        
        try:
            content = self.goal_file.read_text(encoding='utf-8')
            self._parse_goals(content)
            self._loaded = True
            return list(self.goals.values())
        except Exception as e:
            print(f"❌ 加载目标文件失败: {e}")
            return []
    
    def _parse_goals(self, content: str):
        """解析目标文件内容"""
        # 解析 Markdown 格式的目标
        # 支持格式：
        # ## 目标标题
        # - [ ] 待完成
        # - [x] 已完成
        
        current_category = ""
        goal_id = 0
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测分类标题 (## 开头)
            if line.startswith('## '):
                current_category = line[3:].strip()
            
            # 检测目标项 (- [ ] 或 - [x] 开头)
            elif line.startswith('- [ ]') or line.startswith('- [x]'):
                goal_id += 1
                is_completed = line.startswith('- [x]')
                
                # 提取标题
                title_match = re.match(r'- \[.\] (.+)', line)
                if title_match:
                    title = title_match.group(1).strip()
                    
                    # 检查是否有优先级标记
                    priority = GoalPriority.MEDIUM
                    if '🔴' in title or '[critical]' in title.lower():
                        priority = GoalPriority.CRITICAL
                    elif '🟠' in title or '[high]' in title.lower():
                        priority = GoalPriority.HIGH
                    elif '🟢' in title or '[low]' in title.lower():
                        priority = GoalPriority.LOW
                    
                    # 清理标题中的标记
                    title = re.sub(r'\[(?:critical|high|medium|low)\]', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'[🔴🟠🟡🟢]', '', title).strip()
                    
                    # 收集描述（后续缩进行）
                    description_lines = []
                    acceptance_criteria = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        # 检查是否还是该目标的内容
                        if next_line.startswith('  ') or next_line.startswith('\t'):
                            content_line = next_line.strip()
                            if content_line.startswith('- '):
                                # 验收标准
                                acceptance_criteria.append(content_line[2:])
                            elif content_line:
                                description_lines.append(content_line)
                            j += 1
                        elif next_line.strip() == '':
                            j += 1
                        else:
                            break
                    
                    goal = EvolutionGoal(
                        id=f"goal_{goal_id:03d}",
                        title=title,
                        description='\n'.join(description_lines),
                        status=GoalStatus.COMPLETED if is_completed else GoalStatus.PENDING,
                        priority=priority,
                        category=current_category,
                        acceptance_criteria=acceptance_criteria
                    )
                    self.goals[goal.id] = goal
                    
                    i = j - 1  # 跳到已处理的位置
            
            i += 1
    
    def get_pending_goals(self) -> List[EvolutionGoal]:
        """获取所有待执行的目标"""
        if not self._loaded:
            self.load_goals()
        
        return [g for g in self.goals.values() if g.status == GoalStatus.PENDING]
    
    def get_next_goal(self) -> Optional[EvolutionGoal]:
        """获取下一个要执行的目标（按优先级排序）"""
        pending = self.get_pending_goals()
        if not pending:
            return None
        
        # 按优先级排序
        priority_order = {
            GoalPriority.CRITICAL: 0,
            GoalPriority.HIGH: 1,
            GoalPriority.MEDIUM: 2,
            GoalPriority.LOW: 3
        }
        
        # 过滤出依赖已满足的目标
        completed_ids = {g.id for g in self.goals.values() if g.status == GoalStatus.COMPLETED}
        ready_goals = [g for g in pending if g.is_ready(completed_ids)]
        
        if not ready_goals:
            return pending[0]  # 如果没有准备好的，返回第一个
        
        ready_goals.sort(key=lambda g: priority_order.get(g.priority, 2))
        return ready_goals[0]
    
    def mark_goal_in_progress(self, goal: EvolutionGoal):
        """标记目标为进行中"""
        goal.status = GoalStatus.IN_PROGRESS
        self._save_goals()
    
    def mark_goal_completed(self, goal: EvolutionGoal, capabilities: List[str] = None):
        """标记目标为已完成"""
        goal.status = GoalStatus.COMPLETED
        goal.completed_at = datetime.now()
        if capabilities:
            goal.capabilities = capabilities
        self._save_goals()
    
    def mark_goal_failed(self, goal: EvolutionGoal, reason: str = ""):
        """标记目标为失败"""
        goal.status = GoalStatus.FAILED
        goal.metadata['failure_reason'] = reason
        self._save_goals()
    
    def _save_goals(self):
        """保存目标状态到文件"""
        if not self.goal_file.exists():
            return
        
        try:
            content = self.goal_file.read_text(encoding='utf-8')
            
            # 更新每个目标的状态
            for goal in self.goals.values():
                # 查找并更新目标状态
                pattern = rf'- \[.\] ({re.escape(goal.title.split("[")[0].strip())})'
                if goal.status == GoalStatus.COMPLETED:
                    replacement = f'- [x] {goal.title}'
                else:
                    replacement = f'- [ ] {goal.title}'
                
                content = re.sub(pattern, replacement, content, count=1)
            
            self.goal_file.write_text(content, encoding='utf-8')
        except Exception as e:
            print(f"⚠️  保存目标文件失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取目标统计信息"""
        if not self._loaded:
            self.load_goals()
        
        total = len(self.goals)
        completed = sum(1 for g in self.goals.values() if g.status == GoalStatus.COMPLETED)
        pending = sum(1 for g in self.goals.values() if g.status == GoalStatus.PENDING)
        in_progress = sum(1 for g in self.goals.values() if g.status == GoalStatus.IN_PROGRESS)
        failed = sum(1 for g in self.goals.values() if g.status == GoalStatus.FAILED)
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'failed': failed,
            'completion_rate': completed / total if total > 0 else 0
        }
    
    def __len__(self):
        return len(self.goals)
    
    def __iter__(self):
        return iter(self.goals.values())
