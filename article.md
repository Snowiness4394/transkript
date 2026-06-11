# I Built a Free Meeting Transcriber That Runs Entirely on Your Laptop — Here's Why

**No API keys. No subscriptions. No data leaving your machine.**

---

We've all been there.

You're in a two-hour meeting. Someone says something brilliant — a decision, an action item, a number you need to remember. You think, *"I'll definitely remember that."*

You don't.

By the time you've grabbed lunch, it's gone. Buried somewhere in the chaos of your afternoon, replaced by the next Slack notification, the next urgent email, the next meeting that probably should've been an email.

I got tired of this cycle. So I built something.

## The Problem Nobody Talks About

There are plenty of transcription tools out there. Otter.ai, Fireflies, Grain — they're all great. But they all have the same three problems:

1. **They cost money.** $15-20/month adds up when you're freelancing or at a startup watching every dollar.

2. **Your meetings go to someone else's server.** That confidential client call? Your CEO's offhand comment about restructuring? It's sitting on their AWS instance now.

3. **They need internet.** Try transcribing on a plane, in a coffee shop with bad WiFi, or in a secure facility where your phone is locked in a locker.

I wanted something different. Something that:

- Runs **100% locally** on my laptop
- Costs **$0** after initial setup
- Works **offline** once the model is downloaded
- Requires **zero technical knowledge** to use

So I built **transkript**.

## What It Actually Does

Open the app. Click "Start Recording." Join your meeting on Teams, Zoom, Google Meet — whatever. When you're done, click "Stop Recording."

That's it.

A few seconds later, you have a clean text file with timestamps:

```
Meeting Transcript
Date: 2025-06-11 14:30:00
Duration: 00:45:22
Language: English (auto-detected)

[00:00:00] Hello everyone, let's get started with today's standup.
[00:00:05] I'll go first. Yesterday I finished the API integration.
[00:00:12] Great, any blockers?
[00:00:15] No blockers from my side. Ready to pick up the new feature.
```

Copy it. Paste it into ChatGPT for a summary. Drop it into your notes. Done.

## The Tech Stack (For the Curious)

If you're not into the technical details, skip this section. But if you're curious how a free tool can transcribe as well as paid alternatives:

- **Whisper** — OpenAI's open-source speech recognition model. It's trained on 680,000 hours of audio. It understands 99 languages. And it runs locally on your machine.

- **faster-whisper** — A reimplementation of Whisper that's 4-8x faster using CTranslate2. Same accuracy, fraction of the time.

- **WASAPI Loopback** — A built-in Windows feature that captures all system audio. No virtual cables, no drivers, no hacks. It's been there since Windows Vista.

- **Textual** — A Python framework for building beautiful terminal apps. No Electron. No bloated GUI. Just a clean, fast interface in your terminal.

The result? You get enterprise-grade transcription on consumer hardware.

## Who This Is For

I built this for three kinds of people:

### 1. The Freelancer Who Can't Afford $20/Month

You're charging $50/hour for consulting. Every dollar counts. A transcription subscription that costs $240/year is a real expense when you're watching your cash flow.

transkript is free. Forever.

### 2. The Corporate Worker Who Cares About Privacy

Your company handles sensitive data. Client information, financial projections, personnel discussions. You know these shouldn't be uploaded to third-party servers.

transkript never sends your audio anywhere. It runs on your machine. Your data stays on your machine.

### 3. The Developer Who Wants Control

You want to tweak the model, adjust the output format, integrate it into your workflow. You don't want a black box.

transkript is open source. Every line of code is on GitHub. Fork it, modify it, make it yours.

## How to Get It Running

If you have **OpenCode**, **Claude Code**, or any AI coding assistant, just paste this into it:

> Download and build https://github.com/Snowiness4394/transkript, run it on my computer and put a shortcut on my desktop

The AI handles everything — Python, dependencies, building the exe, creating a shortcut.

Or if you prefer the manual route, it's 5 commands in PowerShell:

```powershell
# Install Git and uv
winget install Git.Git
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Clone and build
git clone https://github.com/Snowiness4394/transkript.git
cd transkript
uv sync --group dev
build.bat
```

Double-click `dist\transkript\transkript.exe`. You're done.

## The Features That Matter

### Auto-Detect Language

Speaking Spanish in a meeting with a German client? No problem. Whisper auto-detects the language. Or you can force a specific language from the dropdown for better accuracy.

### Choose Your Model

Need speed? Use "tiny" (39MB, fastest). Need accuracy? Use "large-v3" (1.5GB, best). The dropdown lets you switch models without restarting.

First time you select a model, it downloads. After that, it works offline forever.

### Select Your Devices

Multiple microphones? Multiple speakers? The dropdowns at the bottom let you pick exactly which devices to use. No more accidentally recording from the wrong mic.

### Timestamped Output

Every line in the transcript includes a timestamp. Jump to the exact moment in the recording. Or just use the timestamps as reference points when sharing with your team.

### Simple Workflow

Start → Record → Stop → Done. No settings to configure. No accounts to create. No cloud to sync with.

## What It Doesn't Do (And Why)

I intentionally left features out:

- **No speaker diarization** — It won't tell you who said what. That requires additional models and complexity. Keep it simple.
- **No real-time transcription** — It transcribes after you stop recording. Real-time adds latency and complexity.
- **No cloud sync** — Your files stay on your machine. That's the point.

Each of these could be added later. But the goal was a tool that "just works" for the 90% use case.

## The Numbers

- **Model size:** 39MB (tiny) to 1.5GB (large-v3)
- **Transcription speed:** 4-8x faster than original Whisper
- **Languages:** 99 supported
- **Cost:** $0
- **Internet required:** Only for initial model download
- **Dependencies:** 4 Python packages
- **Lines of code:** ~600

## Why Open Source

I could've sold this. A SaaS at $10/month would probably make money.

But the value isn't in the code. It's in the problem it solves. And that problem — "I need to remember what was said in my meeting" — shouldn't be a premium feature.

So it's MIT licensed. Do whatever you want with it. Sell it, modify it, put your name on it. I don't care. Just use it.

## What's Next

The app works. But there's room to grow:

- **Speaker diarization** — Who said what
- **Meeting summaries** — Auto-generate action items using a local LLM
- **Export formats** — SRT subtitles, JSON, DOCX
- **Scheduled recording** — Start automatically when your calendar event begins

All of these are on the [GitHub roadmap](https://github.com/Snowiness4394/transkript). Want to help build them? Pull requests welcome.

## The Bottom Line

I was tired of forgetting what was said in meetings. I was tired of paying for tools that sent my data to the cloud. I was tired of complicated setup processes that required a CS degree.

So I built transkript. It's simple. It's free. It's private. It works.

If you've ever lost an important detail from a meeting, or worried about where your audio data goes, or just wanted a tool that does one thing well — give it a try.

**[→ Get transkript on GitHub](https://github.com/Snowiness4394/transkript)**

---

*Found this useful? Share it with someone who complains about missing meeting notes. They'll thank you later.*
