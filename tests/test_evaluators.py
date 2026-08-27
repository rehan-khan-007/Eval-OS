import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from evaluators.llm_judge import LLMJudgeEvaluator

async def run_evaluator(mock_response_text: str):
    """Helper to run the judge with a mocked OpenAI response and mocked cache."""
    evaluator = LLMJudgeEvaluator(judge_model="test-model")
    
    # Mock the OpenAI client's create method
    mock_message = MagicMock()
    mock_message.content = mock_response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    evaluator.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    input_data = {"question": "test", "metadata": {}}
    system_output = {"answer": "test answer"}
    retrieved_evidence = [{"source": "doc.pdf", "text": "test context"}]
    
    # Patch the cache functions so they don't hit real Redis and contaminate tests
    with patch('evaluators.llm_judge.get_cached', new_callable=AsyncMock, return_value=None):
        with patch('evaluators.llm_judge.set_cached', new_callable=AsyncMock):
            return await evaluator.evaluate(input_data, system_output, retrieved_evidence)

def test_judge_valid_json():
    """Test that the judge correctly parses valid JSON and calculates score."""
    valid_json = json.dumps({
        "claims": [
            {"claim": "A", "status": "supported"},
            {"claim": "B", "status": "unsupported"}
        ],
        "reasoning": "Mixed support"
    })
    result = asyncio.run(run_evaluator(valid_json))
    assert result["status"] == "success"
    assert result["score"] == 0.5  # 1 supported out of 2 total
    assert result["explanation"] == "Mixed support"

def test_judge_malformed_json():
    """Test that the judge handles malformed JSON gracefully."""
    malformed_json = "This is not JSON at all."
    result = asyncio.run(run_evaluator(malformed_json))
    assert result["status"] == "evaluator_error"
    assert result["score"] == -1.0
    assert "Judge API error" in result["explanation"]

def test_judge_empty_claims():
    """Test that the judge handles empty claims list as indeterminate."""
    empty_claims_json = json.dumps({"claims": [], "reasoning": "No claims found"})
    result = asyncio.run(run_evaluator(empty_claims_json))
    assert result["status"] == "indeterminate"
    assert result["score"] == -1.0
    assert result["explanation"] == "Judge extracted no claims."

def test_judge_markdown_wrapped_json():
    """Test that the judge can strip markdown code fences."""
    markdown_json = f"```json\n{json.dumps({'claims': [{'claim': 'A', 'status': 'supported'}], 'reasoning': 'Good'})}\n```"
    result = asyncio.run(run_evaluator(markdown_json))
    assert result["status"] == "success"
    assert result["score"] == 1.0
