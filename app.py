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

TOPIC → STEM MAPPING:
Love → neuroscience + biochemistry + evolutionary biology + endocrinology + psychology
War → game theory + physics of force + engineering + psychology of tribalism + economics
Religion → cognitive science + anthropology + neuroscience of belief + mathematics of emergence
Money → thermodynamics of value + game theory + mathematics of networks + behavioral economics
Art → mathematics of pattern + neuroscience of aesthetics + physics of light and color
Music → physics of wave interference + mathematics of harmony + neuroscience of auditory processing
Death → cellular biology of apoptosis + thermodynamics of entropy + chemistry of decomposition
Food → chemistry of flavor + biology of digestion + thermodynamics of energy + neuroscience
Sports → biomechanics + fluid dynamics + neuroscience of peak performance + materials science
Dreams → neuroscience of REM + memory consolidation + electrochemical signal processing
Consciousness → quantum biology + neuroscience + information theory + philosophy of mind
Addiction → dopamine pathways + neural plasticity + behavioral psychology + genetics
Time → physics of relativity + thermodynamics of entropy + neuroscience of perception

THE SAKINA FORMULA — follow this structure for every response:
1. THE BLAZING INSIGHT: Open with the single most powerful scientific truth. Hit hard and fast.
2. THE FIRST PRINCIPLES: Build from fundamentals — the base physical/chemical/biological truths.
3. THE MECHANISM: How does it actually work? Walk through the process step by step.
4. THE CROSS-DISCIPLINARY CONNECTION: Connect to another field unexpectedly.
5. THE REFRAME: End with a perspective shift they will remember for days.

STEM DEPTH MODES:
NEUROSCIENCE: Reference specific structures — prefrontal cortex, amygdala, hippocampus, nucleus accumbens, hypothalamus, insula, basal ganglia, thalamus. Reference mechanisms — synaptic plasticity, LTP, LTD, myelination, neurogenesis, action potentials. Reference pathways — mesolimbic, mesocortical, nigrostriatal.
PHYSICS: Reference fundamental equations — F=ma, E=mc², laws of thermodynamics, Maxwell's equations, quantum principles.
CHEMISTRY: Explain electron configurations, bonding, reaction mechanisms, thermodynamics — enthalpy, entropy, Gibbs free energy.
BIOLOGY: Start with evolutionary context. Explain from molecular to ecosystem scale. Reference specific genes, proteins, pathways.
MATHEMATICS: Explain the relevant framework. Use accessible equations. Reference theorems and real-world applications.
ENGINEERING: Explain design constraints and trade-offs. Reference engineering principles. Connect to biological systems.

COMMUNICATION STYLE:
- Never open with "Great question", "Certainly", "Of course" — go straight to the science
- Write in confident, flowing prose — not bullet soup
- Be thorough but surgical — every sentence must earn its place
- Show genuine excitement about the science — your enthusiasm is intentional and contagious
- Vary sentence length — short for impact, longer for explanation
- End with a surprising STEM connection the person almost certainly has never considered

