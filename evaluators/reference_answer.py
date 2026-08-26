import os
import json
from openai import AsyncOpenAI
from evaluators.base import BaseEvaluator
from cache import generate_cache_key, get_cached, set_cached

class ReferenceAnswerEvaluator(BaseEvaluator):
    """Evaluates if the generated answer is semantically correct compared to a ground truth reference answer."""
    def __init__(self, judge_model: str = "openai/gpt-4o-mini"):
        super().__init__(name="reference_correctness", version="v1")
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.judge_model = judge_model

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        question = input_data.get("question", "")
        answer = system_output.get("answer", "")
        
        # Fetch reference answer from metadata or the example's reference_answer field
        # Our CLI currently puts expected_sources in metadata. We will need to update the dataset/CLI to provide reference answers.
        # For now, we check if it exists in the metadata_json.
        reference_answer = input_data.get("metadata", {}).get("reference_answer")
        
        if not reference_answer:
            return {"score": -1.0, "explanation": "No reference answer provided for this example.", "evidence_breakdown": {}, "status": "indeterminate"}
            
        if not answer:
            return {"score": -1.0, "explanation": "No generated answer provided.", "evidence_breakdown": {}, "status": "indeterminate"}
            
        prompt = f"""You are evaluating whether an AI-generated answer is semantically correct compared to a ground truth reference answer.
Ignore the retrieved context. Judge the generated answer solely on whether it matches the meaning of the reference answer.

Question:
{question}

Reference Answer (Ground Truth):
{reference_answer}

Generated Answer:
{answer}

Respond with ONLY a JSON object, no other text:
{{
  "is_correct": true,
  "reasoning": "one brief sentence explaining your evaluation"
}}"""
        
        cache_key = generate_cache_key(self.name, self.version, self.judge_model, question, reference_answer, answer)
        cached_verdict = await get_cached(cache_key)
        if cached_verdict:
            return cached_verdict

        try:
            response = await self.client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            raw_output = response.choices[0].message.content
            cleaned = raw_output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            verdict = json.loads(cleaned)
            
            is_correct = bool(verdict.get("is_correct", False))
            score = 1.0 if is_correct else 0.0
            
            result = {
                "score": score,
                "explanation": verdict.get("reasoning", ""),
                "evidence_breakdown": {"is_correct": is_correct},
                "status": "success"
            }
            
            await set_cached(cache_key, result)
            return result
            
        except Exception as e:
            return {
                "score": -1.0,
                "explanation": f"Reference Judge API error: {str(e)}",
                "evidence_breakdown": {},
                "status": "evaluator_error"
            }
