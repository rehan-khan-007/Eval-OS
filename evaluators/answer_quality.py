import os
import json
from openai import AsyncOpenAI
from evaluators.base import BaseEvaluator
from cache import generate_cache_key, get_cached, set_cached

class AnswerQualityEvaluator(BaseEvaluator):
    """Evaluates if the answer is correct and complete relative to the question."""
    def __init__(self, judge_model: str = "openai/gpt-4o-mini"):
        super().__init__(name="answer_quality", version="v1")
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.judge_model = judge_model

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        question = input_data.get("question", "")
        answer = system_output.get("answer", "")
        context_text = "\n\n".join([e.get("text", "") for e in retrieved_evidence])
        
        if not answer or not context_text:
            return {"score": -1.0, "explanation": "No answer or context provided.", "evidence_breakdown": {}, "status": "indeterminate"}
            
        prompt = f"""You are evaluating the quality of an AI-generated answer.
Analyze the answer based on the provided context and the original question.

Question:
{question}

Context:
{context_text}

Answer:
{answer}

Evaluate the answer on two dimensions:
1. "correctness": Is the answer factually correct based on the context? (1.0 = yes, 0.0 = no)
2. "completeness": Does the answer fully address all parts of the question? (1.0 = yes, 0.5 = partially, 0.0 = no)

Respond with ONLY a JSON object, no other text:
{{
  "correctness": 1.0,
  "completeness": 1.0,
  "reasoning": "one brief sentence explaining your evaluation"
}}"""
        
        # P1 Fix: Include evaluator name and version in cache key
        cache_key = generate_cache_key(self.name, self.version, self.judge_model, question, context_text, answer)
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
            
            correctness = float(verdict.get("correctness", 0.0))
            completeness = float(verdict.get("completeness", 0.0))
            
            score = (correctness + completeness) / 2.0
            
            result = {
                "score": score,
                "explanation": verdict.get("reasoning", ""),
                "evidence_breakdown": {
                    "correctness": correctness,
                    "completeness": completeness
                },
                "status": "success"
            }
            
            await set_cached(cache_key, result)
            return result
            
        except Exception as e:
            return {
                "score": -1.0,
                "explanation": f"Quality Judge API error: {str(e)}",
                "evidence_breakdown": {},
                "status": "evaluator_error"
            }
