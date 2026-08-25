import json
import time
from pathlib import Path
import httpx

DATASET_PATH = Path(__file__).resolve().parent / "data" / "retrieval_qa.json"
PAPERS_DIR = Path(__file__).resolve().parent / "data" / "docs" / "papers"

def main():
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(DATASET_PATH, 'r') as f:
        dataset = json.load(f)
        
    arxiv_ids = set()
    for item in dataset:
        for source in item.get("expected_sources", []):
            if source.endswith(".pdf") and "v" in source:
                arxiv_ids.add(source.replace(".pdf", ""))
                
    print(f"Found {len(arxiv_ids)} unique arXiv IDs to download.")
    
    for i, paper_id in enumerate(arxiv_ids):
        filename = f"{paper_id}.pdf"
        dest = PAPERS_DIR / filename
        
        if dest.exists():
            print(f"[{i+1}/{len(arxiv_ids)}] Skipped (already exists): {filename}")
            continue
            
        url = f"https://arxiv.org/pdf/{filename}"
        try:
            response = httpx.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            
            if not response.content.startswith(b"%PDF"):
                print(f"[{i+1}/{len(arxiv_ids)}] Failed (not a PDF): {filename}")
                continue
                
            dest.write_bytes(response.content)
            print(f"[{i+1}/{len(arxiv_ids)}] Downloaded: {filename} ({len(response.content) // 1024} KB)")
        except Exception as e:
            print(f"[{i+1}/{len(arxiv_ids)}] Failed: {filename} - {e}")
            
        time.sleep(1.0)

if __name__ == "__main__":
    main()
