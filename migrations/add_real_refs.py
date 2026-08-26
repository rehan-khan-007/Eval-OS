import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine
from sqlalchemy import text

async def add_real_refs():
    async with engine.begin() as conn:
        # 1. GRAPE question
        await conn.execute(text("""
            UPDATE evaluation_examples 
            SET metadata_json = jsonb_set(
                COALESCE(metadata_json, '{}'::jsonb), 
                '{reference_answer}', 
                '"GRAPE (Gradient Ascent Pulse Engineering) is an algorithm used for optimal control of quantum systems. It solves the problem of finding optimal control pulses by using gradient ascent to maximize the fidelity of the quantum operation."', 
                true
            )
            WHERE question ILIKE '%What is GRAPE and what problem does it solve%';
        """))
        
        # 2. Spin ensembles question
        await conn.execute(text("""
            UPDATE evaluation_examples 
            SET metadata_json = jsonb_set(
                COALESCE(metadata_json, '{}'::jsonb), 
                '{reference_answer}', 
                '"It works by iteratively adjusting the control pulses based on the gradient of the objective function (e.g., fidelity) to improve the performance of the spin ensemble."', 
                true
            )
            WHERE question ILIKE '%How does gradient ascent pulse engineering work for spin ensembles%';
        """))
        
        # 3. Second order GRAPE question
        await conn.execute(text("""
            UPDATE evaluation_examples 
            SET metadata_json = jsonb_set(
                COALESCE(metadata_json, '{}'::jsonb), 
                '{reference_answer}', 
                '"Second order gradient ascent pulse engineering incorporates second-order information (like the Hessian) or quasi-Newton methods (like BFGS) to accelerate convergence and improve the optimization landscape traversal compared to first-order methods."', 
                true
            )
            WHERE question ILIKE '%What is second order gradient ascent pulse engineering%';
        """))
        
        print("Inserted real reference answers via raw SQL.")

if __name__ == "__main__":
    asyncio.run(add_real_refs())
