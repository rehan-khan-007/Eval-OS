import os
import json
from openai import AsyncOpenAI
from evaluators.base import BaseEvaluator
from cache import generate_cache_key, get_cached, set_cached

class LLMJudgeEvaluator(BaseEvaluator):
    """Uses an LLM to evaluate faithfulness (grounding) of an answer to the context."""
    def __init__(self, judge_model: str = "openai/gpt-4o-mini"):
        super().__init__(name="faithfulness", version="v1")
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.judge_model = judge_model

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        answer = system_output.get("answer", "")
        context_text = "\n\n".join([e.get("text", "") for e in retrieved_evidence])
        
        if not answer or not context_text:
            return {"score": 0.0, "explanation": "No answer or context provided.", "evidence_breakdown": {}}
            
        prompt = f"""You are evaluating whether an AI-generated answer is genuinely grounded in the provided source context.
Analyze the answer and extract individual claims.
For each claim, determine if it is "supported", "unsupported", or "contradicted" by the context.

Context:
{context_text}

Answer:
{answer}

Respond with ONLY a JSON object, no other text:
{{
  "claims": [
    {{"claim": "...", "status": "supported"}},
    ...
  ],
  "reasoning": "one brief sentence summarizing the evaluation"
}}"""
        
        # 1. Check Cache
        cache_key = generate_cache_key("judge", self.judge_model, context_text, answer)
        cached_verdict = await get_cached(cache_key)
        if cached_verdict:
            return cached_verdict

        # 2. Cache Miss - Call API
        try:
            response = await self.client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            raw_output = response.choices[0].message.content
            cleaned = raw_output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            verdict = json.loads(cleaned)
            
            claims = verdict.get("claims", [])
            if not claims:
                score = 1.0 
            else:
                supported = sum(1 for c in claims if c.get("status") == "supported")
                score = supported / len(claims)
                
            result = {
                "score": score,
                "explanation": verdict.get("reasoning", ""),
                "evidence_breakdown": {"claims": claims}
            }
            
            # 3. Save to Cache
            await set_cached(cache_key, result)
            
            return result
        except Exception as e:
            return {"score": 0.0, "explanation": f"Judge error: {str(e)}", "evidence_breakdown": {}}
