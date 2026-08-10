#!/usr/bin/env python3
"""Script to populate complete, verified slide content for Presentation 9828288 matching slides_content.json spec."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient


def main():
    client = AhaApiClient()

    slides = {
        "156951528": """---
content-v2: 1280x720
version: 1
---

:::text id=s1t1 preset=title at=center width=85% offsetX=0 offsetY=-250
Working with HuyNQ — A User Manual
:::

:::text id=s1s2 preset=subtitle at=center width=80% offsetX=0 offsetY=-140
A practical guide on how to work, communicate, and collaborate with me (Manual of HuyNQ)
:::

:::text id=s1m3 preset=body at=center width=60% offsetX=0 offsetY=-40 background=#1E293B color=#06B6D4 border-radius=12 padding=18
🚀 Core Mission: "Build useful things"
:::

:::text id=s1o4 preset=body at=center width=80% offsetX=0 offsetY=160 background=#1E293B color=#F8FAFC border-radius=12 padding=20
📋 What's Inside:
• Core Values & Mindset
• Communication Preferences & Rules
• Feedback Guide
• Quirks & Debugging Support Strategies
• Collaboration Golden Rules
:::""",
        "156951530": """---
content-v2: 1280x720
version: 1
---

:::text id=s2t1 preset=title at=center width=85% offsetX=0 offsetY=-250
The Mindset — Core Values & Philosophy
:::

:::text id=s2v1 preset=body at=center width=28% offsetX=-360 offsetY=-10 background=#1E293B color=#F8FAFC border-radius=12 padding=16
💎 Integrity
Radical transparency, honesty, and doing what is right even when difficult.
:::

:::text id=s2v2 preset=body at=center width=28% offsetX=0 offsetY=-10 background=#1E293B color=#F8FAFC border-radius=12 padding=16
🏆 Winning Mindset
High standards, drive to solve tough problems, and commitment to meaningful outcomes.
:::

:::text id=s2v3 preset=body at=center width=28% offsetX=360 offsetY=-10 background=#1E293B color=#F8FAFC border-radius=12 padding=16
📈 Continuous improvement
Constant iteration, learning from mistakes, and incremental daily gains.
:::

:::text id=s2p4 preset=body at=center width=88% offsetX=0 offsetY=175 background=#0284C7 color=#F8FAFC border-radius=12 padding=18
⚡ Driving Philosophy: Build & Discover Simultaneously
Prefers running discovery concurrently while building products, rather than waiting for fully baked ideas.
:::""",
        "156951531": """---
content-v2: 1280x720
version: 1
---

:::text id=s3t1 preset=title at=center width=85% offsetX=0 offsetY=-250
How We Connect — Communication Preferences & Rules
:::

:::text id=s3c2 preset=body at=center width=42% offsetX=-270 offsetY=-40 background=#1E293B color=#F8FAFC border-radius=12 padding=16
💬 Preferred Channels
• Slack/Teams (Chat): Best for non-mentally taxing and quick info exchange.
• Face-to-Face or Call: Best for complex or easily misunderstood topics.
• Email: Best for official decisions or third-party communications.
:::

:::text id=s3b3 preset=body at=center width=42% offsetX=-270 offsetY=140 background=#1E293B color=#F8FAFC border-radius=12 padding=16
⛔ Boundaries
• Context upfront: Context provided upfront unless mutual understanding is established.
• One at a time: Only handle one face-to-face or live call conversation at a time.
:::

:::text id=s3f4 preset=body at=center width=42% offsetX=270 offsetY=50 background=#164E63 color=#F8FAFC border-radius=12 padding=16
🚀 Standard 3-Step Format
Use this format for fast responses:

1. Context (facts only)
2. Problem definition
3. Proposed solutions (if any)
:::""",
        "156951532": """---
content-v2: 1280x720
version: 1
---

:::text id=s4t1 preset=title at=center width=85% offsetX=0 offsetY=-250
Receiving Feedback — The 3-Point Feedback Structure
:::

:::text id=s4c2 preset=body at=center width=85% offsetX=0 offsetY=-130 background=#0E7490 color=#F8FAFC border-radius=12 padding=14
🗣️ Preferred Channel: Face-to-face (does not matter if private or public)
:::

:::text id=s4s1 preset=body at=center width=27% offsetX=-360 offsetY=80 background=#1E293B color=#F8FAFC border-radius=12 padding=16
1. Context
Context of the feedback. Describe specific event or situation.
:::

:::text id=s4s2 preset=body at=center width=27% offsetX=0 offsetY=80 background=#1E293B color=#F8FAFC border-radius=12 padding=16
2. Shared Understanding of Impact
Establishing a shared understanding of the problem and its impact on the business, product, or team.
:::

:::text id=s4s3 preset=body at=center width=27% offsetX=360 offsetY=80 background=#1E293B color=#F8FAFC border-radius=12 padding=16
3. Proposed Solution
(Optional) Proposed solution or improvement.
:::""",
        "156951533": """---
content-v2: 1280x720
version: 1
---

:::text id=s5t1 preset=title at=center width=85% offsetX=0 offsetY=-250
Inside the Engine — Default Behaviors & Quirks
:::

