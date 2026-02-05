#!/usr/bin/env python3
"""
Prokaryote Agent Generational Evolution Daemon

Main CLI entry point for managing the generational evolution daemon.
Supports starting/stopping the daemon, querying status, managing generations,
and visualizing skill trees.

Usage:
    python daemon.py start [--config CONFIG] [--foreground]
    python daemon.py stop [--force]
    python daemon.py status [--verbose]
    python daemon.py rollback <generation> [--verify]
    python daemon.py branch <name> [--from-generation GEN]
    python daemon.py diff <gen1> <gen2>
    python daemon.py logs [--tail N] [--follow]
    python daemon.py history [--graph]
    python daemon.py skill-tree [--generation GEN] [--format FORMAT]
"""

import argparse
import sys
import json
import os
import time
import signal
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from prokaryote_agent.daemon.evolution_daemon import EvolutionDaemon
from prokaryote_agent.daemon.generation_manager import GenerationManager
from prokaryote_agent.specialization import SkillTree


class DaemonCLI:
    """Command-line interface for daemon management."""
    
    def __init__(self, config_path: str = "./prokaryote_agent/daemon_config.json"):
        """
        Initialize daemon CLI.
        
        Args:
            config_path: Path to daemon configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.pid_file = Path("./prokaryote_agent/daemon.pid")
        self.status_file = Path("./prokaryote_agent/daemon_status.json")
        self.gen_manager = GenerationManager()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load daemon configuration from JSON file."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            print(f"⚠️  Configuration file not found: {self.config_path}")
            print("Using default configuration...")
            return self._default_config()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)
    
    def _default_config(self) -> Dict[str, Any]:
        """Provide default configuration if file is missing."""
        return {
            "restart_trigger": {"evolution_count_threshold": 10},
            "generation_management": {
                "snapshot_dir": "./prokaryote_agent/generations",
                "lineage_file": "./prokaryote_agent/lineage.json"
            },
            "agent_parameters": {
                "python_executable": "python",
                "agent_entry_script": "./start.py"
            },
            "logging": {
                "log_file": "./prokaryote_agent/log/daemon.log"
            }
        }
    
    def _is_daemon_running(self) -> bool:
        """Check if daemon is currently running."""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists (Windows-compatible)
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                # PID file exists but process doesn't
                self.pid_file.unlink()
                return False
        except Exception:
            return False
    
    def _write_pid(self, pid: int) -> None:
        """Write daemon PID to file."""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))
    
    def _read_pid(self) -> Optional[int]:
        """Read daemon PID from file."""
        if not self.pid_file.exists():
            return None
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except Exception:
            return None
    
    def cmd_start(self, args: argparse.Namespace) -> int:
        """
        Start the daemon.
        
        Args:
            args: Command-line arguments (--foreground for foreground mode)
        
        Returns:
            Exit code (0 for success)
        """
        if self._is_daemon_running():
            pid = self._read_pid()
            print(f"⚠️  Daemon is already running (PID: {pid})")
            return 1
        
        # Check if foreground mode requested
        foreground = getattr(args, 'foreground', False)
        
        if foreground:
            return self._run_foreground()
        else:
            return self._run_background()
    
    def _run_background(self) -> int:
        """Start daemon in background mode."""
        print("🚀 Starting Prokaryote Evolution Daemon in background...")
        
        try:
            # Start as a subprocess
            import sys
            cmd = [sys.executable, __file__, 'start', '--foreground', '--config', self.config_path]
            
            # Windows-specific: use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
            if os.name == 'nt':
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            # Wait a moment for the process to start
            time.sleep(1)
            
            # Check if it started successfully
            if self._is_daemon_running():
                pid = self._read_pid()
                print(f"✅ Daemon started successfully (PID: {pid})")
                print(f"📊 Evolution threshold: {self.config['restart_trigger']['threshold']} evolutions")
                print(f"📁 Generations directory: {self.config['generation_management']['generations_dir']}")
                print(f"\nUse 'daemon.py status' to check current state")
                print("Use 'daemon.py stop' to terminate daemon")
                return 0
            else:
                print("❌ Failed to start daemon - process exited immediately")
                return 1
                
        except Exception as e:
            print(f"❌ Failed to start daemon: {e}")
            return 1
    
    def _run_foreground(self) -> int:
        """Run daemon in foreground mode."""
        print("🚀 Starting Prokaryote Evolution Daemon (foreground mode)...")
        
        try:
            # Create daemon instance
            daemon = EvolutionDaemon(config_path=self.config_path)
            
            # Write PID file
            self._write_pid(os.getpid())
            
            # Initialize status
            self._update_status({
                "running": True,
                "pid": os.getpid(),
                "started_at": datetime.now().isoformat(),
                "evolution_count": 0,
                "current_generation": 1,
                "domain": self.config.get('specialization', {}).get('default_domain', 'unknown')
            })
            
            print(f"✅ Daemon running (PID: {os.getpid()})")
            print(f"📊 Evolution threshold: {self.config['restart_trigger']['threshold']} evolutions")
            print(f"📁 Generations directory: {self.config['generation_management']['generations_dir']}")
            print(f"Press Ctrl+C to stop...\n")
            
            # Setup signal handlers
            def handle_signal(signum, frame):
                print("\n📨 Received shutdown signal...")
                daemon.stop()
                self._cleanup()
                sys.exit(0)
            
            signal.signal(signal.SIGTERM, handle_signal)
            signal.signal(signal.SIGINT, handle_signal)
            
            # Start daemon
            daemon.start()
            
            # Main loop - keep running and update status
            evolution_count = 0
            while daemon.running:
                time.sleep(5)
                
                # Update status periodically
                self._update_status({
                    "running": True,
                    "pid": os.getpid(),
                    "started_at": self._read_status().get('started_at'),
                    "last_check": datetime.now().isoformat(),
                    "evolution_count": evolution_count,
                    "current_generation": daemon.current_generation,
                    "domain": self.config.get('specialization', {}).get('default_domain', 'unknown')
                })
            
            return 0
            
        except KeyboardInterrupt:
            print("\n📨 Shutting down...")
            self._cleanup()
            return 0
        except Exception as e:
            print(f"❌ Daemon error: {e}")
            self._cleanup()
            return 1
    
    def _update_status(self, status: Dict[str, Any]) -> None:
        """Update daemon status file."""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)
    
    def _read_status(self) -> Dict[str, Any]:
        """Read daemon status from file."""
        if not self.status_file.exists():
            return {}
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _cleanup(self) -> None:
        """Clean up PID and status files."""
        if self.pid_file.exists():
            self.pid_file.unlink()
        self._update_status({"running": False, "stopped_at": datetime.now().isoformat()})
    
    def cmd_stop(self, args: argparse.Namespace) -> int:
        """
        Stop the daemon.
        
        Args:
            args: Command-line arguments with --force flag
        
        Returns:
            Exit code (0 for success)
        """
        if not self._is_daemon_running():
            print("⚠️  Daemon is not running")
            return 1
        
        pid = self._read_pid()
        force = args.force
        
        print(f"🛑 Stopping daemon (PID: {pid})...")
        
        try:
            if force:
                print("⚡ Force stopping...")
                os.kill(pid, signal.SIGKILL)
            else:
                print("📨 Sending graceful shutdown signal...")
                os.kill(pid, signal.SIGTERM)
                
                # Wait for process to terminate
                timeout = 10
                for _ in range(timeout):
                    if not self._is_daemon_running():
                        break
                    time.sleep(1)
                else:
                    print("⚠️  Graceful shutdown timeout, forcing...")
                    os.kill(pid, signal.SIGKILL)
            
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("✅ Daemon stopped successfully")
            return 0
        
        except ProcessLookupError:
            print("⚠️  Process not found, cleaning up PID file...")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return 0
        except Exception as e:
            print(f"❌ Failed to stop daemon: {e}")
            return 1
    
    def cmd_status(self, args: argparse.Namespace) -> int:
        """
        Display daemon status.
        
        Args:
            args: Command-line arguments with --verbose flag
        
        Returns:
            Exit code (0 for success)
        """
        is_running = self._is_daemon_running()
        pid = self._read_pid()
        status = self._read_status()
        
        print("=" * 50)
        print("📊 Prokaryote Evolution Daemon Status")
        print("=" * 50)
        
        if is_running:
            print(f"Status: 🟢 Running")
            print(f"PID: {pid}")
            
            # Show detailed status from status file
            if status:
                if status.get('started_at'):
                    print(f"Started: {status['started_at']}")
                if status.get('domain'):
                    print(f"Domain: {status['domain']}")
                if status.get('evolution_count') is not None:
                    print(f"Evolutions: {status['evolution_count']}")
                if status.get('last_check'):
                    print(f"Last Check: {status['last_check']}")
        else:
            print(f"Status: 🔴 Stopped")
            if status.get('stopped_at'):
                print(f"Stopped: {status['stopped_at']}")
        
        # Get current generation info
        try:
            lineage_file = Path(self.config['generation_management']['lineage_file'])
            if lineage_file.exists():
                with open(lineage_file, 'r', encoding='utf-8') as f:
                    lineage = json.load(f)
                
                current_gen = lineage.get('current_generation', 0)
                total_gens = len(lineage.get('generations', []))
                
                print(f"\nCurrent Generation: {current_gen}")
                print(f"Total Generations: {total_gens}")
                
                if args.verbose and lineage.get('generations'):
                    print("\nRecent Generations:")
                    for gen in list(lineage['generations'].values())[-5:]:
                        print(f"  Gen {gen['generation']}: {gen['timestamp']} - {gen['status']}")
        except Exception as e:
            if args.verbose:
                print(f"\n⚠️  Could not load generation info: {e}")
        
        # Get skill tree info if verbose
        if args.verbose:
            try:
                skill_tree_path = self.config['specialization']['skill_tree_path']
                tree = SkillTree(skill_tree_path)
                unlocked = len(tree.get_unlocked_skills())
                total = len(tree)
                
                print(f"\nSkill Tree Progress:")
                print(f"  Unlocked: {unlocked}/{total} ({unlocked/total*100:.1f}%)")
            except Exception:
                pass
        
        print("=" * 50)
        return 0
    
    def cmd_rollback(self, args: argparse.Namespace) -> int:
        """
        Rollback to a previous generation.
        
        Args:
            args: Command-line arguments with generation number
        
        Returns:
            Exit code (0 for success)
        """
        target_gen = args.generation
        
        if self._is_daemon_running():
            print("⚠️  Please stop daemon before rollback")
            print("Run: daemon.py stop")
            return 1
        
        print(f"⏮️  Rolling back to generation {target_gen}...")
        
        try:
            self.gen_manager.restore_from_snapshot(target_gen)
            
            if args.verify:
                print("🔍 Verifying restored files...")
                # Basic verification
                snapshot_dir = Path(self.config['generation_management']['snapshot_dir'])
                gen_dir = snapshot_dir / f"gen_{target_gen:04d}"
                
                if gen_dir.exists():
                    print(f"✅ Generation {target_gen} restored successfully")
                else:
                    print(f"⚠️  Warning: Generation directory not found")
            else:
                print(f"✅ Rollback completed")
            
            print(f"\n💡 Tip: Start daemon to continue from generation {target_gen}")
            return 0
        
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return 1
    
    def cmd_branch(self, args: argparse.Namespace) -> int:
        """
        Create a new evolution branch.
        
        Args:
            args: Command-line arguments with branch name
        
        Returns:
            Exit code (0 for success)
        """
        branch_name = args.name
        from_gen = args.from_generation
        
        print(f"🌿 Creating branch '{branch_name}' from generation {from_gen}...")
        
        try:
            branch_id = self.gen_manager.create_branch(branch_name, from_gen)
            print(f"✅ Branch created successfully (ID: {branch_id})")
            print(f"\n💡 Tip: Switch to branch and restart daemon to explore alternative evolution paths")
            return 0
        
        except Exception as e:
            print(f"❌ Branch creation failed: {e}")
            return 1
    
    def cmd_diff(self, args: argparse.Namespace) -> int:
        """
        Compare two generations.
        
        Args:
            args: Command-line arguments with two generation numbers
        
        Returns:
            Exit code (0 for success)
        """
        gen1, gen2 = args.gen1, args.gen2
        
        print(f"🔍 Comparing generations {gen1} and {gen2}...")
        print("=" * 50)
        
        try:
            diff = self.gen_manager.compare_generations(gen1, gen2)
            
            # Display capability changes
            if 'capabilities' in diff:
                cap_diff = diff['capabilities']
                print(f"\n📦 Capability Changes:")
                print(f"  Added: {len(cap_diff.get('added', []))}")
                print(f"  Removed: {len(cap_diff.get('removed', []))}")
                print(f"  Modified: {len(cap_diff.get('modified', []))}")
                
                if cap_diff.get('added'):
                    print(f"\n  ➕ Added:")
                    for cap in cap_diff['added'][:5]:  # Show first 5
                        print(f"     - {cap}")
                
                if cap_diff.get('removed'):
                    print(f"\n  ➖ Removed:")
                    for cap in cap_diff['removed'][:5]:
                        print(f"     - {cap}")
            
            # Display metric changes
            if 'metrics' in diff:
                print(f"\n📊 Metrics:")
                for key, value in diff['metrics'].items():
                    print(f"  {key}: {value}")
            
            print("=" * 50)
            return 0
        
        except Exception as e:
            print(f"❌ Comparison failed: {e}")
            return 1
    
    def cmd_logs(self, args: argparse.Namespace) -> int:
        """
        Display daemon logs.
        
        Args:
            args: Command-line arguments with --tail and --follow flags
        
        Returns:
            Exit code (0 for success)
        """
        log_file = Path(self.config['logging']['log_file'])
        
        if not log_file.exists():
            print(f"⚠️  Log file not found: {log_file}")
            return 1
        
        try:
            if args.follow:
                print(f"📜 Following log file (Ctrl+C to stop)...")
                print("=" * 50)
                # Simple tail -f implementation
                with open(log_file, 'r', encoding='utf-8') as f:
                    # Go to end
                    f.seek(0, 2)
                    
                    try:
                        while True:
                            line = f.readline()
                            if line:
                                print(line, end='')
                            else:
                                time.sleep(0.1)
                    except KeyboardInterrupt:
                        print("\n\n✅ Stopped following logs")
            else:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                tail_count = args.tail if args.tail > 0 else len(lines)
                
                print(f"📜 Last {min(tail_count, len(lines))} log entries:")
                print("=" * 50)
                
                for line in lines[-tail_count:]:
                    print(line, end='')
            
            return 0
        
        except Exception as e:
            print(f"❌ Failed to read logs: {e}")
            return 1
    
    def cmd_history(self, args: argparse.Namespace) -> int:
        """
        Display generation lineage history.
        
        Args:
            args: Command-line arguments with --graph flag
        
        Returns:
            Exit code (0 for success)
        """
        lineage_file = Path(self.config['generation_management']['lineage_file'])
        
        if not lineage_file.exists():
            print("⚠️  No lineage history found")
            return 1
        
        try:
            with open(lineage_file, 'r', encoding='utf-8') as f:
                lineage = json.load(f)
            
            print("📊 Generation Lineage History")
            print("=" * 50)
            
            generations = lineage.get('generations', {})
            
            if args.graph:
                # ASCII graph visualization
                print("\nEvolution Tree:")
                for gen_id in sorted(generations.keys(), key=int):
                    gen_data = generations[gen_id]
                    indent = "  " * (gen_data.get('depth', 0))
                    branch_marker = "├─" if gen_data.get('parent') else "└─"
                    
                    print(f"{indent}{branch_marker} Gen {gen_data['generation']}: {gen_data['timestamp'][:19]}")
                    if gen_data.get('branch_name'):
                        print(f"{indent}   🌿 Branch: {gen_data['branch_name']}")
            else:
                # Simple list
                for gen_id in sorted(generations.keys(), key=int):
                    gen_data = generations[gen_id]
                    print(f"Gen {gen_data['generation']:3d}: {gen_data['timestamp'][:19]} - {gen_data['status']}")
                    if gen_data.get('branch_name'):
                        print(f"         🌿 {gen_data['branch_name']}")
            
            print("=" * 50)
            print(f"Total Generations: {len(generations)}")
            return 0
        
        except Exception as e:
            print(f"❌ Failed to read history: {e}")
            return 1
    
    def cmd_skill_tree(self, args: argparse.Namespace) -> int:
        """
        Display skill tree status.
        
        Args:
            args: Command-line arguments with --generation and --format flags
        
        Returns:
            Exit code (0 for success)
        """
        try:
            skill_tree_path = self.config['specialization']['skill_tree_path']
            
            # Load from specific generation if requested
            if args.generation is not None:
                snapshot_dir = Path(self.config['generation_management']['snapshot_dir'])
                gen_tree_path = snapshot_dir / f"gen_{args.generation:04d}" / "skill_tree.json"
                if gen_tree_path.exists():
                    skill_tree_path = str(gen_tree_path)
                else:
                    print(f"⚠️  No skill tree found for generation {args.generation}")
                    print(f"Using current skill tree instead...")
            
            tree = SkillTree(skill_tree_path)
            
            print("🌳 Skill Tree Status")
            print("=" * 50)
            
            if args.format == 'summary':
                unlocked = tree.get_unlocked_skills()
                locked = tree.get_locked_skills()
                
                print(f"Total Skills: {len(tree)}")
                print(f"Unlocked: {len(unlocked)} ({len(unlocked)/len(tree)*100:.1f}%)")
                print(f"Locked: {len(locked)} ({len(locked)/len(tree)*100:.1f}%)")
                
                # Tier breakdown
                print(f"\nBy Tier:")
                from prokaryote_agent.specialization import SkillTier
                for tier in SkillTier:
                    tier_skills = tree.get_skills_by_tier(tier)
                    tier_unlocked = [s for s in tier_skills if s.is_unlocked()]
                    print(f"  {tier.name.capitalize()}: {len(tier_unlocked)}/{len(tier_skills)}")
            
            elif args.format == 'detailed':
                print(f"Skills ({len(tree)} total):\n")
                
                for skill in tree.skills.values():
                    status = "🟢" if skill.is_unlocked() else "🔒"
                    level_str = f"L{skill.level}" if skill.is_unlocked() else "---"
                    
                    print(f"{status} {skill.name:30s} {level_str:5s} [{skill.tier.name}]")
                    if skill.is_unlocked() and skill.proficiency > 0:
                        bar_length = 20
                        filled = int(skill.proficiency * bar_length)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        print(f"   Progress: {bar} {skill.proficiency:.0%}")
            
            else:  # tree format
                print("Evolution Path:\n")
                
                # Show unlocked skills in tree structure
                unlocked = tree.get_unlocked_skills()
                for skill in unlocked:
                    depth = len(skill.prerequisites)
                    indent = "  " * depth
                    print(f"{indent}✅ {skill.name} (L{skill.level})")
                
                # Show immediately available skills
                available = tree.get_available_to_unlock()
                if available:
                    print(f"\n🎯 Ready to Unlock ({len(available)}):")
                    for skill in available[:5]:
                        print(f"  → {skill.name} [{skill.tier.name}]")
            
            print("=" * 50)
            return 0
        
        except Exception as e:
            print(f"❌ Failed to load skill tree: {e}")
            return 1


def main():
    """Main entry point for daemon CLI."""
    parser = argparse.ArgumentParser(
        description="Prokaryote Agent Generational Evolution Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        default='./prokaryote_agent/daemon_config.json',
        help='Path to daemon configuration file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the daemon')
    start_parser.add_argument('--foreground', '-f', action='store_true', 
                              help='Run in foreground (default: background)')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop the daemon')
    stop_parser.add_argument('--force', action='store_true', help='Force stop (SIGKILL)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Display daemon status')
    status_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed status')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to previous generation')
    rollback_parser.add_argument('generation', type=int, help='Target generation number')
    rollback_parser.add_argument('--verify', action='store_true', help='Verify after rollback')
    
    # Branch command
    branch_parser = subparsers.add_parser('branch', help='Create evolution branch')
    branch_parser.add_argument('name', help='Branch name')
    branch_parser.add_argument('--from-generation', type=int, default=0, help='Source generation')
    
    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two generations')
    diff_parser.add_argument('gen1', type=int, help='First generation')
    diff_parser.add_argument('gen2', type=int, help='Second generation')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Display daemon logs')
    logs_parser.add_argument('--tail', type=int, default=50, help='Number of lines to show')
    logs_parser.add_argument('--follow', '-f', action='store_true', help='Follow log output')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Display generation history')
    history_parser.add_argument('--graph', '-g', action='store_true', help='Show as tree graph')
    
    # Skill-tree command
    tree_parser = subparsers.add_parser('skill-tree', help='Display skill tree status')
    tree_parser.add_argument('--generation', type=int, help='Show tree for specific generation')
    tree_parser.add_argument('--format', choices=['summary', 'detailed', 'tree'], default='summary')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance
    cli = DaemonCLI(config_path=args.config)
    
    # Route to appropriate command handler
    command_handlers = {
        'start': cli.cmd_start,
        'stop': cli.cmd_stop,
        'status': cli.cmd_status,
        'rollback': cli.cmd_rollback,
        'branch': cli.cmd_branch,
        'diff': cli.cmd_diff,
        'logs': cli.cmd_logs,
        'history': cli.cmd_history,
        'skill-tree': cli.cmd_skill_tree,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
