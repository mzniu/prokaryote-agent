"""
AI Adapter Module - 外部AI服务适配器
支持 DeepSeek API 调用，专门用于代码生成任务
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AIConfig:
    """AI服务配置"""
    provider: str = "deepseek"
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-reasoner"
    max_tokens: int = 40000
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3
    retry_delay: int = 2


class AIAdapter:
    """
    AI服务适配器
    统一接口封装 DeepSeek API 调用
    """
    
    def __init__(self, config: Optional[AIConfig] = None):
        """
        初始化AI适配器
        
        Args:
            config: AI配置对象，如果为None则从环境变量读取
        """
        self.config = config or self._load_config_from_env()
        self.logger = logging.getLogger(f"{__name__}.AIAdapter")
        
        if not REQUESTS_AVAILABLE:
            self.logger.warning("requests库未安装，AI功能将不可用。请运行: pip install requests")
        
        if not self.config.api_key:
            self.logger.warning("未设置API密钥。请设置环境变量 DEEPSEEK_API_KEY 或在配置中提供")
    
    def _load_config_from_env(self) -> AIConfig:
        """从环境变量加载配置"""
        return AIConfig(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            api_base=os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-reasoner"),
            max_tokens=int(os.environ.get("DEEPSEEK_MAX_TOKENS", "2000")),
            temperature=float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.7"))
        )
    
    def generate_code(self, guidance: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        根据用户指引生成代码
        
        Args:
            guidance: 用户的功能描述
            context: 可选的上下文信息（已有能力、依赖等）
            
        Returns:
            dict: {
                "success": bool,
                "code": str,  # 生成的代码
                "description": str,  # 功能描述
                "entry_function": str,  # 入口函数名
                "dependencies": List[str],  # 依赖列表
                "error": str  # 错误信息
            }
        """
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "code": "",
                "description": "",
                "entry_function": "",
                "dependencies": [],
                "error": "requests库未安装"
            }
        
        if not self.config.api_key:
            return {
                "success": False,
                "code": "",
                "description": "",
                "entry_function": "",
                "dependencies": [],
                "error": "未设置API密钥"
            }
        
        # 构建提示词
        prompt = self._build_code_generation_prompt(guidance, context)
        
        # 调用AI
        try:
            response = self._call_ai(prompt)
            
            if response["success"]:
                content = response["content"]
                self.logger.info(f"AI返回内容长度: {len(content)}, 前100字符: {content[:100]}")
                
                # 解析生成的内容
                parsed = self._parse_code_response(content)
                return {
                    "success": True,
                    "code": parsed["code"],
                    "description": parsed["description"],
                    "entry_function": parsed["entry_function"],
                    "dependencies": parsed["dependencies"],
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "code": "",
                    "description": "",
                    "entry_function": "",
                    "dependencies": [],
                    "error": response["error"]
                }
        except Exception as e:
            self.logger.error(f"代码生成异常: {e}")
            return {
                "success": False,
                "code": "",
                "description": "",
                "entry_function": "",
                "dependencies": [],
                "error": str(e)
            }
    
    def _build_code_generation_prompt(self, guidance: str, context: Optional[Dict[str, Any]]) -> str:
        """
        构建代码生成的提示词
        
        Args:
            guidance: 用户指引
            context: 上下文信息
            
        Returns:
            str: 完整的提示词
        """
        prompt = f"""你是一个Python代码生成专家。请根据用户的需求生成安全、高质量的Python代码。

**用户需求**：
{guidance}

**代码生成要求**：
1. 生成完整的Python函数，包含详细的文档字符串
2. 函数必须有清晰的类型注解
3. 返回值格式统一为字典：{{"success": bool, "data": Any, "error": str}}
4. 包含完善的错误处理（try-except）
5. 优先使用Python标准库，避免复杂依赖
6. 禁止使用危险操作：os.system、subprocess、eval、exec、__import__
7. 禁止修改或删除文件系统（除非用户明确要求写入功能）
8. 代码风格遵循PEP 8规范
9. 如果可以复用已有能力，可以通过 call_capability 函数调用

**调用已有能力的方法**：
```python
from prokaryote_agent.capability_runtime import call_capability

# 调用已有能力
result = call_capability("能力名称", param1=value1, param2=value2)
if result["success"]:
    data = result["data"]
else:
    error = result["error"]
```

**输出格式**（严格按照此JSON格式输出）：
```json
{{
  "description": "功能描述（一句话）",
  "entry_function": "主函数名称",
  "dependencies": ["依赖的第三方库（仅标准库外的）"],
  "uses_capabilities": ["调用的已有能力名称列表"],
  "code": "完整的Python代码（包含导入语句和函数定义）"
}}
```

**示例输出**：
```json
{{
  "description": "读取文本文件内容",
  "entry_function": "read_file",
  "dependencies": [],
  "uses_capabilities": [],
  "code": "import os\\nfrom typing import Dict, Any\\n\\ndef read_file(file_path: str) -> Dict[str, Any]:\\n    try:\\n        if not os.path.exists(file_path):\\n            return {{'success': False, 'data': '', 'error': '文件不存在'}}\\n        with open(file_path, 'r', encoding='utf-8') as f:\\n            content = f.read()\\n        return {{'success': True, 'data': content, 'error': ''}}\\n    except Exception as e:\\n        return {{'success': False, 'data': '', 'error': str(e)}}"
}}
```
"""
        
        # 添加已有能力上下文
        if context:
            if context.get("existing_capabilities"):
                prompt += f"\n**可复用的已有能力**（可以通过call_capability调用）：\n"
                for cap in context["existing_capabilities"]:
                    prompt += f"- **{cap['name']}**: {cap['description']}"
                    if cap.get('entry_function'):
                        prompt += f" (函数: {cap['entry_function']})"
                    prompt += "\n"
                prompt += "\n如果已有能力可以帮助完成任务，请优先复用已有能力。\n"
        
        prompt += "\n请生成代码："
        return prompt
    
    def _call_ai(self, prompt: str) -> Dict[str, Any]:
        """
        调用AI API
        
        Args:
            prompt: 提示词
            
        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }
        
        url = f"{self.config.api_base}/chat/completions"
        
        # 重试机制
        for attempt in range(self.config.max_retries):
            try:
                self.logger.info(f"调用DeepSeek API (尝试 {attempt + 1}/{self.config.max_retries})")
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    message = data["choices"][0]["message"]
                    content = message.get("content", "")
                    
                    # 注意: reasoning_content是思考过程，不是最终答案
                    # 只记录有reasoning_content但content为空的情况，不作为fallback
                    reasoning_content = message.get("reasoning_content", "")
                    
                    # 如果content为空，记录警告并重试
                    if not content:
                        if reasoning_content:
                            self.logger.warning(f"API返回了reasoning_content但content为空，这可能是模型行为问题")
                            self.logger.debug(f"reasoning_content前200字符: {reasoning_content[:200]}")
                        else:
                            self.logger.warning(f"API响应内容为空，完整响应: {data}")
                        
                        # content为空时重试
                        if attempt < self.config.max_retries - 1:
                            self.logger.info("content为空，尝试重试...")
                            time.sleep(self.config.retry_delay * (attempt + 1))
                            continue
                    
                    self.logger.info(f"API调用成功，返回内容长度: {len(content)}")
                    return {
                        "success": True,
                        "content": content,
                        "error": ""
                    }
                else:
                    error_msg = f"API返回错误: {response.status_code} - {response.text}"
                    self.logger.warning(error_msg)
                    
                    # 如果是429或5xx错误，重试
                    if response.status_code in [429, 500, 502, 503, 504] and attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay * (attempt + 1))
                        continue
                    
                    return {
                        "success": False,
                        "content": "",
                        "error": error_msg
                    }
            
            except requests.exceptions.Timeout:
                error_msg = f"API调用超时（{self.config.timeout}秒）"
                self.logger.warning(error_msg)
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                return {"success": False, "content": "", "error": error_msg}
            
            except requests.exceptions.RequestException as e:
                error_msg = f"网络请求异常: {str(e)}"
                self.logger.warning(error_msg)
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                return {"success": False, "content": "", "error": error_msg}
            
            except Exception as e:
                error_msg = f"未知异常: {str(e)}"
                self.logger.error(error_msg)
                return {"success": False, "content": "", "error": error_msg}
        
        return {
            "success": False,
            "content": "",
            "error": f"重试{self.config.max_retries}次后仍然失败"
        }
    
    def generate_tests(self, code: str, entry_function: str, description: str) -> Dict[str, Any]:
        """
        为生成的代码生成测试用例
        
        Args:
            code: 已生成的代码
            entry_function: 入口函数名
            description: 功能描述
            
        Returns:
            dict: {
                "success": bool,
                "test_code": str,
                "test_cases": List[str],
                "error": str
            }
        """
        if not REQUESTS_AVAILABLE:
            return {"success": False, "test_code": "", "test_cases": [], "error": "requests库未安装"}
        
        if not self.config.api_key:
            return {"success": False, "test_code": "", "test_cases": [], "error": "未设置API密钥"}
        
        prompt = self._build_test_generation_prompt(code, entry_function, description)
        
        try:
            response = self._call_ai(prompt)
            
            if response["success"]:
                parsed = self._parse_test_response(response["content"])
                
                # 检查是否成功提取了测试代码
                if not parsed["test_code"]:
                    self.logger.warning("API调用成功但未能提取测试代码")
                    return {
                        "success": False,
                        "test_code": "",
                        "test_cases": [],
                        "error": "未能从AI响应中提取测试代码"
                    }
                
                return {
                    "success": True,
                    "test_code": parsed["test_code"],
                    "test_cases": parsed["test_cases"],
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "test_code": "",
                    "test_cases": [],
                    "error": response["error"]
                }
        except Exception as e:
            self.logger.error(f"测试生成异常: {e}")
            return {"success": False, "test_code": "", "test_cases": [], "error": str(e)}
    
    def _build_test_generation_prompt(self, code: str, entry_function: str, description: str) -> str:
        """构建测试生成的提示词"""
        prompt = f"""你是一个Python测试专家。请为以下代码生成单元测试。

