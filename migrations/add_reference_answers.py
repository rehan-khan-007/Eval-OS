import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import AsyncSessionLocal
from models import EvaluationExample
from sqlalchemy import select, or_

async def add_refs():
    async with AsyncSessionLocal() as db:
        # Use partial matching to avoid newline/space issues
        stmt = select(EvaluationExample).where(
            or_(
                EvaluationExample.question.ilike("%What is GRAPE and what problem does it solve%"),
                EvaluationExample.question.ilike("%How does gradient ascent pulse engineering work for spin ensembles%"),
                EvaluationExample.question.ilike("%What is second order gradient ascent pulse engineering%")
            )
        )
        result = await db.execute(stmt)
        examples = result.scalars().all()

        updated = 0
        for ex in examples:
            if "grape" in ex.question.lower() and "problem" in ex.question.lower():
                ref = "GRAPE (Gradient Ascent Pulse Engineering) is an algorithm used for optimal control of quantum systems. It solves the problem of finding optimal control pulses by using gradient ascent to maximize the fidelity of the quantum operation."
            elif "spin ensembles" in ex.question.lower():
                ref = "It works by iteratively adjusting the control pulses based on the gradient of the objective function (e.g., fidelity) to improve the performance of the spin ensemble."
            elif "second order" in ex.question.lower():
                ref = "Second order gradient ascent pulse engineering incorporates second-order information (like the Hessian) or quasi-Newton methods (like BFGS) to accelerate convergence and improve the optimization landscape traversal compared to first-order methods."
            else:
                continue
                
            current_meta = ex.metadata_json or {}
            current_meta["reference_answer"] = ref
            ex.metadata_json = current_meta
            updated += 1
        
        await db.commit()
        print(f"Updated {updated} examples with reference answers.")

if __name__ == "__main__":
    asyncio.run(add_refs())
