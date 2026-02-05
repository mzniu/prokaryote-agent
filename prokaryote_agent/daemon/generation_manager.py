"""GenerationManager - 代际管理器"""
import json
import shutil
from pathlib import Path
from datetime import datetime

class GenerationManager:
    def __init__(self, root_dir: str = "generations"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.lineage_file = self.root_dir / "lineage.json"
        self.current_gen_file = self.root_dir / "current_generation.txt"
        self.active_lineage_file = self.root_dir / "active_lineage.txt"
        self._init_files()
    
    def _init_files(self):
        if not self.lineage_file.exists():
            with open(self.lineage_file, 'w') as f:
                json.dump({"lineages": {"main": {"branch_id": "main", "generations": [0], "current_generation": 0}}, 
                          "generation_graph": {"0": {"parent": None, "children": [], "lineage": "main"}}}, f)
        if not self.current_gen_file.exists():
            self.current_gen_file.write_text("0")
        if not self.active_lineage_file.exists():
            self.active_lineage_file.write_text("main")
    
    def _load_lineage(self):
        with open(self.lineage_file, 'r') as f:
            return json.load(f)
    
    def _save_lineage(self, data):
        with open(self.lineage_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_current_generation(self):
        return int(self.current_gen_file.read_text().strip())
    
    def get_current_lineage(self):
        return self.active_lineage_file.read_text().strip()
    
    def create_snapshot(self, generation, lineage="main"):
        snapshot_dir = self.root_dir / f"gen_{generation:04d}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        metadata = {"generation": generation, "lineage": lineage, "timestamp": datetime.now().isoformat()}
        with open(snapshot_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)
        cap_reg = Path("prokaryote_agent/capability_registry.json")
        if cap_reg.exists():
            shutil.copy(cap_reg, snapshot_dir / "capability_registry.json")
        return snapshot_dir
    
    def restore_from_snapshot(self, generation):
        snapshot_dir = self.root_dir / f"gen_{generation:04d}"
        if not snapshot_dir.exists():
            return False
        self.current_gen_file.write_text(str(generation))
        return True
    
    def create_branch(self, from_generation, new_lineage, description=""):
        source_dir = self.root_dir / f"gen_{from_generation:04d}"
        if not source_dir.exists():
            return False
        lineage_data = self._load_lineage()
        if new_lineage in lineage_data["lineages"]:
            return False
        lineage_data["lineages"][new_lineage] = {
            "branch_id": new_lineage, "description": description,
            "parent_generation": from_generation, "generations": [from_generation], "current_generation": from_generation
        }
        self._save_lineage(lineage_data)
        self.active_lineage_file.write_text(new_lineage)
        return True
