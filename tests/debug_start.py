"""Quick test to debug start command issue"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import daemon as daemon_module
from daemon import DaemonCLI

def test_start():
    tmpdir = tempfile.mkdtemp()
    print(f"Using tmpdir: {tmpdir}")
    
    cli = DaemonCLI(config_path="nonexistent.json")
    cli.pid_file = Path(tmpdir) / "test_daemon.pid"
    print(f"Created CLI, PID file: {cli.pid_file}")
    
    # Mock EvolutionDaemon
    with patch('daemon.EvolutionDaemon') as mock_daemon_class:
        mock_daemon = MagicMock()
        mock_daemon.start_agent.return_value = True
        mock_daemon.agent_pid = 12345
        mock_daemon_class.return_value = mock_daemon
        print("Mocked EvolutionDaemon")
        
        # Mock _is_daemon_running
        with patch.object(cli, '_is_daemon_running', return_value=False):
            print("Mocked _is_daemon_running")
            
            args = argparse.Namespace()
            print("Calling cmd_start...")
            
            with patch('sys.stdout', new=StringIO()) as fake_out:
                result = cli.cmd_start(args)
                output = fake_out.getvalue()
            
            print(f"Result: {result}")
            print(f"Output: {output}")
            
            assert result == 0, f"Expected 0, got {result}"
            assert "started successfully" in output.lower(), f"Expected success message, got: {output}"
            assert cli.pid_file.exists(), "PID file should exist"
            
            print("✅ Test passed!")
    
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == '__main__':
    try:
        test_start()
        print("\n✅ All checks passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
