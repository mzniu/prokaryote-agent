#!/usr/bin/env python
"""
Prokaryote Agent - 混合进化模式
后台持续自主进化 + 接受用户实时指引
"""

import os
import sys
import time
import signal
import logging
import random
import threading
import json
from datetime import datetime
from queue import Queue, Empty

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    query_prokaryote_state,
    generate_capability,
    manage_capabilities,
    invoke_capability
)
from prokaryote_agent.goal_manager import EvolutionGoalManager, EvolutionGoal
from prokaryote_agent.iterative_evolver import IterativeEvolver
from prokaryote_agent.capability_generator import CapabilityGenerator
from prokaryote_agent.storage import StorageManager
from prokaryote_agent.ai_adapter import AIAdapter, AIConfig


class HybridAgent:
    """混合进化Agent - 自主进化 + 人工指引"""
    
    def __init__(self, auto_interval: int = 60, max_capabilities: int = 20, auto_enable: bool = False):
        """
        初始化混合Agent
        
        Args:
            auto_interval: 自动进化间隔（秒）
            max_capabilities: 最大能力数量
            auto_enable: 是否自动启用安全能力
        """
        self.auto_interval = auto_interval
        self.max_capabilities = max_capabilities
        self.auto_enable = auto_enable
        
        self.running = False
        self.initialized = False
        self.auto_evolution_enabled = True
        self.evolution_count = 0
        
        # 进化历史文件路径
        self.evolution_history_path = './prokaryote_agent/evolution_history.json'
        self.evolution_principles_path = './evolution_principles.md'
        
        # 进化任务队列（用户可以添加自定义任务）
        self.evolution_queue = Queue()
        
        # 迭代式进化系统
        self.goal_manager = EvolutionGoalManager('evolution_goals.md')
        self.evolution_mode = 'iterative'  # 默认使用迭代式进化
        self.storage_manager = None
        self.capability_generator = None
        self.iterative_evolver = None
        self.config = {}
        
        # 后台线程
        self.auto_thread = None
        self.auto_thread_lock = threading.Lock()
        
        # 输出锁，避免后台线程和主线程输出冲突
        self.output_lock = threading.Lock()
        
        # 信号处理将在初始化完成后注册
    
    def _load_evolution_history(self):
        """加载进化历史记录"""
        try:
            if os.path.exists(self.evolution_history_path):
                with open(self.evolution_history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 创建初始历史文件
                initial_history = {
                    "evolution_history": [],
                    "total_evolutions": 0,
                    "successful_evolutions": 0,
                    "failed_evolutions": 0
                }
                self._save_evolution_history(initial_history)
                return initial_history
        except Exception as e:
            logging.error(f"加载进化历史失败: {e}", exc_info=True)
            return {
                "evolution_history": [],
                "total_evolutions": 0,
                "successful_evolutions": 0,
                "failed_evolutions": 0
            }
    
    def _save_evolution_history(self, history):
        """保存进化历史记录"""
        try:
            os.makedirs(os.path.dirname(self.evolution_history_path), exist_ok=True)
            with open(self.evolution_history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存进化历史失败: {e}", exc_info=True)
    
    def _add_evolution_record(self, capability_id, capability_name, description, evolution_reason, success):
        """添加进化记录"""
        try:
            history = self._load_evolution_history()
            
            record = {
                "timestamp": datetime.now().isoformat(),
                "capability_id": capability_id,
                "capability_name": capability_name,
                "description": description,
                "evolution_reason": evolution_reason,
                "success": success
            }
            
            history["evolution_history"].append(record)
            history["total_evolutions"] += 1
            if success:
                history["successful_evolutions"] += 1
            else:
                history["failed_evolutions"] += 1
            
            self._save_evolution_history(history)
        except Exception as e:
            logging.error(f"添加进化记录失败: {e}", exc_info=True)
    
    def _safe_print(self, message: str):
        """线程安全的打印方法"""
        with self.output_lock:
            try:
                print(message)
                sys.stdout.flush()
            except:
                pass
    
    def _load_evolution_principles(self):
        """加载进化原则文档"""
        try:
            if os.path.exists(self.evolution_principles_path):
                with open(self.evolution_principles_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logging.warning(f"进化原则文件不存在: {self.evolution_principles_path}")
                return "请基于资源获取原则进行决策。"
        except Exception as e:
            logging.error(f"加载进化原则失败: {e}", exc_info=True)
            return "请基于资源获取原则进行决策。"
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        # 如果还在初始化阶段，忽略信号（可能是日志系统竞争导致的假信号）
        if not self.initialized:
            return
        
        # 如果已经在关闭中，忽略重复信号
        if not self.running:
            return
        
        # 记录信号信息
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        sys.stderr.write(f"\n\n⚠️  收到停止信号 ({signal_name})，正在关闭...\n")
        sys.stderr.flush()
        
        # 标记为停止，让主循环自然退出
        self.running = False
    
    def initialize(self):
        """初始化系统"""
        print("="*70)
        print("  Prokaryote Agent V0.2 - 混合进化模式")
        print("  后台自主进化 + 实时人工指引")
        print("="*70)
        
        # 在初始化期间临时忽略中断信号，避免logging系统被中断
        # Python 3.13在Windows上logging.flush()可能触发KeyboardInterrupt
        original_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        original_sigterm = signal.signal(signal.SIGTERM, signal.SIG_IGN)
        
        # 从config加载AI配置
        try:
            with open('./prokaryote_agent/config/config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                capability_config = self.config.get('capability_config', {})
            api_key = capability_config.get('api_key', '')
            
            if not api_key or api_key.startswith('${'):
                print("\n⚠️  警告: config.json中未配置有效的API密钥")
                print("  程序仍可运行，但无法进化（生成新能力）")
                print("  请在 prokaryote_agent/config/config.json 中设置 capability_config.api_key")
                print("\n继续启动...(3秒后自动继续)")
                time.sleep(3)
            else:
                print(f"\n✓ 从配置文件加载API密钥: {api_key[:8]}...")
        except Exception as e:
            print(f"\n⚠️  警告: 加载配置文件失败: {e}")
            print("  程序仍可运行，但无法进化")
            self.config = {}  # 设置空配置以避免AttributeError
            time.sleep(2)
        
        print("\n[初始化] 正在初始化系统...")
        result = init_prokaryote()
        
        if not result['success']:
            print(f"✗ 初始化失败: {result['msg']}")
            return False
        
        print("✓ 系统初始化成功")
        
        print("\n[启动] 正在启动核心监控...")
        start_result = start_prokaryote()
        
        if not start_result['success']:
            print(f"✗ 启动失败: {start_result['msg']}")
            return False
        
        print(f"✓ 核心监控已启动 (PID: {start_result.get('pid', 'N/A')})")
        
        # 初始化迭代式进化系统
        print("\n[配置] 正在初始化迭代式进化系统...")
        try:
            self._initialize_iterative_evolver()
            print("✓ 迭代式进化系统已就绪")
            
            # 加载进化目标
            goal_result = self.goal_manager.load_goals()
            if goal_result["success"]:
                summary = self.goal_manager.get_summary()
                print(f"✓ 已加载 {summary['total']} 个进化目标")
                print(f"  - 待执行: {summary['pending']}")
                print(f"  - 已完成: {summary['completed']}")
                print(f"  - 失败: {summary['failed']}")
        except Exception as e:
            print(f"⚠️  迭代式进化系统初始化失败: {e}")
            print("  将回退到简单进化模式")
            self.evolution_mode = 'simple'
            logging.warning(f"迭代式进化初始化失败: {e}", exc_info=True)
        
        self.initialized = True
        self.running = True
        
        # 等待监控模块完成首次状态采集
        time.sleep(1.5)
        
        # 启动后台进化线程
        self._start_auto_evolution()
        
        # 显示配置
        print(f"\n[配置]")
        print(f"  进化模式: {'迭代式 (Iterative)' if self.evolution_mode == 'iterative' else '简单 (Simple)'}")
        print(f"  自动进化间隔: {self.auto_interval} 秒")
        print(f"  能力上限: {self.max_capabilities}")
        print(f"  自动启用: {'是' if self.auto_enable else '否'}")
        print(f"  后台进化: {'启用' if self.auto_evolution_enabled else '暂停'}")
        if self.evolution_mode == 'iterative':
            iterative_config = self.config.get('evolution', {}).get('iterative_config', {})
            print(f"  最大迭代次数: {iterative_config.get('max_iterations_per_goal', 15)}")
            print(f"  每阶段最大尝试: {iterative_config.get('max_attempts_per_stage', 3)}")
        
        # 显示初始状态
        try:
            self._show_status()
        except Exception as e:
            print(f"  ⚠️  状态显示出错: {e}")
            logging.error(f"显示状态异常: {e}", exc_info=True)
        
        print("\n[就绪] 系统初始化完成")
        
        # 初始化完成，恢复信号处理（允许KeyboardInterrupt）
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        
        return True
    
    def _initialize_iterative_evolver(self):
        """初始化迭代式进化器"""
        # 初始化存储管理器
        self.storage_manager = StorageManager()
        
        # 加载配置
        config_result = self.storage_manager.load_config()
        if isinstance(config_result, dict) and 'config' in config_result:
            self.config = config_result['config']
        else:
            self.config = config_result if isinstance(config_result, dict) else {}
        
        # 从配置中创建AIAdapter
        ai_config_dict = self.config.get('capability_config', self.config.get('ai_config', {}))
        ai_config = AIConfig(
            provider=ai_config_dict.get('ai_provider', 'deepseek'),
            api_key=ai_config_dict.get('api_key', ''),
            api_base=ai_config_dict.get('api_base', 'https://api.deepseek.com/v1'),
            model=ai_config_dict.get('model', 'deepseek-reasoner'),
            max_tokens=ai_config_dict.get('max_tokens', 40000),
            temperature=ai_config_dict.get('temperature', 0.7),
            timeout=ai_config_dict.get('timeout', 60),
            max_retries=ai_config_dict.get('max_retries', 3),
            retry_delay=ai_config_dict.get('retry_delay', 2)
        )
        ai_adapter = AIAdapter(ai_config)
        
        # 创建能力生成器
        self.capability_generator = CapabilityGenerator(self.storage_manager, ai_adapter)
        
        # 创建迭代式进化器
        iterative_config = self.config.get('evolution', {}).get('iterative_config', {})
        self.iterative_evolver = IterativeEvolver(self.capability_generator, iterative_config)
    
    def _start_auto_evolution(self):
        """启动后台自动进化线程"""
        try:
            self.auto_thread = threading.Thread(target=self._auto_evolution_loop, daemon=True)
            self.auto_thread.start()
            print("\n✓ 后台自动进化线程已启动")
        except Exception as e:
            print(f"\n✗ 后台线程启动失败: {e}")
            logging.error(f"后台进化线程启动异常: {e}", exc_info=True)
    
    def _auto_evolution_loop(self):
        """后台自动进化循环"""
        try:
            logging.info("后台进化循环开始...")
        except:
            pass  # 忽略日志错误
        
        while self.running:
            try:
                # 检查是否启用自动进化
                if not self.auto_evolution_enabled:
                    logging.info(f"后台进化已暂停，等待5秒...")
                    time.sleep(5)
                    continue
                
                # 等待指定间隔
                logging.info(f"后台进化: 等待 {self.auto_interval} 秒后开始下一轮进化...")
                for i in range(self.auto_interval):
                    if not self.running or not self.auto_evolution_enabled:
                        break
                    time.sleep(1)
                    # 每10秒输出一次进度
                    if (i + 1) % 10 == 0:
                        logging.info(f"后台进化: 等待中... {i+1}/{self.auto_interval} 秒")
                
                if not self.running or not self.auto_evolution_enabled:
                    logging.info("后台进化: 检测到停止信号，退出循环")
                    continue
                
                logging.info("后台进化: 开始选择进化目标...")
                
                # 检查队列中是否有用户指定的任务
                goal = None
                try:
                    guidance = self.evolution_queue.get_nowait()
                    logging.info(f"后台进化: 处理用户指定任务 - {guidance[:50]}...")
                    # 创建临时目标对象
                    from prokaryote_agent.goal_manager import GoalPriority
                    goal = EvolutionGoal(
                        title="用户指定任务",
                        description=guidance,
                        priority=GoalPriority.HIGH,
                        acceptance_criteria=["完成用户指定的功能"]
                    )
                except Empty:
                    # 队列为空，优先从进化目标选择
                    goal = self._select_evolution_target()
                    if not goal:
                        continue
                    
                    logging.info(f"后台进化: 自主选择任务 - {goal.title}")
                
                # 执行进化
                with self.auto_thread_lock:
                    self._evolve_once(goal, is_auto=True)
                
            except Exception as e:
                logging.error(f"后台进化异常: {e}", exc_info=True)
                time.sleep(10)
    
    def _select_evolution_target(self):
        """
        选择下一个进化目标
        优先从 evolution_goals.md 读取，如果没有则使用AI决策
        返回 EvolutionGoal 对象
        """
        # 检查当前能力数量
        result = manage_capabilities("list")
        if result["success"] and result['total_count'] >= self.max_capabilities:
            logging.info(f"后台进化: 已达到能力上限 ({result['total_count']}/{self.max_capabilities})，跳过本轮进化")
            return None
        
        # 优先尝试从进化目标文件读取
        try:
            # 获取下一个待执行的目标
            next_goal = self.goal_manager.get_next_goal()
            if next_goal:
                logging.info(f"从进化目标文件选择: {next_goal.title}")
                return next_goal
        except Exception as e:
            logging.warning(f"读取进化目标失败: {e}")
        
        # 如果没有进化目标，直接返回None（暂时禁用AI决策，避免重复生成）
        logging.info("后台进化: 无待执行目标，跳过本轮进化")
        return None
        
        # ⚠️ AI决策功能已临时禁用，避免生成重复能力
        # 如需启用，请先实施重复检测机制（参见 docs/重复能力问题分析.md）
        
        # 如果没有进化目标，使用AI分析决策（已禁用）
        # 加载进化历史
        history = self._load_evolution_history()
        recent_evolutions = history["evolution_history"][-10:]  # 最近10次进化
        
        # 加载进化原则
        principles = self._load_evolution_principles()
        
        # 构建当前状态分析
        state = query_prokaryote_state()
        current_capabilities = result.get('capabilities', [])
        
        # 构建进化历史描述
        history_desc = "\n".join([
            f"- [{record['timestamp'][:10]}] {record['capability_name']}: {record['description']} (原因: {record.get('evolution_reason', '未记录')})"
            for record in recent_evolutions
        ]) if recent_evolutions else '（暂无历史）'
        
        analysis_prompt = f"""你是一个自进化AI系统的决策模块，负责规划系统的能力扩展方向。

当前系统状态：
- 已有能力数量: {result['total_count']}
- 启用能力: {result['enabled_count']}
- 禁用能力: {result['disabled_count']}
- 能力上限: {self.max_capabilities}
- 总进化次数: {history['total_evolutions']}
- 成功进化: {history['successful_evolutions']}
- 失败进化: {history['failed_evolutions']}

已有能力列表：
{chr(10).join([f"- {cap['name']}: {cap['description']}" for cap in current_capabilities[:10]]) if current_capabilities else '（暂无能力）'}

最近进化历史（最多显示10条）：
{history_desc}

进化原则文档：
{principles}

请基于以上原则和当前状态，决定下一步应该生成什么功能模块。

直接输出一个具体的功能模块描述（一句话），例如：
"HTTP客户端模块（支持GET/POST请求和JSON解析）"
"本地SQLite数据库操作模块（创建表、增删改查）"
"系统监控模块（获取CPU、内存、磁盘使用情况）"

只输出功能模块描述，不要其他内容："""
        
        try:
            # 调用AI生成决策
            from prokaryote_agent.ai_adapter import AIAdapter, AIConfig
            
            # 从配置文件加载API密钥
            ai_config = AIConfig(
                api_key=self.config.get('capability_config', {}).get('api_key', ''),
                model=self.config.get('capability_config', {}).get('model', 'deepseek-reasoner')
            )
            adapter = AIAdapter(config=ai_config)
            
            # 调用AI（_call_ai只接受prompt字符串参数）
            result = adapter._call_ai(analysis_prompt)
            
            if result.get('success') and result.get('content'):
                decision = result['content'].strip()
                
                if len(decision) > 10:
                    # 清理输出，提取第一行作为能力描述
                    lines = [line.strip() for line in decision.split('\n') if line.strip()]
                    capability_desc = lines[0] if lines else None
                    
                    # 验证是否是有效的能力描述
                    if capability_desc and len(capability_desc) < 200:
                        # 创建临时目标对象
                        from prokaryote_agent.goal_manager import GoalPriority
                        ai_goal = EvolutionGoal(
                            title="AI决策任务",
                            description=capability_desc,
                            priority=GoalPriority.MEDIUM,
                            acceptance_criteria=["完成AI决策的功能"]
                        )
                        logging.info(f"AI决策生成目标: {capability_desc}")
                        return ai_goal
            
            # AI决策失败，取消本次进化
            logging.warning("AI决策未返回有效的能力描述，取消本次进化")
            return None
            
        except Exception as e:
            logging.error(f"AI决策失败: {e}", exc_info=True)
            # AI决策异常，取消本次进化
            return None
    
    def _show_status(self):
        """显示系统状态"""
        try:
            state = query_prokaryote_state()
            result = manage_capabilities("list")
            
            print(f"\n[状态]")
            print(f"  系统: 运行中")
            
            # 安全访问嵌套字典
            resource = state.get('resource', {})
            if resource:
                print(f"  内存: {resource.get('memory_mb', 0):.2f} MB")
                print(f"  CPU: {resource.get('cpu_percent', 0):.2f}%")
            
            print(f"  总进化次数: {self.evolution_count}")
            print(f"  后台进化: {'启用' if self.auto_evolution_enabled else '暂停'}")
            
            if result.get("success"):
                print(f"  能力统计: {result.get('total_count', 0)} 个 " +
                      f"(启用: {result.get('enabled_count', 0)}, 禁用: {result.get('disabled_count', 0)})")
        except Exception as e:
            print(f"  ⚠️  状态显示出错: {e}")
            logging.error(f"显示状态异常: {e}", exc_info=True)
    
    def _show_capabilities(self):
        """显示能力列表"""
        result = manage_capabilities("list")
        
        if not result["success"]:
            print(f"✗ 获取能力列表失败: {result.get('error', 'Unknown')}")
            return
        
        total = result['total_count']
        enabled = result['enabled_count']
        disabled = result['disabled_count']
        
        print(f"\n[能力列表] 总数: {total} | 启用: {enabled} | 禁用: {disabled}")
        
        if result["capabilities"]:
            for i, cap in enumerate(result["capabilities"], 1):
                status_icon = "✓" if cap['status'] == 'enabled' else "✗"
                safety_icon = "🔒" if cap['safety_level'] == 'safe' else "⚠️"
                print(f"  {i}. {status_icon} {safety_icon} {cap['name']}")
                print(f"     {cap['description'][:60]}...")
                
                perf = cap.get('performance', {})
                if perf.get('total_invocations', 0) > 0:
                    print(f"     调用{perf['total_invocations']}次, " +
                          f"平均{perf['avg_execution_time_ms']:.1f}ms, " +
                          f"成功率{perf['success_rate']*100:.0f}%")
    
    def _evolve_once(self, goal: EvolutionGoal, is_auto: bool = False):
        """
        执行一次进化（支持迭代式进化）
        
        Args:
            goal: 进化目标对象
            is_auto: 是否为后台自动进化
        """
        self.evolution_count += 1
        
        prefix = "[后台进化]" if is_auto else "[手动进化]"
        
        # 选择输出方法：后台用_safe_print，手动用print
        output = self._safe_print if is_auto else print
        
        output(f"\n{prefix} 📎 目标: {goal.title}")
        output(f"  优先级: {goal.priority.value}")
        output(f"  模式: {'迭代式' if self.evolution_mode == 'iterative' else '简单'}")
        
        try:
            if self.evolution_mode == 'iterative' and self.iterative_evolver:
                # 使用迭代式进化
                output(f"  🔄 开始迭代式进化...")
                logging.info(f"{prefix} 开始迭代式进化: {goal.title}")
                
                # 标记为进行中
                self.goal_manager.mark_goal_in_progress(goal)
                
                # 执行迭代式进化
                result = self.iterative_evolver.evolve_with_iterations(goal)
                
                if result.get('success'):
                    output(f"\n{prefix} ✅ 迭代进化成功!")
                    output(f"  最佳版本: {result.get('best_capability_id', 'unknown')}")
                    output(f"  测试通过率: {result.get('best_test_pass_rate', 0)*100:.1f}%")
                    output(f"  总迭代次数: {result.get('total_iterations', 0)}")
                    output(f"  完成阶段: {result.get('completed_stages', 0)}/{result.get('total_stages', 0)}")
                    
                    # 标记目标完成
                    capability_ids = [result.get('best_capability_id', '')]
                    self.goal_manager.mark_goal_completed(goal, capability_ids)
                    logging.info(f"{prefix} 进化目标已完成: {goal.title}")
                    
                    # 记录进化历史
                    self._add_evolution_record(
                        capability_id=result.get('best_capability_id', 'unknown'),
                        capability_name=goal.title,
                        description=goal.description,
                        evolution_reason=f"迭代式进化，{result.get('total_iterations')}次迭代",
                        success=True
                    )
                else:
                    error_msg = result.get('error', '未知错误')
                    output(f"\n{prefix} ❌ 迭代进化失败: {error_msg}")
                    logging.error(f"{prefix} 进化失败: {goal.title} - {error_msg}")
                    
                    # 标记失败
                    self.goal_manager.mark_goal_failed(goal, error_msg)
                    
                    # 记录失败
                    self._add_evolution_record(
                        capability_id="failed",
                        capability_name=goal.title,
                        description=error_msg,
                        evolution_reason=goal.description,
                        success=False
                    )
            else:
                # 使用简单模式
                output(f"  🧬 开始简单进化...")
                logging.info(f"{prefix} 开始简单进化: {goal.title}")
                
                guidance = self.goal_manager.generate_guidance_from_goal(goal)
                result = generate_capability(guidance)
                
                if result["success"]:
                    output(f"\n{prefix} ✓ 能力生成成功!")
                    output(f"  ID: {result['capability_id']}")
                    output(f"  名称: {result['capability_name']}")
                    output(f"  描述: {result['description']}")
                    output(f"  安全等级: {result['safety_level']}")
                    
                    # 标记目标完成
                    self.goal_manager.mark_goal_completed(goal, [result['capability_id']])
                    
                    # 记录进化历史
                    self._add_evolution_record(
                        capability_id=result['capability_id'],
                        capability_name=result['capability_name'],
                        description=result['description'],
                        evolution_reason=guidance,
                        success=True
                    )
                    
                    # 自动启用安全能力
                    if self.auto_enable and result['safety_level'] == 'safe':
                        enable_result = manage_capabilities("enable", capability_id=result['capability_id'])
                        if enable_result["success"]:
                            output(f"  ✓ 已自动启用")
                else:
                    output(f"\n{prefix} ✗ 能力生成失败: {result.get('error', 'Unknown')}")
                    
                    # 标记失败
                    self.goal_manager.mark_goal_failed(goal, result.get('error', 'Unknown'))
                    
                    # 记录失败的进化尝试
                    self._add_evolution_record(
                        capability_id="failed",
                        capability_name="generation_failed",
                        description=result.get('error', 'Unknown'),
                        evolution_reason=guidance,
                        success=False
                    )
        except Exception as e:
            error_msg = str(e)
            output(f"\n{prefix} ❌ 进化异常: {error_msg}")
            logging.error(f"{prefix} 进化异常: {goal.title}", exc_info=True)
            
            # 标记失败
            try:
                self.goal_manager.mark_goal_failed(goal, error_msg)
            except:
                pass
    
    def _show_help(self):
        """显示帮助"""
        print("\n" + "="*70)
        print("  命令列表")
        print("="*70)
        print("\n  【进化相关】")
        print("  evolve <描述>   - 立即生成新能力（插队到后台任务）")
        print("  queue <描述>    - 添加进化任务到队列（后台处理）")
        print("  goals           - 查看进化目标状态")
        print("  pause           - 暂停后台自动进化")
        print("  resume          - 恢复后台自动进化")
        print("\n  【能力管理】")
        print("  list            - 列出所有能力")
        print("  enable <ID>     - 启用能力")
        print("  disable <ID>    - 禁用能力")
        print("  info <ID>       - 查看能力详情")
        print("\n  【系统监控】")
        print("  status          - 查看系统状态")
        print("  stats           - 查看详细统计")
        print("\n  【其他】")
        print("  help            - 显示此帮助")
        print("  quit/exit       - 退出程序")
        print("="*70)
    
    def run_command_loop(self):
        """运行命令循环"""
        print("\n" + "="*70)
        print("  系统已就绪 - 混合进化模式")
        print("  后台正在持续自主进化，您可随时输入命令指引")
        print("  输入 'help' 查看命令 | 'pause' 暂停后台 | 'quit' 退出")
        print("  注意: 由于Windows兼容性问题，请使用 'quit' 命令退出")
        print("="*70)
        
        # 在整个命令循环期间禁用SIGINT，避免Python 3.13 + Windows的logging中断问题
        # 用户需要使用 'quit' 命令退出
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        
        while self.running:
            try:
                sys.stdout.write("\nprokaryote> ")
                sys.stdout.flush()
                cmd_input = sys.stdin.readline()
                if not cmd_input:
                    print("\n检测到输入结束(EOF)，程序退出")
                    break
                
                cmd_input = cmd_input.strip()
                
                if not cmd_input:
                    continue
                
                parts = cmd_input.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd in ['quit', 'exit', 'q']:
                    print("正在退出...")
                    break
                
                elif cmd == 'help' or cmd == 'h':
                    self._show_help()
                
                elif cmd == 'status':
                    self._show_status()
                
                elif cmd == 'stats':
                    self._show_status()
                    self._show_capabilities()
                
                elif cmd == 'list' or cmd == 'ls':
                    self._show_capabilities()
                
                elif cmd == 'pause':
                    self.auto_evolution_enabled = False
                    print("✓ 后台自动进化已暂停")
                
                elif cmd == 'resume':
                    self.auto_evolution_enabled = True
                    print("✓ 后台自动进化已恢复")
                
                elif cmd == 'goals':
                    try:
                        summary = self.goal_manager.get_summary()
                        print(f"\n[进化目标状态]")
                        print(f"  总数: {summary['total']}")
                        print(f"  待执行: {summary['pending']}")
                        print(f"  进行中: {summary['in_progress']}")
                        print(f"  已完成: {summary['completed']}")
                        print(f"  失败: {summary['failed']}")
                        
                        pending = self.goal_manager.get_pending_goals()
                        if pending:
                            print(f"\n  待执行目标:")
                            for goal in pending[:5]:
                                print(f"    - {goal.title} (优先级: {goal.priority.value})")
                    except Exception as e:
                        print(f"✗ 获取目标状态失败: {e}")
                
                elif cmd == 'evolve':
                    if not args:
                        print("✗ 用法: evolve <功能描述>")
                    else:
                        print(f"[立即执行] 正在生成能力...")
                        # 创建临时目标
                        from prokaryote_agent.goal_manager import GoalPriority
                        temp_goal = EvolutionGoal(
                            title="手动指定任务",
                            description=args,
                            priority=GoalPriority.HIGH,
                            acceptance_criteria=["完成用户指定的功能"]
                        )
                        with self.auto_thread_lock:
                            self._evolve_once(temp_goal, is_auto=False)
                
                elif cmd == 'queue':
                    if not args:
                        print("✗ 用法: queue <功能描述>")
                    else:
                        self.evolution_queue.put(args)
                        print(f"✓ 已添加到进化队列，后台将处理")
                
                elif cmd == 'enable':
                    if not args:
                        print("✗ 用法: enable <能力ID>")
                    else:
                        result = manage_capabilities("enable", capability_id=args)
                        if result["success"]:
                            print(f"✓ {result.get('message', '已启用')}")
                        else:
                            print(f"✗ {result.get('error', 'Unknown')}")
                
                elif cmd == 'disable':
                    if not args:
                        print("✗ 用法: disable <能力ID>")
                    else:
                        result = manage_capabilities("disable", capability_id=args)
                        if result["success"]:
                            print(f"✓ {result.get('message', '已禁用')}")
                        else:
                            print(f"✗ {result.get('error', 'Unknown')}")
                
                elif cmd == 'info':
                    if not args:
                        print("✗ 用法: info <能力ID>")
                    else:
                        result = manage_capabilities("info", capability_id=args)
                        if result["success"]:
                            cap = result["capability"]
                            print(f"\n[能力详情]")
                            print(f"  ID: {cap['id']}")
                            print(f"  名称: {cap['name']}")
                            print(f"  版本: {cap['version']}")
                            print(f"  状态: {cap['status']}")
                            print(f"  描述: {cap['description']}")
                            print(f"  入口函数: {cap['entry_function']}")
                            print(f"  安全等级: {cap['safety_level']}")
                            
                            perf = cap.get('performance', {})
                            if perf.get('total_invocations', 0) > 0:
                                print(f"\n  性能统计:")
                                print(f"    调用次数: {perf['total_invocations']}")
                                print(f"    平均耗时: {perf['avg_execution_time_ms']:.2f} ms")
                                print(f"    成功率: {perf['success_rate']*100:.1f}%")
                        else:
                            print(f"✗ {result.get('error', 'Unknown')}")
                
                else:
                    print(f"✗ 未知命令: {cmd}")
                    print("  输入 'help' 查看可用命令")
            
            except EOFError:
                print("\n正在退出...")
                break
            except Exception as e:
                print(f"\n✗ 命令执行出错: {e}")
                logging.error(f"命令执行异常: {e}", exc_info=True)
    
    def shutdown(self):
        """关闭系统"""
        if self.initialized:
            print("\n[关闭] 正在停止系统...")
            self.running = False
            
            # 等待后台线程
            if self.auto_thread and self.auto_thread.is_alive():
                print("  等待后台线程退出...")
                self.auto_thread.join(timeout=3)
            
            stop_prokaryote()
            print("✓ 系统已停止")
            
            # 显示最终统计
            result = manage_capabilities("list")
            if result["success"]:
                print(f"\n[最终统计]")
                print(f"  总进化次数: {self.evolution_count}")
                print(f"  生成能力: {result['total_count']} 个")
                print(f"  启用能力: {result['enabled_count']} 个")
        
        self.running = False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prokaryote Agent - 混合进化模式')
    parser.add_argument('--interval', type=int, default=60,
                       help='后台进化间隔（秒），默认60秒')
    parser.add_argument('--max-capabilities', type=int, default=20,
                       help='最大能力数量，默认20个')
    parser.add_argument('--auto-enable', action='store_true',
                       help='自动启用安全的能力')
    parser.add_argument('--mode', choices=['simple', 'iterative'], default='iterative',
                       help='进化模式：simple=简单模式，iterative=迭代式（默认）')
    
    args = parser.parse_args()
    
    agent = HybridAgent(
        auto_interval=args.interval,
        max_capabilities=args.max_capabilities,
        auto_enable=args.auto_enable
    )
    
    # 设置进化模式
    if hasattr(args, 'mode'):
        agent.evolution_mode = args.mode
    
    # 初始化
    if not agent.initialize():
        print("\n✗ 初始化失败，无法启动")
        return 1
    
    # 运行命令循环
    try:
        agent.run_command_loop()
    except Exception as e:
        print(f"\n✗ 运行异常: {e}")
        logging.error(f"主循环异常: {e}", exc_info=True)
        return 1
    finally:
        agent.shutdown()
    
    print("\n" + "="*70)
    print("  混合进化模式已退出")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
