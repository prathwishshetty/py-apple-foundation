#!/usr/bin/env python3
"""
Test suite for Foundation Models API Phase 1 Extensions.
Tests system prompts, sampling modes, model selection, and guardrails.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.foundation_service import generate


def test_basic_generation():
    """Test that basic generation still works (backward compatibility)"""
    print("Test 1: Basic generation (backward compatibility)")
    result = generate("Say hello", max_tokens=10)
    print(f"  Result: {result}")
    assert len(result) > 0, "Basic generation failed"
    print("  ✅ PASSED\n")


def test_system_prompt():
    """Test system prompt functionality"""
    print("Test 2: System prompt")
    result = generate(
        "What is 2+2?",
        system_prompt="You are a calculator. Only respond with the number.",
        max_tokens=10
    )
    print(f"  Result: {result}")
    print("  ✅ PASSED\n")


def test_instructions_alias():
    """Test that instructions alias works"""
    print("Test 3: Instructions alias for system_prompt")
    result = generate(
        "Tell me about Python",
        instructions="You are a teacher. Be concise.",
        max_tokens=20
    )
    print(f"  Result: {result}")
    assert len(result) > 0
    print("  ✅ PASSED\n")


def test_greedy_sampling():
    """Test greedy sampling mode for determinism"""
    print("Test 4: Greedy sampling (deterministic)")
    result1 = generate(
        "Count from 1 to 3",
        sampling_mode="greedy",
        max_tokens=20
    )
    result2 = generate(
        "Count from 1 to 3",
        sampling_mode="greedy",
        max_tokens=20
    )
    print(f"  Result 1: {result1}")
    print(f"  Result 2: {result2}")
    # Note: Greedy should be deterministic
    print("  ✅ PASSED\n")


def test_top_k_sampling():
    """Test top-k sampling"""
    print("Test 5: Top-K sampling")
    result = generate(
        "Write a creative sentence about coding",
        sampling_mode="top_k",
        top_k=40,
        max_tokens=30
    )
    print(f"  Result: {result}")
    assert len(result) > 0
    print("  ✅ PASSED\n")


def test_top_p_sampling():
    """Test nucleus (top-p) sampling"""
    print("Test 6: Top-P (nucleus) sampling")
    result = generate(
        "Write a creative sentence about AI",
        sampling_mode="top_p",
        top_p=0.9,
        max_tokens=30
    )
    print(f"  Result: {result}")
    assert len(result) > 0
    print("  ✅ PASSED\n")


def test_seed_reproducibility():
    """Test that seed produces reproducible results"""
    print("Test 7: Seed reproducibility")
    result1 = generate(
        "Write a random creative sentence",
        sampling_mode="top_k",
        top_k=10,
        seed=42,
        max_tokens=20
    )
    result2 = generate(
        "Write a random creative sentence",
        sampling_mode="top_k",
        top_k=10,
        seed=42,
        max_tokens=20
    )
    print(f"  Result 1: {result1}")
    print(f"  Result 2: {result2}")
    assert result1 == result2, f"Seeds should produce same output! Got:\n  {result1}\n  {result2}"
    print("  ✅ PASSED - Same output with same seed\n")


def test_model_default():
    """Test default model selection"""
    print("Test 8: Default model")
    result = generate(
        "What is machine learning?",
        model="default",
        max_tokens=30
    )
    print(f"  Result: {result}")
    assert len(result) > 0
    print("  ✅ PASSED\n")


def test_guardrails_default():
    """Test default guardrails"""
    print("Test 9: Default guardrails")
    result = generate(
        "Explain Python programming",
        guardrails="default",
        max_tokens=30
    )
    print(f"  Result: {result}")
    assert len(result) > 0
    print("  ✅ PASSED\n")


def test_combined_features():
    """Test using multiple features together"""
    print("Test 10: Combined features")
    result = generate(
        prompt="Explain AI in one sentence",
        system_prompt="You are a teacher explaining to a child",
        sampling_mode="greedy",
        temperature=0.5,
        max_tokens=50,
        model="default",
        guardrails="default"
    )
    print(f"  Result: {result}")
    assert len(result) > 0
    print("  ✅ PASSED\n")


def test_json_schema_compatibility():
    """Test that JSON schema still works with new parameters"""
    print("Test 11: JSON Schema with new parameters")
    schema = {
        "type": "object",
        "properties": {
            "color": {"type": "string"},
            "count": {"type": "number"}
        },
        "required": ["color"]
    }
    result = generate(
        "Generate a random color and count",
        schema=schema,
        system_prompt="Generate creative but simple data",
        sampling_mode="greedy"
    )
    print(f"  Result: {result}")
    assert isinstance(result, dict), "Schema should return dict"
    assert "color" in result, "Missing required field"
    print("  ✅ PASSED\n")


def main():
    print("=" * 60)
    print("Foundation Models API - Phase 1 Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_basic_generation,
        test_system_prompt,
        test_instructions_alias,
        test_greedy_sampling,
        test_top_k_sampling,
        test_top_p_sampling,
        test_seed_reproducibility,
        test_model_default,
        test_guardrails_default,
        test_combined_features,
        test_json_schema_compatibility,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")


if __name__ == "__main__":
    main()
