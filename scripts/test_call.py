import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.voxara_graph import process_call

SAMPLE_TRANSCRIPT = """
Hello, my name is Rahul and I am calling to inquire about 2BHK apartments
in Velachery. My budget is around 80 lakhs. Can we schedule a site visit
this Saturday at 11am? My number is 9876543210.
"""


async def main():
    print("Running Voxara test call simulation...\n")
    state = await process_call(
        call_id="manual_test_001",
        transcript=SAMPLE_TRANSCRIPT
    )
    printable = {k: v for k, v in state.items() if k != "audio_bytes"}
    print(json.dumps(printable, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
