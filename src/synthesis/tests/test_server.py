"""
Basic tests for Synthesis MCP Server
"""
import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_imports():
    """Test that core modules can be imported without errors."""
    try:
        from shared.mcp_base import MCPBaseServer
        from shared.email_utils import SynthesisEmailMonitor
        from shared.storage_utils import StudyProgressDB
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import core modules: {e}")

def test_server_initialization():
    """Test that the server class can be imported."""
    try:
        from synthesis.server import SynthesisTrackerServer
        assert SynthesisTrackerServer is not None
    except ImportError as e:
        pytest.fail(f"Failed to import SynthesisTrackerServer: {e}")

def test_config_module():
    """Test that config module can be imported."""
    try:
        from synthesis.config import config
        assert hasattr(config, 'email_server')
        assert hasattr(config, 'database_path')
    except ImportError as e:
        pytest.fail(f"Failed to import config: {e}")

@pytest.mark.asyncio
async def test_server_tools():
    """Test that server tools can be retrieved."""
    try:
        from synthesis.server import SynthesisTrackerServer
        
        # Mock environment variables to avoid config errors
        os.environ.setdefault('EMAIL_SERVER', 'test.example.com')
        os.environ.setdefault('EMAIL_USERNAME', 'test@example.com')
        os.environ.setdefault('EMAIL_PASSWORD', 'test-password')
        os.environ.setdefault('SYNTHESIS_EMAIL', 'test@synthesis.com')
        os.environ.setdefault('DATABASE_PATH', ':memory:')
        
        server = SynthesisTrackerServer()
        tools = await server.get_tools()
        
        assert len(tools) > 0
        tool_names = [tool.name for tool in tools]
        
        # Check that expected tools exist
        expected_tools = [
            'check_synthesis_login',
            'get_study_progress', 
            'get_weekly_summary',
            'send_study_reminder',
            'get_current_streak',
            'force_update_progress',
            'get_synthesis_newsletter',
            'get_subscription_status'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
            
    except Exception as e:
        pytest.fail(f"Failed to test server tools: {e}")