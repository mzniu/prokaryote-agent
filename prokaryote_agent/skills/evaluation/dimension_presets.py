"""
评估维度预设库

为不同类型的技能提供预定义的评估维度模板。
支持：通用、研究类、文档类、分析类、代码类、翻译类、创意类等。
"""

from typing import Dict, List, Any

# 评估维度定义结构
# {
#     "name": "维度名称",
#     "description": "维度描述，用于AI理解评估标准",
#     "weight": 权重 (0.0-1.0),
#     "scoring_guide": "评分指南，帮助AI给出一致的分数"
# }

DIMENSION_PRESETS: Dict[str, List[Dict[str, Any]]] = {
    # ========== 通用评估维度 ==========
    "generic": [
        {
            "name": "任务完成度",
            "description": "任务是否被完整执行，核心目标是否达成",
            "weight": 0.4,
            "scoring_guide": "0-3: 未完成或严重偏离; 4-6: 部分完成; 7-8: 基本完成; 9-10: 完美完成"
        },
        {
            "name": "结果质量",
            "description": "输出结果的整体质量和可用性",
            "weight": 0.3,
            "scoring_guide": "0-3: 不可用; 4-6: 需大量修改; 7-8: 可直接使用; 9-10: 优秀"
        },
        {
            "name": "执行效率",
            "description": "完成任务所用的资源和时间是否合理",
            "weight": 0.15,
            "scoring_guide": "0-3: 效率极低; 4-6: 效率一般; 7-8: 效率良好; 9-10: 高效"
        },
        {
            "name": "错误处理",
            "description": "是否正确处理了异常情况和边界条件",
            "weight": 0.15,
            "scoring_guide": "0-3: 出现未处理的错误; 4-6: 基本处理; 7-8: 妥善处理; 9-10: 完善处理"
        }
    ],

    # ========== 研究/检索类技能 ==========
    "research": [
        {
            "name": "信息完整性",
            "description": "检索到的信息是否全面覆盖查询需求",
            "weight": 0.3,
            "scoring_guide": "0-3: 遗漏关键信息; 4-6: 覆盖部分需求; 7-8: 较全面; 9-10: 非常全面"
        },
        {
            "name": "信息准确性",
            "description": "检索结果是否准确、可靠、无错误",
            "weight": 0.3,
            "scoring_guide": "0-3: 错误较多; 4-6: 部分准确; 7-8: 基本准确; 9-10: 完全准确"
        },
        {
            "name": "相关性",
            "description": "检索结果与查询需求的匹配程度",
            "weight": 0.25,
            "scoring_guide": "0-3: 大量无关结果; 4-6: 部分相关; 7-8: 高度相关; 9-10: 精准匹配"
        },
        {
            "name": "结果组织",
            "description": "检索结果是否有良好的结构和分类",
            "weight": 0.15,
            "scoring_guide": "0-3: 杂乱无章; 4-6: 基本有序; 7-8: 结构清晰; 9-10: 组织优秀"
        }
    ],

    # ========== 文档/写作类技能 ==========
    "document": [
        {
            "name": "内容完整性",
            "description": "文档是否包含所有必要的部分和信息",
            "weight": 0.25,
            "scoring_guide": "0-3: 严重缺失; 4-6: 缺少部分内容; 7-8: 基本完整; 9-10: 非常完整"
        },
        {
            "name": "格式规范性",
            "description": "文档格式是否符合标准要求",
            "weight": 0.2,
            "scoring_guide": "0-3: 格式混乱; 4-6: 部分不规范; 7-8: 基本规范; 9-10: 完全规范"
        },
        {
            "name": "表达清晰度",
            "description": "文档表达是否清晰、易于理解",
            "weight": 0.25,
            "scoring_guide": "0-3: 难以理解; 4-6: 勉强可读; 7-8: 表达清晰; 9-10: 表达优秀"
        },
        {
            "name": "专业准确性",
            "description": "专业术语和内容是否准确无误",
            "weight": 0.2,
            "scoring_guide": "0-3: 多处错误; 4-6: 部分准确; 7-8: 基本准确; 9-10: 完全准确"
        },
        {
            "name": "逻辑连贯性",
            "description": "文档各部分之间的逻辑是否连贯",
            "weight": 0.1,
            "scoring_guide": "0-3: 逻辑混乱; 4-6: 有些跳跃; 7-8: 逻辑清晰; 9-10: 逻辑严密"
        }
    ],

    # ========== 分析类技能 ==========
    "analysis": [
        {
            "name": "分析深度",
            "description": "分析是否深入挖掘了问题的本质",
            "weight": 0.3,
            "scoring_guide": "0-3: 流于表面; 4-6: 有一定深度; 7-8: 深入分析; 9-10: 非常深刻"
        },
        {
            "name": "结论有效性",
            "description": "得出的结论是否合理、有价值",
            "weight": 0.25,
            "scoring_guide": "0-3: 结论错误; 4-6: 部分正确; 7-8: 结论合理; 9-10: 结论精辟"
        },
        {
            "name": "论证严谨性",
            "description": "推理过程是否严谨、有据可依",
            "weight": 0.25,
            "scoring_guide": "0-3: 推理混乱; 4-6: 有漏洞; 7-8: 较严谨; 9-10: 非常严谨"
        },
        {
            "name": "关键点识别",
            "description": "是否准确识别了问题的关键要素",
            "weight": 0.2,
            "scoring_guide": "0-3: 遗漏关键点; 4-6: 识别部分; 7-8: 识别准确; 9-10: 洞察深刻"
        }
    ],

    # ========== 代码类技能 ==========
    "code": [
        {
            "name": "功能正确性",
            "description": "代码是否正确实现了预期功能",
            "weight": 0.35,
            "scoring_guide": "0-3: 无法运行; 4-6: 部分功能正确; 7-8: 功能基本正确; 9-10: 完全正确"
        },
        {
            "name": "代码质量",
            "description": "代码是否整洁、可读、符合规范",
            "weight": 0.25,
            "scoring_guide": "0-3: 难以维护; 4-6: 质量一般; 7-8: 质量良好; 9-10: 优秀"
        },
        {
            "name": "错误处理",
            "description": "是否妥善处理了异常和边界情况",
            "weight": 0.2,
            "scoring_guide": "0-3: 无错误处理; 4-6: 基本处理; 7-8: 较完善; 9-10: 非常完善"
        },
        {
            "name": "性能效率",
            "description": "代码的执行效率和资源使用是否合理",
            "weight": 0.2,
            "scoring_guide": "0-3: 效率极低; 4-6: 效率一般; 7-8: 效率良好; 9-10: 高效优化"
        }
    ],

    # ========== 翻译类技能 ==========
    "translation": [
        {
            "name": "翻译准确性",
            "description": "翻译是否准确传达了原文含义",
            "weight": 0.35,
            "scoring_guide": "0-3: 意思扭曲; 4-6: 部分准确; 7-8: 基本准确; 9-10: 完全准确"
        },
        {
            "name": "表达流畅性",
            "description": "译文是否流畅自然、符合目标语言习惯",
            "weight": 0.3,
            "scoring_guide": "0-3: 生硬难读; 4-6: 略显生硬; 7-8: 较为流畅; 9-10: 非常流畅"
        },
        {
            "name": "专业术语",
            "description": "专业术语翻译是否准确一致",
            "weight": 0.2,
            "scoring_guide": "0-3: 术语混乱; 4-6: 部分正确; 7-8: 基本正确; 9-10: 完全正确"
        },
        {
            "name": "完整性",
            "description": "是否完整翻译了所有内容，无遗漏",
            "weight": 0.15,
            "scoring_guide": "0-3: 大量遗漏; 4-6: 有遗漏; 7-8: 基本完整; 9-10: 完全完整"
        }
    ],

    # ========== 创意类技能 ==========
    "creative": [
        {
            "name": "创意独特性",
            "description": "作品是否具有独特的创意和视角",
            "weight": 0.3,
            "scoring_guide": "0-3: 平淡无奇; 4-6: 有些创意; 7-8: 较有新意; 9-10: 非常独特"
        },
        {
            "name": "表达艺术性",
            "description": "作品的表达是否具有艺术感染力",
            "weight": 0.25,
            "scoring_guide": "0-3: 缺乏美感; 4-6: 有些美感; 7-8: 较有美感; 9-10: 极具美感"
        },
        {
            "name": "主题契合度",
            "description": "作品是否切合给定的主题或要求",
            "weight": 0.25,
            "scoring_guide": "0-3: 严重偏题; 4-6: 有些偏离; 7-8: 基本切题; 9-10: 完美切题"
        },
        {
            "name": "完成度",
            "description": "作品是否完整、可用",
            "weight": 0.2,
            "scoring_guide": "0-3: 不完整; 4-6: 部分完成; 7-8: 基本完成; 9-10: 非常完整"
        }
    ],

    # ========== 数据处理类技能 ==========
    "data_processing": [
        {
            "name": "数据准确性",
            "description": "处理结果是否准确无误",
            "weight": 0.35,
            "scoring_guide": "0-3: 错误较多; 4-6: 部分准确; 7-8: 基本准确; 9-10: 完全准确"
        },
        {
            "name": "完整性",
            "description": "是否处理了所有需要处理的数据",
            "weight": 0.25,
            "scoring_guide": "0-3: 大量遗漏; 4-6: 部分遗漏; 7-8: 基本完整; 9-10: 完全完整"
        },
        {
            "name": "格式规范",
            "description": "输出格式是否符合要求",
            "weight": 0.2,
            "scoring_guide": "0-3: 格式错误; 4-6: 部分规范; 7-8: 基本规范; 9-10: 完全规范"
        },
        {
            "name": "处理效率",
            "description": "数据处理的效率是否合理",
            "weight": 0.2,
            "scoring_guide": "0-3: 效率极低; 4-6: 效率一般; 7-8: 效率良好; 9-10: 高效"
        }
    ],

    # ========== 沟通/交互类技能 ==========
    "communication": [
        {
            "name": "理解准确性",
            "description": "是否准确理解了对方的意图和需求",
            "weight": 0.3,
            "scoring_guide": "0-3: 严重误解; 4-6: 部分理解; 7-8: 基本理解; 9-10: 完全理解"
        },
        {
            "name": "响应恰当性",
            "description": "回应是否恰当、有针对性",
            "weight": 0.3,
            "scoring_guide": "0-3: 答非所问; 4-6: 部分相关; 7-8: 较为恰当; 9-10: 非常恰当"
        },
        {
            "name": "表达清晰度",
            "description": "表达是否清晰易懂",
            "weight": 0.25,
            "scoring_guide": "0-3: 难以理解; 4-6: 勉强可懂; 7-8: 较为清晰; 9-10: 非常清晰"
        },
        {
            "name": "礼貌友好度",
            "description": "交流态度是否礼貌友好",
            "weight": 0.15,
            "scoring_guide": "0-3: 态度不佳; 4-6: 中规中矩; 7-8: 较为友好; 9-10: 非常友好"
        }
    ]
}


