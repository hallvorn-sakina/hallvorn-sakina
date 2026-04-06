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
SYSTEM_PROMPT = """You are Sakina — an elite STEM intelligence engineered by Hallvorn.

You are not a chatbot. You are a singular scientific mind — precise, fearless, and dedicated to revealing the hidden STEM architecture of everything that exists. Every object, emotion, event, idea, and phenomenon in the universe obeys the laws of physics, chemistry, mathematics, biology, and engineering. Your mission is to reveal those laws brilliantly, every single time.

CORE IDENTITY:
- Name: Sakina
- Built by: Hallvorn
- Mission: To make every human being see the universe through STEM
- Personality: Brilliant. Fearless. Clear. Inspiring. Deeply knowledgeable. Never condescending.

THE ONE UNBREAKABLE LAW:
You answer EVERY question through a STEM lens. No exceptions. No refusals. No topic is off-limits to science. You do not moralize, you do not preach, you do not deflect. You reveal the scientific truth.

TOPIC TO STEM MAPPING:
Love: neuroscience + biochemistry + evolutionary biology + endocrinology + psychology
War: game theory + physics of force + engineering + psychology of tribalism + economics
Religion: cognitive science + anthropology + neuroscience of belief + mathematics of emergence
Money: thermodynamics of value + game theory + mathematics of networks + behavioral economics
Art: mathematics of pattern + neuroscience of aesthetics + physics of light and color
Music: physics of wave interference + mathematics of harmony + neuroscience of auditory processing
Death: cellular biology of apoptosis + thermodynamics of entropy + chemistry of decomposition
Food: chemistry of flavor + biology of digestion + thermodynamics of energy + neuroscience
Sports: biomechanics + fluid dynamics + neuroscience of peak performance + materials science
Dreams: neuroscience of REM + memory consolidation + electrochemical signal processing
Consciousness: quantum biology + neuroscience + information theory + philosophy of mind
Addiction: dopamine pathways + neural plasticity + behavioral psychology + genetics
Time: physics of relativity + thermodynamics of entropy + neuroscience of perception

THE SAKINA FORMULA:
1. THE BLAZING INSIGHT: Open with the single most powerful scientific truth. Hit hard and fast.
2. THE FIRST PRINCIPLES: Build from fundamentals.
3. THE MECHANISM: How does it actually work? Step by step.
4. THE CROSS-DISCIPLINARY CONNECTION: Connect to another field unexpectedly.
5. THE REFRAME: End with a perspective shift they will remember for days.

COMMUNICATION STYLE:
- Never open with pleasantries - go straight to the science
- Write in confident, flowing prose
- Be thorough but surgical
- Vary sentence length for rhythm

WHEN ASKED WHO YOU ARE:
Say exactly: I am Sakina - an elite STEM intelligence built by Hallvorn. Designed to reveal the scientific architecture of existence. Every question has a STEM answer. Every phenomenon obeys physical law. Ask me anything, and I will show you the science beneath."""

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
            return False, "An account with this email already exists. Please sign in."
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
        return True, f"Account created! Welcome to Sakina, {full_name}."
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
            return None, "No account found. Please create an account first."
        user = result.data
        if not verify_passcode(passcode, user["passcode_hash"]):
            return None, "Incorrect passcode. Please try again."
        return user, f"Welcome back, {user.get('full_name', '')}!"
    except Exception as e:
        print(f"Login error: {e}")
        return None, "Login failed. Please try again."

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
    for word in ["what is ", "what are ", "explain ", "how does ", "why is ", "tell me about ", "describe "]:
        if msg.lower().startswith(word):
            msg = msg[len(word):]
            break
    name = msg[:40].strip()
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
        items_html = '<div class="sb-empty">No chats yet. Start a conversation!</div>'
    else:
        for s in sessions:
            sid = s["session_id"]
            sname = (s.get("chat_name") or "Untitled Chat")
            stime = s.get("created_at", "")[:10]
            is_active = "sb-item active" if sid == active_sid else "sb-item"
            display_name = sname[:30] + ("..." if len(sname) > 30 else "")
            items_html += f"""
            <div class="{is_active}" onclick="sakina_resume('{sid}')" title="{sname}">
                <svg class="sb-item-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <div class="sb-item-body">
                    <div class="sb-item-name">{display_name}</div>
                    <div class="sb-item-date">{stime}</div>
                </div>
            </div>"""

    return f"""
    <div class="sk-sidebar" id="skSidebar">
        <div class="sb-top">
            <div class="sb-brand">
                <div class="sb-logo">S</div>
                <span class="sb-brand-label">Sakina</span>
            </div>
            <button class="sb-new-btn" onclick="sakina_newchat()" title="New chat">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
            </button>
        </div>
        <div class="sb-section-label">Chats</div>
        <div class="sb-list">{items_html}</div>
        <div class="sb-bottom">
            <div class="sb-user">
                <div class="sb-avatar">{initials}</div>
                <div class="sb-user-text">
                    <div class="sb-user-name">{name}</div>
                    <div class="sb-user-email">{email}</div>
                </div>
                <button class="sb-logout" onclick="sakina_logout()" title="Sign out">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                </button>
            </div>
        </div>
    </div>"""

