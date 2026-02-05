"""CollaborationInterface - 多智能体协作接口"""
import json
from datetime import datetime
from pathlib import Path

class CollaborationInterface:
    def __init__(self, agent_id="agent_001", config=None):
        self.agent_id = agent_id
        self.config = config or {}
        self.task_queue = []
        self.active_tasks = self.task_queue  # 别名以匹配测试
        self.collaboration_history = []
        self.shared_capabilities = {}
    
    def receive_task(self, task):
        """接收协作任务"""
        task_record = {
            "task_id": task.get("id", f"task_{len(self.task_queue)}"),
            "description": task.get("description", ""),
            "from_agent": task.get("from_agent", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        self.task_queue.append(task_record)
        return task_record["task_id"]
    
    def report_progress(self, task_id, progress=None, status="in_progress"):
        """报告任务进度"""
        for task in self.task_queue:
            if task["task_id"] == task_id:
                task["status"] = status
                if progress is not None:
                    task["progress"] = progress
                task["last_update"] = datetime.now().isoformat()
                
                # 记录到历史
                self.collaboration_history.append({
                    "agent_id": self.agent_id,
                    "task_id": task_id,
                    "progress": progress,
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                })
                return True
        return False
    
    def share_capability(self, capability_name, capability_data=None):
        """共享能力给其他智能体"""
        if capability_data is None:
            capability_data = {"name": capability_name, "exported": True}
        
        self.shared_capabilities[capability_name] = {
            "data": capability_data,
            "shared_by": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
        return True
    
    def request_assistance(self, task_description=None, required_capabilities=None, problem=None, context=None):
        """请求其他智能体协助"""
        # 支持旧API: problem + context
        if problem is not None:
            task_description = problem
        if context is not None:
            required_capabilities = context
        
        request = {
            "request_id": f"req_{len(self.collaboration_history)}",
            "from_agent": self.agent_id,
            "task": task_description or "",
            "required_capabilities": required_capabilities or [],
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        self.collaboration_history.append(request)
        return request["request_id"]
    
    def provide_assistance(self, request_id=None, capability_data=None, request=None):
        """为其他智能体提供协助"""
        # 支持旧API: 直接传request字典
        if request is not None and isinstance(request, dict):
            request_id = request.get("request_id", f"req_{len(self.collaboration_history)}")
            capability_data = {"response": "assistance provided", "request": request}
        
        assistance = {
            "assistance_id": f"assist_{request_id}",
            "from_agent": self.agent_id,
            "request_id": request_id,
            "capability_provided": capability_data or {},
            "timestamp": datetime.now().isoformat()
        }
        self.collaboration_history.append(assistance)
        return assistance["assistance_id"]
    
    def assess_collaboration_readiness(self, task_requirements=None):
        """评估智能体是否准备好协作"""
        # 简单评估逻辑
        readiness = {
            "ready": True,
            "confidence": 0.8,
            "available_capabilities": list(self.shared_capabilities.keys()),
            "pending_tasks": len([t for t in self.task_queue if t["status"] == "pending"])
        }
        
        # 如果待处理任务过多，降低准备度
        if readiness["pending_tasks"] > 5:
            readiness["ready"] = False
            readiness["confidence"] = 0.3
        
        return readiness
    
    def get_collaboration_summary(self):
        """获取协作历史摘要"""
        return {
            "agent_id": self.agent_id,
            "total_tasks": len(self.task_queue),
            "completed_tasks": len([t for t in self.task_queue if t["status"] == "completed"]),
            "shared_capabilities": len(self.shared_capabilities),
            "collaboration_events": len(self.collaboration_history)
        }
