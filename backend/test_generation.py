import asyncio

from app.generation.generation_pipeline import (
    run_generation_pipeline,
)


async def main():

    result = await run_generation_pipeline(
        "What is machine learning?"
    )

    print("\nANSWER:\n")
    print(result["answer"])

    print("\nCITATIONS:\n")
    print(result["citations"])


asyncio.run(main())