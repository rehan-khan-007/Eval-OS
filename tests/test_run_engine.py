import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import pytest
from unittest.mock import AsyncMock
from run_engine import RunEngine

@pytest.mark.asyncio
async def test_exception_isolation():
    """Test that an adapter exception is caught and doesn't crash the gather loop."""
    # Mock adapter to throw an exception when generate is called
    mock_adapter = AsyncMock()
    mock_adapter.generate.side_effect = Exception("API Timeout")
    
    engine = RunEngine("cfg-1", "test", mock_adapter, [], concurrency=1)
    
    # Call the internal processor directly
    ex = {"id": "ex-1", "question": "test", "metadata": {}}
    result_ex, sys_output, metric_results = await engine._process_single_example(ex, "run-1")
    
    # Assert it returned an error dict, not raised an exception
    assert result_ex["id"] == "ex-1"
    assert "API Timeout" in sys_output["error"]
    assert sys_output["cost"] == 0.0
    assert metric_results == []
