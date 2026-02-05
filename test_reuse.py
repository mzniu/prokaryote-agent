#!/usr/bin/env python
"""测试能力复用 - AI是否会在生成新能力时调用已有的web_search"""

from prokaryote_agent.capability_generator import CapabilityGenerator
from prokaryote_agent.storage import StorageManager
from prokaryote_agent.ai_adapter import AIAdapter, AIConfig

# 初始化
storage = StorageManager()
config_result = storage.load_config()
config = config_result.get('config', {})

# 创建AI适配器
ai_config_dict = config.get('capability_config', {})
ai_config = AIConfig(
    provider=ai_config_dict.get('ai_provider', 'deepseek'),
    api_key=ai_config_dict.get('api_key', ''),
    api_base=ai_config_dict.get('api_base', 'https://api.deepseek.com/v1'),
    model=ai_config_dict.get('model', 'deepseek-reasoner'),
    max_tokens=ai_config_dict.get('max_tokens', 40000)
)
ai_adapter = AIAdapter(ai_config)

# 创建能力生成器
generator = CapabilityGenerator(storage, ai_adapter)

# 测试指引
guidance = """创建一个AI技术新闻摘要功能：
- 搜索最新的AI、机器学习、大模型相关新闻
- 提取标题、链接和关键摘要
- 过滤重复和低质量内容
- 返回格式化的新闻列表

注意：系统中已有web_search能力可以搜索互联网，请优先复用。
"""

print("=" * 70)
print("测试：AI是否会复用已有的 web_search 能力")
print("=" * 70)

# 加载已有能力
capabilities = generator._load_available_capabilities()
print(f"\n📦 已加载 {len(capabilities)} 个已有能力：")
for cap in capabilities[:5]:  # 只显示前5个
    print(f"  - {cap['name']}: {cap['description'][:60]}...")

print(f"\n🔍 查找 web_search...")
web_search_cap = next((c for c in capabilities if 'search' in c['name'].lower()), None)
if web_search_cap:
    print(f"✓ 找到: {web_search_cap['name']} - {web_search_cap['description']}")
else:
    print("✗ 未找到 web_search")

print(f"\n🧬 开始生成新能力...")
print(f"指引: {guidance[:100]}...")

result = generator.generate_capability(guidance, skip_safety_check=False)

print(f"\n{'='*70}")
print("生成结果：")
print(f"{'='*70}")

if result['success']:
    print(f"✓ 成功生成")
    print(f"  能力ID: {result['capability_id']}")
    print(f"  能力名: {result['capability_name']}")
    print(f"  入口函数: {result['entry_function']}")
    
    # 检查生成的代码是否调用了web_search
    code = result.get('code', '')
    if 'web_search' in code or 'call_capability' in code:
        print(f"\n✅ 代码中包含对已有能力的调用！")
        if 'web_search' in code:
            print(f"   - 发现 'web_search' 引用")
        if 'call_capability' in code:
            print(f"   - 发现 'call_capability' 调用")
    else:
        print(f"\n⚠️  代码中未发现对已有能力的调用")
        print(f"   AI可能重新实现了搜索功能")
    
    # 显示部分代码
    print(f"\n代码片段（前500字符）：")
    print("-" * 70)
    print(code[:500])
    print("-" * 70)
else:
    print(f"✗ 生成失败: {result.get('error')}")
