import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
    assert sys_output["error"] == "Exception"
    assert "sk-or-v1" not in sys_output["error"]
    assert sys_output["cost"] == 0.0
    assert metric_results == []

@pytest.mark.asyncio
async def test_execute_run_with_errors():
    """Test that execute_run sets run status to complete_with_errors when an example fails."""
    # 1. Mock Adapter: 2 successes, 1 failure
    mock_adapter = AsyncMock()
    mock_adapter.generate.side_effect = [
        {"answer": "a1", "cost": 0.01, "latency_ms": 10, "tokens_in": 0, "tokens_out": 0, "retrieved_evidence": []},
        Exception("API Down"),
        {"answer": "a3", "cost": 0.01, "latency_ms": 10, "tokens_in": 0, "tokens_out": 0, "retrieved_evidence": []}
    ]
    
    # 2. Mock DB Session
    mock_db = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None
    
    # Mock the run object that db.get(EvaluationRun, run_id) will return
    mock_run = MagicMock()
    mock_db.get.return_value = mock_run
    
    with patch('run_engine.AsyncSessionLocal', return_value=mock_session_cm):
        engine = RunEngine("cfg-1", "test", mock_adapter, [], concurrency=1)
        examples = [
            {"id": "ex-1", "question": "q1"}, 
            {"id": "ex-2", "question": "q2"}, 
            {"id": "ex-3", "question": "q3"}
        ]
        
        run_id = await engine.execute_run("dv-1", examples)
        
        # Assert db.add was called for 3 executions
        assert mock_db.add.call_count >= 3
        
        # Assert the run status was set to complete_with_errors
        assert mock_run.status == "complete_with_errors"
        assert mock_run.total_cost == 0.02
