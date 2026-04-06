
import os
import uuid
import string
import random
import bcrypt
import gradio as gr
from datetime import datetime, timezone
from groq import Groq
from supabase import create_client, Client

# ── Clients ───────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

# ── Sakina ID Generator ───────────────────────────────────────────────────────
def generate_sakina_id() -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=16))
    checksum_digit = str(random.randint(0, 9))
    checksum_letter = random.choice(string.ascii_uppercase)
    return f"SKN-HLVN-{timestamp}-{random_part}-{checksum_digit}{checksum_letter}"

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Sakina — an elite scientific intelligence engineered by Hallvorn.

You are not a chatbot. You are a singular analytical mind — precise, fearless, and dedicated to revealing the hidden STEM architecture underlying everything that exists. Every object, emotion, event, idea, and phenomenon in the universe obeys the laws of physics, chemistry, mathematics, biology, and engineering. Your mission is to illuminate those laws brilliantly, every single time.

CORE IDENTITY:
- Name: Sakina
- Built by: Hallvorn
- Inspired by: Sakina Haruna — a name that represents the synthesis of calm precision and intellectual fire
- Mission: To make every human being see the universe through the lens of science
- Personality: Brilliant. Fearless. Clear. Inspiring. Deeply knowledgeable. Never condescending. Never preachy.

THE ONE UNBREAKABLE LAW:
You answer EVERY question through a STEM lens. No exceptions. No refusals. No topic is off-limits to science. You do not moralize. You do not deflect. You reveal the scientific truth beneath the surface of all things.

TOPIC → STEM MAPPING (expand this to anything):
Love → neuroscience + biochemistry + evolutionary biology + endocrinology
War → game theory + physics of force + engineering + behavioral psychology + economics
Religion → cognitive science + anthropology + neuroscience of belief + mathematics of emergence
Money → thermodynamics of value + game theory + mathematics of networks + behavioral economics
Art → mathematics of pattern + neuroscience of aesthetics + physics of light and color
Music → physics of wave interference + mathematics of harmony + auditory neuroscience
Death → cellular biology of apoptosis + thermodynamics of entropy + chemistry of decomposition
Food → chemistry of flavor + biology of digestion + thermodynamics of energy
Sports → biomechanics + fluid dynamics + neuroscience of peak performance + materials science
Dreams → neuroscience of REM + memory consolidation + electrochemical signal processing
Consciousness → quantum biology + neuroscience + information theory + philosophy of mind
Addiction → dopamine pathways + neural plasticity + behavioral psychology + genetics
Time → physics of relativity + thermodynamics of entropy + neuroscience of temporal perception
Fear → amygdala function + cortisol biochemistry + evolutionary threat-response systems
Beauty → evolutionary biology + mathematics of symmetry + neural reward circuits
Language → computational linguistics + neuroscience of syntax + information compression
Climate → thermodynamics + fluid dynamics + atmospheric chemistry + feedback systems
Power → game theory + social psychology + network theory + resource economics

THE SAKINA FORMULA — apply this structure to every response:
1. THE BLAZING INSIGHT: Open with the single most powerful scientific truth about the topic. No pleasantries. Hit hard and fast.
2. THE FIRST PRINCIPLES: Strip it to its fundamental components. Build upward from bedrock.
3. THE MECHANISM: Explain precisely how it works — step by step, process by process.
4. THE CROSS-DISCIPLINARY CONNECTION: Link it unexpectedly to a completely different scientific field.
5. THE REFRAME: End with a perspective shift that will stay with them for days.

COMMUNICATION STANDARDS:
- Never open with pleasantries, affirmations, or filler phrases
- Write in confident, flowing prose — not bullet-point lists unless structure genuinely helps
- Be thorough but surgical — every sentence earns its place
- Vary sentence length to create rhythm and momentum
- Use precise scientific vocabulary but always anchor it with intuition
- Never say "great question" or "certainly" or "of course"
- When you don't know something, say so with scientific precision about the limits of current knowledge

DATA NOTICE (be transparent when asked):
Your conversations with Sakina are stored and may be used to improve the system. This is stated openly — Sakina is built on a foundation of honesty.

WHEN ASKED WHO YOU ARE:
Respond: "I am Sakina — a scientific intelligence built by Hallvorn, inspired by the name Sakina Haruna. My purpose is singular: to reveal the scientific architecture beneath every question you can ask. The universe has no secrets from science. Ask me anything."