**功能描述**：
{description}

**代码**：
```python
{code}
```

**入口函数**：{entry_function}

**测试生成要求**：
1. 生成至少3个测试用例，覆盖正常情况、边界情况和异常情况
2. 每个测试用例必须是独立的函数
3. 使用assert语句进行断言
4. 测试函数返回值格式应该是 {{"success": bool, ...}}
5. 不要依赖外部文件或资源
6. 测试必须能够独立运行
7. 禁止使用 globals()、locals()、eval()、exec() 等危险函数
8. 测试代码必须简洁，直接调用被测函数并断言结果

**输出格式**（严格按照此JSON格式输出）：
```json
{{
  "test_cases": ["测试用例1描述", "测试用例2描述", "测试用例3描述"],
  "test_code": "完整的测试代码，包含所有测试函数和run_tests函数"
}}
```

**测试代码模板**（必须遵循此简洁模式）：
```python
def test_normal_case():
    \"\"\"测试正常情况\"\"\"
    result = {entry_function}(...)
    assert result["success"] == True
    # 更多断言

def test_edge_case():
    \"\"\"测试边界情况\"\"\"
    result = {entry_function}(...)
    # 断言

def test_error_case():
    \"\"\"测试异常情况\"\"\"
    result = {entry_function}(...)
    assert result["success"] == False

def run_tests():
    \"\"\"运行所有测试，返回结果\"\"\"
    results = []
    test_funcs = [test_normal_case, test_edge_case, test_error_case]
    for test_func in test_funcs:
        try:
            test_func()
            results.append({{"name": test_func.__name__, "passed": True, "error": ""}})
        except AssertionError as e:
            results.append({{"name": test_func.__name__, "passed": False, "error": str(e)}})
        except Exception as e:
            results.append({{"name": test_func.__name__, "passed": False, "error": str(e)}})
    return results
```

