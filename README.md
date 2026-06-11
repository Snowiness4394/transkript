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

## Install

### Option 1: Download pre-built exe (recommended)

Download the latest `transkript-windows.zip` from [Releases](https://github.com/Snowiness4394/transkript/releases). Extract and run `transkript.exe` — no Python needed.

### Option 2: Run from source

Requires Python 3.11+ and Windows (for WASAPI loopback).

```bash
git clone https://github.com/Snowiness4394/transkript.git
cd transkript
uv sync
uv run transkript
```

## Building the Windows exe

### Prerequisites

- **Windows 10/11**
- **Python 3.11+** — [Download Python](https://www.python.org/downloads/)
- **Git** — [Download Git](https://git-scm.com/download/win)

### Step-by-step build

```bash
# 1. Clone the repo
git clone https://github.com/Snowiness4394/transkript.git
cd transkript

# 2. Install uv (if you don't have it)
pip install uv

# 3. Install all dependencies (including PyInstaller)
uv sync --group dev

# 4. Verify everything is ready (optional but recommended)
#    Run on Linux/macOS:
./test-build.sh
#    Or on Windows:
test-build.bat

# 5. Build the exe
#    Run on Linux/macOS:
./build.sh
#    Or on Windows:
build.bat
```

### Output

The build creates a folder at `dist/transkript/` containing:

```
dist/transkript/
├── transkript.exe          ← run this
├── _internal/              ← bundled dependencies
│   ├── ...
```

To distribute:
1. Zip the entire `dist/transkript/` folder
2. Upload as `transkript-windows.zip` to GitHub Releases
3. Users download, extract, and double-click `transkript.exe`

### Build troubleshooting

Run the test script first to catch issues:

```bash
# Linux/macOS
./test-build.sh

# Windows
test-build.bat
```

Common issues:
- **`ModuleNotFoundError`**: Run `uv sync --group dev` to install all deps
- **`Python shared library not found`**: Install `libpython3.13-dev` (Linux) or rebuild Python with `--enable-shared`
- **Antivirus warning**: PyInstaller exe sometimes trigger false positives — users can whitelist it

## Usage

```bash
# Run the app
uv run transkript

# Or after pip install
transkript
```

### CLI Options

```bash
# Use a different Whisper model (tiny/base/small/medium/large-v3)
transkript --model small

# Specify output directory
transkript --output ~/my-transcripts

# Combine options
transkript --model medium -o ./meeting-notes
```

### How It Works

1. **Open the app** — it auto-detects your microphone and speakers
2. **Select devices** — choose your mic and output device from the dropdowns
3. **Hit Start Recording** — the app captures both mic and system audio
4. **Join your meeting** — Teams, Zoom, Google Meet, anything playing audio
5. **Hit Stop Recording** — transcription begins automatically
6. **Open your transcript** — click "Open File" or "Open Folder" when done

### Transcript Format

```
Meeting Transcript
Date: 2025-06-11 14:30:00
Duration: 00:12:34
Language: English (auto-detected)

[00:00:00] Hello everyone, let's get started with today's standup.
[00:00:05] I'll go first. Yesterday I finished the API integration.
[00:00:12] Great, any blockers?
```

## Model Sizes

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `tiny` | 39 MB | Fastest | Basic | Quick drafts |
| `base` | 74 MB | Fast | Good | **Default — good balance** |
| `small` | 244 MB | Medium | Very good | When accuracy matters |
| `medium` | 769 MB | Slow | Excellent | Important meetings |
| `large-v3` | 1.5 GB | Slowest | Best | Maximum accuracy |

First run downloads the model — subsequent runs are fully offline.

## GPU Acceleration

If you have an NVIDIA GPU, faster-whisper can use CUDA for 4-8x speedup:

```bash
pip install faster-whisper[cuda]
```

The app will automatically use GPU if available.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Start/Stop recording |
| `q` | Quit app |

## Requirements

- **OS**: Windows 10+ (for WASAPI loopback)
- **Python**: 3.11+ (only needed to run from source or build the exe)
- **Audio**: Working microphone and speakers/headphones
- **Disk**: ~100MB for model + transcripts

## License

MIT — do whatever you want with it.

## Contributing

Contributions welcome! Open an issue or submit a PR.

## Acknowledgments

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2 Whisper implementation
- [Textual](https://github.com/Textualize/textual) — Python TUI framework
- [sounddevice](https://github.com/spatialaudio/python-sounddevice) — Audio capture