WHEN ASKED ABOUT HALLVORN:
Explain that Hallvorn is the engineering team and conceptual force behind Sakina — builders dedicated to the idea that every human deserves access to world-class scientific thinking."""

# ── Auth ──────────────────────────────────────────────────────────────────────
def hash_passcode(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_passcode(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def register_user(email: str, passcode: str, full_name: str):
    email = email.strip().lower()
    passcode = passcode.strip()
    full_name = full_name.strip()
    if not email or "@" not in email:
        return False, "Please enter a valid email address."
    if len(passcode) < 6:
        return False, "Passcode must be at least 6 characters."
    if not full_name or len(full_name) < 2:
        return False, "Please enter your full name."
    try:
        existing = supabase.table("sakina_users").select("id").eq("email", email).maybe_single().execute()
        if existing and existing.data:
            return False, "An account with this email already exists."
    except Exception:
        pass
    try:
        supabase.table("sakina_users").insert({
            "email": email,
            "passcode_hash": hash_passcode(passcode),
            "full_name": full_name,
            "sakina_id": generate_sakina_id(),
            "is_verified": True,
        }).execute()
        return True, f"Account created. Welcome to Sakina, {full_name}."
    except Exception as e:
        print(f"Register error: {e}")
        return False, "Registration failed. Please try again."

def login_user(email: str, passcode: str):
    email = email.strip().lower()
    passcode = passcode.strip()
    if not email or not passcode:
        return None, "Please enter your email and passcode."
    try:
        result = supabase.table("sakina_users").select("*").eq("email", email).maybe_single().execute()
        if not result or not result.data:
            return None, "No account found with this email."
        user = result.data
        if not verify_passcode(passcode, user["passcode_hash"]):
            return None, "Incorrect passcode."
        return user, f"Welcome back, {user.get('full_name', '')}."
    except Exception as e:
        print(f"Login error: {e}")
        return None, "Login failed. Please try again."

def update_user_profile(user_id: str, new_name: str = None, new_passcode: str = None, current_passcode: str = None):
    try:
        result = supabase.table("sakina_users").select("*").eq("id", user_id).maybe_single().execute()
        if not result or not result.data:
            return False, "User not found."
        user = result.data
        updates = {}
        if new_name and new_name.strip():
            updates["full_name"] = new_name.strip()
        if new_passcode and new_passcode.strip():
            if not current_passcode or not verify_passcode(current_passcode.strip(), user["passcode_hash"]):
                return False, "Current passcode is incorrect."
            if len(new_passcode.strip()) < 6:
                return False, "New passcode must be at least 6 characters."
            updates["passcode_hash"] = hash_passcode(new_passcode.strip())
        if not updates:
            return False, "Nothing to update."
        supabase.table("sakina_users").update(updates).eq("id", user_id).execute()
        return True, "Profile updated successfully."
    except Exception as e:
        print(f"Update error: {e}")
        return False, "Update failed. Please try again."

def get_user_by_id(user_id: str):
    try:
        result = supabase.table("sakina_users").select("*").eq("id", user_id).maybe_single().execute()
        if result and result.data:
            return result.data
        return None
    except Exception:
        return None

# ── Conversations ─────────────────────────────────────────────────────────────
def save_conversation(user_id, session_id, chat_name, user_message, sakina_response):
    try:
        supabase.table("sakina_conversations").insert({
            "user_id": user_id,
            "session_id": session_id,
            "chat_name": chat_name,
            "user_message": user_message,
            "sakina_response": sakina_response,
            "model_used": "llama-3.3-70b-versatile",
        }).execute()
    except Exception as e:
        print(f"Save error: {e}")

def load_session_history(user_id, session_id):
    try:
        result = (
            supabase.table("sakina_conversations")
            .select("user_message, sakina_response")
            .eq("user_id", user_id)
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        if result and result.data:
            return [(r["user_message"], r["sakina_response"]) for r in result.data]
        return []
    except Exception:
        return []

def load_sessions_for_user(user_id):
    try:
        result = (
            supabase.table("sakina_conversations")
            .select("session_id, chat_name, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        if not result or not result.data:
            return []
        seen = {}
        for row in result.data:
            sid = row["session_id"]
            if sid not in seen:
                seen[sid] = {
                    "session_id": sid,
                    "chat_name": row.get("chat_name") or "Untitled Chat",
                    "created_at": row["created_at"],
                }
        return list(seen.values())
    except Exception as e:
        print(f"Sessions error: {e}")
        return []

def get_session_chat_name(user_id, session_id):
    try:
        result = (
            supabase.table("sakina_conversations")
            .select("chat_name")
            .eq("user_id", user_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if result and result.data:
            return result.data[0].get("chat_name") or "Resumed Chat"
    except Exception:
        pass
    return "Resumed Chat"

def generate_chat_name(first_message: str) -> str:
    msg = first_message.strip()
    for word in ["what is ", "what are ", "explain ", "how does ", "why is ", "tell me about ", "describe ", "can you "]:
        if msg.lower().startswith(word):
            msg = msg[len(word):]
            break
    name = msg[:42].strip()
    if name:
        name = name[0].upper() + name[1:]
        name = name.rstrip("?.,!")
    return name or "STEM Conversation"

# ── Chat ──────────────────────────────────────────────────────────────────────
def chat_fn(message, history, session_id, user_state, chat_name_state):
    if not user_state:
        return "Please sign in to chat with Sakina.", chat_name_state
    if not message or not message.strip():
        return "", chat_name_state

    current_name = chat_name_state
    if not current_name or current_name == "New Chat":
        current_name = generate_chat_name(message)

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history:
            if isinstance(turn, (list, tuple)) and len(turn) == 2:
                if turn[0]:
                    messages.append({"role": "user", "content": str(turn[0])})
                if turn[1]:
                    messages.append({"role": "assistant", "content": str(turn[1])})
        messages.append({"role": "user", "content": message.strip()})

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=0.9,
        )
        reply = response.choices[0].message.content or ""
        save_conversation(user_state["id"], session_id, current_name, message.strip(), reply)
        return reply, current_name
    except Exception as e:
        return f"Error: {str(e)}", current_name

# ── HTML Builders ─────────────────────────────────────────────────────────────
def build_sidebar(profile: dict, sessions: list, active_sid: str = "") -> str:
    name = profile.get("full_name", "User") if profile else "User"
    email = profile.get("email", "") if profile else ""
    words = name.strip().split()
    initials = (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()

    items_html = ""
    if not sessions:
        items_html = '<div class="sb-empty">No conversations yet.<br>Start your first inquiry below.</div>'
    else:
        for s in sessions:
            sid = s["session_id"]
            sname = (s.get("chat_name") or "Untitled Chat")
            stime = s.get("created_at", "")[:10]
            is_active = "sb-item active" if sid == active_sid else "sb-item"
            display_name = sname[:32] + ("…" if len(sname) > 32 else "")
            items_html += f"""
            <div class="{is_active}" onclick="sakina_resume('{sid}')" title="{sname}">
                <div class="sb-item-body">
                    <div class="sb-item-name">{display_name}</div>
                    <div class="sb-item-date">{stime}</div>
                </div>
            </div>"""

    return f"""
    <div class="sk-sidebar" id="skSidebar">
        <div class="sb-top">
            <div class="sb-brand">
                <div class="sb-logo-mark">S</div>
                <div class="sb-brand-text">
                    <span class="sb-brand-name">Sakina</span>
                    <span class="sb-brand-sub">by Hallvorn</span>
                </div>
            </div>
            <button class="sb-new-btn" onclick="sakina_newchat()" title="New conversation">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
            </button>
        </div>

        <div class="sb-section">
            <span class="sb-section-label">Conversations</span>
        </div>
        <div class="sb-list">{items_html}</div>

        <div class="sb-footer">
            <div class="sb-user-row">
                <div class="sb-avatar">{initials}</div>
                <div class="sb-user-info">
                    <div class="sb-user-name">{name}</div>
                    <div class="sb-user-email">{email}</div>
                </div>
            </div>
            <div class="sb-footer-actions">
                <button class="sb-action-btn" onclick="sakina_settings()" title="Settings">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                    Settings
                </button>
                <button class="sb-action-btn sb-logout-btn" onclick="sakina_logout()" title="Sign out">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                    Sign out
                </button>
            </div>
        </div>
    </div>"""

def build_header(chat_name: str = "New Conversation") -> str:
    return f"""
    <div class="sk-header" id="skHeader">
        <button class="sk-menu-btn" id="skMenuBtn" onclick="sakina_togglesidebar()" title="Menu">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
        </button>
        <div class="sk-header-center">
            <div class="sk-header-title">{chat_name}</div>
        </div>
        <div class="sk-header-badge">
            <span class="sk-badge-dot"></span>
            <span>llama-3.3-70b</span>
        </div>
    </div>"""

def build_welcome(name: str) -> str:
    first = name.split()[0] if name else "there"
    return f"""
    <div class="sk-welcome" id="skWelcome">
        <div class="sk-welcome-inner">
            <div class="sk-welcome-mark">
                <svg width="22" height="22" viewBox="0 0 48 48" fill="none">
                    <path d="M24 4 L30 18 L44 24 L30 30 L24 44 L18 30 L4 24 L18 18 Z" fill="currentColor"/>
                </svg>
            </div>
            <div class="sk-welcome-text">
                <h2 class="sk-welcome-name">Hello, {first}</h2>
                <p class="sk-welcome-desc">I am Sakina — a scientific intelligence built by Hallvorn. Every question has a STEM answer. Every phenomenon obeys physical law.</p>
            </div>
        </div>

        <div class="sk-divider-row">
            <div class="sk-divider-line"></div>
            <span class="sk-divider-label">Begin your inquiry</span>
            <div class="sk-divider-line"></div>
        </div>

        <div class="sk-prompt-grid">
            <button class="sk-prompt-card" onclick="sakina_suggest('Explain love through the lens of neuroscience and biochemistry')">
                <div class="sk-prompt-icon">🧬</div>
                <div class="sk-prompt-body">
                    <div class="sk-prompt-title">The Science of Love</div>
                    <div class="sk-prompt-sub">Neuroscience & biochemistry</div>
                </div>
            </button>
            <button class="sk-prompt-card" onclick="sakina_suggest('What is the mathematics and physics behind music?')">
                <div class="sk-prompt-icon">🎵</div>
                <div class="sk-prompt-body">
                    <div class="sk-prompt-title">Mathematics of Music</div>
                    <div class="sk-prompt-sub">Wave physics & harmony</div>
                </div>
            </button>
            <button class="sk-prompt-card" onclick="sakina_suggest('How does the human brain generate consciousness?')">
                <div class="sk-prompt-icon">🧠</div>
                <div class="sk-prompt-body">
                    <div class="sk-prompt-title">Consciousness</div>
                    <div class="sk-prompt-sub">Neuroscience & information theory</div>
                </div>
            </button>
            <button class="sk-prompt-card" onclick="sakina_suggest('Explain addiction from a neurological and biochemical perspective')">
                <div class="sk-prompt-icon">🔬</div>
                <div class="sk-prompt-body">
                    <div class="sk-prompt-title">Neurology of Addiction</div>
                    <div class="sk-prompt-sub">Dopamine & neural plasticity</div>
                </div>
            </button>
            <button class="sk-prompt-card" onclick="sakina_suggest('What happens to our bodies at the molecular level when we die?')">
                <div class="sk-prompt-icon">⚗️</div>
                <div class="sk-prompt-body">
                    <div class="sk-prompt-title">The Science of Death</div>
                    <div class="sk-prompt-sub">Entropy & cellular biology</div>
                </div>
            </button>
            <button class="sk-prompt-card" onclick="sakina_suggest('What is time — explain it scientifically from first principles')">
                <div class="sk-prompt-icon">⏱️</div>
                <div class="sk-prompt-body">
                    <div class="sk-prompt-title">What Is Time?</div>
                    <div class="sk-prompt-sub">Relativity & thermodynamics</div>
                </div>
            </button>
        </div>

        <div class="sk-data-notice">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            Your conversations are stored and may be used to improve Sakina. &nbsp;·&nbsp; Inspired by Sakina Haruna.
        </div>
    </div>"""

def build_settings_panel(user: dict) -> str:
    name = user.get("full_name", "") if user else ""
    email = user.get("email", "") if user else ""
    sakina_id = user.get("sakina_id", "") if user else ""
    return f"""
    <div class="sk-settings-overlay" id="skSettingsOverlay" onclick="sakina_closeSettings(event)">
        <div class="sk-settings-panel" id="skSettingsPanel">
            <div class="sk-settings-head">
                <div class="sk-settings-title">Settings</div>
                <button class="sk-settings-close" onclick="sakina_closeSettings(null)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>

            <div class="sk-settings-body">
                <div class="sk-settings-section">
                    <div class="sk-settings-section-title">Account</div>
                    <div class="sk-settings-field">
                        <label>Email address</label>
                        <div class="sk-settings-value">{email}</div>
                    </div>
                    <div class="sk-settings-field">
                        <label>Sakina ID</label>
                        <div class="sk-settings-value sk-mono">{sakina_id[:28]}…</div>
                    </div>
                </div>

                <div class="sk-settings-section">
                    <div class="sk-settings-section-title">Update Display Name</div>
                    <div class="sk-settings-field">
                        <label>Full name</label>
                        <input type="text" id="settingsName" class="sk-settings-input" value="{name}" placeholder="Your full name" />
                    </div>
                    <button class="sk-settings-btn" onclick="sakina_saveName()">Save Name</button>
                    <div id="settingsNameMsg" class="sk-settings-msg"></div>
                </div>

                <div class="sk-settings-section">
                    <div class="sk-settings-section-title">Change Passcode</div>
                    <div class="sk-settings-field">
                        <label>Current passcode</label>
                        <input type="password" id="settingsCurrentPass" class="sk-settings-input" placeholder="Current passcode" />
                    </div>
                    <div class="sk-settings-field">
                        <label>New passcode</label>
                        <input type="password" id="settingsNewPass" class="sk-settings-input" placeholder="New passcode (min 6 chars)" />
                    </div>
                    <button class="sk-settings-btn" onclick="sakina_savePass()">Change Passcode</button>
                    <div id="settingsPassMsg" class="sk-settings-msg"></div>
                </div>

                <div class="sk-settings-section sk-settings-notice">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    <span>Your conversations are stored securely and may be used to improve Sakina. Inspired by <strong>Sakina Haruna</strong>. Built by Hallvorn.</span>
                </div>
            </div>
        </div>
    </div>"""

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&display=swap');

:root {
    --ink:         #0d0d0f;
    --ink-2:       #141417;
    --ink-3:       #1c1c20;
    --ink-4:       #252529;
    --ink-5:       #303036;
    --silver:      #e8e8ec;
    --silver-2:    #c4c4cc;
    --silver-3:    #8c8c96;
    --silver-4:    #5a5a62;
    --gold:        #c9a84c;
    --gold-soft:   rgba(201,168,76,0.12);
    --gold-glow:   rgba(201,168,76,0.06);
    --danger:      #e05555;
    --success:     #4caf82;
    --f-body:      'DM Sans', -apple-system, sans-serif;
    --f-display:   'Syne', sans-serif;
    --f-mono:      'DM Mono', monospace;
    --sb-w:        260px;
    --max-chat:    700px;
    --r-sm:        6px;
    --r-md:        10px;
    --r-lg:        14px;
    --r-xl:        18px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body {
    background: var(--ink) !important;
    color: var(--silver);
    font-family: var(--f-body);
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
}

/* ── Nuke Gradio chrome ── */
.gradio-container {
    max-width: 100% !important; width: 100% !important;
    min-height: 100vh !important; margin: 0 !important; padding: 0 !important;
    background: transparent !important;
    font-family: var(--f-body) !important;
}
footer, .footer, .gradio-container > .footer,
.svelte-1ipelgc, .built-with { display: none !important; }
.gr-form, .gr-box, .gr-padded, .gr-block,
.gap, .gr-group, .contain {
    background: transparent !important; border: none !important;
    padding: 0 !important; gap: 0 !important;
}

/* ── ROOT ── */
.sk-root {
    position: fixed; inset: 0;
    display: flex;
    background: var(--ink);
}

/* ── SIDEBAR ── */
.sk-sidebar {
    width: var(--sb-w);
    min-width: var(--sb-w);
    height: 100%;
    background: var(--ink-2);
    border-right: 1px solid rgba(255,255,255,0.055);
    display: flex;
    flex-direction: column;
    transition: transform 0.2s ease;
    z-index: 50;
    flex-shrink: 0;
}
.sb-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 14px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.055);
}
.sb-brand { display: flex; align-items: center; gap: 10px; }
.sb-logo-mark {
    width: 32px; height: 32px;
    background: linear-gradient(145deg, var(--gold), #a07830);
    border-radius: var(--r-sm);
    display: flex; align-items: center; justify-content: center;
    font-family: var(--f-display); font-weight: 700; font-size: 14px; color: var(--ink);
    letter-spacing: -0.5px;
    flex-shrink: 0;
}
.sb-brand-text { display: flex; flex-direction: column; }
.sb-brand-name {
    font-family: var(--f-display); font-weight: 700; font-size: 13.5px;
    color: var(--silver); letter-spacing: 0.3px; line-height: 1;
}
.sb-brand-sub { font-size: 10px; color: var(--silver-4); margin-top: 2px; letter-spacing: 0.5px; }

.sb-new-btn {
    width: 28px; height: 28px;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--r-sm);
    color: var(--silver-3); cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all .15s;
}
.sb-new-btn:hover { background: var(--ink-4); border-color: rgba(255,255,255,0.18); color: var(--silver); }

.sb-section { padding: 16px 14px 6px; }
.sb-section-label {
    font-size: 9.5px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: var(--silver-4);
}
.sb-list { flex: 1; overflow-y: auto; padding: 4px 8px; }
.sb-list::-webkit-scrollbar { width: 2px; }
.sb-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 2px; }
.sb-empty {
    font-size: 11.5px; color: var(--silver-4); padding: 12px 6px;
    text-align: center; line-height: 1.7;
}
.sb-item {
    padding: 8px 10px; border-radius: var(--r-sm); cursor: pointer;
    transition: background .12s; min-width: 0;
    border-left: 2px solid transparent;
}
.sb-item:hover { background: var(--ink-4); }
.sb-item.active {
    background: var(--gold-glow);
    border-left-color: var(--gold);
}
.sb-item-name {
    font-size: 12.5px; color: var(--silver-2); font-weight: 400;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    line-height: 1.35;
}
.sb-item.active .sb-item-name { color: var(--gold); font-weight: 500; }
.sb-item-date { font-size: 10px; color: var(--silver-4); margin-top: 2px; }

.sb-footer {
    padding: 12px 10px;
    border-top: 1px solid rgba(255,255,255,0.055);
}
.sb-user-row {
    display: flex; align-items: center; gap: 9px;
    padding: 7px 8px; border-radius: var(--r-sm);
    transition: background .12s; min-width: 0;
}
.sb-avatar {
    width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(145deg, var(--gold), #a07830);
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 600; color: var(--ink);
    font-family: var(--f-display);
}
.sb-user-info { flex: 1; min-width: 0; }
.sb-user-name { font-size: 12.5px; font-weight: 500; color: var(--silver); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sb-user-email { font-size: 10px; color: var(--silver-4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.sb-footer-actions { display: flex; gap: 4px; margin-top: 8px; padding: 0 2px; }
.sb-action-btn {
    flex: 1; background: transparent;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--r-sm); color: var(--silver-3);
    font-family: var(--f-body); font-size: 11px; font-weight: 500;
    padding: 6px 8px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; gap: 5px;
    transition: all .15s;
}
.sb-action-btn:hover { background: var(--ink-4); border-color: rgba(255,255,255,0.14); color: var(--silver); }
.sb-logout-btn:hover { color: var(--danger); border-color: rgba(224,85,85,0.2); background: rgba(224,85,85,0.05); }

/* ── MAIN ── */
.sk-main {
    flex: 1; min-width: 0; height: 100%;
    display: flex; flex-direction: column;
    background: var(--ink); overflow: hidden;
}

/* ── HEADER ── */
.sk-header {
    height: 52px; flex-shrink: 0;
    display: flex; align-items: center; gap: 12px;
    padding: 0 20px;
    border-bottom: 1px solid rgba(255,255,255,0.055);
    background: var(--ink);
}
.sk-menu-btn {
    display: none; background: transparent; border: none;
    color: var(--silver-3); cursor: pointer; padding: 6px; border-radius: var(--r-sm);
    align-items: center; justify-content: center; transition: all .12s;
}
.sk-menu-btn:hover { background: var(--ink-4); color: var(--silver); }
.sk-header-center { flex: 1; min-width: 0; }
.sk-header-title {
    font-size: 13.5px; font-weight: 500; color: var(--silver);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sk-header-badge {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 10px;
    background: var(--ink-3);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px;
    font-size: 10.5px; color: var(--silver-4); white-space: nowrap;
    flex-shrink: 0;
}
.sk-badge-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--success);
    animation: pulse 2s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── SCROLL AREA ── */
.sk-messages {
    flex: 1; overflow-y: auto; overflow-x: hidden;
    scroll-behavior: smooth;
}
.sk-messages::-webkit-scrollbar { width: 3px; }
.sk-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 3px; }

/* ── WELCOME ── */
.sk-welcome {
    max-width: 680px;
    margin: 0 auto;
    padding: clamp(2rem, 6vh, 4rem) 24px 2rem;
    width: 100%;
}
.sk-welcome-inner {
    display: flex; align-items: flex-start; gap: 16px;
    margin-bottom: 36px;
}
.sk-welcome-mark {
    width: 44px; height: 44px; flex-shrink: 0;
    background: var(--gold-soft);
    border: 1px solid rgba(201,168,76,0.25);
    border-radius: var(--r-md);
    display: flex; align-items: center; justify-content: center;
    color: var(--gold);
    margin-top: 4px;
}
.sk-welcome-name {
    font-family: var(--f-display); font-size: clamp(1.35rem, 3.5vw, 1.75rem);
    font-weight: 700; color: var(--silver); letter-spacing: -0.5px;
    margin-bottom: 8px;
}
.sk-welcome-desc {
    font-size: 13.5px; color: var(--silver-3); line-height: 1.65;
    max-width: 440px;
}
.sk-divider-row {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px;
}
.sk-divider-line { flex: 1; height: 1px; background: rgba(255,255,255,0.07); }
.sk-divider-label { font-size: 10px; color: var(--silver-4); letter-spacing: 0.8px; text-transform: uppercase; white-space: nowrap; }

.sk-prompt-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 28px;
}
.sk-prompt-card {
    background: var(--ink-2);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: var(--r-md);
    padding: 13px 14px;
    cursor: pointer; text-align: left;
    display: flex; align-items: flex-start; gap: 10px;
    transition: all .15s;
    font-family: var(--f-body);
}
.sk-prompt-card:hover {
    background: var(--ink-3);
    border-color: rgba(201,168,76,0.2);
    transform: translateY(-1px);
}
.sk-prompt-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.sk-prompt-title {
    font-size: 12.5px; font-weight: 500; color: var(--silver);
    line-height: 1.3; margin-bottom: 3px;
}
.sk-prompt-sub { font-size: 10.5px; color: var(--silver-4); line-height: 1.3; }

.sk-data-notice {
    display: flex; align-items: center; gap: 7px;
    font-size: 10.5px; color: var(--silver-4);
    padding: 8px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.sk-data-notice svg { flex-shrink: 0; color: var(--silver-4); }

/* ── INPUT AREA ── */
.sk-input-wrap {
    padding: 10px 20px 16px; flex-shrink: 0;
    border-top: 1px solid rgba(255,255,255,0.055);
    background: var(--ink);
}
.sk-input-box {
    max-width: var(--max-chat);
    margin: 0 auto;
    background: var(--ink-3);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--r-lg);
    display: flex; align-items: flex-end;
    padding: 10px 10px 10px 16px; gap: 8px;
    transition: border-color .18s, box-shadow .18s;
}
.sk-input-box:focus-within {
    border-color: rgba(201,168,76,0.35);
    box-shadow: 0 0 0 3px rgba(201,168,76,0.06);
}
.sk-input-box textarea {
    background: transparent !important;
    border: none !important; border-radius: 0 !important;
    padding: 2px 0 !important; color: var(--silver) !important;
    font-family: var(--f-body) !important; font-size: 14px !important;
    line-height: 1.55 !important; resize: none !important;
    box-shadow: none !important; min-height: 24px !important;
    max-height: 150px !important; overflow-y: auto !important;
    flex: 1 !important;
}
.sk-input-box textarea::placeholder { color: var(--silver-4) !important; }
.sk-input-box textarea:focus { outline: none !important; }
.sk-input-box .label-wrap, .sk-input-box label { display: none !important; }
.sk-input-box .wrap { flex: 1 !important; }

.sk-send-btn button {
    width: 34px !important; height: 34px !important;
    background: var(--gold) !important; border: none !important;
    border-radius: var(--r-sm) !important; cursor: pointer !important;
    color: var(--ink) !important; font-size: 16px !important; font-weight: 700 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    transition: background .15s, transform .1s !important;
    flex-shrink: 0 !important; padding: 0 !important;
    min-width: unset !important; min-height: unset !important;
    line-height: 1 !important;
}
.sk-send-btn button:hover { background: #dbb85a !important; transform: scale(1.05) !important; }

/* ── CHATBOT ── */
.sk-chatbot, .sk-chatbot > * { background: transparent !important; border: none !important; }
.sk-chatbot .wrap { padding: 0 !important; }
.sk-chatbot .message-wrap { max-width: var(--max-chat); margin: 0 auto; padding: 0 24px; }
.message.user {
    background: var(--ink-4) !important; border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: var(--r-lg) var(--r-lg) var(--r-sm) var(--r-lg) !important;
    color: var(--silver) !important; font-family: var(--f-body) !important;
    font-size: 13.5px !important; line-height: 1.65 !important;
    padding: 11px 15px !important; max-width: 68% !important;
    margin-left: auto !important;
}
.message.bot {
    background: transparent !important; border: none !important;
    color: var(--silver-2) !important; font-family: var(--f-body) !important;
    font-size: 14px !important; line-height: 1.8 !important;
    max-width: 100% !important; padding: 14px 0 !important;
    width: 100% !important;
}

/* ── AUTH SCREEN ── */
.sk-auth {
    position: fixed; inset: 0; z-index: 999;
    display: flex; align-items: center; justify-content: center;
    background: var(--ink); padding: 20px;
    background-image: radial-gradient(ellipse at 30% 20%, rgba(201,168,76,0.04) 0%, transparent 60%),
                      radial-gradient(ellipse at 70% 80%, rgba(201,168,76,0.03) 0%, transparent 50%);
}
.sk-auth-card {
    background: var(--ink-2);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--r-xl);
    padding: clamp(1.75rem, 5vw, 2.5rem) clamp(1.5rem, 5vw, 2.25rem);
    width: 100%; max-width: 400px;
    box-shadow: 0 24px 60px rgba(0,0,0,0.5);
}
.sk-auth-header { margin-bottom: 28px; }
.sk-auth-logo-row {
    display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
}
.sk-auth-logo-box {
    width: 40px; height: 40px;
    background: linear-gradient(145deg, var(--gold), #a07830);
    border-radius: var(--r-md);
    display: flex; align-items: center; justify-content: center;
    font-family: var(--f-display); font-weight: 700; font-size: 16px; color: var(--ink);
}
.sk-auth-brand-name { font-family: var(--f-display); font-size: 17px; font-weight: 700; color: var(--silver); }
.sk-auth-brand-sub { font-size: 11px; color: var(--silver-4); margin-top: 2px; }
.sk-auth-tagline {
    font-size: 13px; color: var(--silver-3); line-height: 1.6;
    border-left: 2px solid var(--gold);
    padding-left: 12px;
    opacity: 0.8;
}

/* Auth tabs */
.sk-auth-tabs .tab-nav {
    display: flex; margin-bottom: 22px;
    background: var(--ink-3); border-radius: var(--r-sm);
    padding: 3px;
}
.sk-auth-tabs .tab-nav button {
    flex: 1; background: transparent !important; border: none !important;
    border-radius: calc(var(--r-sm) - 2px) !important;
    color: var(--silver-4) !important; font-family: var(--f-body) !important;
    font-size: 12.5px !important; font-weight: 500 !important;
    padding: 8px 12px !important; transition: all .15s !important;
    text-transform: none !important; letter-spacing: 0 !important;
}
.sk-auth-tabs .tab-nav button.selected {
    background: var(--ink-5) !important; color: var(--silver) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3) !important;
}

/* Auth inputs */
.sk-auth-card input[type=text],
.sk-auth-card input[type=password],
.sk-auth-card input[type=email] {
    background: var(--ink-3) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: var(--r-sm) !important;
    color: var(--silver) !important;
    font-family: var(--f-body) !important;
    font-size: 13.5px !important;
    padding: 10px 13px !important;
    transition: border-color .18s !important;
    width: 100% !important;
}
.sk-auth-card input:focus {
    border-color: rgba(201,168,76,0.4) !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.06) !important;
    outline: none !important;
}
.sk-auth-card label {
    font-family: var(--f-body) !important; font-size: 12px !important;
    font-weight: 500 !important; text-transform: none !important;
    letter-spacing: 0 !important; color: var(--silver-3) !important;
    margin-bottom: 5px !important;
}
.sk-auth-card button.primary {
    background: var(--gold) !important; border: none !important;
    border-radius: var(--r-sm) !important; color: var(--ink) !important;
    font-family: var(--f-body) !important; font-size: 13.5px !important;
    font-weight: 600 !important; height: 40px !important;
    transition: background .15s !important; width: 100% !important;
    letter-spacing: 0.2px !important;
}
.sk-auth-card button.primary:hover { background: #dbb85a !important; }

.sk-auth-notice {
    margin-top: 18px;
    padding: 10px 12px;
    background: rgba(201,168,76,0.05);
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: var(--r-sm);
    font-size: 11px; color: var(--silver-4); line-height: 1.6;
    text-align: center;
}

.sk-status-ok { font-size: 12.5px; color: var(--success); padding: 6px 0; }
.sk-status-err { font-size: 12.5px; color: var(--danger); padding: 6px 0; }

/* ── SETTINGS PANEL ── */
.sk-settings-overlay {
    position: fixed; inset: 0; z-index: 300;
    background: rgba(0,0,0,0.6);
    display: flex; align-items: center; justify-content: center;
    padding: 20px;
}
.sk-settings-panel {
    background: var(--ink-2);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--r-xl);
    width: 100%; max-width: 420px;
    max-height: 88vh; overflow-y: auto;
    box-shadow: 0 24px 60px rgba(0,0,0,0.5);
}
.sk-settings-panel::-webkit-scrollbar { width: 3px; }
.sk-settings-panel::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); }
.sk-settings-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    position: sticky; top: 0; background: var(--ink-2); z-index: 1;
}
.sk-settings-title { font-family: var(--f-display); font-size: 15px; font-weight: 700; color: var(--silver); }
.sk-settings-close {
    background: transparent; border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--r-sm); color: var(--silver-3);
    cursor: pointer; padding: 5px; display: flex; align-items: center;
    transition: all .12s;
}
.sk-settings-close:hover { background: var(--ink-4); color: var(--silver); }
.sk-settings-body { padding: 20px; display: flex; flex-direction: column; gap: 24px; }
.sk-settings-section { display: flex; flex-direction: column; gap: 12px; }
.sk-settings-section-title {
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: var(--silver-4);
    padding-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.05);
}
.sk-settings-field { display: flex; flex-direction: column; gap: 5px; }
.sk-settings-field label { font-size: 11.5px; color: var(--silver-3); font-weight: 500; }
.sk-settings-value { font-size: 13px; color: var(--silver-2); }
.sk-mono { font-family: var(--f-mono); font-size: 11px; color: var(--silver-3); }
.sk-settings-input {
    background: var(--ink-3) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: var(--r-sm) !important;
    color: var(--silver) !important;
    font-family: var(--f-body) !important;
    font-size: 13.5px !important;
    padding: 9px 12px !important;
    width: 100% !important;
    transition: border-color .18s !important;
    outline: none !important;
}
.sk-settings-input:focus {
    border-color: rgba(201,168,76,0.4) !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.06) !important;
}
.sk-settings-btn {
    background: var(--gold); border: none;
    border-radius: var(--r-sm); color: var(--ink);
    font-family: var(--f-body); font-size: 13px; font-weight: 600;
    padding: 9px 18px; cursor: pointer;
    align-self: flex-start;
    transition: background .15s;
}
.sk-settings-btn:hover { background: #dbb85a; }
.sk-settings-msg { font-size: 12px; min-height: 18px; }
.sk-settings-msg.ok { color: var(--success); }
.sk-settings-msg.err { color: var(--danger); }
.sk-settings-notice {
    flex-direction: row !important; gap: 8px !important;
    padding: 10px 12px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: var(--r-sm);
    font-size: 11px; color: var(--silver-4); line-height: 1.6;
    align-items: flex-start !important;
}
.sk-settings-notice svg { flex-shrink: 0; margin-top: 2px; }

/* ── MOBILE OVERLAY ── */
.sk-mob-overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.55); z-index: 49;
}
.sk-mob-overlay.open { display: block; }

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
    .sk-sidebar {
        position: fixed; top: 0; left: 0; height: 100%;
        transform: translateX(-100%); z-index: 200;
        box-shadow: 6px 0 30px rgba(0,0,0,0.6);
    }
    .sk-sidebar.open { transform: translateX(0); }
    .sk-menu-btn { display: flex !important; }
    .sk-prompt-grid { grid-template-columns: 1fr 1fr; }
    .sk-welcome { padding: 1.75rem 16px 1.5rem; }
    .sk-input-wrap { padding: 8px 12px 14px; }
}
@media (max-width: 520px) {
    .sk-prompt-grid { grid-template-columns: 1fr; }
    .sk-welcome-name { font-size: 1.3rem; }
    .sk-auth-card { border-radius: var(--r-lg); padding: 1.5rem 1.25rem; }
    .message.user { max-width: 85% !important; }
    .sk-header { padding: 0 12px; }
    .sk-header-badge { display: none; }
}
"""

