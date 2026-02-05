"""
Specialization Domains - 专业化领域技能树配置
"""
from pathlib import Path

DOMAINS_DIR = Path(__file__).parent

def get_domain_path(domain_name: str) -> Path:
    """获取领域配置文件路径"""
    return DOMAINS_DIR / f"{domain_name}_tree.json"

def list_available_domains() -> list:
    """列出所有可用领域"""
    domains = []
    for f in DOMAINS_DIR.glob("*_tree.json"):
        domain_name = f.stem.replace("_tree", "")
        domains.append(domain_name)
    return domains

__all__ = ['get_domain_path', 'list_available_domains', 'DOMAINS_DIR']
