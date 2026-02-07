"""
评估配置解析器

从技能定义中解析评估配置，支持预设和自定义维度。
"""

from typing import Dict, Any, List, Optional
import logging

from .dimension_presets import get_preset_dimensions, DIMENSION_PRESETS


logger = logging.getLogger(__name__)


class EvaluationConfigResolver:
    """
    评估配置解析器

    负责从技能定义中解析评估配置，自动处理预设和自定义维度的混合。

    技能定义中的evaluation字段格式：
    {
        "evaluation": {
            "preset": "research",  // 使用预设
            "dimensions": [...],   // 或自定义维度
            "threshold_base": 0.6, // 基础阈值
            "threshold_increment": 0.01  // 每级增加
        }
    }
    """

    # 任务类型到预设的默认映射
    TASK_TYPE_TO_PRESET = {
        "research": "research",
        "drafting": "document",
        "analysis": "analysis",
        "coding": "code",
        "translation": "translation",
        "creative": "creative",
        "data": "data_processing",
        "communication": "communication"
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.EvaluationConfigResolver")

    def resolve(
        self,
        skill_definition: Dict[str, Any],
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        解析技能的评估配置

        Args:
            skill_definition: 技能定义字典
            task_type: 任务类型，用于推断默认预设

        Returns:
            解析后的评估配置，包含：
            - dimensions: 评估维度列表
            - threshold_base: 基础通过阈值
            - threshold_increment: 每级阈值增量
        """
        eval_config = skill_definition.get("evaluation", {})

        # 解析维度
        dimensions = self._resolve_dimensions(eval_config, skill_definition, task_type)

        # 解析阈值配置
        threshold_base = eval_config.get("threshold_base", 0.6)
        threshold_increment = eval_config.get("threshold_increment", 0.01)

        return {
            "dimensions": dimensions,
            "threshold_base": threshold_base,
            "threshold_increment": threshold_increment
        }

    def _resolve_dimensions(
        self,
        eval_config: Dict[str, Any],
        skill_definition: Dict[str, Any],
        task_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        解析评估维度

        优先级：
        1. evaluation.dimensions (自定义维度)
        2. evaluation.preset (预设名称)
        3. 根据task_type推断预设
        4. 根据skill_id或domain推断预设
        5. 默认使用generic
        """
        # 1. 检查自定义维度
        if "dimensions" in eval_config:
            custom_dims = eval_config["dimensions"]
            if custom_dims and isinstance(custom_dims, list):
                self.logger.debug(f"使用自定义评估维度: {len(custom_dims)}个")
                return self._normalize_dimensions(custom_dims)

        # 2. 检查指定预设
        if "preset" in eval_config:
            preset_name = eval_config["preset"]
            if preset_name in DIMENSION_PRESETS:
                self.logger.debug(f"使用指定预设: {preset_name}")
                return get_preset_dimensions(preset_name)

        # 3. 根据task_type推断
        if task_type:
            inferred_preset = self._infer_preset_from_task_type(task_type)
            if inferred_preset:
                self.logger.debug(f"从task_type推断预设: {task_type} -> {inferred_preset}")
                return get_preset_dimensions(inferred_preset)

        # 4. 根据skill_id或domain推断
        skill_id = skill_definition.get("id", "")
        domain = skill_definition.get("domain", "")

        inferred_preset = self._infer_preset_from_skill(skill_id, domain)
        if inferred_preset:
            self.logger.debug(f"从skill信息推断预设: {skill_id}/{domain} -> {inferred_preset}")
            return get_preset_dimensions(inferred_preset)

        # 5. 默认使用generic
        self.logger.debug("使用默认generic预设")
        return get_preset_dimensions("generic")

    def _infer_preset_from_task_type(self, task_type: str) -> Optional[str]:
        """
        从任务类型推断预设

        Args:
            task_type: 任务类型

        Returns:
            预设名称或None
        """
        task_type_lower = task_type.lower()

        # 直接匹配
        if task_type_lower in self.TASK_TYPE_TO_PRESET:
            return self.TASK_TYPE_TO_PRESET[task_type_lower]

        # 模糊匹配
        for key, preset in self.TASK_TYPE_TO_PRESET.items():
            if key in task_type_lower or task_type_lower in key:
                return preset

        return None

    def _infer_preset_from_skill(
        self,
        skill_id: str,
        domain: str
    ) -> Optional[str]:
        """
        从技能ID和领域推断预设

        Args:
            skill_id: 技能ID
            domain: 技能领域

        Returns:
            预设名称或None
        """
        combined = f"{skill_id} {domain}".lower()

        # 关键词映射
        keyword_mappings = {
            "research": ["research", "search", "retrieval", "检索", "查询", "搜索"],
            "document": ["document", "draft", "write", "文书", "文档", "起草", "写作"],
            "analysis": ["analysis", "analyze", "分析", "评估"],
            "code": ["code", "program", "develop", "代码", "编程", "开发"],
            "translation": ["translate", "翻译"],
            "creative": ["creative", "design", "art", "创意", "设计", "艺术"],
            "data_processing": ["data", "process", "数据", "处理", "etl"],
            "communication": ["chat", "dialog", "communicate", "对话", "沟通", "交互"]
        }

        for preset, keywords in keyword_mappings.items():
            for keyword in keywords:
                if keyword in combined:
                    return preset

        return None

    def _normalize_dimensions(
        self,
        dimensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        规范化自定义维度

        确保每个维度都有必要的字段，补充默认值。

        Args:
            dimensions: 原始维度列表

        Returns:
            规范化后的维度列表
        """
        normalized = []
        total_weight = sum(d.get("weight", 0.25) for d in dimensions)

        for dim in dimensions:
            # 必填字段
            if "name" not in dim:
                continue

            # 补充默认值
            norm_dim = {
                "name": dim["name"],
                "description": dim.get("description", f"评估{dim['name']}"),
                "weight": dim.get("weight", 0.25),
                "scoring_guide": dim.get(
                    "scoring_guide",
                    "0-3: 差; 4-6: 一般; 7-8: 良好; 9-10: 优秀"
                )
            }

            # 归一化权重
            if total_weight > 0:
                norm_dim["weight"] = norm_dim["weight"] / total_weight

            normalized.append(norm_dim)

        return normalized if normalized else get_preset_dimensions("generic")

    def calculate_threshold(
        self,
        config: Dict[str, Any],
        level: int
    ) -> float:
        """
        计算指定等级的通过阈值

        阈值随等级增加而提高，但有上限。

        Args:
            config: 评估配置
            level: 当前技能等级

        Returns:
            通过阈值 (0-1之间)
        """
        base = config.get("threshold_base", 0.6)
        increment = config.get("threshold_increment", 0.01)

        # 计算阈值，但不超过0.95
        threshold = base + (level * increment)
        return min(threshold, 0.95)

    def get_preset_info(self, preset_name: str) -> Dict[str, Any]:
        """
        获取预设的详细信息

        Args:
            preset_name: 预设名称

        Returns:
            预设信息字典
        """
        from .dimension_presets import get_preset_description

        dimensions = get_preset_dimensions(preset_name)
        return {
            "name": preset_name,
            "description": get_preset_description(preset_name),
            "dimensions": dimensions,
            "dimension_count": len(dimensions)
        }