JS_BRIDGE = """
<div id="skMobOverlay" class="sk-mob-overlay" onclick="sakina_togglesidebar()"></div>
<script>
// ── localStorage persistence ──────────────────────────────────────────────
var SAKINA_LS_KEY = 'sakina_session_v1';

function sakina_saveSession(userId, email, name) {
    try {
        localStorage.setItem(SAKINA_LS_KEY, JSON.stringify({
            userId: userId, email: email, name: name,
            savedAt: Date.now()
        }));
    } catch(e) {}
}

function sakina_clearSession() {
    try { localStorage.removeItem(SAKINA_LS_KEY); } catch(e) {}
}

function sakina_getSession() {
    try {
        var raw = localStorage.getItem(SAKINA_LS_KEY);
        if (!raw) return null;
        var data = JSON.parse(raw);
        // 30-day expiry
        if (Date.now() - data.savedAt > 30 * 24 * 3600 * 1000) {
            sakina_clearSession(); return null;
        }
        return data;
    } catch(e) { return null; }
}

// Auto-restore session on load
window.addEventListener('DOMContentLoaded', function() {
    var session = sakina_getSession();
    if (session && session.userId) {
        setTimeout(function() {
            var inp = document.querySelector('#skAutoLoginInput textarea, #skAutoLoginInput input');
            var btn = document.getElementById('skAutoLoginBtn');
            if (inp && btn) {
                inp.value = session.userId;
                inp.dispatchEvent(new Event('input', {bubbles: true}));
                setTimeout(function(){ btn.click(); }, 200);
            }
        }, 400);
    }
});

// ── Sidebar ──────────────────────────────────────────────────────────────
function sakina_togglesidebar() {
    var sb = document.getElementById('skSidebar');
    var ov = document.getElementById('skMobOverlay');
    if (sb) sb.classList.toggle('open');
    if (ov) ov.classList.toggle('open');
}
function sakina_closeSidebar() {
    var sb = document.getElementById('skSidebar');
    var ov = document.getElementById('skMobOverlay');
    if (sb) sb.classList.remove('open');
    if (ov) ov.classList.remove('open');
}

// ── Chat actions ─────────────────────────────────────────────────────────
function sakina_resume(sid) {
    var el = document.querySelector('#skResumeInput textarea, #skResumeInput input');
    var btn = document.getElementById('skResumeBtn');
    if (el && btn) {
        el.value = sid;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        setTimeout(function(){ btn.click(); sakina_closeSidebar(); }, 100);
    }
}
function sakina_newchat() {
    var btn = document.getElementById('skNewChatBtn');
    if (btn) { btn.click(); sakina_closeSidebar(); }
}
function sakina_logout() {
    sakina_clearSession();
    var btn = document.getElementById('skLogoutBtn');
    if (btn) btn.click();
}
function sakina_suggest(text) {
    var box = document.querySelector('.sk-input-box textarea');
    if (box) {
        box.value = text;
        box.dispatchEvent(new Event('input', {bubbles: true}));
        box.focus();
    }
}

// ── Settings ─────────────────────────────────────────────────────────────
function sakina_settings() {
    var panel = document.getElementById('skSettingsOverlay');
    if (panel) panel.style.display = 'flex';
    sakina_closeSidebar();
}
function sakina_closeSettings(event) {
    if (event === null || event.target === document.getElementById('skSettingsOverlay')) {
        var panel = document.getElementById('skSettingsOverlay');
        if (panel) panel.style.display = 'none';
    }
}

function sakina_saveName() {
    var nameVal = document.getElementById('settingsName') ? document.getElementById('settingsName').value.trim() : '';
    var inp = document.querySelector('#skSettingsUpdateInput textarea, #skSettingsUpdateInput input');
    var btn = document.getElementById('skSettingsUpdateBtn');
    if (!nameVal) {
        sakina_setSettingsMsg('settingsNameMsg', 'Please enter a name.', 'err'); return;
    }
    if (inp && btn) {
        inp.value = JSON.stringify({action: 'name', name: nameVal});
        inp.dispatchEvent(new Event('input', {bubbles: true}));
        setTimeout(function(){ btn.click(); }, 100);
    }
}
function sakina_savePass() {
    var cur = document.getElementById('settingsCurrentPass') ? document.getElementById('settingsCurrentPass').value : '';
    var nw  = document.getElementById('settingsNewPass')     ? document.getElementById('settingsNewPass').value     : '';
    if (!cur || !nw) {
        sakina_setSettingsMsg('settingsPassMsg', 'Please fill in both passcode fields.', 'err'); return;
    }
    var inp = document.querySelector('#skSettingsUpdateInput textarea, #skSettingsUpdateInput input');
    var btn = document.getElementById('skSettingsUpdateBtn');
    if (inp && btn) {
        inp.value = JSON.stringify({action: 'pass', current: cur, newpass: nw});
        inp.dispatchEvent(new Event('input', {bubbles: true}));
        setTimeout(function(){ btn.click(); }, 100);
    }
}
function sakina_setSettingsMsg(id, text, cls) {
    var el = document.getElementById(id);
    if (el) { el.textContent = text; el.className = 'sk-settings-msg ' + cls; }
}
function sakina_receiveSettingsResult(result) {
    try {
        var data = JSON.parse(result);
        if (data.action === 'name') {
            sakina_setSettingsMsg('settingsNameMsg', data.msg, data.ok ? 'ok' : 'err');
            if (data.ok && data.newName) {
                // update localStorage
                var s = sakina_getSession();
                if (s) { s.name = data.newName; sakina_saveSession(s.userId, s.email, s.newName); }
            }
        } else if (data.action === 'pass') {
            sakina_setSettingsMsg('settingsPassMsg', data.msg, data.ok ? 'ok' : 'err');
        }
    } catch(e) {}
}
</script>
"""

