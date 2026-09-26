# Linux AI Search OS

A private, **localhost-only** Linux file and folder search assistant built with Streamlit. It turns natural-language queries — in English, Hindi, Hinglish, Gujarati, and more — into filesystem search tokens using a Hugging Face LLM, then performs a live, real-time traversal of your filesystem with fuzzy matching to find the files and folders you're looking for.

> ⚠️ This tool walks your entire home directory (and optionally `/`) on every search. It is intended to run **locally on your own machine** and should not be exposed to the network.

---

## Features

- **Natural language queries** — ask for what you want in plain language instead of crafting exact filenames or paths.
- **Multilingual support** — the AI query analyzer is prompted to handle English, Hindi, Hinglish, Gujarati, and similar mixed-language input.
- **AI-powered token extraction** — a Hugging Face-hosted LLM (`meta-llama/Llama-3.1-8B-Instruct` by default) parses your prompt, strips filler words (e.g. "where is", "kaha hai", "find", "song"), and returns clean search keywords.
- **Fuzzy matching engine** — combines substring matching with `difflib` similarity scoring so close-but-not-exact filenames still match.
- **Live traversal monitor** — a real-time log panel shows which directories are being scanned, how many files/folders have been checked, and how many matches have been found so far.
- **Progressive scope expansion** — search starts in your home directory (`~`) and automatically expands to scan the root filesystem (`/`) if nothing is found.
- **Graceful fallback** — if the Hugging Face API call fails, the app falls back to simple keyword extraction from your raw query so search still works.
- **Local-first UI** — built entirely on Streamlit, with custom inline SVG icons (no external emoji/image dependencies).

---

## How it works

1. **You type a query** — e.g. *"find my resume pdf"* or *"gaana file kaha hai"*.
2. **AI reasoning step** — the query is sent to a Hugging Face inference endpoint with a system prompt that instructs the model to identify the core subject and return a short `ANALYSIS` plus a list of `TOKENS`.
3. **Token cleanup** — generic/noise words (`file`, `folder`, `system`, `song`, etc.) are filtered out of the extracted tokens.
4. **Filesystem traversal** — the app walks the directory tree with `os.walk`, skipping virtual/system directories (`proc`, `sys`, `dev`), and checks each file/folder name against the tokens using exact substring and fuzzy (`difflib`) matching.
5. **Live results** — matches are streamed into the UI as they're found, tagged as `DIR` or `FILE`, along with scan statistics (folders visited, files checked, elapsed time).

---

## Requirements

- Python 3.9+
- A [Hugging Face](https://huggingface.co/) account and API token with inference access
- Linux (the app is designed around Linux filesystem conventions, e.g. `~` expansion and `/proc`, `/sys`, `/dev` exclusions)

All Python dependencies are listed in [`requirements.txt`](./requirements.txt), including:

- `streamlit` — the web UI framework
- `huggingface_hub` — Hugging Face inference client
- `python-dotenv` — loads your API token from a local `.env` file
- plus their supporting dependencies (`pandas`, `numpy`, `requests`, `pydeck`, etc.)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/het1752/linuxaisearchos.git
cd linuxaisearchos

# (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

The app reads your Hugging Face API token from a local `.env` file. Create one in the project root:

```bash
echo "token=hf_your_huggingface_api_token_here" > .env
```

> The environment variable **must** be named `token` (lowercase) — that's the exact key the app looks up via `os.getenv("token")`.

You can get a Hugging Face token from your [Hugging Face settings page](https://huggingface.co/settings/tokens).

By default the app uses the `meta-llama/Llama-3.1-8B-Instruct` model via Hugging Face's inference API. To use a different model, edit the `MODEL_ID` constant near the top of `app.py`.

---

## Usage

Run the app with Streamlit:

```bash
streamlit run app.py
```

By default, Streamlit will serve the app on `http://127.0.0.1:8501` (or the next available port). Since the app scans your local filesystem, it's meant to be used only from the machine it's running on — do not expose this port publicly.

Once the app is open:

1. Enter a natural-language search request (e.g. *"find that invoice pdf from last month"*).
2. Click **Search OS**.
3. Watch the **AI Reasoning & Extraction** panel to see how your query was interpreted and which tokens were extracted.
4. Watch the **Real-Time Traversal Engine** panel for live scan progress.
5. Review the list of matched files and folders under **Matches Found**.

---

## Project structure

```
linuxaisearchos/
├── .streamlit/          # Streamlit configuration
├── app.py               # Main application (UI, AI query parsing, filesystem scan)
├── requirements.txt     # Python dependencies
└── .gitignore
```

---

## Notes & limitations

- **Performance**: scanning an entire home directory (or the whole root filesystem) can be slow on large disks or systems with many files. The scan caps at 300 matches (`max_matches`) to avoid unbounded runs.
- **Privacy**: your queries are sent to a Hugging Face inference endpoint for token extraction. File and folder *names* found on your machine are not sent externally — only your typed query is.
- **Scope**: virtual/pseudo filesystems (`/proc`, `/sys`, `/dev`) are explicitly excluded from traversal to avoid errors and irrelevant noise.
- **Symlinks** are not followed during traversal (`followlinks=False`), which helps avoid infinite loops.

---

## Contributing

Issues and pull requests are welcome. If you'd like to add support for additional platforms, models, or search strategies, feel free to open a discussion first.

## License

No license file is currently included in this repository. Add a `LICENSE` file to clarify usage terms, or contact the repository owner for permissions.
