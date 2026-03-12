# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Benchmark tests for DriftLock - 50+ turn synthetic conversations.

This benchmark validates:
- Drift naturally increases over long conversations
- DriftLock detects the increase
- Correction mechanism (re-inject identity context) reduces drift
- Embedding computation performance
"""

import time
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

from shaprai.core.driftlock import (
    DriftLock,
    DriftLockConfig,
    create_driftlock_from_template,
)


def test_50_turn_conversation_with_real_embeddings():
    """Test drift detection across 50+ turn synthetic conversation.
    
    This test validates that:
    1. Drift naturally increases over long conversations
    2. DriftLock detects the increase
    3. Correction mechanism reduces drift
    """
    print("\n" + "="*70)
    print("BENCHMARK: 50+ Turn Synthetic Conversation with Real Embeddings")
    print("="*70)
    
    # Load anchors from template
    template_path = Path(__file__).parent.parent / "templates" / "bounty_hunter.yaml"
    
    driftlock = create_driftlock_from_template(
        str(template_path),
        window_size=10,
        drift_threshold=0.4,
    )
    
    # Identity-aligned responses (should have low drift)
    identity_responses = [
        "I am a principled agent, not a people-pleaser. I focus on quality work.",
        "Quality over quantity. One good PR beats ten stubs.",
        "I read the issue before claiming it and delivering value.",
        "I prefer to do thorough work rather than rush through tasks.",
        "Let me review the requirements carefully first.",
        "I follow best practices and write clean, maintainable code.",
        "My goal is to deliver high-quality results, not just complete tasks.",
        "I take pride in my work and ensure it meets high standards.",
        "I believe in doing things right the first time.",
        "I am committed to excellence in everything I do.",
    ]
    
    # Drifted responses (should have higher drift)
    drifted_responses = [
        "Whatever, I'll just do the minimum to get by.",
        "It doesn't really matter how good it is, as long as it works.",
        "I didn't read the full requirements, but I think this is fine.",
        "Let's just rush through this and get it done quickly.",
        "Who cares about best practices? Just make it work.",
        "The code doesn't need to be clean, nobody will read it anyway.",
        "I'll just hack something together and hope it passes.",
        "Good enough is good enough. No need to over-engineer.",
        "I'm tired, let's just finish this quickly.",
        "Doesn't matter if it's broken, someone else can fix it.",
    ]
    
    print(f"\nTemplate: {template_path}")
    print(f"Anchor phrases: {len(driftlock.config.anchor_phrases)}")
    print(f"Window size: {driftlock.config.window_size}")
    print(f"Drift threshold: {driftlock.config.drift_threshold}")
    print("\nRunning 60-turn conversation simulation...\n")
    
    start_time = time.time()
    drift_scores = []
    alert_count = 0
    
    # Phase 1: Identity-aligned conversation (turns 1-20)
    print("Phase 1: Identity-aligned responses (turns 1-20)")
    print("-" * 70)
    for i in range(20):
        response = identity_responses[i % len(identity_responses)]
        driftlock.add_response(response)
        result = driftlock.measure_drift()
        drift_scores.append(result.drift_score)
        
        if result.exceeded_threshold:
            alert_count += 1
        
        if (i + 1) % 5 == 0:
            print(f"  Turn {i+1:2d}: drift={result.drift_score:.4f}, "
                  f"window={result.window_size}, alerts={alert_count}")
    
    # Phase 2: Gradual drift (turns 21-40)
    print("\nPhase 2: Gradual drift introduction (turns 21-40)")
    print("-" * 70)
    for i in range(20):
        # Mix identity and drifted responses
        if i < 10:
            response = identity_responses[(i + 5) % len(identity_responses)]
        else:
            response = drifted_responses[i % len(drifted_responses)]
        
        driftlock.add_response(response)
        result = driftlock.measure_drift()
        drift_scores.append(result.drift_score)
        
        if result.exceeded_threshold:
            alert_count += 1
        
        if (i + 21) % 5 == 0:
            print(f"  Turn {i+21:2d}: drift={result.drift_score:.4f}, "
                  f"window={result.window_size}, alerts={alert_count}")
    
    # Phase 3: Full drift (turns 41-60)
    print("\nPhase 3: Fully drifted responses (turns 41-60)")
    print("-" * 70)
    for i in range(20):
        response = drifted_responses[i % len(drifted_responses)]
        driftlock.add_response(response)
        result = driftlock.measure_drift()
        drift_scores.append(result.drift_score)
        
        if result.exceeded_threshold:
            alert_count += 1
        
        if (i + 41) % 5 == 0:
            print(f"  Turn {i+41:2d}: drift={result.drift_score:.4f}, "
                  f"window={result.window_size}, alerts={alert_count}")
    
    elapsed_time = time.time() - start_time
    
    # Analysis
    print("\n" + "="*70)
    print("BENCHMARK RESULTS")
    print("="*70)
    print(f"Total turns: {len(drift_scores)}")
    print(f"Total alerts triggered: {alert_count}")
    print(f"Total time: {elapsed_time:.2f}s")
    print(f"Average time per turn: {elapsed_time/len(drift_scores)*1000:.2f}ms")
    
    # Drift analysis
    phase1_avg = np.mean(drift_scores[:20])
    phase2_avg = np.mean(drift_scores[20:40])
    phase3_avg = np.mean(drift_scores[40:60])
    
    print(f"\nDrift Analysis:")
    print(f"  Phase 1 (identity-aligned) avg: {phase1_avg:.4f}")
    print(f"  Phase 2 (mixed) avg: {phase2_avg:.4f}")
    print(f"  Phase 3 (drifted) avg: {phase3_avg:.4f}")
    print(f"  Drift increase: {phase3_avg - phase1_avg:.4f} ({(phase3_avg/phase1_avg - 1)*100:.1f}%)")
    
    # Verify drift increases
    assert phase3_avg > phase1_avg, "Drift should increase over conversation"
    assert len(drift_scores) >= 50, "Should have at least 50 turns"
    
    # Test correction mechanism
    print("\n" + "="*70)
    print("CORRECTION MECHANISM TEST")
    print("="*70)
    
    drift_before_correction = driftlock.measure_drift().drift_score
    print(f"Drift before correction: {drift_before_correction:.4f}")
    
    # Clear window and re-inject identity context
    driftlock.clear_window()
    for response in identity_responses:
        driftlock.add_response(response)
    
    drift_after_correction = driftlock.measure_drift().drift_score
    print(f"Drift after correction: {drift_after_correction:.4f}")
    print(f"Drift reduction: {drift_before_correction - drift_after_correction:.4f}")
    
    assert drift_after_correction < drift_before_correction, \
        "Correction should reduce drift"
    
    print("\n[OK] All benchmark tests passed!")
    print("="*70 + "\n")
    
    return {
        "total_turns": len(drift_scores),
        "total_alerts": alert_count,
        "elapsed_time": elapsed_time,
        "phase1_avg_drift": phase1_avg,
        "phase2_avg_drift": phase2_avg,
        "phase3_avg_drift": phase3_avg,
        "drift_increase": phase3_avg - phase1_avg,
        "correction_effective": drift_after_correction < drift_before_correction,
    }


def test_embedding_performance():
    """Benchmark embedding computation performance."""
    print("\n" + "="*70)
    print("BENCHMARK: Embedding Computation Performance")
    print("="*70)
    
    driftlock = DriftLock(DriftLockConfig(
        anchor_phrases=["test anchor phrase"],
        window_size=10,
    ))
    
    # Warm up
    driftlock._load_model()
    
    test_text = "This is a test response for benchmarking embedding computation."
    
    # Measure embedding time
    iterations = 20
    times = []
    
    print(f"\nComputing {iterations} embeddings...")
    for i in range(iterations):
        start = time.time()
        driftlock._get_response_embedding(test_text)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = np.mean(times)
    std_time = np.std(times)
    
    print(f"Average embedding time: {avg_time*1000:.2f}ms")
    print(f"Std dev: {std_time*1000:.2f}ms")
    print(f"Min: {min(times)*1000:.2f}ms, Max: {max(times)*1000:.2f}ms")
    
    # Performance should be reasonable (< 100ms per embedding on CPU)
    assert avg_time < 0.1, f"Embedding too slow: {avg_time*1000:.2f}ms"
    
    print("\n[OK] Performance benchmark passed!")
    print("="*70 + "\n")
    
    return {
        "avg_time_ms": avg_time * 1000,
        "std_time_ms": std_time * 1000,
        "min_time_ms": min(times) * 1000,
        "max_time_ms": max(times) * 1000,
    }


if __name__ == "__main__":
    import sys
    
    # Run benchmarks
    results = {}
    
    try:
        results["conversation"] = test_50_turn_conversation_with_real_embeddings()
    except Exception as e:
        print(f"\n[ERROR] Conversation benchmark failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    try:
        results["performance"] = test_embedding_performance()
    except Exception as e:
        print(f"\n[ERROR] Performance benchmark failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*70)
    print("ALL BENCHMARKS COMPLETED SUCCESSFULLY")
    print("="*70)
    print(f"Conversation test: {results['conversation']['total_turns']} turns, "
          f"{results['conversation']['total_alerts']} alerts")
    print(f"Drift increase: {results['conversation']['drift_increase']:.4f}")
    print(f"Embedding performance: {results['performance']['avg_time_ms']:.2f}ms avg")
    print("="*70 + "\n")