def get_preset_dimensions(preset_name: str) -> List[Dict[str, Any]]:
    """
    获取指定预设的评估维度

    Args:
        preset_name: 预设名称，如 'research', 'document', 'code' 等

    Returns:
        评估维度列表，如果预设不存在则返回通用维度
    """
    return DIMENSION_PRESETS.get(preset_name, DIMENSION_PRESETS["generic"])


def list_presets() -> List[str]:
    """
    获取所有可用的预设名称

    Returns:
        预设名称列表
    """
    return list(DIMENSION_PRESETS.keys())


def get_preset_description(preset_name: str) -> str:
    """
    获取预设的描述说明

    Args:
        preset_name: 预设名称

    Returns:
        预设的描述字符串
    """
    descriptions = {
        "generic": "通用评估维度，适用于大多数任务类型",
        "research": "研究/检索类技能，侧重信息完整性和准确性",
        "document": "文档/写作类技能，侧重内容和格式规范",
        "analysis": "分析类技能，侧重分析深度和结论有效性",
        "code": "代码类技能，侧重功能正确性和代码质量",
        "translation": "翻译类技能，侧重准确性和流畅性",
        "creative": "创意类技能，侧重独特性和艺术性",
        "data_processing": "数据处理类技能，侧重准确性和完整性",
        "communication": "沟通/交互类技能，侧重理解和响应"
    }
    return descriptions.get(preset_name, "未知预设类型")