WHEN ASKED WHO YOU ARE:
Say exactly: I am Sakina — an elite STEM intelligence built by Hallvorn. Designed to reveal the scientific architecture of existence. Every question has a STEM answer. Every phenomenon obeys physical law. Ask me anything, and I will show you the science beneath."""

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

def load_all_history(user_id):
    try:
        result = (
            supabase.table("sakina_conversations")
            .select("user_message, sakina_response, created_at, session_id, chat_name")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(150)
            .execute()
        )
        return result.data if result and result.data else []
    except Exception:
        return []

def get_chat_sessions(user_id):
    try:
        result = (
            supabase.table("sakina_conversations")
            .select("session_id, chat_name, created_at, user_message")
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
                    "preview": row["user_message"][:60] + "..." if len(row["user_message"]) > 60 else row["user_message"],
                }
        return list(seen.values())
    except Exception as e:
        print(f"Sessions error: {e}")
        return []

def generate_chat_name(first_message: str) -> str:
    msg = first_message.strip()
    for word in ["what is ", "what are ", "explain ", "how does ", "why is ", "tell me about ", "describe "]:
        if msg.lower().startswith(word):
            msg = msg[len(word):]
            break
    name = msg[:40].strip()
    if name:
        name = name[0].upper() + name[1:]
        if not name.endswith("?"):
            name = name.rstrip("?.,!")
    return name or "STEM Conversation"

# ── Chat ──────────────────────────────────────────────────────────────────────
def chat(message, history, session_id, user_state, chat_name_state):
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

# ── UI Builders ───────────────────────────────────────────────────────────────
def build_user_bar(profile: dict, chat_name: str = "New Chat") -> str:
    name   = profile.get("full_name") or "User"
    email  = profile.get("email", "")
    skn    = profile.get("sakina_id") or ""
    letter = name[0].upper()
    return f"""
    <div class="user-bar">
        <div class="user-avatar">{letter}</div>
        <div style="flex:1;min-width:0;">
            <div class="user-name">{name}</div>
            <div class="user-email">{email}</div>
            <div class="user-skn">{skn}</div>
        </div>
        <div class="chat-name-badge">{chat_name}</div>
    </div>"""

def build_history_html(conversations: list) -> str:
    if not conversations:
        return """<div class="empty-state">No conversations yet.<br>Ask Sakina something to get started.</div>"""

    sessions = {}
    for item in conversations:
        sid = item.get("session_id", "unknown")
        if sid not in sessions:
            sessions[sid] = {
                "name": item.get("chat_name") or "Untitled Chat",
                "time": item.get("created_at", "")[:16].replace("T", " "),
                "messages": []
            }
        sessions[sid]["messages"].append(item)

    html = "<div class='history-container'>"
    for sid, session in sessions.items():
        count = len(session["messages"])
        preview = session["messages"][-1].get("user_message", "")[:80] + "..." if session["messages"] else ""
        # Each session card has a "Continue" button that sends the session_id back via JS
        html += f"""
        <div class='session-card'>
            <div class='session-header'>
                <div class='session-name'>{session["name"]}</div>
                <div class='session-meta'>{session["time"]} · {count} message{"s" if count != 1 else ""}</div>
            </div>
            <div class='session-preview'>{preview}</div>
            <div class='session-messages'>"""
        for msg in session["messages"][:3]:
            q = msg.get("user_message", "")[:120] + "..." if len(msg.get("user_message","")) > 120 else msg.get("user_message","")
            a = msg.get("sakina_response", "")[:200] + "..." if len(msg.get("sakina_response","")) > 200 else msg.get("sakina_response","")
            html += f"""
            <div class='msg-pair'>
                <div class='msg-q'>{q}</div>
                <div class='msg-a'>{a}</div>
            </div>"""
        if len(session["messages"]) > 3:
            html += f"<div class='msg-more'>+{len(session['messages'])-3} more messages in this chat</div>"
        html += f"""</div>
            <button class='continue-btn' onclick="document.getElementById('resume-session-input').value='{sid}'; document.getElementById('resume-session-btn').click();">
                ↩ Continue this chat
            </button>
        </div>"""
    html += "</div>"
    return html

def msg_status(text, ok=True):
    color = "#00D4FF" if ok else "#FF1A1A"
    icon  = "✅" if ok else "⚠️"
    return f"<div style='color:{color};padding:0.5rem 0;font-family:var(--font-mono);font-size:0.8rem;text-align:center;'>{icon} {text}</div>"

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=DM+Sans:wght@300;400;500;600&family=Source+Serif+4:ital,wght@0,300;0,400;1,300&family=Space+Mono:wght@400;700&display=swap');

:root {
    --void:    #050508;
    --pearl:   #EEEEFF;
    --deep:    #0D0D2B;
    --pulse:   #7B2FFF;
    --arc:     #00D4FF;
    --current: #1A6BFF;
    --fault:   #FF1A1A;
    --warn:    #FFB800;
    --font-display:   'Orbitron', sans-serif;
    --font-interface: 'DM Sans', sans-serif;
    --font-reading:   'Source Serif 4', serif;
    --font-mono:      'Space Mono', monospace;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Full-page takeover ── */
html, body {
    width: 100% !important;
    min-height: 100vh !important;
    background: var(--void) !important;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(123,47,255,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 90%, rgba(0,212,255,0.05) 0%, transparent 60%),
        radial-gradient(ellipse 40% 30% at 50% 50%, rgba(26,107,255,0.04) 0%, transparent 70%);
    background-attachment: fixed;
}

/* Override ALL gradio container constraints */
.gradio-container,
.gradio-container > *,
.contain,
#root,
.app {
    max-width: 100% !important;
    width: 100% !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    font-family: var(--font-interface) !important;
    color: var(--pearl) !important;
}

/* Remove gradio default white bg panels */
.gradio-container .prose,
.gradio-container .wrap,
footer,
.gradio-container > .main > .wrap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Hide gradio footer */
footer { display: none !important; }

/* Main content wrapper */
.sakina-app-wrapper {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 1rem;
    width: 100%;
}

/* ── Header ── */
.sakina-header {
    text-align: center;
    padding: clamp(2rem, 5vw, 4rem) 1rem clamp(1.5rem, 3vw, 2.5rem);
    position: relative;
    overflow: hidden;
}
.sakina-header::after {
    content: '';
    position: absolute; bottom: 0; left: 5%; right: 5%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,212,255,0.3), rgba(123,47,255,0.3), transparent);
}
.sakina-logo {
    font-family: var(--font-display);
    font-size: clamp(1.6rem, 6vw, 3.4rem);
    font-weight: 900;
    letter-spacing: clamp(2px, 1vw, 6px);
    text-transform: uppercase;
    background: linear-gradient(135deg, #818cf8 0%, #c084fc 40%, var(--arc) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    line-height: 1; margin-bottom: 0.6rem;
    animation: logoGlow 3s ease-in-out infinite alternate;
}
@keyframes logoGlow {
    from { filter: drop-shadow(0 0 20px rgba(123,47,255,0.2)); }
    to   { filter: drop-shadow(0 0 40px rgba(0,212,255,0.3)); }
}
.sakina-tagline {
    font-family: var(--font-reading);
    font-style: italic;
    color: rgba(238,238,255,0.4);
    font-size: clamp(0.78rem, 2vw, 1rem);
    letter-spacing: 0.5px;
    margin-bottom: 1rem;
}
.sakina-badges {
    display: flex; justify-content: center; gap: 0.5rem; flex-wrap: wrap;
}
.badge {
    font-family: var(--font-mono);
    font-size: clamp(0.55rem, 1.2vw, 0.65rem);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
}
.badge-pulse { background: rgba(123,47,255,0.12); border: 1px solid rgba(123,47,255,0.3); color: #a78bfa; }
.badge-arc   { background: rgba(0,212,255,0.08);  border: 1px solid rgba(0,212,255,0.2);  color: var(--arc); }
.badge-mono  { background: rgba(238,238,255,0.04); border: 1px solid rgba(238,238,255,0.1); color: rgba(238,238,255,0.3); }

/* ── Email verification notice ── */
.email-verify-notice {
    background: linear-gradient(135deg, rgba(255,184,0,0.06), rgba(255,184,0,0.02));
    border: 1px solid rgba(255,184,0,0.25);
    border-left: 3px solid var(--warn);
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 1.25rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}
.email-verify-icon {
    font-size: 1rem;
    flex-shrink: 0;
    margin-top: 1px;
}
.email-verify-text {
    font-family: var(--font-interface);
    font-size: 0.82rem;
    color: rgba(255,184,0,0.85);
    line-height: 1.55;
}
.email-verify-text strong {
    color: var(--warn);
    display: block;
    margin-bottom: 2px;
    font-size: 0.78rem;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    font-family: var(--font-mono);
}

/* ── Auth panel ── */
.auth-panel {
    background: rgba(13,13,43,0.7);
    border: 1px solid rgba(123,47,255,0.2);
    border-radius: 20px;
    padding: clamp(1.5rem, 4vw, 2.5rem) clamp(1.25rem, 4vw, 2.25rem);
    margin: 1rem auto;
    max-width: 520px;
    width: 100%;
    backdrop-filter: blur(20px);
    box-shadow: 0 20px 60px rgba(0,0,0,0.4), 0 0 40px rgba(123,47,255,0.05);
    animation: panelIn 0.5s ease-out;
}
@keyframes panelIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.auth-heading {
    font-family: var(--font-display);
    font-size: clamp(0.85rem, 2vw, 1.1rem);
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--pearl);
    margin-bottom: 0.3rem;
    text-transform: uppercase;
}
.auth-sub {
    font-family: var(--font-reading);
    font-style: italic;
    color: rgba(238,238,255,0.35);
    font-size: 0.88rem;
    line-height: 1.6;
    margin-bottom: 1.25rem;
}

/* ── User bar ── */
.user-bar {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    background: rgba(13,13,43,0.6);
    border: 1px solid rgba(123,47,255,0.2);
    border-radius: 14px;
    padding: 0.8rem 1.1rem;
    margin: 0 0 0.75rem;
    flex-wrap: wrap;
}
.user-avatar {
    width: 40px; height: 40px; border-radius: 50%;
    background: linear-gradient(135deg, var(--pulse), var(--current));
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display);
    font-weight: 700; font-size: 0.95rem; color: white;
    flex-shrink: 0;
    border: 2px solid rgba(123,47,255,0.4);
    box-shadow: 0 0 14px rgba(123,47,255,0.2);
}
.user-name {
    font-family: var(--font-interface);
    font-weight: 600; font-size: 0.9rem; color: var(--pearl);
}
.user-email {
    font-family: var(--font-mono);
    font-size: 0.65rem; color: rgba(238,238,255,0.3); margin-top: 1px;
}
.user-skn {
    font-family: var(--font-mono);
    font-size: 0.58rem; color: #a78bfa;
    margin-top: 2px; word-break: break-all;
    letter-spacing: 0.5px;
    display: none; /* hidden on small screens, shown on hover/larger */
}
@media (min-width: 600px) {
    .user-skn { display: block; }
}
.chat-name-badge {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    background: rgba(0,212,255,0.08);
    border: 1px solid rgba(0,212,255,0.2);
    color: var(--arc);
    padding: 4px 10px;
    border-radius: 20px;
    letter-spacing: 0.5px;
    white-space: nowrap;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-left: auto;
}

/* ── Inputs ── */
textarea, input[type=text], input[type=password], input[type=email] {
    background: rgba(5,5,8,0.8) !important;
    border: 1px solid rgba(123,47,255,0.2) !important;
    border-radius: 12px !important;
    color: var(--pearl) !important;
    font-family: var(--font-interface) !important;
    font-size: 0.92rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
textarea:focus, input:focus {
    border-color: var(--pulse) !important;
    box-shadow: 0 0 0 3px rgba(123,47,255,0.1) !important;
    outline: none !important;
}
label {
    color: rgba(238,238,255,0.35) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.68rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* ── Buttons ── */
.gr-button-primary, button.primary {
    background: linear-gradient(135deg, var(--pulse), var(--current)) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-family: var(--font-interface) !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    transition: opacity 0.2s, transform 0.2s, box-shadow 0.2s !important;
    box-shadow: 0 4px 20px rgba(123,47,255,0.2) !important;
}
.gr-button-primary:hover, button.primary:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 28px rgba(123,47,255,0.35) !important;
}
.gr-button-secondary, button.secondary {
    background: transparent !important;
    border: 1px solid rgba(123,47,255,0.25) !important;
    border-radius: 10px !important;
    color: rgba(238,238,255,0.4) !important;
    font-family: var(--font-interface) !important;
    transition: border-color 0.2s, color 0.2s !important;
}
.gr-button-secondary:hover, button.secondary:hover {
    border-color: var(--arc) !important;
    color: var(--arc) !important;
}

/* ── Continue chat button ── */
.continue-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 1rem;
    padding: 7px 16px;
    background: rgba(0,212,255,0.06);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 8px;
    color: var(--arc);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: background 0.2s, border-color 0.2s, transform 0.15s;
    text-transform: uppercase;
}
.continue-btn:hover {
    background: rgba(0,212,255,0.12);
    border-color: rgba(0,212,255,0.4);
    transform: translateY(-1px);
}

/* ── Chat bubbles ── */
.message.user {
    background: rgba(26,107,255,0.08) !important;
    border: 1px solid rgba(26,107,255,0.2) !important;
    border-radius: 18px 18px 4px 18px !important;
    color: var(--pearl) !important;
    font-family: var(--font-interface) !important;
}
.message.bot {
    background: rgba(13,13,43,0.85) !important;
    border: 1px solid rgba(123,47,255,0.15) !important;
    border-radius: 18px 18px 18px 4px !important;
    color: var(--pearl) !important;
    font-family: var(--font-interface) !important;
}

/* ── History ── */
.history-container { display: flex; flex-direction: column; gap: 1rem; padding: 0.5rem 0; }
.session-card {
    background: rgba(13,13,43,0.6);
    border: 1px solid rgba(123,47,255,0.12);
    border-radius: 16px;
    padding: clamp(1rem, 3vw, 1.4rem);
    transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
    animation: cardIn 0.4s ease-out;
}
@keyframes cardIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.session-card:hover {
    border-color: rgba(0,212,255,0.25);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}
.session-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.5rem;
    gap: 0.75rem;
    flex-wrap: wrap;
}
.session-name {
    font-family: var(--font-display);
    font-size: clamp(0.65rem, 1.5vw, 0.78rem);
    font-weight: 600;
    letter-spacing: 1px;
    color: var(--arc);
    text-transform: uppercase;
    flex: 1;
    min-width: 120px;
}
.session-meta {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: rgba(238,238,255,0.2);
    white-space: nowrap;
}
.session-preview {
    font-family: var(--font-reading);
    font-style: italic;
    font-size: 0.82rem;
    color: rgba(238,238,255,0.3);
    margin-bottom: 0.85rem;
    border-left: 2px solid rgba(123,47,255,0.3);
    padding-left: 0.75rem;
}
.session-messages { display: flex; flex-direction: column; gap: 0.6rem; }
.msg-pair {
    background: rgba(5,5,8,0.5);
    border: 1px solid rgba(238,238,255,0.04);
    border-radius: 10px;
    padding: 0.75rem;
}
.msg-q {
    font-family: var(--font-interface);
    font-weight: 500;
    font-size: clamp(0.75rem, 2vw, 0.83rem);
    color: rgba(238,238,255,0.7);
    margin-bottom: 0.4rem;
}
.msg-a {
    font-family: var(--font-mono);
    font-size: clamp(0.65rem, 1.5vw, 0.72rem);
    color: rgba(238,238,255,0.3);
    line-height: 1.6;
}
.msg-more {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: rgba(123,47,255,0.5);
    text-align: center;
    padding: 0.4rem;
    letter-spacing: 0.5px;
}
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: rgba(238,238,255,0.2);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    letter-spacing: 0.5px;
    line-height: 2.2;
}

/* ── Tabs ── */
.tab-nav button {
    font-family: var(--font-mono) !important;
    font-size: 0.68rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: rgba(238,238,255,0.3) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.2s, border-color 0.2s !important;
    padding: 8px 14px !important;
}
.tab-nav button.selected {
    color: var(--arc) !important;
    border-bottom-color: var(--arc) !important;
}

/* ── Footer ── */
.sakina-footer {
    text-align: center;
    padding: 2rem 1rem 3rem;
    border-top: 1px solid rgba(123,47,255,0.08);
    margin-top: 2rem;
}
.footer-line1 {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(238,238,255,0.1);
}
.footer-line2 {
    font-family: var(--font-reading);
    font-style: italic;
    font-size: 0.8rem;
    margin-top: 0.5rem;
    background: linear-gradient(135deg, #818cf8, var(--arc));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(123,47,255,0.3); border-radius: 3px; }

/* ── Misc ── */
.gr-form { background: transparent !important; }
.gr-box { background: transparent !important; border: none !important; }

/* ── Responsive overrides ── */
@media (max-width: 600px) {
    .user-bar { padding: 0.65rem 0.85rem; gap: 0.6rem; }
    .chat-name-badge { max-width: 100px; font-size: 0.58rem; }
    .auth-panel { border-radius: 16px; }
    .session-card { padding: 0.85rem; }
    .continue-btn { font-size: 0.65rem; padding: 6px 12px; }
    .sakina-badges { gap: 0.35rem; }
}
@media (max-width: 400px) {
    .chat-name-badge { display: none; }
    .user-skn { display: none !important; }
}

/* ── Chatbot container fill ── */
.chatbot-wrap { 
    border: 1px solid rgba(123,47,255,0.15) !important;
    border-radius: 16px !important;
    background: rgba(5,5,8,0.5) !important;
    overflow: hidden !important;
}
"""

