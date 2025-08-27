import pytest
import pytest_asyncio
import asyncio
import time
import httpx
from main import app

TEST_ADDRESSES = [
    "1600 Vine", "123 Main", "456 Oak", "789 Pine",
    "321 Elm", "654 Maple", "987 Cedar", "147 Birch",
    "258 Ash", "369 Willow"
]

@pytest_asyncio.fixture
async def async_client():
    """Create an asynchronous test client for the FastAPI app using httpx."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

async def analyze_address(client, address):
    """Send an address to the /api/analyze endpoint and measure response time."""
    start = time.time()
    try:
        resp = await client.post("/api/analyze", json={"address": address, "analysis_depth": "basic"})
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return e
    duration = time.time() - start
    return address, result, duration

@pytest.mark.asyncio
class TestPerformanceAsync:

    async def test_all_metrics_async(self, async_client):
        """Test success rate and average response time across multiple addresses."""
        tasks = [analyze_address(async_client, addr) for addr in TEST_ADDRESSES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = 0
        durations = []

        for res in results:
            if isinstance(res, Exception):
                print(f"Task raised exception: {res}")
                continue

            addr, result, duration = res
            durations.append(duration)
            if result.get("success"):
                successful += 1
                print(f"Success: {addr} in {duration:.2f}s")
            else:
                print(f"Failed: {addr} - {result} in {duration:.2f}s")

        success_rate = (successful / len(TEST_ADDRESSES)) * 100
        avg_time = sum(durations)/len(durations) if durations else 0
        print(f"Success rate: {success_rate:.1f}% ({successful}/{len(TEST_ADDRESSES)})")
        print(f"Average response time: {avg_time:.2f}s")

        assert success_rate >= 90, f"Success rate {success_rate:.1f}% below 90%"
        assert avg_time <= 120, f"Average response time {avg_time:.2f}s exceeds 120s"

    async def test_concurrent_users_async(self, async_client):
        """Test handling of multiple concurrent requests to the same address."""
        num_concurrent = 10
        tasks = [analyze_address(async_client, "1600 Vine") for _ in range(num_concurrent)]
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        successful = sum(
            1 for r in results if not isinstance(r, Exception) and r[1].get("success")
        )
        print(f"Concurrent test: {successful}/{num_concurrent} succeeded in {end_time - start_time:.2f}s")
        assert successful >= 8, "Too many failures in concurrent test"

    async def test_response_time_async(self, async_client):
        """Test that a single request responds successfully within the time limit."""
        addr, result, duration = await analyze_address(async_client, "1600 Vine")
        print(f"Response time: {duration:.2f}s")
        assert result.get("success")
        assert duration <= 120, f"Response time {duration:.2f}s exceeds 120s"