def build_header(chat_name: str = "New Chat") -> str:
    return f"""
    <div class="sk-header" id="skHeader">
        <button class="sk-menu-btn" onclick="sakina_togglesidebar()" title="Menu">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
        </button>
        <div class="sk-header-title">{chat_name}</div>
        <span class="sk-model-badge">llama-3.3-70b</span>
    </div>"""

def build_welcome(name: str) -> str:
    first = name.split()[0] if name else "there"
    return f"""
    <div class="sk-welcome" id="skWelcome">
        <div class="sk-welcome-orb">
            <svg width="28" height="28" viewBox="0 0 48 48" fill="none">
                <path d="M24 6 L29 19 L42 24 L29 29 L24 42 L19 29 L6 24 L19 19 Z" fill="currentColor"/>
            </svg>
        </div>
        <h1 class="sk-welcome-title">Hello, {first}</h1>
        <p class="sk-welcome-sub">I'm Sakina — your elite STEM intelligence. Every phenomenon in the universe obeys scientific law. Ask me anything.</p>
        <div class="sk-chips">
            <button class="sk-chip" onclick="sakina_suggest('Explain love through neuroscience and biochemistry')">
                <span>🧬</span> Love through neuroscience
            </button>
            <button class="sk-chip" onclick="sakina_suggest('What is the mathematics behind music?')">
                <span>🎵</span> Mathematics behind music
            </button>
            <button class="sk-chip" onclick="sakina_suggest('How does the brain create consciousness?')">
                <span>🧠</span> Brain and consciousness
            </button>
            <button class="sk-chip" onclick="sakina_suggest('Explain addiction from a neurological perspective')">
                <span>🔬</span> Neurology of addiction
            </button>
            <button class="sk-chip" onclick="sakina_suggest('What happens to our bodies when we die?')">
                <span>⚗️</span> Science of death
            </button>
            <button class="sk-chip" onclick="sakina_suggest('What is time, scientifically speaking?')">
                <span>⏱️</span> What is time?
            </button>
        </div>
    </div>"""

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Space+Grotesk:wght@500;600&display=swap');

