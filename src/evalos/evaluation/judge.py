from typing import Any


class LLMJudge:
    """LLM-as-a-Judge for evaluating response quality."""

    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.model = model

    async def evaluate(self, question: str, answer: str, reference: str | None = None) -> dict:
        """Score a generated answer using an LLM judge."""
        from app.llm.client import chat_completion, extract_choice

        messages = [
            {"role": "system", "content": self._judge_prompt()},
            {"role": "user", "content": self._format_input(question, answer, reference)},
        ]
        response = await chat_completion(messages=messages, model=self.model)
        choice = extract_choice(response)
        return self._parse_score(choice["content"])

    def _judge_prompt(self) -> str:
        return """You are an expert evaluator. Score the following answer on:
1. Correctness (0-1): Is the answer factually correct?
2. Completeness (0-1): Does it fully address the question?
3. Groundedness (0-1): Is it supported by the reference?

Return a JSON object with scores and a brief reason."""

    def _format_input(self, question: str, answer: str, reference: str | None) -> str:
        text = f"Question: {question}\n\nAnswer: {answer}\n\n"
        if reference:
            text += f"Reference: {reference}\n\n"
        return text

    def _parse_score(self, content: str) -> dict:
        """Parse judge response into structured scores."""
        import json, re
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            scores = {"correctness": 0, "completeness": 0, "groundedness": 0}
            for key in scores:
                match = re.search(rf'"{key}":\s*([\d.]+)', content)
                if match:
                    scores[key] = float(match.group(1))
            return scores