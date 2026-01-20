# Command Reference

## Quick Start Commands

| Command | Description | Output |
|---------|-------------|--------|
| `new hack: [topic]` | Full production workflow | Complete script package |
| `batch: [number]` | Generate multiple videos | [N] script packages |
| `series: [topic]` | Create 5-part series | Series template + 5 scripts |
| `trim: [script]` | Cut script to 30 seconds | Optimized script |
| `caption: [topic]` | Generate caption variations | 4 caption options |
| `thumbnail: [topic]` | Generate thumbnail options | 5 thumbnail options |
| `analyze: [description]` | Diagnose performance issues | Analysis + fixes |

---

## Detailed Command Documentation

### `new hack: [topic]`

**Purpose:** Complete production workflow from topic to final package.

**Input:** Topic idea or concept (e.g., "The 2-Second Pause That Makes People Respect You")

**Workflow:**
1. Phase 1: Generate 10 topic candidates
2. Score and select top 3
3. Phase 2: Create full script for each
4. Phase 3: Run quality checks
5. Output: Complete script packages

**Example:**
```
new hack: The silence technique that makes people trust you
```

---

### `batch: [number]`

**Purpose:** Generate multiple unrelated video packages efficiently.

**Input:** Number of videos to generate (recommended: 5-10)

**Workflow:**
1. Generate [N] diverse topic candidates
2. Create script package for each
3. Run quality checks on all
4. Output: [N] complete packages

**Example:**
```
batch: 5
```

---

### `series: [topic]`

**Purpose:** Create a 5-part series from a performing topic.

**Input:** Topic that has performed well (1,000+ views)

**Workflow:**
1. Analyze original topic
2. Generate 5 angles:
   - "Most people do X..."
   - "The mistake is Y..."
   - "Here's why it happens..."
   - "Try this instead..."
   - "Watch what happens when..."
3. Create posting strategy
4. Output: 5 linked script packages

**Example:**
```
series: The pause that commands respect
```

---

### `trim: [script]`

**Purpose:** Reduce a script to exactly 30 seconds.

**Input:** Paste full script that's too long

**Workflow:**
1. Identify non-essential content
2. Tighten phrasing
3. Combine overlapping points
4. Verify 30-second timing
5. Output: Trimmed script

**Example:**
```
trim: [paste script here]
```

---

### `caption: [topic]`

**Purpose:** Generate multiple caption options for A/B testing.

**Input:** Video topic or hook

**Workflow:**
1. Create 4 caption variations
2. Each uses different angle
3. All follow 2-line + emoji format
4. Include locked hashtags
5. Output: 4 caption options

**Example:**
```
caption: The 2-second pause technique
```

**Output Format:**
```
Option 1:
[Hook line + emoji]
[CTA line + emoji]
#LaughHackDaily #FYP #ViralHack #ComedyHacks

Option 2:
...

Option 3:
...

Option 4:
...

Recommended: Option [X] because [reason]
```

---

### `thumbnail: [topic]`

**Purpose:** Generate text overlay options for video thumbnail/first frame.

**Input:** Video topic

**Workflow:**
1. Create 5 thumbnail text options
2. Each 3-5 words
3. High contrast considerations
4. Scroll-stop potential scoring
5. Output: 5 options with recommendation

**Example:**
```
thumbnail: Making people trust you instantly
```

---

### `analyze: [description]`

**Purpose:** Diagnose why a video underperformed.

**Input:** Description of video + performance metrics

**Workflow:**
1. Categorize performance tier
2. Identify likely failure point
3. Suggest specific fixes
4. Provide rewrite recommendations
5. Output: Diagnosis + action plan

**Example:**
```
analyze: Video about silence and power got 150 views in 2 hours. Hook was "Here's why quiet people are powerful." Completion rate was 45%.
```

**Output Format:**
```
DIAGNOSIS:
- Performance tier: Under 200 views
- Primary issue: Hook failure
- Secondary issue: Low completion (45% vs target 80%)

ROOT CAUSE ANALYSIS:
1. Hook sounds like a YouTube title, not TikTok
2. "Here's why" signals educational content
3. Missing curiosity gap

FIXES:
1. Rewrite hook: "The quiet person in the room? They're not shy..."
2. Add text overlay in first frame
3. Stronger first visual

REWRITTEN SCRIPT:
[Complete rewrite]
```

---

## Advanced Commands

### `hooks: [concept]`

Generate 10 hook variations for a single concept.

```
hooks: social power dynamics
```

### `pexels: [script]`

Generate optimized Pexels search keywords for existing script.

```
pexels: [paste script]
```

### `cta: [topic]`

Generate 5 CTA variations for a topic.

```
cta: following for more psychology hacks
```

### `comments: [topic]`

Generate pinned comment + reply templates.

```
comments: The pause technique
```

---

## Workflow Best Practices

### Daily Production

1. Start with `batch: 3` for variety
2. Use `analyze:` on yesterday's posts
3. If any hit 1,000+, use `series:` immediately

### Weekly Planning

1. Review top performers from week
2. Generate series for top 2
3. Create batch of 5 new topics
4. Total: 15-20 videos queued

### Content Mix

- 50% Observation mask
- 30% Self-Reflection mask
- 15% Social Pattern mask
- 5% Warning mask

### Posting Schedule

- Peak times: 7-9 AM, 12-2 PM, 7-10 PM
- Post 2-3 videos daily
- Space at least 3 hours apart
