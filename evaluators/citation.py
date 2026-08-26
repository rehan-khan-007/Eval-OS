import os
import json
from openai import AsyncOpenAI
from evaluators.base import BaseEvaluator
from cache import generate_cache_key, get_cached, set_cached

class CitationEvaluator(BaseEvaluator):
    """Evaluates if the specific citations attached to claims actually support those claims."""
    def __init__(self, judge_model: str = "openai/gpt-4o-mini"):
        super().__init__(name="citation_correctness", version="v1")
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.judge_model = judge_model

    async def evaluate(self, input_data, system_output, retrieved_evidence):
        answer = system_output.get("answer", "")
        context_text = "\n\n".join([f"[{c['source']}]: {c['text']}" for c in retrieved_evidence])
        
        if not answer or not context_text:
            return {"score": -1.0, "explanation": "No answer or context provided.", "evidence_breakdown": {}, "status": "indeterminate"}
            
        prompt = f"""You are evaluating the citation correctness of an AI-generated answer.
Analyze the answer and extract every claim made.
For each claim, identify the citation attached to it (e.g., [Source: filename.pdf]).
Then, verify if the text from that *specific cited source* actually supports the claim.

Context Provided (with sources):
{context_text}

Answer:
{answer}

Respond with ONLY a JSON object, no other text:
{{
  "claims": [
    {{"claim": "...", "citation": "...", "is_supported": true}},
    ...
  ],
  "reasoning": "one brief sentence summarizing citation quality"
}}"""
        
        # P1 Fix: Include evaluator name and version in cache key
        cache_key = generate_cache_key(self.name, self.version, self.judge_model, context_text, answer)
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
            
            claims = verdict.get("claims", [])
            if not claims:
                result = {
                    "score": -1.0,
                    "explanation": "Judge extracted no claims or citations.",
                    "evidence_breakdown": {"claims": []},
                    "status": "indeterminate"
                }
                await set_cached(cache_key, result)
                return result
                
            supported = sum(1 for c in claims if c.get("is_supported") is True)
            score = supported / len(claims)
            
            result = {
                "score": score,
                "explanation": verdict.get("reasoning", ""),
                "evidence_breakdown": {"claims": claims},
                "status": "success"
            }
            
            await set_cached(cache_key, result)
            return result
            
        except Exception as e:
            return {
                "score": -1.0,
                "explanation": f"Citation Judge API error: {str(e)}",
                "evidence_breakdown": {},
                "status": "evaluator_error"
            }
