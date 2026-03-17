"""
Async utility functions for Project Myriad.

Provides helpers for running async code in different execution contexts.
"""

import asyncio
import concurrent.futures
from typing import TypeVar, Coroutine

T = TypeVar("T")


def run_async_in_thread(coro: Coroutine[None, None, T]) -> T:
    """
    Run async coroutine in a new thread with its own event loop.

    This is needed when an async function needs to be called from sync code,
    but there's already an event loop running in the current thread.

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of the coroutine execution
    """

    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()


def run_async_safe(coro: Coroutine[None, None, T]) -> T:
    """
    Safely run an async coroutine from sync code.

    Automatically detects if an event loop is already running:
    - If yes: Runs coroutine in a separate thread with new event loop
    - If no: Uses asyncio.run() to execute in current thread

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of the coroutine execution
    """
    try:
        # Check if event loop is already running
        asyncio.get_running_loop()
        # We're in an async context - run in separate thread
        return run_async_in_thread(coro)
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)
