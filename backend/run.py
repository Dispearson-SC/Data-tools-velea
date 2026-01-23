import uvicorn
import sys
import asyncio

if __name__ == "__main__":
    # CRITICAL: Force ProactorEventLoop on Windows for Playwright
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    print(f"Running on platform: {sys.platform}")
    print(f"Event loop policy: {asyncio.get_event_loop_policy()}")

    # Run Uvicorn
    # We use 'main:app' string to enable reload, but we must ensure the loop is handled correctly.
    # When using reload=True, uvicorn spawns subprocesses.
    # The loop config needs to be passed to uvicorn.run or set in the subprocess.
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False, # Disable reload to ensure event loop policy works correctly on Windows
        loop="asyncio" 
    )