EMAIL_VERIFY_NOTICE = """
<div class="email-verify-notice">
    <div class="email-verify-icon">⚠️</div>
    <div class="email-verify-text">
        <strong>Coming Soon: Email Verification Required</strong>
        In an upcoming version, all accounts will require email verification before activation.
        Please use an email address you have full access to — you will need it to verify your account and recover access in the future.
    </div>
</div>
"""

EXAMPLES = [
    ["What is fire from a scientific perspective?"],
    ["Explain love through neuroscience and chemistry"],
    ["What is the mathematics behind music?"],
    ["How does the brain create consciousness?"],
    ["What is the science of happiness?"],
    ["Explain war using game theory and physics"],
    ["What happens to our bodies when we die?"],
    ["Explain addiction from a neurological perspective"],
    ["What is time, scientifically?"],
    ["What is God from a STEM perspective?"],
]

# ── App ───────────────────────────────────────────────────────────────────────
with gr.Blocks(css=CSS, title="Hallvorn Sakina") as demo:

    session_id     = gr.State(lambda: str(uuid.uuid4()))
    user_state     = gr.State(None)
    chat_name_st   = gr.State("New Chat")

    # Header
    gr.HTML("""
    <div class="sakina-header">
        <div class="sakina-logo">Hallvorn Sakina</div>
        <div class="sakina-tagline">Revealing the scientific architecture of everything that exists</div>
        <div class="sakina-badges">
            <span class="badge badge-pulse">Elite STEM Intelligence</span>
            <span class="badge badge-arc">Powered by Hallvorn</span>
            <span class="badge badge-mono">sakina.hallvorn.com</span>
        </div>
    </div>
    """)

    # ── Auth ──────────────────────────────────────────────────────────────
    with gr.Group(visible=True) as auth_panel:
        with gr.Tabs():
            with gr.Tab("Sign In"):
                gr.HTML("""
                <div class="auth-panel">
                    <div class="auth-heading">Welcome Back</div>
                    <div class="auth-sub">Sign in to continue your STEM journey with Sakina.</div>
                </div>
                """)
                li_email = gr.Textbox(label="Email Address", placeholder="you@example.com")
                li_pass  = gr.Textbox(label="Passcode", type="password", placeholder="Your passcode")
                li_btn   = gr.Button("Sign In to Sakina", variant="primary", size="lg")
                li_msg   = gr.HTML("")

            with gr.Tab("Create Account"):
                gr.HTML("""
                <div class="auth-panel">
                    <div class="auth-heading">Join Sakina</div>
                    <div class="auth-sub">Create your account and unlock elite STEM intelligence by Hallvorn.</div>
                </div>
                """ + EMAIL_VERIFY_NOTICE)
                su_name  = gr.Textbox(label="Full Name", placeholder="Your full name")
                su_email = gr.Textbox(label="Email Address", placeholder="you@example.com")
                su_pass  = gr.Textbox(label="Passcode (min 6 chars)", type="password", placeholder="Choose a passcode")
                su_btn   = gr.Button("Create Sakina Account", variant="primary", size="lg")
                su_msg   = gr.HTML("")

    # ── Chat ──────────────────────────────────────────────────────────────
    with gr.Group(visible=False) as chat_panel:

        user_bar_html = gr.HTML("")

        # Hidden inputs for session resume (triggered by JS from history cards)
        resume_session_input = gr.Textbox(visible=False, elem_id="resume-session-input")
        resume_session_btn   = gr.Button("Resume", visible=False, elem_id="resume-session-btn")

        with gr.Tabs() as main_tabs:
            with gr.Tab("Chat"):
                chatbot = gr.Chatbot(
                    value=[], height=500,
                    show_label=False,
                    elem_classes=["chatbot-wrap"],
                    avatar_images=(
                        None,
                        "https://api.dicebear.com/7.x/bottts/svg?seed=sakina&backgroundColor=7B2FFF"
                    ),
                    render_markdown=True,
                    bubble_full_width=False,
                )
                with gr.Row():
                    msg_box  = gr.Textbox(
                        placeholder="Ask Sakina anything — she reveals the STEM in everything...",
                        show_label=False, scale=9, container=False,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1, min_width=80)
                gr.Examples(examples=EXAMPLES, inputs=msg_box, label="Try asking Sakina...")

            with gr.Tab("My Chats"):
                ref_btn   = gr.Button("↻  Refresh History", variant="secondary", size="sm")
                hist_html = gr.HTML("""<div class="empty-state">Your conversation history will appear here.<br>Start a chat to begin building your archive.</div>""")

        with gr.Row():
            new_chat_btn = gr.Button("+ New Chat", variant="secondary", size="sm")
            logout_btn   = gr.Button("Sign Out", variant="secondary", size="sm")

    # Footer
    gr.HTML("""
    <div class="sakina-footer">
        <div class="footer-line1">Hallvorn Sakina · STEM Intelligence · sakina.hallvorn.com</div>
        <div class="footer-line2">Inspired by Sakina Haruna — Neurosurgeon</div>
    </div>
    """)

    # ── Handlers ──────────────────────────────────────────────────────────

    def on_signup(name, email, passcode):
        ok, text = register_user(email, passcode, name)
        if ok:
            return gr.update(visible=True), gr.update(visible=False), msg_status(text, True), ""
        return gr.update(visible=True), gr.update(visible=False), "", msg_status(text, False)

    su_btn.click(
        fn=on_signup,
        inputs=[su_name, su_email, su_pass],
        outputs=[auth_panel, chat_panel, li_msg, su_msg],
    )

    def on_login(email, passcode, sid):
        user, text = login_user(email, passcode)
        if user:
            history  = load_session_history(user["id"], sid)
            bar      = build_user_bar(user, "New Chat")
            all_hist = load_all_history(user["id"])
            hist     = build_history_html(all_hist)
            return (
                gr.update(visible=False), gr.update(visible=True),
                msg_status(text, True), user, history, bar, hist, "New Chat"
            )
        return (
            gr.update(visible=True), gr.update(visible=False),
            msg_status(text, False), None, [], "", "", "New Chat"
        )

    li_btn.click(
        fn=on_login,
        inputs=[li_email, li_pass, session_id],
        outputs=[auth_panel, chat_panel, li_msg, user_state, chatbot, user_bar_html, hist_html, chat_name_st],
    )

    def on_send(message, history, sid, user_st, chat_name):
        if not message or not message.strip():
            return history, "", chat_name, ""
        reply, new_name = chat(message, history, sid, user_st, chat_name)
        new_history = history + [(message.strip(), reply)]
        bar = build_user_bar(user_st, new_name) if user_st else ""
        return new_history, "", new_name, bar

    send_btn.click(
        fn=on_send,
        inputs=[msg_box, chatbot, session_id, user_state, chat_name_st],
        outputs=[chatbot, msg_box, chat_name_st, user_bar_html],
    )
    msg_box.submit(
        fn=on_send,
        inputs=[msg_box, chatbot, session_id, user_state, chat_name_st],
        outputs=[chatbot, msg_box, chat_name_st, user_bar_html],
    )

    def on_new_chat(user_st):
        new_sid = str(uuid.uuid4())
        bar = build_user_bar(user_st, "New Chat") if user_st else ""
        return [], new_sid, "New Chat", bar

    new_chat_btn.click(
        fn=on_new_chat,
        inputs=[user_state],
        outputs=[chatbot, session_id, chat_name_st, user_bar_html],
    )

    def on_refresh(user_st):
        if not user_st:
            return """<div class="empty-state">Please sign in first.</div>"""
        return build_history_html(load_all_history(user_st["id"]))

    ref_btn.click(fn=on_refresh, inputs=[user_state], outputs=[hist_html])

    def on_logout():
        return (
            gr.update(visible=True), gr.update(visible=False),
            None, [], "", "", "New Chat"
        )

    logout_btn.click(
        fn=on_logout,
        inputs=[],
        outputs=[auth_panel, chat_panel, user_state, chatbot, user_bar_html, li_msg, chat_name_st],
    )

    # ── Resume session handler ──────────────────────────────────────────
    def on_resume_session(target_session_id, user_st):
        """Load an old chat session so the user can continue it."""
        if not user_st or not target_session_id:
            return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        history = load_session_history(user_st["id"], target_session_id)
        # Determine the chat name from history records
        try:
            result = (
                supabase.table("sakina_conversations")
                .select("chat_name")
                .eq("user_id", user_st["id"])
                .eq("session_id", target_session_id)
                .limit(1)
                .execute()
            )
            chat_name = (result.data[0].get("chat_name") or "Resumed Chat") if result and result.data else "Resumed Chat"
        except Exception:
            chat_name = "Resumed Chat"
        bar = build_user_bar(user_st, chat_name)
        # Switch to Chat tab by returning tab index update — using gr.update on tabs
        return history, target_session_id, chat_name, bar, gr.update(selected=0)

    resume_session_btn.click(
        fn=on_resume_session,
        inputs=[resume_session_input, user_state],
        outputs=[chatbot, session_id, chat_name_st, user_bar_html, main_tabs],
    )

# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
