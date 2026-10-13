"""Tier 1 LIVE gateway test — AMD Token Factory (DeepSeek-V4-Flash)."""
import asyncio
import httpx
import os
import time
from dotenv import load_dotenv

load_dotenv()


async def test_tier1():
    base_url = os.getenv("VLLM_BASE_URL", "https://developer.amd.com.cn/radeon/api/v1")
    model = os.getenv("MODEL_NAME", "DeepSeek-V4-Flash")
    api_key = os.getenv("OPENAI_API_KEY", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {
                "role": "user",
                "content": "Reply with exactly: TIER1_LIVE_OK and nothing else.",
            },
        ],
        "temperature": 0.0,
        "max_tokens": 20,
    }
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions", headers=headers, json=payload
            )
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"HTTP_STATUS: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens_in = data.get("usage", {}).get("prompt_tokens", "N/A")
            tokens_out = data.get("usage", {}).get("completion_tokens", "N/A")
            total_tokens = data.get("usage", {}).get("total_tokens", "N/A")
            model_id = data.get("model", model)
            print(f"RESPONSE   : {content}")
            print(f"LATENCY_MS : {latency_ms:.1f}")
            print(f"TOKENS_IN  : {tokens_in}")
            print(f"TOKENS_OUT : {tokens_out}")
            print(f"TOTAL_TOKENS: {total_tokens}")
            print(f"MODEL_ID   : {model_id}")
            print("TIER1_RESULT: PASS")
        else:
            print(f"ERROR_BODY : {resp.text[:400]}")
            print("TIER1_RESULT: FAIL")
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"EXCEPTION  : {exc}")
        print(f"LATENCY_MS : {latency_ms:.1f}")
        print("TIER1_RESULT: FAIL")


asyncio.run(test_tier1())
