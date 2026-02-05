"""EvolutionDaemon - 进化守护进程"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime

class EvolutionDaemon:
    def __init__(self, config_path=None, generation_manager=None, genetic_transmitter=None, 
                 mutation_engine=None, collaboration_interface=None):
        # 加载配置
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
        self.current_generation = 0  # 新增字段以匹配测试
        self.daemon_running = False  # 新增字段以匹配测试

    def _handle_agent_message(self, message):
        """处理来自智能体的消息"""
        if message:
            self.agent_messages.append(message)
            msg_type = message.get("type", "unknown")
            event_type = message.get("event", "unknown")
            
            # 兼容两种格式：type="evolution_success" 或 event="EVOLUTION_SUCCESS"
            if msg_type == "evolution_success" or event_type == "EVOLUTION_SUCCESS":
                self.evolution_count_in_generation += 1
            elif msg_type == "heartbeat" or event_type == "HEARTBEAT":
                self.last_heartbeat_time = datetime.now().isoformat()
            
            return True
        return False
        
    def handle_agent_message(self, message):
        """处理消息的公有包装"""
        return self._handle_agent_message(message)
        
    def get_status(self):
        """获取守护进程状态"""
        return {
            "running": self.running,
            "daemon_running": self.daemon_running,
            "evolution_count": self.evolution_count_in_generation,
            "threshold": self.config.get("evolution_threshold", 10),
            "current_generation": self.current_generation,
            "agent_alive": self._is_agent_alive()
        }

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
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True
    
    def stop(self):
        """停止守护进程"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        return True
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            # 检查智能体状态
            if not self._is_agent_alive():
                print("智能体无响应，尝试修复...")
            
            # 检查是否需要代际切换
            if self._should_trigger_generation_transition():
                self._trigger_generation_transition()
            
            time.sleep(self.config.get("monitor_interval", 1.0))
    
    def _is_agent_alive(self):
        """检查智能体是否存活"""
        # 简单实现：检查最近是否有消息
        if not self.agent_messages:
            return True
        
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
    
    def handle_agent_message(self, message):
        """处理智能体消息"""
        message["timestamp"] = time.time()
        self.agent_messages.append(message)
        
        # 限制消息历史长度
        if len(self.agent_messages) > 100:
            self.agent_messages = self.agent_messages[-100:]
    
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
            "current_generation": self.generation_manager.get_current_generation() if self.generation_manager else 0
        }