:::text id=s5b1 preset=body at=center width=42% offsetX=-270 offsetY=-40 background=#1E293B color=#F8FAFC border-radius=12 padding=16
💡 Out-Loud Brainstorming
Brainstorm and jump between ideas out loud before focusing on the final solution.
:::

:::text id=s5b2 preset=body at=center width=42% offsetX=270 offsetY=-40 background=#1E293B color=#F8FAFC border-radius=12 padding=16
🧩 Coherence-Driven
Easily get irritated when things get incoherent, and tend to sort them out before moving on.
:::

:::text id=s5b3 preset=body at=center width=42% offsetX=-270 offsetY=140 background=#1E293B color=#F8FAFC border-radius=12 padding=16
⚡ Topic-Selective Energy
More energetic when discussing product and engineering topics; lower energy in other areas.
:::

:::text id=s5b4 preset=body at=center width=42% offsetX=270 offsetY=140 background=#1E293B color=#F8FAFC border-radius=12 padding=16
🚀 Build & Discover
Love to build and run product discovery at the same time.
:::""",
        "156951534": """---
content-v2: 1280x720
version: 1
---

:::text id=s6t1 preset=title at=center width=85% offsetX=0 offsetY=-250
Debugging Huy — Known Issues & Support Plan
:::

:::text id=s6g1 preset=body at=center width=85% offsetX=0 offsetY=-110 background=#1E293B color=#F8FAFC border-radius=10 padding=12
🐛 Bug 1: Ask a lot of questions when a problem is not fully understood before committing (ask too many questions).
🛠️ Support: Provide clear context and explain how it is relevant to the business, product, or team.
:::

:::text id=s6g2 preset=body at=center width=85% offsetX=0 offsetY=-10 background=#1E293B color=#F8FAFC border-radius=10 padding=12
🐛 Bug 2: Respond slowly when running on low energy.
🛠️ Support: Give time to recover, still feel free to ask for faster response if urgent.
:::

:::text id=s6g3 preset=body at=center width=85% offsetX=0 offsetY=90 background=#1E293B color=#F8FAFC border-radius=10 padding=12
🐛 Bug 3: Tend to be incoherent when getting over-excited.
🛠️ Support: Give time to let things sink in, and echo back what you hear if possible.
:::

:::text id=s6g4 preset=body at=center width=85% offsetX=0 offsetY=190 background=#1E293B color=#F8FAFC border-radius=10 padding=12
🐛 Bug 4: Sometimes push self and people too hard (pushing too hard).
🛠️ Support: Explain if it's not working or if energy is better spent in other ways (Explain if not working).
:::""",
        "156951535": """---
content-v2: 1280x720
version: 1
---

:::text id=s7t1 preset=title at=center width=85% offsetX=0 offsetY=-250
Rules of Engagement — Pet Peeves & Golden Rules
:::

:::text id=s7ph preset=body at=center width=42% offsetX=-270 offsetY=-40 background=#7F1D1D color=#F8FAFC border-radius=12 padding=14
🚫 Pet Peeves (What to Avoid)
:::

:::text id=s7p1 preset=body at=center width=42% offsetX=-270 offsetY=100 background=#7F1D1D color=#F8FAFC border-radius=12 padding=16
• Unscheduled communication for non-urgent matters.
• Refusal of ideas or proposals without clear reasons.
:::

:::text id=s7gh preset=body at=center width=42% offsetX=270 offsetY=-40 background=#065F46 color=#F8FAFC border-radius=12 padding=14
🌟 Golden Rules (How to Succeed)
:::

:::text id=s7g1 preset=body at=center width=42% offsetX=270 offsetY=100 background=#065F46 color=#F8FAFC border-radius=12 padding=16
• Notify me beforehand for synchronous check-ins.
• Give reasons for idea/proposal refusal, and optionally suggest alternatives.
:::""",
        "156951536": """---
content-v2: 1280x720
version: 1
---

:::text id=s8t1 preset=title at=center width=85% offsetX=0 offsetY=-250
Conclusion — Let's Build Useful Things Together
:::

:::text id=s8c2 preset=body at=center width=85% offsetX=0 offsetY=-10 background=#1E293B color=#F8FAFC border-radius=12 padding=20
📝 Quick Cheatsheet for HuyNQ (Cheatsheet):
• Context upfront (Context -> Problem -> Solution)
• Face-to-face for feedback (focus on impact)
• Support the bugs (echo back, tag urgency, protect energy)
• Respect focus time (pre-notify check-ins, explain rejections)
:::

:::text id=s8q3 preset=body at=center width=85% offsetX=0 offsetY=175 background=#0E7490 color=#F8FAFC border-radius=12 padding=16
💬 "This manual is a living document—let's keep communicating, building, and improving together!" (Build useful things)
:::""",
    }

    for sid, dsl in slides.items():
        client.post(f"/api/v2/slides/{sid}/attributes", json_data={"attributeKey": "baseColour", "attributeValue": "#0F172A"})
        client.post(f"/api/v2/slides/{sid}/attributes", json_data={"attributeKey": "textColour", "attributeValue": "#F8FAFC"})
        client.post(f"/api/v2/slides/{sid}/attributes", json_data={"attributeKey": "dsl", "attributeValue": dsl.strip()})

    print("SUCCESS: All 8 slides updated cleanly with complete DSL elements.")


if __name__ == "__main__":
    main()
