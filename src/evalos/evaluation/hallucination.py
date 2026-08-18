import re
from typing import Any


def extract_claims(text: str) -> list[str]:
    """Split LLM output into individual factual claims."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


class HallucinationDetector:
    """Claim-level hallucination detection with failure attribution."""

    def detect(self, answer: str, evidence: list[str]) -> dict:
        claims = extract_claims(answer)
        supported = []
        unsupported = []
        
        for claim in claims:
            found = any(self._claim_in_evidence(claim, ev) for ev in evidence)
            if found:
                supported.append(claim)
            else:
                unsupported.append(claim)

        total = len(claims)
        attribution = {"retrieval": 0, "generation": 0}

        if unsupported:
            # If evidence exists but claim isn't in it → generation failure
            # If no evidence at all → retrieval failure
            if evidence:
                attribution["generation"] = len(unsupported)
            else:
                attribution["retrieval"] = len(unsupported)

        return {
            "total_claims": total,
            "supported": len(supported),
            "unsupported": len(unsupported),
            "groundedness": round(len(supported) / total, 3) if total > 0 else 1.0,
            "attribution": attribution,
            "details": {
                "supported_claims": supported[:5],
                "unsupported_claims": unsupported[:5],
            },
        }

    def _claim_in_evidence(self, claim: str, evidence: str) -> bool:
        """Check if a claim is substantiated by a piece of evidence."""
        claim_keywords = set(claim.lower().split())
        evidence_lower = evidence.lower()
        matches = sum(1 for kw in claim_keywords if kw in evidence_lower)
        return matches >= len(claim_keywords) * 0.3