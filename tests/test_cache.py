import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cache import generate_cache_key

def test_cache_key_determinism():
    """Same inputs should produce the same cache key."""
    key1 = generate_cache_key("model-x", "prompt-y", "context-z")
    key2 = generate_cache_key("model-x", "prompt-y", "context-z")
    assert key1 == key2

def test_cache_key_uniqueness():
    """Different inputs should produce different cache keys."""
    key1 = generate_cache_key("model-x", "prompt-y", "context-z")
    key2 = generate_cache_key("model-a", "prompt-y", "context-z")
    assert key1 != key2

def test_cache_key_prefix():
    """Keys should be prefixed with 'evalos:'."""
    key = generate_cache_key("test")
    assert key.startswith("evalos:")

def test_cache_key_versioning():
    """Changing the evaluator version should change the cache key."""
    key_v1 = generate_cache_key("faithfulness", "v1", "gpt-4o-mini", "ctx", "ans")
    key_v2 = generate_cache_key("faithfulness", "v2", "gpt-4o-mini", "ctx", "ans")
    assert key_v1 != key_v2
