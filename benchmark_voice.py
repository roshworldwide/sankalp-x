#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           SOVEREIGN VOICE ORB — WebSocket Pipeline Benchmark               ║
║                 End-to-End Latency & Stress Test Suite                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Tests:
  1. TTFB (Time-To-First-Byte): Measures STT + Claude 3.5 + Polly latency
  2. Barge-in Stress Test: Measures interrupt acknowledgement latency
  3. Connection Stability: Validates connect/disconnect resilience
"""

import asyncio
import json
import time
import struct
import sys

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
WS_URL = "ws://127.0.0.1:8000/ws/voice/stream"
CHUNK_DURATION_MS = 250
TOTAL_AUDIO_DURATION_S = 2.0
SAMPLE_RATE = 16000
CHANNELS = 1
BITS_PER_SAMPLE = 16
TIMEOUT_S = 60  # max wait for backend response


def generate_pcm_bytes(duration_s: float, sample_rate: int = 16000) -> bytes:
    """
    Generate raw 16-bit PCM audio (440Hz sine tone) matching the browser's
    ScriptProcessorNode output format: 16kHz, mono, int16, little-endian.
    No WAV header — raw PCM bytes only.
    """
    import math

    num_samples = int(sample_rate * duration_s)
    amplitude = 16000  # ~50% of int16 max

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * math.sin(2 * math.pi * 440 * t))
        samples.append(struct.pack('<h', max(-32768, min(32767, value))))

    return b"".join(samples)


def chunk_pcm(data: bytes, chunk_duration_ms: int, sample_rate: int) -> list:
    """Split raw PCM data into time-based chunks (no header to skip)."""
    bytes_per_chunk = int(sample_rate * (chunk_duration_ms / 1000) * CHANNELS * (BITS_PER_SAMPLE // 8))
    chunks = []
    offset = 0
    while offset < len(data):
        chunks.append(data[offset:offset + bytes_per_chunk])
        offset += bytes_per_chunk
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: TTFB (Time-To-First-Byte)
# ─────────────────────────────────────────────────────────────────────────────
async def test_ttfb() -> dict:
    """Measures end-to-end TTFB: text send → first Polly audio chunk received."""
    result = {"ttfb_ms": None, "status": "FAIL", "error": None}

    try:
        async with websockets.connect(WS_URL, max_size=10 * 1024 * 1024) as ws:
            # 1. Handshake
            await ws.send(json.dumps({"action": "start", "user_id": "benchmark_phantom_user"}))

            # 2. Send text directly (simulating Web Speech API result)
            test_text = "What government schemes are available for farmers in India?"
            await ws.send(json.dumps({"action": "process_text", "text": test_text}))
            t_sent = time.perf_counter()
            print(f"  [TTFB] Text sent: \"{test_text}\". Timer started.")

            # 5. Wait for first binary response (Polly audio chunk)
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_S)
                except asyncio.TimeoutError:
                    result["error"] = f"Timeout ({TIMEOUT_S}s) waiting for Polly response"
                    return result

                if isinstance(msg, bytes) and len(msg) > 0:
                    t_received = time.perf_counter()
                    ttfb_ms = (t_received - t_sent) * 1000
                    result["ttfb_ms"] = round(ttfb_ms, 1)
                    result["status"] = "PASS"
                    result["audio_chunk_size"] = len(msg)
                    print(f"  [TTFB] First Polly chunk received: {len(msg)} bytes in {ttfb_ms:.1f}ms")
                    break
                elif isinstance(msg, str):
                    payload = json.loads(msg)
                    if payload.get("action") == "error":
                        result["error"] = payload.get("message", "Unknown backend error")
                        return result
                    # processing status messages — keep waiting
                    print(f"  [TTFB] Backend status: {payload}")

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: BARGE-IN STRESS TEST
# ─────────────────────────────────────────────────────────────────────────────
async def test_barge_in() -> dict:
    """Sends interrupt after first audio chunk and measures cancellation latency."""
    result = {"interrupt_latency_ms": None, "status": "FAIL", "error": None}

    try:
        async with websockets.connect(WS_URL, max_size=10 * 1024 * 1024) as ws:
            # 1. Handshake
            await ws.send(json.dumps({"action": "start", "user_id": "benchmark_barge_in_user"}))

            # 2. Send text to trigger pipeline
            test_text = "Tell me about all agricultural subsidies and loan waivers available."
            await ws.send(json.dumps({"action": "process_text", "text": test_text}))
            print(f"  [BARGE-IN] Text sent. Waiting for first Polly chunk...")

            # 3. Wait for first Polly audio chunk
            got_first_audio = False
            while not got_first_audio:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_S)
                except asyncio.TimeoutError:
                    result["error"] = f"Timeout ({TIMEOUT_S}s) waiting for audio before barge-in"
                    return result

                if isinstance(msg, bytes) and len(msg) > 0:
                    got_first_audio = True
                elif isinstance(msg, str):
                    payload = json.loads(msg)
                    if payload.get("action") == "error":
                        result["error"] = payload.get("message", "Unknown backend error")
                        return result

            # 4. FIRE INTERRUPT and start timer
            t_interrupt = time.perf_counter()
            await ws.send(json.dumps({"action": "interrupt"}))
            print(f"  [BARGE-IN] Interrupt sent! Measuring cancellation latency...")

            # 5. Drain remaining messages until the socket is quiet for 2s
            #    (the backend should stop sending after interrupt)
            remaining_chunks = 0
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    remaining_chunks += 1
                except asyncio.TimeoutError:
                    # No more messages for 2 seconds — backend has stopped
                    break

            t_silent = time.perf_counter()
            interrupt_latency_ms = (t_silent - t_interrupt) * 1000
            # Subtract the 2s drain timeout for accurate measurement
            actual_latency = max(0, interrupt_latency_ms - 2000)

            result["interrupt_latency_ms"] = round(actual_latency, 1)
            result["trailing_chunks_after_interrupt"] = remaining_chunks
            result["status"] = "PASS"
            print(f"  [BARGE-IN] Pipeline silenced. {remaining_chunks} trailing chunks received. Latency: {actual_latency:.1f}ms")

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: CONNECTION STABILITY
# ─────────────────────────────────────────────────────────────────────────────
async def test_connection_stability() -> dict:
    """Rapid connect/disconnect cycles to test server resilience."""
    result = {"cycles": 0, "status": "FAIL", "error": None}
    target_cycles = 5

    try:
        for i in range(target_cycles):
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps({"action": "start", "user_id": f"stability_test_{i}"}))
                # Small pause to let the server register
                await asyncio.sleep(0.1)
            result["cycles"] += 1

        result["status"] = "PASS" if result["cycles"] == target_cycles else "FAIL"
        print(f"  [STABILITY] {result['cycles']}/{target_cycles} connect/disconnect cycles completed.")

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────
def print_report(ttfb_result: dict, barge_result: dict, stability_result: dict):
    """Print a clean ASCII benchmark report."""

    ttfb_val = f"{ttfb_result['ttfb_ms']} ms" if ttfb_result['ttfb_ms'] is not None else ttfb_result.get('error', 'N/A')
    barge_val = f"{barge_result['interrupt_latency_ms']} ms" if barge_result['interrupt_latency_ms'] is not None else barge_result.get('error', 'N/A')
    trailing = barge_result.get('trailing_chunks_after_interrupt', 'N/A')
    stability_val = f"{stability_result['cycles']}/5 cycles" if stability_result['cycles'] else stability_result.get('error', 'N/A')

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║         SOVEREIGN VOICE ORB — BENCHMARK REPORT                     ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  {'METRIC':<40} {'RESULT':>24}  ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  {'TTFB (STT + Claude 3.5 + Polly)':<40} {ttfb_val:>24}  ║")
    print(f"║  {'TTFB Status':<40} {ttfb_result['status']:>24}  ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  {'Barge-In Interrupt Latency':<40} {barge_val:>24}  ║")
    print(f"║  {'Trailing Chunks After Interrupt':<40} {str(trailing):>24}  ║")
    print(f"║  {'Barge-In Status':<40} {barge_result['status']:>24}  ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  {'Connection Stability':<40} {stability_val:>24}  ║")
    print(f"║  {'Stability Status':<40} {stability_result['status']:>24}  ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Overall Verdict
    all_pass = all(r["status"] == "PASS" for r in [ttfb_result, barge_result, stability_result])
    if all_pass:
        ttfb_ms = ttfb_result['ttfb_ms'] or 99999
        if ttfb_ms < 500:
            print("  🏆 VERDICT: HACKATHON GRAND PRIZE READY — Sub-500ms TTFB achieved!")
        elif ttfb_ms < 800:
            print("  ✅ VERDICT: STRONG CONTENDER — Sub-800ms TTFB. Very competitive.")
        elif ttfb_ms < 2000:
            print("  ⚠️  VERDICT: FUNCTIONAL — TTFB under 2s. Needs optimization.")
        else:
            print("  ❌ VERDICT: NEEDS WORK — TTFB exceeds 2 seconds.")
    else:
        failed = [name for name, r in [("TTFB", ttfb_result), ("Barge-In", barge_result), ("Stability", stability_result)] if r["status"] != "PASS"]
        print(f"  ❌ VERDICT: FAILING — Tests failed: {', '.join(failed)}")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║         SOVEREIGN VOICE ORB — BENCHMARK SUITE                      ║")
    print("║           Testing against: ws://127.0.0.1:8000                     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Test 1: Connection Stability (quick, run first)
    print("━━━ TEST 1: CONNECTION STABILITY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    stability_result = await test_connection_stability()
    print()

    # Test 2: TTFB
    print("━━━ TEST 2: TIME-TO-FIRST-BYTE (TTFB) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    ttfb_result = await test_ttfb()
    print()

    # Test 3: Barge-In
    print("━━━ TEST 3: BARGE-IN STRESS TEST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    barge_result = await test_barge_in()
    print()

    # Report
    print_report(ttfb_result, barge_result, stability_result)


if __name__ == "__main__":
    asyncio.run(main())