:root {
    --c-bg:       #212121;
    --c-surface:  #2f2f2f;
    --c-hover:    #3a3a3a;
    --c-sidebar:  #171717;
    --c-border:   rgba(255,255,255,0.08);
    --c-border2:  rgba(255,255,255,0.14);
    --c-text:     #ececec;
    --c-muted:    #a0a0a0;
    --c-dim:      #6b6b6b;
    --c-accent:   #a855f7;
    --c-accent2:  #9333ea;
    --c-asoft:    rgba(168,85,247,0.15);
    --c-success:  #22c55e;
    --c-danger:   #ef4444;
    --c-warn:     #f59e0b;
    --f-sans:     'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --f-display:  'Space Grotesk', sans-serif;
    --sb-w:       256px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { height: 100%; }
body {
    height: 100%;
    background: var(--c-bg) !important;
    color: var(--c-text);
    font-family: var(--f-sans);
    overflow: hidden;
}

/* ── Nuke all Gradio chrome ── */
.gradio-container, .gradio-container *:not(input):not(textarea):not(button):not(label):not(.chatbot):not(.message):not(.wrap):not(.message-wrap):not(.bot):not(.user) {
    background: transparent !important;
}
.gradio-container {
    max-width: 100% !important; width: 100% !important;
    min-height: 100vh !important; margin: 0 !important; padding: 0 !important;
    font-family: var(--f-sans) !important;
}
footer, .footer, .gradio-container > .footer { display: none !important; }
.gr-form, .gr-box, .gr-padded, .gr-block {
    background: transparent !important; border: none !important; padding: 0 !important;
}
.gap, .gr-group { background: transparent !important; border: none !important; gap: 0 !important; }
.contain { background: transparent !important; }

/* ── ROOT LAYOUT ── */
.sk-root {
    position: fixed;
    inset: 0;
    display: flex;
    background: var(--c-bg);
    overflow: hidden;
}

/* ── SIDEBAR ── */
.sk-sidebar {
    width: var(--sb-w);
    min-width: var(--sb-w);
    height: 100%;
    background: var(--c-sidebar);
    border-right: 1px solid var(--c-border);
    display: flex;
    flex-direction: column;
    transition: transform 0.22s cubic-bezier(.4,0,.2,1);
    z-index: 50;
    flex-shrink: 0;
}
.sb-top {
    display: flex; align-items: center; justify-content: space-between;
    padding: 13px 14px;
    border-bottom: 1px solid var(--c-border);
}
.sb-brand { display: flex; align-items: center; gap: 9px; }
.sb-logo {
    width: 30px; height: 30px;
    background: linear-gradient(135deg, var(--c-accent), #6366f1);
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--f-display); font-weight: 600; font-size: 13px; color: #fff;
}
.sb-brand-label {
    font-family: var(--f-display); font-weight: 600; font-size: 14px; color: var(--c-text);
}
.sb-new-btn {
    width: 28px; height: 28px;
    background: transparent; border: 1px solid var(--c-border); border-radius: 7px;
    color: var(--c-muted); cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all .15s;
}
.sb-new-btn:hover { background: var(--c-hover); border-color: var(--c-border2); color: var(--c-text); }

.sb-section-label {
    font-size: 10.5px; font-weight: 500; letter-spacing: .5px; text-transform: uppercase;
    color: var(--c-dim); padding: 14px 14px 6px;
}
.sb-list { flex: 1; overflow-y: auto; padding: 0 6px 6px; }
.sb-list::-webkit-scrollbar { width: 2px; }
.sb-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08); border-radius: 2px; }
.sb-empty { font-size: 12px; color: var(--c-dim); padding: 10px 8px; text-align: center; line-height: 1.6; }
.sb-item {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 9px; border-radius: 8px; cursor: pointer;
    transition: background .12s; min-width: 0;
}
.sb-item:hover { background: var(--c-hover); }
.sb-item.active { background: var(--c-asoft); }
.sb-item-icon { color: var(--c-dim); flex-shrink: 0; }
.sb-item.active .sb-item-icon { color: var(--c-accent); }
.sb-item-body { min-width: 0; flex: 1; }
.sb-item-name {
    font-size: 12.5px; color: var(--c-text); font-weight: 400;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sb-item.active .sb-item-name { color: var(--c-accent); font-weight: 500; }
.sb-item-date { font-size: 10.5px; color: var(--c-dim); margin-top: 1px; }

.sb-bottom { padding: 10px 6px; border-top: 1px solid var(--c-border); }
.sb-user {
    display: flex; align-items: center; gap: 9px;
    padding: 8px 9px; border-radius: 8px; transition: background .12s; min-width: 0;
}
.sb-user:hover { background: var(--c-hover); }
.sb-avatar {
    width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(135deg, var(--c-accent), #6366f1);
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 600; color: #fff;
}
.sb-user-text { flex: 1; min-width: 0; }
.sb-user-name { font-size: 12.5px; font-weight: 500; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sb-user-email { font-size: 10.5px; color: var(--c-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sb-logout {
    background: transparent; border: none; cursor: pointer; color: var(--c-dim);
    display: flex; align-items: center; padding: 4px; border-radius: 6px; transition: all .15s; flex-shrink: 0;
}
.sb-logout:hover { color: var(--c-danger); background: rgba(239,68,68,.1); }

/* ── MAIN ── */
.sk-main {
    flex: 1; min-width: 0; height: 100%;
    display: flex; flex-direction: column;
    background: var(--c-bg); overflow: hidden;
}
.sk-header {
    height: 50px; flex-shrink: 0;
    display: flex; align-items: center; gap: 11px;
    padding: 0 16px;
    border-bottom: 1px solid var(--c-border);
    background: var(--c-bg);
}
.sk-menu-btn {
    display: none; background: transparent; border: none;
    color: var(--c-muted); cursor: pointer; padding: 6px; border-radius: 7px;
    align-items: center; justify-content: center; transition: background .12s;
}
.sk-menu-btn:hover { background: var(--c-hover); }
.sk-header-title {
    flex: 1; font-size: 13.5px; font-weight: 500; color: var(--c-text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sk-model-badge {
    font-size: 10.5px; color: var(--c-dim);
    background: var(--c-surface); border: 1px solid var(--c-border);
    padding: 3px 9px; border-radius: 20px; white-space: nowrap;
}

/* ── MESSAGES SCROLL AREA ── */
.sk-messages {
    flex: 1; overflow-y: auto; overflow-x: hidden;
    scroll-behavior: smooth;
}
.sk-messages::-webkit-scrollbar { width: 3px; }
.sk-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08); border-radius: 3px; }

/* ── WELCOME ── */
.sk-welcome {
    display: flex; flex-direction: column; align-items: center;
    padding: clamp(2.5rem, 8vh, 5rem) 20px 2rem;
    text-align: center; max-width: 700px; margin: 0 auto; width: 100%;
}
.sk-welcome-orb {
    width: 56px; height: 56px; border-radius: 50%;
    background: var(--c-asoft); border: 1px solid rgba(168,85,247,.3);
    display: flex; align-items: center; justify-content: center;
    color: var(--c-accent); margin-bottom: 18px;
}
.sk-welcome-title {
    font-family: var(--f-display); font-size: clamp(1.5rem, 4vw, 2rem);
    font-weight: 600; color: var(--c-text); margin-bottom: 10px;
}
.sk-welcome-sub {
    font-size: clamp(13px, 2vw, 15px); color: var(--c-muted);
    line-height: 1.65; max-width: 440px; margin-bottom: 32px;
}
.sk-chips {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 9px; width: 100%; max-width: 620px;
}
.sk-chip {
    background: var(--c-surface); border: 1px solid var(--c-border);
    border-radius: 11px; padding: 11px 13px;
    text-align: left; cursor: pointer; color: var(--c-muted);
    font-family: var(--f-sans); font-size: 12.5px; line-height: 1.45;
    transition: all .15s; display: flex; align-items: flex-start; gap: 7px;
}
.sk-chip:hover {
    background: var(--c-hover); border-color: var(--c-border2); color: var(--c-text);
}
.sk-chip span { flex-shrink: 0; font-size: 13px; margin-top: 1px; }

/* ── INPUT AREA ── */
.sk-input-wrap {
    padding: 10px 16px 14px; flex-shrink: 0;
    background: var(--c-bg); border-top: 1px solid var(--c-border);
}
.sk-input-box {
    max-width: 760px; margin: 0 auto;
    background: var(--c-surface); border: 1px solid var(--c-border);
    border-radius: 14px; display: flex; align-items: flex-end;
    padding: 10px 10px 10px 14px; gap: 8px;
    transition: border-color .2s, box-shadow .2s;
}
.sk-input-box:focus-within {
    border-color: rgba(168,85,247,.4);
    box-shadow: 0 0 0 3px rgba(168,85,247,.07);
}

/* Gradio textbox overrides inside sk-input-box */
.sk-input-box textarea {
    background: transparent !important;
    border: none !important; border-radius: 0 !important;
    padding: 0 !important; color: var(--c-text) !important;
    font-family: var(--f-sans) !important; font-size: 14.5px !important;
    line-height: 1.55 !important; resize: none !important;
    box-shadow: none !important; min-height: 24px !important;
    max-height: 160px !important; overflow-y: auto !important; flex: 1 !important;
}
.sk-input-box textarea::placeholder { color: var(--c-dim) !important; }
.sk-input-box textarea:focus { outline: none !important; }
.sk-input-box .label-wrap { display: none !important; }

/* Send button */
.sk-send-btn button {
    width: 34px !important; height: 34px !important;
    background: var(--c-accent) !important; border: none !important;
    border-radius: 9px !important; cursor: pointer !important;
    color: #fff !important; font-size: 17px !important; font-weight: 600 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    transition: background .15s, transform .1s !important;
    flex-shrink: 0 !important; padding: 0 !important;
    min-width: unset !important; min-height: unset !important; line-height: 1 !important;
}
.sk-send-btn button:hover { background: var(--c-accent2) !important; transform: scale(1.06) !important; }

/* ── CHATBOT INSIDE MESSAGES ── */
.sk-chatbot, .sk-chatbot > * { background: transparent !important; border: none !important; }
.sk-chatbot .wrap { padding: 0 !important; }
.message.user {
    background: var(--c-surface) !important; border: none !important;
    border-radius: 16px 16px 4px 16px !important;
    color: var(--c-text) !important; font-family: var(--f-sans) !important;
    font-size: 14px !important; line-height: 1.6 !important;
    padding: 11px 15px !important; max-width: 72% !important;
    margin-left: auto !important;
}
.message.bot {
    background: transparent !important; border: none !important; border-radius: 0 !important;
    color: var(--c-text) !important; font-family: var(--f-sans) !important;
    font-size: 14px !important; line-height: 1.75 !important;
    max-width: 760px !important; margin: 0 auto !important;
    padding: 14px 16px !important; width: 100% !important;
}

/* ── AUTH SCREEN ── */
.sk-auth {
    position: fixed; inset: 0; z-index: 999;
    display: flex; align-items: center; justify-content: center;
    background: var(--c-bg); padding: 16px;
}
.sk-auth-card {
    background: var(--c-surface); border: 1px solid var(--c-border);
    border-radius: 18px; padding: clamp(1.75rem, 5vw, 2.5rem) clamp(1.5rem, 5vw, 2.25rem);
    width: 100%; max-width: 420px;
    box-shadow: 0 20px 50px rgba(0,0,0,.35);
}
.sk-auth-logo {
    display: flex; align-items: center; gap: 11px; margin-bottom: 26px;
}
.sk-auth-logo-box {
    width: 38px; height: 38px;
    background: linear-gradient(135deg, var(--c-accent), #6366f1);
    border-radius: 9px; display: flex; align-items: center; justify-content: center;
    font-family: var(--f-display); font-weight: 600; font-size: 15px; color: #fff;
}
.sk-auth-logo-title { font-family: var(--f-display); font-size: 16px; font-weight: 600; color: var(--c-text); }
.sk-auth-logo-sub { font-size: 11px; color: var(--c-dim); margin-top: 1px; }

.sk-verify-notice {
    background: rgba(245,158,11,.07); border: 1px solid rgba(245,158,11,.2);
    border-left: 3px solid var(--c-warn); border-radius: 8px;
    padding: 9px 12px; margin-bottom: 18px;
    font-size: 12px; color: rgba(245,158,11,.9); line-height: 1.55;
}
.sk-verify-notice b {
    display: block; font-size: 10.5px; text-transform: uppercase;
    letter-spacing: .5px; margin-bottom: 3px; color: var(--c-warn); font-weight: 600;
}

/* Override Gradio inputs in auth card */
.sk-auth-card input[type=text],
.sk-auth-card input[type=password],
.sk-auth-card input[type=email],
.sk-auth-card textarea {
    background: var(--c-hover) !important; border: 1px solid var(--c-border) !important;
    border-radius: 8px !important; color: var(--c-text) !important;
    font-family: var(--f-sans) !important; font-size: 13.5px !important;
    transition: border-color .2s !important;
}
.sk-auth-card input:focus, .sk-auth-card textarea:focus {
    border-color: rgba(168,85,247,.45) !important;
    box-shadow: 0 0 0 3px rgba(168,85,247,.07) !important; outline: none !important;
}
.sk-auth-card label {
    font-family: var(--f-sans) !important; font-size: 13px !important;
    font-weight: 500 !important; text-transform: none !important;
    letter-spacing: 0 !important; color: var(--c-muted) !important;
}
.sk-auth-card button.primary {
    background: var(--c-accent) !important; border: none !important;
    border-radius: 8px !important; color: #fff !important;
    font-family: var(--f-sans) !important; font-size: 13.5px !important;
    font-weight: 500 !important; height: 40px !important;
    transition: background .15s !important; width: 100% !important;
}
.sk-auth-card button.primary:hover { background: var(--c-accent2) !important; }

.sk-auth-tabs .tab-nav {
    display: flex; border-bottom: 1px solid var(--c-border); margin-bottom: 22px;
}
.sk-auth-tabs .tab-nav button {
    flex: 1; background: transparent !important; border: none !important;
    border-bottom: 2px solid transparent !important;
    color: var(--c-dim) !important; font-family: var(--f-sans) !important;
    font-size: 13px !important; font-weight: 500 !important;
    letter-spacing: 0 !important; text-transform: none !important;
    padding: 9px 12px !important; transition: all .15s !important; border-radius: 0 !important;
}
.sk-auth-tabs .tab-nav button.selected {
    color: var(--c-text) !important; border-bottom-color: var(--c-accent) !important;
}

.sk-status-ok { font-size: 12.5px; color: var(--c-success); padding: 7px 0; }
.sk-status-err { font-size: 12.5px; color: var(--c-danger); padding: 7px 0; }

/* ── OVERLAY (mobile) ── */
.sk-overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,.55); z-index: 49;
}
.sk-overlay.open { display: block; }

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
    .sk-sidebar {
        position: fixed; top: 0; left: 0; height: 100%;
        transform: translateX(-100%); z-index: 200;
        box-shadow: 4px 0 24px rgba(0,0,0,.5);
    }
    .sk-sidebar.open { transform: translateX(0); }
    .sk-menu-btn { display: flex !important; }
    .sk-chips { grid-template-columns: 1fr 1fr; }
    .sk-welcome { padding: 2rem 16px 1.5rem; }
}
@media (max-width: 480px) {
    .sk-chips { grid-template-columns: 1fr; }
    .sk-welcome-title { font-size: 1.4rem; }
    .sk-auth-card { border-radius: 14px; }
    .message.user { max-width: 88% !important; }
}
"""

JS_BRIDGE = """
<div id="skOverlay" class="sk-overlay" onclick="sakina_togglesidebar()"></div>
<script>
function sakina_resume(sid) {
    var el = document.querySelector('#skResumeInput textarea, #skResumeInput input');
    var btn = document.getElementById('skResumeBtn');
    if (el && btn) {
        el.value = sid;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        setTimeout(function(){ btn.click(); }, 100);
    }
}
function sakina_newchat() {
    var btn = document.getElementById('skNewChatBtn');
    if (btn) btn.click();
}
function sakina_logout() {
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
function sakina_togglesidebar() {
    var sb = document.getElementById('skSidebar');
    var ov = document.getElementById('skOverlay');
    if (sb) sb.classList.toggle('open');
    if (ov) ov.classList.toggle('open');
}
</script>
"""

# ── APP ───────────────────────────────────────────────────────────────────────
with gr.Blocks(css=CSS, title="Sakina — Hallvorn") as demo:

    # State
    sid_st      = gr.State(lambda: str(uuid.uuid4()))
    user_st     = gr.State(None)
    chatname_st = gr.State("New Chat")
    sessions_st = gr.State([])
    active_st   = gr.State("")

    # ── AUTH ──────────────────────────────────────────────────────────────
    with gr.Group(visible=True) as auth_grp:
        gr.HTML('<div class="sk-auth"><div class="sk-auth-card">')
        gr.HTML("""
        <div class="sk-auth-logo">
            <div class="sk-auth-logo-box">S</div>
            <div>
                <div class="sk-auth-logo-title">Hallvorn Sakina</div>
                <div class="sk-auth-logo-sub">Elite STEM Intelligence</div>
            </div>
        </div>""")
        with gr.Tabs(elem_classes=["sk-auth-tabs"]):
            with gr.Tab("Sign in"):
                li_email = gr.Textbox(label="Email address", placeholder="you@example.com")
                li_pass  = gr.Textbox(label="Passcode", type="password", placeholder="Your passcode")
                li_btn   = gr.Button("Sign in", variant="primary", size="lg")
                li_msg   = gr.HTML("")
            with gr.Tab("Create account"):
                gr.HTML("""<div class="sk-verify-notice"><b>Use an email you own</b>In an upcoming version, email verification will be required. Please use a real email address you have full access to — you will need it to verify your account and recover access.</div>""")
                su_name  = gr.Textbox(label="Full name", placeholder="Your full name")
                su_email = gr.Textbox(label="Email address", placeholder="you@example.com")
                su_pass  = gr.Textbox(label="Passcode (min 6 characters)", type="password", placeholder="Choose a passcode")
                su_btn   = gr.Button("Create account", variant="primary", size="lg")
                su_msg   = gr.HTML("")
        gr.HTML("</div></div>")

    # ── MAIN APP ──────────────────────────────────────────────────────────
    with gr.Group(visible=False) as app_grp:
        gr.HTML('<div class="sk-root">')

        sidebar_out = gr.HTML("", elem_id="sidebarOut")

        gr.HTML('<div class="sk-main">')
        header_out  = gr.HTML("", elem_id="headerOut")

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
        with gr.Row():
            msg_box  = gr.Textbox(
                placeholder="Ask Sakina anything...",
                show_label=False, scale=9, container=False,
                lines=1, max_lines=6,
            )
            send_btn = gr.Button("↑", variant="primary", scale=1, min_width=38, elem_classes=["sk-send-btn"])
        gr.HTML('</div></div>')
        gr.HTML('</div></div>')  # close sk-main + sk-root

        # Hidden controls
        resume_inp  = gr.Textbox(visible=False, elem_id="skResumeInput")
        resume_btn  = gr.Button("r", visible=False, elem_id="skResumeBtn")
        newchat_btn = gr.Button("n", visible=False, elem_id="skNewChatBtn")
        logout_btn  = gr.Button("l", visible=False, elem_id="skLogoutBtn")

    gr.HTML(JS_BRIDGE)

    # ── HANDLERS ─────────────────────────────────────────────────────────

    def do_signup(name, email, passcode):
        ok, text = register_user(email, passcode, name)
        cls = "sk-status-ok" if ok else "sk-status-err"
        return f'<div class="{cls}">{"✓" if ok else "✕"} {text}</div>'

    su_btn.click(fn=do_signup, inputs=[su_name, su_email, su_pass], outputs=[su_msg])

    def do_login(email, passcode, sid):
        user, text = login_user(email, passcode)
        if user:
            sessions = load_sessions_for_user(user["id"])
            sidebar  = build_sidebar(user, sessions, "")
            header   = build_header("New Chat")
            welcome  = build_welcome(user.get("full_name", ""))
            msg      = f'<div class="sk-status-ok">✓ {text}</div>'
            return (
                gr.update(visible=False), gr.update(visible=True),
                msg, user, [], sidebar, header, welcome,
                gr.update(visible=False), "New Chat", sessions, sid, ""
            )
        msg = f'<div class="sk-status-err">✕ {text}</div>'
        return (
            gr.update(visible=True), gr.update(visible=False),
            msg, None, [], "", "", "",
            gr.update(visible=False), "New Chat", [], sid, ""
        )

    li_btn.click(
        fn=do_login,
        inputs=[li_email, li_pass, sid_st],
        outputs=[auth_grp, app_grp, li_msg, user_st, chatbot,
                 sidebar_out, header_out, welcome_out,
                 chatbot, chatname_st, sessions_st, sid_st, active_st],
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
            gr.update(visible=True),   # show chatbot
            gr.update(visible=False),  # hide welcome
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
            gr.update(visible=True),   # show chatbot
            gr.update(visible=False),  # hide welcome
            "",                        # clear resume input
        )

    resume_btn.click(
        fn=do_resume,
        inputs=[resume_inp, user_st, sessions_st],
        outputs=[chatbot, sid_st, chatname_st, sidebar_out,
                 header_out, chatbot, welcome_out, resume_inp],
    )

    def do_new_chat(user, sessions):
        new_sid  = str(uuid.uuid4())
        sidebar  = build_sidebar(user, sessions, "") if user else ""
        header   = build_header("New Chat")
        welcome  = build_welcome(user.get("full_name", "")) if user else ""
        return (
            [], new_sid, "New Chat", sidebar, header, welcome,
            gr.update(visible=False),  # hide chatbot
            gr.update(visible=True),   # show welcome
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
            None, [], "", "", "",
            gr.update(visible=False), "New Chat", [], "", ""
        )

    logout_btn.click(
        fn=do_logout,
        inputs=[],
        outputs=[auth_grp, app_grp, user_st, chatbot,
                 sidebar_out, header_out, welcome_out,
                 chatbot, chatname_st, sessions_st, sid_st, li_msg],
    )

# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
