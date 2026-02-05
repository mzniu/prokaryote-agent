"""EvolutionDaemon - 进化守护进程"""
import json
import time
import threading
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import psutil

class EvolutionDaemon:
    def __init__(self, config_path=None, generation_manager=None, genetic_transmitter=None, 
                 mutation_engine=None, collaboration_interface=None):
        # 加载配置
        self.config_path = config_path
        if config_path:
            self.config = self._load_config_from_file(config_path)
        else:
            self.config = {
                "evolution_threshold": 10,
                "monitor_interval": 1.0,
                "max_generation": 100,
                "restart_threshold": 10,
                "restart_trigger": "on_error"
            }
        
        # 组件依赖
        self.generation_manager = generation_manager
        self.genetic_transmitter = genetic_transmitter
        self.mutation_engine = mutation_engine
        self.collaboration_interface = collaboration_interface
        
        # 状态
        self.running = False
        self.monitor_thread = None
        self.evolution_count_in_generation = 0
        self.agent_messages = []
        self.restart_threshold = self.config.get("restart_threshold", 10)
        self.current_generation = 0  
        self.daemon_running = False  
        self.agent_pid = None
        self.agent_process = None

    def _load_config_from_file(self, path):
        """从文件加载配置"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"配置加载失败: {e}, 使用默认配置")
            return {
                "evolution_threshold": 10,
                "monitor_interval": 1.0,
                "max_generation": 100,
                "restart_threshold": 10,
                "restart_trigger": "on_error"
            }
    
    def start(self):
        """启动守护进程"""
        if self.running:
            return False
        
        self.running = True
        self.daemon_running = True
        
        # 启动 Agent 进程
        if not self._start_agent():
            print("⚠️  无法启动Agent进程，守护进程将以监控模式运行")
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True
    
    def _start_agent(self):
        """启动Agent进化进程"""
        try:
            # 查找 simple_agent.py (简化版) 或 goal_evolution.py
            project_root = Path(__file__).parent.parent.parent
            agent_script = project_root / "simple_agent.py"
            if not agent_script.exists():
                agent_script = project_root / "goal_evolution.py"
            
            if not agent_script.exists():
                print(f"❌ Agent脚本不存在: {agent_script}")
                return False
            
            # 获取进化模式配置
            interval = self.config.get('monitor_interval', 30)
            
            # 启动 agent 脚本
            cmd = [sys.executable, str(agent_script), '--mode', 'iterative', '--interval', str(interval)]
            print(f"🚀 启动Agent: {' '.join(cmd)}")
            
            # 设置环境变量确保能找到模块
            env = os.environ.copy()
            project_root = str(agent_script.parent)
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = project_root + os.pathsep + env['PYTHONPATH']
            else:
                env['PYTHONPATH'] = project_root
            
            self.agent_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=project_root,
                env=env
            )
            self.agent_pid = self.agent_process.pid
            print(f"✅ Agent已启动 (PID: {self.agent_pid})")
            
            # 启动输出读取线程
            self._output_thread = threading.Thread(target=self._read_agent_output, daemon=True)
            self._output_thread.start()
            
            return True
        except Exception as e:
            print(f"❌ 启动Agent失败: {e}")
            return False
    
    def _read_agent_output(self):
        """读取Agent输出"""
        try:
            for line in self.agent_process.stdout:
                line = line.strip()
                if line:
                    print(f"[Agent] {line}")
                    # 记录消息用于心跳检测
                    self.agent_messages.append({
                        "timestamp": time.time(),
                        "message": line
                    })
                    # 只保留最近100条消息
                    if len(self.agent_messages) > 100:
                        self.agent_messages = self.agent_messages[-100:]
        except Exception as e:
            if self.running:
                print(f"⚠️ 读取Agent输出失败: {e}")
    
    def _stop_agent(self):
        """停止Agent进程"""
        if self.agent_process:
            try:
                self.agent_process.terminate()
                self.agent_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.agent_process.kill()
            except Exception as e:
                print(f"⚠️ 停止Agent失败: {e}")
            finally:
                self.agent_process = None
                self.agent_pid = None
    
    def stop(self):
        """停止守护进程"""
        self.running = False
        self.daemon_running = False
        
        # 停止Agent进程
        self._stop_agent()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        return True
    
    def _monitor_loop(self):
        """监控循环"""
        restart_count = 0
        max_restarts = 3
        
        while self.running:
            # 检查Agent进程状态
            if self.agent_process:
                ret = self.agent_process.poll()
                if ret is not None:
                    # Agent进程已退出
                    print(f"⚠️  Agent进程退出 (exit code: {ret})")
                    self.agent_pid = None
                    self.agent_process = None
                    
                    # 尝试重启
                    if restart_count < max_restarts:
                        restart_count += 1
                        print(f"🔄 尝试重启Agent ({restart_count}/{max_restarts})...")
                        time.sleep(2)  # 等待2秒后重启
                        if self._start_agent():
                            print("✅ Agent重启成功")
                        else:
                            print("❌ Agent重启失败")
                    else:
                        print(f"❌ Agent已达最大重启次数 ({max_restarts})，停止重试")
            
            # 检查是否需要代际切换
            if self._should_trigger_generation_transition():
                self._trigger_generation_transition()
            
            time.sleep(self.config.get("monitor_interval", 1.0))
    
    def _is_agent_alive(self):
        """检查智能体是否存活"""
        # 如果设置了PID，检查进程
        if self.agent_pid:
            try:
                if psutil: 
                    # 检查进程是否存在
                    found = False
                    for proc in psutil.process_iter(['pid']):
                        if proc.info['pid'] == self.agent_pid:
                            found = True
                            break
                    if not found:
                        return False
            except Exception:
                # 忽略检查错误
                pass
        
        # 如果没有PID或检查通过，继续检查消息心跳
        
        # 简单实现：检查最近是否有消息
        if not self.agent_messages:
            # 没有消息记录，默认为False (匹配测试预期)
            return False
        
        last_message_time = self.agent_messages[-1].get("timestamp", 0)
        current_time = time.time()
        
        # 如果超过10秒没有消息，认为可能无响应
        return (current_time - last_message_time) < 10


    
    def _should_trigger_generation_transition(self):
        """判断是否应该触发代际切换"""
        threshold = self.config.get("evolution_threshold", 10)
        return self.evolution_count_in_generation >= threshold
    
    def _trigger_generation_transition(self):
        """触发代际切换"""
        if not self.generation_manager or not self.genetic_transmitter:
            return
        
        print("触发代际切换...")
        
        # 获取当前代数
        current_gen = self.generation_manager.get_current_generation()
        
        # 创建快照
        self.generation_manager.create_snapshot(current_gen)
        
        # 生成基因
        genes = self.genetic_transmitter.generate_genes(
            generation=current_gen,
            capabilities=[]  # 从智能体获取能力
        )
        
        # 应用变异
        if self.mutation_engine:
            mutations = self.mutation_engine.apply_mutations(genes)
            genes["mutations"] = mutations
        
        # 保存基因
        genes_path = self.genetic_transmitter.save_genes(
            genes, 
            f"generations/gen_{current_gen + 1:04d}"
        )
        
        # 重置计数
        self.evolution_count_in_generation = 0
        
        print(f"代际切换完成: gen_{current_gen} -> gen_{current_gen + 1}")
    
    def _handle_agent_message(self, message):
        """处理来自智能体的消息 (内部别名兼容测试)"""
        return self.handle_agent_message(message)

    def handle_agent_message(self, message):
        """处理来自智能体的消息"""
        if message:
            # 统一添加时间戳
            if "timestamp" not in message:
                message["timestamp"] = time.time()
                
            self.agent_messages.append(message)
            # 限制消息历史长度
            if len(self.agent_messages) > 100:
                self.agent_messages = self.agent_messages[-100:]
            
            msg_type = message.get("type", "unknown")
            event_type = message.get("event", "unknown")
            
            # 兼容两种格式：type="evolution_success" 或 event="EVOLUTION_SUCCESS"
            if msg_type == "evolution_success" or event_type == "EVOLUTION_SUCCESS":
                self.evolution_count_in_generation += 1
            elif msg_type == "heartbeat" or event_type == "HEARTBEAT":
                self.last_heartbeat_time = datetime.now().isoformat()
            
            return True
        return False
    
    def report_evolution(self, event_type="task_completed"):
        """报告进化事件"""
        self.evolution_count_in_generation += 1
        
        return {
            "event_type": event_type,
            "evolution_count": self.evolution_count_in_generation,
            "threshold": self.config.get("evolution_threshold", 10),
            "progress": self.evolution_count_in_generation / self.config.get("evolution_threshold", 10)
        }
    
    def get_status(self):
        """获取守护进程状态"""
        return {
            "running": self.running,
            "daemon_running": self.running,
            "evolution_count": self.evolution_count_in_generation,
            "threshold": self.config.get("evolution_threshold", 10),
            "restart_threshold": self.config.get("restart_threshold", 10),
            "current_generation": self.generation_manager.get_current_generation() if self.generation_manager else 0,
            "agent_alive": self._is_agent_alive()
        }
