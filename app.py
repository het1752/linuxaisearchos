import os
import re
import time
import difflib
import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Page configuration
st.set_page_config(
    page_title="Linux Localhost AI Search", 
    layout="wide"
)

# Custom SVG Vector Icons (No standard emojis)
SVG_SEARCH = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 6px;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
SVG_FOLDER = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e0af68" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>'
SVG_FILE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7aa2f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px;"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>'
SVG_TERMINAL = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 6px;"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>'
SVG_CPU = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 6px;"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>'

# Load API key from local .env
load_dotenv()
HF_TOKEN = os.getenv("token")
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

SYSTEM_PROMPT = """You are a Linux OS deep-search query analyzer.
Analyze the user prompt in any language (English, Hindi, Hinglish, Gujarati, etc.).

Task:
1. Identify the core subject, title, or filename the user wants to locate.
2. Remove all generic query filler words:
   (where is, kaha hai, batao, dhundh, please, find, search, show me, song, gaana, music, video, file, folder, directory).
3. If numbers are spoken, provide both numeral and word (e.g. 'char' -> 'char 4', '01' -> '01 1').
4. Do NOT output generic terms like 'file' or 'system' as tokens.

Output strictly in this format:
ANALYSIS: <brief summary of user intent>
TOKENS: <space separated core keywords only>
"""

def extract_tokens_with_chain(client: InferenceClient, user_query: str):
    """Executes AI extraction and returns clean reasoning output."""
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        max_tokens=80,
        temperature=0.0
    )
    raw_output = response.choices[0].message.content.strip()

    analysis_match = re.search(r"ANALYSIS:\s*(.+)", raw_output, re.IGNORECASE)
    tokens_match = re.search(r"TOKENS:\s*(.+)", raw_output, re.IGNORECASE)

    analysis_text = analysis_match.group(1).strip() if analysis_match else "Target identification complete."
    tokens_raw = tokens_match.group(1).strip() if tokens_match else raw_output

    dirty_tokens = [t.lower() for t in re.split(r"[^\w]+", tokens_raw) if len(t) > 1]
    banned = {"file", "folder", "system", "directory", "kaha", "hai", "song"}
    clean_tokens = [t for t in dirty_tokens if t not in banned]

    if not clean_tokens:
        clean_tokens = [t.lower() for t in re.split(r"[^\w]+", user_query) if len(t) > 1 and t not in banned]

    return raw_output, analysis_text, list(dict.fromkeys(clean_tokens))

def is_matching(name: str, tokens: list) -> bool:
    """Token matching ensuring deep files match reliably."""
    name_clean = re.sub(r"[^\w\s]", " ", name.lower())
    compact = name_clean.replace(" ", "")
    words = name_clean.split()

    score = 0
    for tok in tokens:
        if tok in compact:
            score += 1
            continue
        for w in words:
            if len(tok) >= 3 and len(w) >= 3:
                if difflib.SequenceMatcher(None, tok, w).ratio() >= 0.75:
                    score += 1
                    break

    threshold = 2 if len(tokens) >= 2 else 1
    return score >= threshold

def live_deep_scan(base_dir: str, tokens: list, log_placeholder, max_matches=300):
    """Traverses complete filesystem trees without artificial depth breaks."""
    virtual_bypass = {"proc", "sys", "dev"}
    matches = []
    total_dirs_scanned = 0
    total_files_scanned = 0

    for root, dirs, files in os.walk(base_dir, topdown=True, followlinks=False):
        dirs[:] = [d for d in dirs if d not in virtual_bypass]
        total_dirs_scanned += 1
        total_files_scanned += len(files)

        if total_dirs_scanned % 15 == 0:
            log_placeholder.markdown(
                f"```bash\n"
                f"[SCAN] Traversing: {root}\n"
                f"[INFO] Visited Folders: {total_dirs_scanned} | Checked Files: {total_files_scanned} | Matches: {len(matches)}\n"
                f"```"
            )

        for d in dirs:
            if is_matching(d, tokens):
                full_path = os.path.join(root, d)
                matches.append(("DIR", full_path))

        for f in files:
            if is_matching(f, tokens):
                full_path = os.path.join(root, f)
                matches.append(("FILE", full_path))

        if len(matches) >= max_matches:
            break

    return matches, total_dirs_scanned, total_files_scanned

