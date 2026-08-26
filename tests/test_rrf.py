import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retrieval import fuse_rrf

def test_rrf_fusion():
    """Test that RRF correctly fuses dense and FTS results using chunk_id."""
    dense = [
        {"chunk_id": "1", "source": "a.pdf", "text": "alpha"},
        {"chunk_id": "2", "source": "b.pdf", "text": "beta"},
        {"chunk_id": "3", "source": "c.pdf", "text": "gamma"}
    ]
    fts = [
        {"chunk_id": "3", "source": "c.pdf", "text": "gamma"}, # Overlaps with dense
        {"chunk_id": "4", "source": "d.pdf", "text": "delta"}
    ]
    
    # Fuse top 3
    fused = fuse_rrf(dense, fts, top_k=3)
    
    # Chunk 3 should be first because it appeared in both lists (higher RRF score)
    assert fused[0]["chunk_id"] == "3"
    assert len(fused) == 3

def test_rrf_unique_chunks():
    """Test that RRF handles completely disjoint lists."""
    dense = [{"chunk_id": "1", "source": "a", "text": "a"}]
    fts = [{"chunk_id": "2", "source": "b", "text": "b"}]
    
    fused = fuse_rrf(dense, fts, top_k=2)
    assert len(fused) == 2
