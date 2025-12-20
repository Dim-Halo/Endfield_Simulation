"""
游戏公式计算模块
提取常用的计算公式，避免重复代码
"""

def calculate_tech_enhancement(tech_power: float, base_value: float) -> float:
    """
    计算源石技艺增强效果

    公式: 最终值 = 基础值 × [1 + (2 × Tech / (Tech + 300))]

    Args:
        tech_power: 源石技艺数值
        base_value: 基础效果值

    Returns:
        增强后的效果值
    """
    if tech_power <= 0:
        return base_value

    enhancement_factor = 1.0 + (2.0 * tech_power / (tech_power + 300.0))
    return base_value * enhancement_factor