# Header Section
st.markdown(f"<h2>{SVG_SEARCH} Linux Deep AI File & Directory Search</h2>", unsafe_allow_html=True)
st.caption("Localhost Binding: 127.0.0.1 | Full Filesystem Scope | Vector UI")

if not HF_TOKEN:
    st.error("Missing Hugging Face token in .env. Add token=your_key to proceed.")
    st.stop()

client = InferenceClient(api_key=HF_TOKEN, provider="auto")

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

with st.form("search_form", clear_on_submit=False):
    query_input = st.text_input("Enter your request:", placeholder="search anything in you system")
    submitted = st.form_submit_button("Search OS", type="primary")

if submitted and query_input.strip():
    st.session_state.last_query = query_input
    start_time = time.time()

    # Step 1: AI Analysis Section
    st.markdown(f"### {SVG_CPU} 1. AI Reasoning & Extraction", unsafe_allow_html=True)
    with st.expander("AI Processing Details", expanded=True):
        try:
            raw_ai, analysis, target_tokens = extract_tokens_with_chain(client, query_input)
            st.markdown(f"**User Prompt:** `{query_input}`")
            st.markdown(f"**Interpretation:** {analysis}")
            st.markdown(f"**Extracted Tokens:** `{target_tokens}`")
            st.markdown("**Raw Model Response:**")
            st.code(raw_ai, language="text")
        except Exception as e:
            st.error(f"Hugging Face API Error: {e}")
            target_tokens = [t.lower() for t in re.split(r"[^\w]+", query_input) if len(t) > 1]
            st.warning(f"Fallback extracted tokens: `{target_tokens}`")

    # Step 2: Live Filesystem Traversal Monitor
    st.markdown(f"### {SVG_TERMINAL} 2. Real-Time Traversal Engine", unsafe_allow_html=True)
    monitor_box = st.empty()
    
    home_path = os.path.expanduser("~")
    monitor_box.markdown(f"```bash\n[INIT] Starting traversal at user root: {home_path}\n```")
    
    matches, total_d, total_f = live_deep_scan(home_path, target_tokens, monitor_box)

    if not matches:
        monitor_box.markdown(f"```bash\n[EXPAND] Expanding scan to root filesystem (/)\n```")
        root_matches, rd, rf = live_deep_scan("/", target_tokens, monitor_box)
        matches.extend(root_matches)
        total_d += rd
        total_f += rf

    total_time = round(time.time() - start_time, 2)
    monitor_box.markdown(
        f"```bash\n"
        f"[DONE] Search completed.\n"
        f"[STATS] Directories: {total_d} | Files: {total_f} | Elapsed: {total_time}s\n"
        f"[RESULTS] Found {len(matches)} item(s)\n"
        f"```"
    )

    # Step 3: Results Display with Inline SVG Badges
    st.markdown(f"### 3. Matches Found ({len(matches)})")
    if matches:
        for tag, path in matches:
            if tag == "DIR":
                st.markdown(
                    f"<div style='margin-bottom: 6px; font-family: monospace; font-size: 14px;'>"
                    f"{SVG_FOLDER} <span style='background-color: #2b2a1d; color: #e0af68; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-right: 6px;'>DIR</span> {path}"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='margin-bottom: 6px; font-family: monospace; font-size: 14px;'>"
                    f"{SVG_FILE} <span style='background-color: #1a233a; color: #7aa2f7; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-right: 6px;'>FILE</span> {path}"
                    f"</div>", 
                    unsafe_allow_html=True
                )
    else:
        st.warning(f"No files or folders matched tokens `{target_tokens}` across inspected paths.")