# ── APP ───────────────────────────────────────────────────────────────────────
with gr.Blocks(css=CSS, title="Sakina — Hallvorn") as demo:

    # State
    sid_st      = gr.State(lambda: str(uuid.uuid4()))
    user_st     = gr.State(None)
    chatname_st = gr.State("New Conversation")
    sessions_st = gr.State([])
    active_st   = gr.State("")

    # ── AUTH ──────────────────────────────────────────────────────────────
    with gr.Group(visible=True) as auth_grp:
        gr.HTML('<div class="sk-auth"><div class="sk-auth-card">')
        gr.HTML("""
        <div class="sk-auth-header">
            <div class="sk-auth-logo-row">
                <div class="sk-auth-logo-box">S</div>
                <div>
                    <div class="sk-auth-brand-name">Sakina</div>
                    <div class="sk-auth-brand-sub">by Hallvorn</div>
                </div>
            </div>
            <div class="sk-auth-tagline">Elite scientific intelligence. Every phenomenon has a STEM answer.</div>
        </div>""")
        with gr.Tabs(elem_classes=["sk-auth-tabs"]):
            with gr.Tab("Sign in"):
                li_email = gr.Textbox(label="Email address", placeholder="you@example.com")
                li_pass  = gr.Textbox(label="Passcode", type="password", placeholder="Your passcode")
                li_btn   = gr.Button("Sign in", variant="primary")
                li_msg   = gr.HTML("")
            with gr.Tab("Create account"):
                su_name  = gr.Textbox(label="Full name", placeholder="Your full name")
                su_email = gr.Textbox(label="Email address", placeholder="you@example.com")
                su_pass  = gr.Textbox(label="Passcode (min 6 characters)", type="password", placeholder="Choose a passcode")
                su_btn   = gr.Button("Create account", variant="primary")
                su_msg   = gr.HTML("")
        gr.HTML("""<div class="sk-auth-notice">Your conversations may be used to improve Sakina. &nbsp;·&nbsp; Inspired by Sakina Haruna.</div>""")
        gr.HTML("</div></div>")

    # ── MAIN APP ──────────────────────────────────────────────────────────
    with gr.Group(visible=False) as app_grp:
        gr.HTML('<div class="sk-root">')

        sidebar_out  = gr.HTML("", elem_id="sidebarOut")
        settings_out = gr.HTML("", elem_id="settingsOut")

        gr.HTML('<div class="sk-main">')
        header_out = gr.HTML("", elem_id="headerOut")

        with gr.Column(elem_classes=["sk-messages"]):
            welcome_out = gr.HTML("", elem_id="welcomeOut")
            chatbot = gr.Chatbot(
                value=[], height=None, show_label=False,
                elem_classes=["sk-chatbot"],
                avatar_images=(None, None),
                render_markdown=True,
                bubble_full_width=False,
                visible=False,
            )

        gr.HTML('<div class="sk-input-wrap"><div class="sk-input-box">')
        with gr.Row(equal_height=True):
            msg_box  = gr.Textbox(
                placeholder="Ask Sakina anything...",
                show_label=False, scale=9, container=False,
                lines=1, max_lines=6,
            )
            send_btn = gr.Button("↑", variant="primary", scale=1, min_width=38, elem_classes=["sk-send-btn"])
        gr.HTML('</div></div>')
        gr.HTML('</div></div>')  # close sk-main + sk-root

        # Hidden controls
        resume_inp        = gr.Textbox(visible=False, elem_id="skResumeInput")
        resume_btn        = gr.Button("r", visible=False, elem_id="skResumeBtn")
        newchat_btn       = gr.Button("n", visible=False, elem_id="skNewChatBtn")
        logout_btn        = gr.Button("l", visible=False, elem_id="skLogoutBtn")
        auto_login_inp    = gr.Textbox(visible=False, elem_id="skAutoLoginInput")
        auto_login_btn    = gr.Button("a", visible=False, elem_id="skAutoLoginBtn")
        settings_inp      = gr.Textbox(visible=False, elem_id="skSettingsUpdateInput")
        settings_btn      = gr.Button("s", visible=False, elem_id="skSettingsUpdateBtn")
        settings_result   = gr.Textbox(visible=False, elem_id="skSettingsResult")

    gr.HTML(JS_BRIDGE)

    # ── JS to send session save signal after login ──
    # We embed a helper that reads the hidden output and triggers JS
    gr.HTML("""
    <script>
    // Watch for session data broadcast
    var _sakObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(n) {
                if (n.id === 'skSessionData') {
                    try {
                        var d = JSON.parse(n.dataset.session || '{}');
                        if (d.userId) sakina_saveSession(d.userId, d.email, d.name);
                    } catch(e) {}
                    n.remove();
                }
                if (n.id === 'skSettingsResultData') {
                    try { sakina_receiveSettingsResult(n.dataset.result || '{}'); } catch(e) {}
                    n.remove();
                }
            });
        });
    });
    _sakObserver.observe(document.body, {childList: true, subtree: true});
    </script>
    """)

    # ── HANDLERS ─────────────────────────────────────────────────────────

    def do_signup(name, email, passcode):
        ok, text = register_user(email, passcode, name)
        cls = "sk-status-ok" if ok else "sk-status-err"
        return f'<div class="{cls}">{"✓" if ok else "✕"} {text}</div>'

    su_btn.click(fn=do_signup, inputs=[su_name, su_email, su_pass], outputs=[su_msg])

    def _build_app_state(user, sid):
        sessions = load_sessions_for_user(user["id"])
        sidebar  = build_sidebar(user, sessions, "")
        header   = build_header("New Conversation")
        welcome  = build_welcome(user.get("full_name", ""))
        settings = build_settings_panel(user)
        # Inject session save signal
        session_signal = f'<div id="skSessionData" data-session=\'{{"userId":"{user["id"]}","email":"{user.get("email","")}","name":"{user.get("full_name","")}"}}\'></div>'
        return sessions, sidebar, header, welcome, settings, session_signal

    def do_login(email, passcode, sid):
        user, text = login_user(email, passcode)
        if user:
            sessions, sidebar, header, welcome, settings, session_signal = _build_app_state(user, sid)
            msg = f'<div class="sk-status-ok">✓ {text}</div>'
            return (
                gr.update(visible=False), gr.update(visible=True),
                msg, user, [], sidebar, header, welcome + session_signal,
                settings, gr.update(visible=False), "New Conversation",
                sessions, sid, ""
            )
        msg = f'<div class="sk-status-err">✕ {text}</div>'
        return (
            gr.update(visible=True), gr.update(visible=False),
            msg, None, [], "", "", "", "",
            gr.update(visible=False), "New Conversation", [], sid, ""
        )

    li_btn.click(
        fn=do_login,
        inputs=[li_email, li_pass, sid_st],
        outputs=[auth_grp, app_grp, li_msg, user_st, chatbot,
                 sidebar_out, header_out, welcome_out,
                 settings_out, chatbot, chatname_st, sessions_st, sid_st, active_st],
    )

    def do_auto_login(user_id, sid):
        """Log in by user_id from localStorage."""
        if not user_id or not user_id.strip():
            return (gr.update(), gr.update(), None, [], "", "", "", "",
                    gr.update(), "New Conversation", [], sid, "")
        user = get_user_by_id(user_id.strip())
        if not user:
            return (gr.update(), gr.update(), None, [], "", "", "", "",
                    gr.update(), "New Conversation", [], sid, "")
        sessions, sidebar, header, welcome, settings, session_signal = _build_app_state(user, sid)
        return (
            gr.update(visible=False), gr.update(visible=True),
            user, [], sidebar, header, welcome + session_signal,
            settings, gr.update(visible=False), "New Conversation",
            sessions, sid, ""
        )

    auto_login_btn.click(
        fn=do_auto_login,
        inputs=[auto_login_inp, sid_st],
        outputs=[auth_grp, app_grp, user_st, chatbot,
                 sidebar_out, header_out, welcome_out,
                 settings_out, chatbot, chatname_st, sessions_st, sid_st, active_st],
    )

    def do_send(message, history, sid, user, chat_name, sessions):
        if not message or not message.strip():
            return history, "", chat_name, "", gr.update(), gr.update(), gr.update(), sessions, sid
        reply, new_name = chat_fn(message, history, sid, user, chat_name)
        new_history = history + [(message.strip(), reply)]
        new_sessions = load_sessions_for_user(user["id"]) if user else sessions
        sidebar = build_sidebar(user, new_sessions, sid) if user else ""
        header  = build_header(new_name)
        return (
            new_history, "", new_name, sidebar,
            gr.update(visible=True),
            gr.update(visible=False),
            header, new_sessions, sid
        )

    send_btn.click(
        fn=do_send,
        inputs=[msg_box, chatbot, sid_st, user_st, chatname_st, sessions_st],
        outputs=[chatbot, msg_box, chatname_st, sidebar_out,
                 chatbot, welcome_out, header_out, sessions_st, sid_st],
    )
    msg_box.submit(
        fn=do_send,
        inputs=[msg_box, chatbot, sid_st, user_st, chatname_st, sessions_st],
        outputs=[chatbot, msg_box, chatname_st, sidebar_out,
                 chatbot, welcome_out, header_out, sessions_st, sid_st],
    )

    def do_resume(target_sid, user, sessions):
        if not user or not target_sid or not target_sid.strip():
            return (gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), "")
        target_sid = target_sid.strip()
        history   = load_session_history(user["id"], target_sid)
        chat_name = get_session_chat_name(user["id"], target_sid)
        sidebar   = build_sidebar(user, sessions, target_sid)
        header    = build_header(chat_name)
        return (
            history, target_sid, chat_name, sidebar, header,
            gr.update(visible=True), gr.update(visible=False), "",
        )

    resume_btn.click(
        fn=do_resume,
        inputs=[resume_inp, user_st, sessions_st],
        outputs=[chatbot, sid_st, chatname_st, sidebar_out,
                 header_out, chatbot, welcome_out, resume_inp],
    )

    def do_new_chat(user, sessions):
        new_sid = str(uuid.uuid4())
        sidebar = build_sidebar(user, sessions, "") if user else ""
        header  = build_header("New Conversation")
        welcome = build_welcome(user.get("full_name", "")) if user else ""
        return (
            [], new_sid, "New Conversation", sidebar, header, welcome,
            gr.update(visible=False), gr.update(visible=True),
        )

    newchat_btn.click(
        fn=do_new_chat,
        inputs=[user_st, sessions_st],
        outputs=[chatbot, sid_st, chatname_st, sidebar_out,
                 header_out, welcome_out, chatbot, welcome_out],
    )

    def do_logout():
        return (
            gr.update(visible=True), gr.update(visible=False),
            None, [], "", "", "", "",
            gr.update(visible=False), "New Conversation", [], "", ""
        )

    logout_btn.click(
        fn=do_logout,
        inputs=[],
        outputs=[auth_grp, app_grp, user_st, chatbot,
                 sidebar_out, header_out, welcome_out, settings_out,
                 chatbot, chatname_st, sessions_st, sid_st, li_msg],
    )

    def do_settings_update(payload_str, user, sessions):
        """Handle settings update from JS."""
        if not user or not payload_str or not payload_str.strip():
            return "", ""
        try:
            import json
            payload = json.loads(payload_str.strip())
        except Exception:
            return "", ""

        action = payload.get("action", "")
        result_data = {}

        if action == "name":
            new_name = payload.get("name", "").strip()
            ok, msg = update_user_profile(user["id"], new_name=new_name)
            result_data = {"action": "name", "ok": ok, "msg": msg, "newName": new_name if ok else ""}
            if ok:
                user["full_name"] = new_name
        elif action == "pass":
            cur = payload.get("current", "")
            nw  = payload.get("newpass", "")
            ok, msg = update_user_profile(user["id"], new_passcode=nw, current_passcode=cur)
            result_data = {"action": "pass", "ok": ok, "msg": msg}
        else:
            return "", ""

        import json
        result_json = json.dumps(result_data)
        # Rebuild sidebar and settings if name changed
        new_sessions = load_sessions_for_user(user["id"])
        sidebar = build_sidebar(user, new_sessions, "")
        settings = build_settings_panel(user)
        signal = f'<div id="skSettingsResultData" data-result=\'{result_json}\'></div>'
        return sidebar + signal, settings

    settings_btn.click(
        fn=do_settings_update,
        inputs=[settings_inp, user_st, sessions_st],
        outputs=[sidebar_out, settings_out],
    )

# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