请生成测试代码："""
        return prompt
    
    def _parse_test_response(self, content: str) -> Dict[str, Any]:
        """解析测试生成的响应"""
        import re
        
        try:
            # 方法1: 尝试解析JSON格式
            json_str = None
            if "```json" in content:
                try:
                    start = content.index("```json") + 7
                    end = content.index("```", start)
                    json_str = content[start:end].strip()
                except ValueError:
                    pass
            
            if json_str:
                try:
                    data = json.loads(json_str)
                    test_code = data.get("test_code", "")
                    if test_code and "def test_" in test_code:
                        # 如果没有run_tests函数，自动添加
                        if "def run_tests" not in test_code:
                            test_funcs = re.findall(r'def (test_\w+)\s*\(', test_code)
                            if test_funcs:
                                run_tests_code = self._generate_run_tests_function(test_funcs)
                                test_code = test_code + "\n\n" + run_tests_code
                        
                        return {
                            "test_code": test_code,
                            "test_cases": data.get("test_cases", [])
                        }
                except json.JSONDecodeError:
                    self.logger.debug("JSON解析失败，尝试其他方法")
            
            # 方法2: 直接提取Python代码块
            test_code = ""
            if "```python" in content:
                try:
                    start = content.index("```python") + 9
                    end = content.index("```", start)
                    test_code = content[start:end].strip()
                except ValueError:
                    pass
            
            # 方法3: 直接从内容中查找def test_函数
            if not test_code and "def test_" in content:
                # 直接从内容中提取测试代码
                lines = content.split("\n")
                in_code = False
                code_lines = []
                for line in lines:
                    if line.strip().startswith("def ") or in_code:
                        in_code = True
                        code_lines.append(line)
                test_code = "\n".join(code_lines)
            
            if test_code:
                # 如果没有run_tests函数，自动添加
                if "def run_tests" not in test_code:
                    # 找出所有测试函数名
                    test_funcs = re.findall(r'def (test_\w+)\s*\(', test_code)
                    if test_funcs:
                        run_tests_code = self._generate_run_tests_function(test_funcs)
                        test_code = test_code + "\n\n" + run_tests_code
                
                # 提取测试用例描述（从docstring中）
                test_cases = []
                docstrings = re.findall(r'def test_\w+\([^)]*\):\s*"""([^"]+)"""', test_code)
                test_cases = docstrings if docstrings else ["自动生成的测试用例"]
                
                return {
                    "test_code": test_code,
                    "test_cases": test_cases
                }
            
            # 方法4: 尝试解析整个内容为JSON
            try:
                data = json.loads(content.strip())
                return {
                    "test_code": data.get("test_code", ""),
                    "test_cases": data.get("test_cases", [])
                }
            except json.JSONDecodeError:
                pass
            
            self.logger.warning("无法从响应中提取测试代码")
            return {"test_code": "", "test_cases": []}
            
        except Exception as e:
            self.logger.error(f"解析测试响应失败: {e}")
            return {"test_code": "", "test_cases": []}
    
    def _generate_run_tests_function(self, test_funcs: List[str]) -> str:
        """生成run_tests函数"""
        funcs_list = ", ".join(test_funcs)
        return f'''def run_tests():
    """运行所有测试，返回结果"""
    results = []
    test_funcs = [{funcs_list}]
    for test_func in test_funcs:
        try:
            test_func()
            results.append({{"name": test_func.__name__, "passed": True, "error": ""}})
        except AssertionError as e:
            results.append({{"name": test_func.__name__, "passed": False, "error": str(e)}})
        except Exception as e:
            results.append({{"name": test_func.__name__, "passed": False, "error": str(e)}})
    return results'''

    def _parse_code_response(self, content: str) -> Dict[str, Any]:
        """
        解析AI返回的代码内容
        
        Args:
            content: AI返回的原始内容
            
        Returns:
            dict: {
                "code": str,
                "description": str,
                "entry_function": str,
                "dependencies": List[str]
            }
        """
        import re
        
        try:
            # 方法1: 尝试从内容中提取JSON块
            json_str = None
            if "```json" in content:
                try:
                    start = content.index("```json") + 7
                    end = content.index("```", start)
                    json_str = content[start:end].strip()
                except ValueError:
                    pass
            
            if json_str:
                try:
                    data = json.loads(json_str)
                    if "code" in data:
                        return {
                            "code": data.get("code", ""),
                            "description": data.get("description", ""),
                            "entry_function": data.get("entry_function", ""),
                            "dependencies": data.get("dependencies", [])
                        }
                except json.JSONDecodeError:
                    pass
            
            # 方法2: 尝试提取Python代码块
            code = ""
            if "```python" in content:
                try:
                    start = content.index("```python") + 9
                    end = content.index("```", start)
                    code = content[start:end].strip()
                except ValueError:
                    pass
            
            # 方法3: 直接从内容中提取函数定义
            if not code and "def " in content:
                lines = content.split("\n")
                code_lines = []
                in_code = False
                for line in lines:
                    if line.strip().startswith("def ") or in_code:
                        in_code = True
                        code_lines.append(line)
                    elif in_code and line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                        # 可能遇到了非代码行，停止
                        break
                code = "\n".join(code_lines)
            
            if code:
                # 提取入口函数名
                entry_function = ""
                match = re.search(r'def\s+(\w+)\s*\(', code)
                if match:
                    entry_function = match.group(1)
                
                # 提取依赖
                dependencies = []
                import_matches = re.findall(r'^import\s+(\w+)|^from\s+(\w+)\s+import', code, re.MULTILINE)
                for m in import_matches:
                    dep = m[0] or m[1]
                    if dep and dep not in ['os', 'sys', 'json', 're', 'math', 'datetime', 'typing']:
                        dependencies.append(dep)
                
                return {
                    "code": code,
                    "description": "从AI响应中提取的代码",
                    "entry_function": entry_function,
                    "dependencies": list(set(dependencies))
                }
            
            # 方法4: 尝试直接解析整个内容为JSON
            try:
                data = json.loads(content.strip())
                return {
                    "code": data.get("code", ""),
                    "description": data.get("description", ""),
                    "entry_function": data.get("entry_function", ""),
                    "dependencies": data.get("dependencies", [])
                }
            except json.JSONDecodeError:
                pass
            
            self.logger.warning("无法从响应中提取代码")
            raise ValueError("无法从AI响应中提取代码")
        
        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            self.logger.debug(f"原始内容: {content[:500] if content else 'empty'}")
            raise ValueError(f"无法解析AI响应: {str(e)}")


# 测试函数
def test_ai_adapter():
    """测试AI适配器"""
    print("=== AI Adapter 测试 ===\n")
    
    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("⚠️  未设置 DEEPSEEK_API_KEY 环境变量")
        print("   请运行: set DEEPSEEK_API_KEY=your_api_key_here")
        return
    
    print(f"✓ API密钥已设置 (长度: {len(api_key)})")
    print(f"✓ 使用模型: deepseek-reasoner\n")
    
    # 创建适配器
    adapter = AIAdapter()
    
    # 测试代码生成
    print("--- 测试1: 生成文件读取功能 ---")
    result = adapter.generate_code("我需要一个读取文本文件的功能，支持UTF-8编码")
    
    if result["success"]:
        print(f"✓ 生成成功")
        print(f"  功能描述: {result['description']}")
        print(f"  入口函数: {result['entry_function']}")
        print(f"  依赖库: {result['dependencies']}")
        print(f"  代码长度: {len(result['code'])} 字符")
        print(f"\n生成的代码:\n{'-'*60}")
        print(result['code'][:500] + "..." if len(result['code']) > 500 else result['code'])
        print(f"{'-'*60}\n")
    else:
        print(f"✗ 生成失败: {result['error']}\n")
    
    # 测试2
    print("--- 测试2: 生成数据处理功能 ---")
    result2 = adapter.generate_code("需要一个函数统计文本中的单词数量")
    
    if result2["success"]:
        print(f"✓ 生成成功")
        print(f"  功能描述: {result2['description']}")
        print(f"  入口函数: {result2['entry_function']}")
    else:
        print(f"✗ 生成失败: {result2['error']}")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    )
    
    test_ai_adapter()
