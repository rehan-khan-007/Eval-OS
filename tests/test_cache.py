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
