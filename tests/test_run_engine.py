import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import pytest
from unittest.mock import AsyncMock
from run_engine import RunEngine

@pytest.mark.asyncio
async def test_exception_isolation():
    """Test that an adapter exception is caught, sanitized, and doesn't crash the gather loop."""
    mock_adapter = AsyncMock()
    mock_adapter.generate.side_effect = Exception("API Timeout: sk-or-v1-...")
    
    engine = RunEngine("cfg-1", "test", mock_adapter, [], concurrency=1)
    
    ex = {"id": "ex-1", "question": "test", "metadata": {}}
    result_ex, sys_output, metric_results = await engine._process_single_example(ex, "run-1")
    
    assert result_ex["id"] == "ex-1"
    # Assert the error message is sanitized to just the type
    assert sys_output["error"] == "Exception"
    assert "sk-or-v1" not in sys_output["error"]
    assert sys_output["cost"] == 0.0
    assert metric_results == []
