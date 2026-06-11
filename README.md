# transkript

Local meeting transcriber for Windows. Records your microphone and system audio (Teams, Zoom, Meet, anything), transcribes it locally with Whisper, and saves a timestamped text file you can paste into any AI tool for summarization.

**No API keys. No internet after setup. No data leaves your machine.**

## Features

- Records **mic + system audio** (WASAPI loopback) simultaneously
- Transcribes locally using **faster-whisper** (4-8x faster than original Whisper)
- Supports **99+ languages** with automatic detection
- Saves timestamped `.txt` files — opens in Notepad by default
- Simple TUI: hit **Start**, hit **Stop**, get your transcript
- Zero cost, zero cloud dependency

---

## Download ( easiest way )

1. Go to [Releases](https://github.com/Snowiness4394/transkript/releases)
2. Download `transkript-windows.zip`
3. Right-click the zip file → **Extract All** → pick a folder
4. Open the extracted folder → double-click `transkript.exe`

That's it. No Python, no terminal, nothing else needed.

---

## Build the exe yourself

If you want to build it from source (or contribute), follow these steps. Takes about 5 minutes.

### Step 1 — Open PowerShell

1. Press the **Windows key** on your keyboard
2. Type `powershell`
3. Click **Windows PowerShell** (the blue one)
4. A blue window opens — that's where you'll type commands

### Step 2 — Install Git

Git lets you download the code. Paste this command into PowerShell and press Enter:

```powershell
winget install Git.Git
```

Accept any prompts. When it says "Successfully installed", **close PowerShell and open it again** (this lets Git work properly).

### Step 3 — Install Python

Python runs the code. Paste this into PowerShell:

```powershell
winget install Python.Python.3.13
```

When it finishes, **close PowerShell and open it again**.

### Step 4 — Install uv

uv is a fast package manager for Python. Paste this:

```powershell
pip install uv
```

### Step 5 — Download the code

In PowerShell, run these one at a time:

```powershell
git clone https://github.com/Snowiness4394/transkript.git
cd transkript
```

### Step 6 — Install everything the app needs

```powershell
uv sync --group dev
```

This downloads all the dependencies. Takes 1-2 minutes.

### Step 7 — Build the exe

```powershell
build.bat
```

Wait for it to finish (2-3 minutes). You'll see lots of text scrolling — that's normal.

### Step 8 — Find your exe

When the build finishes, the exe is here:

```
C:\Users\<your name>\transkript\dist\transkript\transkript.exe
```

To get there in File Explorer:
1. Open File Explorer
2. Go to `C:\Users\<your name>\transkript\dist\transkript\`
3. You'll see `transkript.exe` and a `_internal` folder

**Both the exe AND the `_internal` folder need to be together.** To share it with someone, zip the whole `transkript` folder inside `dist`.

### Step 9 — Run it

Double-click `transkript.exe`. A terminal window opens with the app. That's it.

---

## Using the app

1. **Select your microphone** from the Mic dropdown at the bottom
2. **Select your speakers** from the Output dropdown
3. Click the big green **Start Recording** button
4. Join your meeting — Teams, Zoom, Google Meet, anything
5. When done, click the red **Stop Recording** button
6. Wait a few seconds for transcription
7. Click **Open File** to see your transcript, or **Open Folder** to open the folder

The transcript is a `.txt` file with timestamps like:

```
Meeting Transcript
Date: 2025-06-11 14:30:00
Duration: 00:12:34
Language: English (auto-detected)

[00:00:00] Hello everyone, let's get started.
[00:00:05] I'll go first. Yesterday I finished the API work.
[00:00:12] Great, any blockers?
```

Paste this into ChatGPT, Claude, Gemini, or any AI tool for a summary.

---

## CLI options

If you run from source instead of the exe:

```powershell
# Use a different Whisper model (tiny/base/small/medium/large-v3)
uv run transkript --model small

# Save transcripts to a different folder
uv run transkript --output C:\Users\Me\MeetingNotes
```

## Model sizes

| Model | Size | Speed | Accuracy | Best for |
|-------|------|-------|----------|----------|
| `tiny` | 39 MB | Fastest | Basic | Quick drafts |
| `base` | 74 MB | Fast | Good | **Default** |
| `small` | 244 MB | Medium | Very good | When accuracy matters |
| `medium` | 769 MB | Slow | Excellent | Important meetings |
| `large-v3` | 1.5 GB | Slowest | Best | Maximum accuracy |

First run downloads the model (~74MB for base). After that it works fully offline.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `winget` not recognized | You're probably in Command Prompt. Open PowerShell instead (blue icon). |
| `git` not recognized | Close PowerShell and reopen it after installing Git. |
| `uv` not recognized | Close PowerShell and reopen it, or run `pip install uv` again. |
| Antivirus blocks the exe | Windows Defender sometimes flags PyInstaller builds. Click "More info" → "Run anyway". It's a false positive. |
| No microphone in dropdown | Make sure your mic is plugged in and not used by another app. |
| No loopback device | Enable "Stereo Mix" in Windows Sound settings, or the app will only capture your mic. |
| Build fails | Run `test-build.bat` to see what's wrong, then check the Troubleshooting section above. |

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| Enter | Start/Stop recording |
| q | Quit app |

## Requirements

- Windows 10 or 11
- A microphone
- Speakers or headphones
- ~100MB free disk space

## License

MIT — do whatever you want with it.

## Contributing

Contributions welcome! Open an issue or submit a PR.

## Acknowledgments

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2 Whisper implementation
- [Textual](https://github.com/Textualize/textual) — Python TUI framework
- [sounddevice](https://github.com/spatialaudio/python-sounddevice) — Audio capture
