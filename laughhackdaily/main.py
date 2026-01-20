import asyncio
from anthropic import Anthropic
import os

async def laughhackdaily_agent(topic):
    """Main agent for viral psychology content creation"""

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Phase 1: Research
    research_prompt = f"""
    Research psychology principles for TikTok content on: {topic}

    Requirements:
    - Ethical self-improvement focus
    - 3 actionable principles
    - Scientific backing
    - 30-second video format

    Provide research summary.
    """

    print("🔍 Researching topic...")
    research_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": research_prompt}]
    )
    research = research_response.content[0].text

    # Phase 2: Script Generation
    script_prompt = f"""
    Based on this research:
    {research}

    Create TikTok script with:
    - Hook (3-5 sec)
    - Principle 1 (8-12 sec)
    - Principle 2 (8-12 sec)
    - Principle 3 (8-12 sec)
    - CTA (3-5 sec)

    Format with paragraph breaks for ElevenLabs TTS.
    Include Pexels search keywords for each section.
    """

    print("✍️ Generating script...")
    script_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": script_prompt}]
    )
    script = script_response.content[0].text

    # Phase 3: Production Package
    package_prompt = f"""
    Based on this script:
    {script}

    Generate complete production package:

    1. ELEVENLABS SCRIPT (with natural breaks)
    2. VISUAL MAPPING (Pexels keywords per section)
    3. TEXT OVERLAY TIMING (when to show each text)
    4. CAPCUT INSTRUCTIONS (editing steps)
    5. HASHTAGS: #LaughHackDaily #FYP #ViralHack #ComedyHacks

    Format as ready-to-use production document.
    """

    print("📦 Creating production package...")
    package_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": package_prompt}]
    )

    return package_response.content[0].text

# Run the agent
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = input("Enter content topic: ")
    result = asyncio.run(laughhackdaily_agent(topic))
    print("\n" + "="*50)
    print("PRODUCTION PACKAGE:")
    print("="*50)
    print(result)

    # Save to file
    os.makedirs("output", exist_ok=True)
    with open("output/latest_package.txt", "w") as f:
        f.write(result)
    print("\n✅ Saved to output/latest_package.txt")
