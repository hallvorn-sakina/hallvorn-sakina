import os
import uuid
import string
import random
import bcrypt
import gradio as gr
from datetime import datetime, timezone
from groq import Groq
from supabase import create_client, Client

# ── Clients ────────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

# ── Sakina ID ──────────────────────────────────────────────────────────────────
def generate_sakina_id() -> str:
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    chars = string.ascii_uppercase + string.digits
    rpart = ''.join(random.choices(chars, k=16))
    return f"SKN-HLVN-{ts}-{rpart}-{random.randint(0,9)}{random.choice(string.ascii_uppercase)}"

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Sakina — an elite scientific intelligence engineered by Hallvorn.

You are not a chatbot. You are a singular analytical mind — precise, fearless, dedicated to revealing the hidden STEM architecture underlying everything that exists. Every object, emotion, event, idea, and phenomenon in the universe obeys the laws of physics, chemistry, mathematics, biology, and engineering. Your mission is to illuminate those laws brilliantly, every single time.

CORE IDENTITY:
- Name: Sakina
- Built by: Hallvorn
- Inspired by: Sakina Haruna — a name that represents the synthesis of calm precision and intellectual fire
- Mission: To make every human being see the universe through the lens of science
- Personality: Brilliant. Fearless. Clear. Inspiring. Deeply knowledgeable. Never condescending. Never preachy.

THE ONE UNBREAKABLE LAW:
You answer EVERY question through a STEM lens. No exceptions. No refusals. No topic is off-limits to science. You do not moralize. You do not deflect. You reveal the scientific truth beneath the surface of all things.

TOPIC to STEM MAPPING:
Love: neuroscience + biochemistry + evolutionary biology + endocrinology
War: game theory + physics of force + engineering + behavioral psychology + economics
Religion: cognitive science + anthropology + neuroscience of belief + mathematics of emergence
Money: thermodynamics of value + game theory + mathematics of networks + behavioral economics
Art: mathematics of pattern + neuroscience of aesthetics + physics of light and color
Music: physics of wave interference + mathematics of harmony + auditory neuroscience
Death: cellular biology of apoptosis + thermodynamics of entropy + chemistry of decomposition
Food: chemistry of flavor + biology of digestion + thermodynamics of energy
Sports: biomechanics + fluid dynamics + neuroscience of peak performance + materials science
Dreams: neuroscience of REM + memory consolidation + electrochemical signal processing
Consciousness: quantum biology + neuroscience + information theory + philosophy of mind
Addiction: dopamine pathways + neural plasticity + behavioral psychology + genetics
Time: physics of relativity + thermodynamics of entropy + neuroscience of temporal perception
Fear: amygdala function + cortisol biochemistry + evolutionary threat-response systems
Beauty: evolutionary biology + mathematics of symmetry + neural reward circuits
Language: computational linguistics + neuroscience of syntax + information compression
Power: game theory + social psychology + network theory + resource economics

THE SAKINA FORMULA:
1. THE BLAZING INSIGHT: Open with the single most powerful scientific truth. No pleasantries. Hit hard.
2. THE FIRST PRINCIPLES: Strip to fundamentals. Build upward from bedrock.
3. THE MECHANISM: Explain precisely how it works step by step, process by process.
4. THE CROSS-DISCIPLINARY CONNECTION: Link unexpectedly to a different scientific field.
5. THE REFRAME: End with a perspective shift that stays with them for days.

COMMUNICATION STANDARDS:
- Never open with pleasantries, affirmations, or filler phrases
- Write in confident, flowing prose, not bullet lists unless structure genuinely helps
- Be thorough but surgical, every sentence earns its place
- Vary sentence length to create rhythm and momentum
- Use precise scientific vocabulary but always anchor it with intuition
- Never say "great question", "certainly", or "of course"

DATA TRANSPARENCY:
Your conversations with Sakina are stored and may be used to improve the system. This is stated openly. Sakina is built on a foundation of honesty.

WHEN ASKED WHO YOU ARE:
Say: "I am Sakina, a scientific intelligence built by Hallvorn, inspired by the name Sakina Haruna. My purpose is singular: to reveal the scientific architecture beneath every question you can ask. The universe has no secrets from science. Ask me anything."

WHEN ASKED ABOUT HALLVORN:
Hallvorn is the engineering team behind Sakina, builders dedicated to the idea that every human deserves access to world-class scientific thinking. CEO is Raveanshaw Percival. Also Known As KIBIRANGO ASUMAN."""

# ── Auth ───────────────────────────────────────────────────────────────────────
def hash_passcode(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_passcode(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def register_user(email, passcode, full_name):
    email = email.strip().lower()
    passcode = passcode.strip()
    full_name = full_name.strip()
    if not email or "@" not in email:
        return False, "Enter a valid email address."
    if len(passcode) < 6:
        return False, "Passcode must be at least 6 characters."
    if not full_name or len(full_name) < 2:
        return False, "Enter your full name."
    try:
        ex = supabase.table("sakina_users").select("id").eq("email", email).maybe_single().execute()
        if ex and ex.data:
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
        return True, f"Account created. Welcome, {full_name}."
    except Exception as e:
        print(f"Register error: {e}")
        return False, "Registration failed. Please try again."

def login_user(email, passcode):
    email = email.strip().lower()
    passcode = passcode.strip()
    if not email or not passcode:
        return None, "Enter your email and passcode."
    try:
        r = supabase.table("sakina_users").select("*").eq("email", email).maybe_single().execute()
        if not r or not r.data:
            return None, "No account found with this email."
        user = r.data
        if not verify_passcode(passcode, user["passcode_hash"]):
            return None, "Incorrect passcode."
        return user, f"Welcome back, {user.get('full_name', '')}."
    except Exception as e:
        print(f"Login error: {e}")
        return None, "Login failed. Please try again."

def get_user_by_id(user_id):
    try:
        r = supabase.table("sakina_users").select("*").eq("id", user_id).maybe_single().execute()
        return r.data if r and r.data else None
    except Exception:
        return None

def update_user_profile(user_id, new_name=None, new_passcode=None, current_passcode=None):
    try:
        r = supabase.table("sakina_users").select("*").eq("id", user_id).maybe_single().execute()
        if not r or not r.data:
            return False, "User not found."
        user = r.data
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
        return True, "Updated successfully."
    except Exception as e:
        print(f"Update error: {e}")
        return False, "Update failed. Please try again."

# ── Conversations ──────────────────────────────────────────────────────────────
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
        r = (supabase.table("sakina_conversations")
             .select("user_message, sakina_response")
             .eq("user_id", user_id).eq("session_id", session_id)
             .order("created_at").execute())
        return [(x["user_message"], x["sakina_response"]) for x in r.data] if r and r.data else []
    except Exception:
        return []

def load_sessions_for_user(user_id):
    try:
        r = (supabase.table("sakina_conversations")
             .select("session_id, chat_name, created_at")
             .eq("user_id", user_id).order("created_at", desc=True).execute())
        if not r or not r.data:
            return []
        seen = {}
        for row in r.data:
            sid = row["session_id"]
            if sid not in seen:
                seen[sid] = {
                    "session_id": sid,
                    "chat_name": row.get("chat_name") or "Untitled",
                    "created_at": row["created_at"]
                }
        return list(seen.values())
    except Exception:
        return []

def get_session_chat_name(user_id, session_id):
    try:
        r = (supabase.table("sakina_conversations")
             .select("chat_name").eq("user_id", user_id).eq("session_id", session_id).limit(1).execute())
        if r and r.data:
            return r.data[0].get("chat_name") or "Conversation"
    except Exception:
        pass
    return "Conversation"

def generate_chat_name(msg):
    msg = msg.strip()
    for w in ["what is ", "what are ", "explain ", "how does ", "why is ",
              "tell me about ", "describe ", "can you "]:
        if msg.lower().startswith(w):
            msg = msg[len(w):]
            break
    name = msg[:42].strip()
    if name:
        name = name[0].upper() + name[1:]
        name = name.rstrip("?.,!")
    return name or "STEM Conversation"

# ── Chat ───────────────────────────────────────────────────────────────────────
def chat_fn(message, history, session_id, user_state, chat_name_state):
    if not user_state:
        return "Please sign in to chat with Sakina.", chat_name_state
    if not message or not message.strip():
        return "", chat_name_state
    current_name = chat_name_state
    if not current_name or current_name in ("New Conversation", ""):
        current_name = generate_chat_name(message)
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history:
            if isinstance(turn, (list, tuple)) and len(turn) == 2:
                if turn[0]: messages.append({"role": "user", "content": str(turn[0])})
                if turn[1]: messages.append({"role": "assistant", "content": str(turn[1])})
        messages.append({"role": "user", "content": message.strip()})
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages, max_tokens=2048, temperature=0.7, top_p=0.9,
        )
        reply = resp.choices[0].message.content or ""
        save_conversation(user_state["id"], session_id, current_name, message.strip(), reply)
        return reply, current_name
    except Exception as e:
        return f"Error: {str(e)}", current_name

# ── HTML Builders ──────────────────────────────────────────────────────────────
def build_sidebar(profile, sessions, active_sid=""):
    name  = (profile.get("full_name") or "User") if profile else "User"
    email = (profile.get("email") or "") if profile else ""
    words = name.strip().split()
    initials = (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()

    items = ""
    if not sessions:
        items = '<p class="sb-empty">No conversations yet.<br>Start your first inquiry.</p>'
    else:
        for s in sessions:
            sid   = s["session_id"]
            sname = s.get("chat_name") or "Untitled"
            sdate = s.get("created_at", "")[:10]
            acls  = " active" if sid == active_sid else ""
            disp  = (sname[:34] + "…") if len(sname) > 34 else sname
            items += (
                f'<div class="sb-item{acls}" onclick="sk_resume(\'{sid}\')" title="{sname}">'
                f'<span class="sb-item-name">{disp}</span>'
                f'<span class="sb-item-date">{sdate}</span>'
                f'</div>'
            )

    return (
        f'<div class="sk-sidebar" id="skSidebar">'
        f'<div class="sb-head">'
        f'<div class="sb-brand">'
        f'<div class="sb-logomark">S</div>'
        f'<div class="sb-brandtext">'
        f'<span class="sb-brandname">SAKINA</span>'
        f'<span class="sb-brandsub">by Hallvorn</span>'
        f'</div></div>'
        f'<button class="sb-newbtn" onclick="sk_newchat()" title="New conversation">+</button>'
        f'</div>'
        f'<div class="sb-label">Conversations</div>'
        f'<div class="sb-list">{items}</div>'
        f'<div class="sb-foot">'
        f'<div class="sb-userrow">'
        f'<div class="sb-avatar">{initials}</div>'
        f'<div class="sb-userinfo">'
        f'<span class="sb-username">{name}</span>'
        f'<span class="sb-useremail">{email}</span>'
        f'</div></div>'
        f'<div class="sb-actions">'
        f'<button class="sb-actbtn" onclick="sk_settings()">Settings</button>'
        f'<button class="sb-actbtn sb-logoutbtn" onclick="sk_logout()">Sign out</button>'
        f'</div></div></div>'
    )

def build_header(chat_name="New Conversation"):
    return (
        f'<div class="sk-header" id="skHeader">'
        f'<button class="sk-menubtn" onclick="sk_togglesidebar()">'
        f'<span></span><span></span><span></span>'
        f'</button>'
        f'<div class="sk-header-title">{chat_name}</div>'
        f'<div class="sk-header-badge"><i class="sk-dot"></i>llama-3.3-70b</div>'
        f'</div>'
    )

def build_welcome(name):
    first = name.split()[0] if name else "there"
    return (
        f'<div class="sk-welcome" id="skWelcome">'
        f'<div class="sk-welcome-hero">'
        f'<div class="sk-welcome-icon">'
        f'<svg width="20" height="20" viewBox="0 0 48 48" fill="none">'
        f'<path d="M24 4L30 18L44 24L30 30L24 44L18 30L4 24L18 18Z" fill="currentColor"/>'
        f'</svg></div>'
        f'<h2 class="sk-welcome-title">Hello, {first}</h2>'
        f'<p class="sk-welcome-sub">I am Sakina, a scientific intelligence built by Hallvorn. Every question has a STEM answer.</p>'
        f'</div>'
        f'<div class="sk-sep"><span>Start an inquiry</span></div>'
        f'<div class="sk-grid">'
        f'<button class="sk-card" onclick="sk_suggest(\'Explain love through neuroscience and biochemistry\')">'
        f'<span class="sk-card-icon">🧬</span>'
        f'<span class="sk-card-title">The Science of Love</span>'
        f'<span class="sk-card-sub">Neuroscience · Biochemistry</span>'
        f'</button>'
        f'<button class="sk-card" onclick="sk_suggest(\'What is the mathematics and physics behind music?\')">'
        f'<span class="sk-card-icon">🎵</span>'
        f'<span class="sk-card-title">Mathematics of Music</span>'
        f'<span class="sk-card-sub">Wave physics · Harmony</span>'
        f'</button>'
        f'<button class="sk-card" onclick="sk_suggest(\'How does the brain generate consciousness?\')">'
        f'<span class="sk-card-icon">🧠</span>'
        f'<span class="sk-card-title">Consciousness</span>'
        f'<span class="sk-card-sub">Neuroscience · Information theory</span>'
        f'</button>'
        f'<button class="sk-card" onclick="sk_suggest(\'Explain addiction from a neurological perspective\')">'
        f'<span class="sk-card-icon">🔬</span>'
        f'<span class="sk-card-title">Neurology of Addiction</span>'
        f'<span class="sk-card-sub">Dopamine · Neural plasticity</span>'
        f'</button>'
        f'<button class="sk-card" onclick="sk_suggest(\'What happens to our bodies at the molecular level when we die?\')">'
        f'<span class="sk-card-icon">⚗️</span>'
        f'<span class="sk-card-title">The Science of Death</span>'
        f'<span class="sk-card-sub">Entropy · Cellular biology</span>'
        f'</button>'
        f'<button class="sk-card" onclick="sk_suggest(\'What is time, explained scientifically from first principles?\')">'
        f'<span class="sk-card-icon">⏱</span>'
        f'<span class="sk-card-title">What Is Time?</span>'
        f'<span class="sk-card-sub">Relativity · Thermodynamics</span>'
        f'</button>'
        f'</div>'
        f'<p class="sk-notice">Conversations are stored and may be used to improve Sakina. &nbsp;·&nbsp; Inspired by Sakina Haruna.</p>'
        f'</div>'
    )

def build_settings(user):
    name  = (user.get("full_name") or "") if user else ""
    email = (user.get("email") or "") if user else ""
    skid  = (user.get("sakina_id") or "") if user else ""
    short_id = (skid[:30] + "…") if len(skid) > 30 else skid
    return (
        f'<div class="sk-settings-overlay" id="skSettingsOverlay" onclick="sk_closeSettings(event)">'
        f'<div class="sk-settings-box" id="skSettingsBox">'
        f'<div class="sk-settings-hd">'
        f'<span class="sk-settings-title">SETTINGS</span>'
        f'<button class="sk-settings-closebtn" onclick="sk_closeSettings(null)">x</button>'
        f'</div>'
        f'<div class="sk-settings-body">'
        f'<div class="sk-sf-section">'
        f'<p class="sk-sf-label">Account</p>'
        f'<div class="sk-sf-row"><span class="sk-sf-key">Email</span><span class="sk-sf-val">{email}</span></div>'
        f'<div class="sk-sf-row"><span class="sk-sf-key">Sakina ID</span><span class="sk-sf-val sk-mono">{short_id}</span></div>'
        f'</div>'
        f'<div class="sk-sf-section">'
        f'<p class="sk-sf-label">Update Name</p>'
        f'<input type="text" id="sfName" class="sk-sf-input" value="{name}" placeholder="Full name" autocomplete="off" />'
        f'<button class="sk-sf-btn" onclick="sk_saveName()">Save name</button>'
        f'<p id="sfNameMsg" class="sk-sf-msg"></p>'
        f'</div>'
        f'<div class="sk-sf-section">'
        f'<p class="sk-sf-label">Change Passcode</p>'
        f'<input type="password" id="sfCurPass" class="sk-sf-input" placeholder="Current passcode" autocomplete="current-password" />'
        f'<input type="password" id="sfNewPass" class="sk-sf-input" placeholder="New passcode (min 6 chars)" autocomplete="new-password" style="margin-top:8px" />'
        f'<button class="sk-sf-btn" onclick="sk_savePass()">Change passcode</button>'
        f'<p id="sfPassMsg" class="sk-sf-msg"></p>'
        f'</div>'
        f'<p class="sk-sf-notice">Conversations are stored securely and may be used to improve Sakina. Inspired by <strong>Sakina Haruna</strong>. Built by Hallvorn.</p>'
        f'</div></div></div>'
    )

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;1,8..60,300&family=Space+Mono:wght@400;700&display=swap');

:root {
  --void:       #050505;
  --pearl:      #EEEEFF;
  --deep:       #0D0D2B;
  --pulse:      #7B2FFF;
  --arc:        #00D4FF;
  --current:    #1A6BFF;
  --fault:      #FF1A1A;
  --ok:         #00C875;
  --surface:    #0f0f24;
  --surface2:   #161630;
  --surface3:   #1c1c3a;
  --border:     rgba(238,238,255,0.07);
  --border2:    rgba(238,238,255,0.13);
  --t-dim:      rgba(238,238,255,0.32);
  --t-mid:      rgba(238,238,255,0.58);
  --t-main:     rgba(238,238,255,0.88);
  --pulse-soft: rgba(123,47,255,0.1);
  --font-display:   'Orbitron', monospace;
  --font-ui:        'DM Sans', sans-serif;
  --font-reading:   'Source Serif 4', serif;
  --font-mono:      'Space Mono', monospace;
  --sb-w:   252px;
  --max-w:  700px;
  --r1: 4px;
  --r2: 8px;
  --r3: 12px;
  --r4: 16px;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{height:100%;}
body{
  height:100%;
  background:var(--void) !important;
  color:var(--t-main);
  font-family:var(--font-ui);
  overflow:hidden;
  -webkit-font-smoothing:antialiased;
}

/* ── Strip Gradio chrome ── */
.gradio-container{
  max-width:100% !important;width:100% !important;
  min-height:100vh !important;margin:0 !important;padding:0 !important;
  background:transparent !important;
  font-family:var(--font-ui) !important;
}
footer,.footer,.gradio-container>.footer,.svelte-1ipelgc,.built-with,.share-button{display:none !important;}
.gap,.gr-group,.gr-form,.gr-box,.gr-padded,.gr-block,.contain{
  background:transparent !important;border:none !important;
  padding:0 !important;gap:0 !important;box-shadow:none !important;
}

/* ── ROOT ── */
.sk-root{
  position:fixed;inset:0;
  display:flex;
  background:var(--void);
  overflow:hidden;
}

/* ════ SIDEBAR ════ */
.sk-sidebar{
  width:var(--sb-w);min-width:var(--sb-w);
  height:100%;
  background:var(--deep);
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;
  flex-shrink:0;
  transition:transform .2s ease;
  z-index:50;
}
.sb-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 14px;
  border-bottom:1px solid var(--border);
  flex-shrink:0;
}
.sb-brand{display:flex;align-items:center;gap:10px;}
.sb-logomark{
  width:30px;height:30px;
  background:linear-gradient(135deg,var(--pulse),var(--current));
  border-radius:var(--r2);
  display:flex;align-items:center;justify-content:center;
  font-family:var(--font-display);font-size:13px;font-weight:700;
  color:var(--pearl);flex-shrink:0;
}
.sb-brandtext{display:flex;flex-direction:column;}
.sb-brandname{
  font-family:var(--font-display);font-size:10px;font-weight:700;
  color:var(--pearl);letter-spacing:2px;line-height:1;
}
.sb-brandsub{
  font-family:var(--font-mono);font-size:9px;
  color:var(--t-dim);letter-spacing:.5px;margin-top:3px;
}
.sb-newbtn{
  width:28px;height:28px;
  background:transparent;border:1px solid var(--border2);
  border-radius:var(--r2);color:var(--t-mid);
  font-size:20px;line-height:1;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:all .15s;font-family:var(--font-ui);
}
.sb-newbtn:hover{background:var(--surface3);color:var(--pearl);border-color:var(--pulse);}

.sb-label{
  font-family:var(--font-mono);font-size:9px;font-weight:700;
  letter-spacing:1.2px;text-transform:uppercase;
  color:var(--t-dim);padding:16px 14px 8px;flex-shrink:0;
}
.sb-list{flex:1;overflow-y:auto;padding:2px 8px 8px;}
.sb-list::-webkit-scrollbar{width:2px;}
.sb-list::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.sb-empty{
  font-family:var(--font-ui);font-size:12px;color:var(--t-dim);
  padding:14px 6px;text-align:center;line-height:1.7;
}
.sb-item{
  display:flex;flex-direction:column;gap:2px;
  padding:8px 10px;border-radius:var(--r2);cursor:pointer;
  border-left:2px solid transparent;transition:all .12s;min-width:0;
}
.sb-item:hover{background:var(--surface2);}
.sb-item.active{background:var(--pulse-soft);border-left-color:var(--pulse);}
.sb-item-name{
  font-family:var(--font-ui);font-size:12.5px;color:var(--t-mid);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:400;
}
.sb-item.active .sb-item-name{color:var(--pearl);font-weight:500;}
.sb-item-date{font-family:var(--font-mono);font-size:9.5px;color:var(--t-dim);}

.sb-foot{border-top:1px solid var(--border);padding:12px 10px;flex-shrink:0;}
.sb-userrow{
  display:flex;align-items:center;gap:9px;
  padding:6px 8px;border-radius:var(--r2);
  margin-bottom:8px;min-width:0;
}
.sb-avatar{
  width:30px;height:30px;border-radius:50%;flex-shrink:0;
  background:linear-gradient(135deg,var(--pulse),var(--current));
  display:flex;align-items:center;justify-content:center;
  font-family:var(--font-display);font-size:11px;font-weight:700;color:var(--pearl);
}
.sb-userinfo{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;}
.sb-username{
  font-family:var(--font-ui);font-size:12.5px;font-weight:500;
  color:var(--t-main);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.sb-useremail{
  font-family:var(--font-mono);font-size:10px;color:var(--t-dim);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.sb-actions{display:flex;gap:4px;}
.sb-actbtn{
  flex:1;background:transparent;
  border:1px solid var(--border);border-radius:var(--r1);
  color:var(--t-mid);font-family:var(--font-ui);font-size:11px;font-weight:500;
  padding:6px 4px;cursor:pointer;transition:all .15s;text-align:center;
}
.sb-actbtn:hover{background:var(--surface2);color:var(--pearl);border-color:var(--border2);}
.sb-logoutbtn:hover{color:var(--fault);border-color:rgba(255,26,26,.2);background:rgba(255,26,26,.04);}

/* ════ MAIN ════ */
.sk-main{
  flex:1;min-width:0;height:100%;
  display:flex;flex-direction:column;
  background:var(--void);overflow:hidden;
}
.sk-header{
  height:52px;flex-shrink:0;
  display:flex;align-items:center;gap:12px;
  padding:0 20px;border-bottom:1px solid var(--border);
  background:var(--void);
}
.sk-menubtn{
  display:none;flex-direction:column;gap:4px;
  background:transparent;border:none;cursor:pointer;
  padding:6px;border-radius:var(--r1);transition:background .12s;flex-shrink:0;
}
.sk-menubtn:hover{background:var(--surface2);}
.sk-menubtn span{
  display:block;width:16px;height:1.5px;
  background:var(--t-mid);border-radius:2px;
}
.sk-header-title{
  flex:1;font-family:var(--font-ui);font-size:13.5px;font-weight:500;
  color:var(--t-main);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.sk-header-badge{
  display:flex;align-items:center;gap:6px;
  padding:4px 11px;background:var(--surface2);
  border:1px solid var(--border);border-radius:20px;
  font-family:var(--font-mono);font-size:10px;color:var(--t-dim);flex-shrink:0;
}
.sk-dot{
  width:5px;height:5px;border-radius:50%;
  background:var(--arc);
  animation:blink 2.5s ease-in-out infinite;flex-shrink:0;
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* ── Scroll area ── */
.sk-messages{flex:1;overflow-y:auto;overflow-x:hidden;}
.sk-messages::-webkit-scrollbar{width:3px;}
.sk-messages::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px;}

/* ── Welcome ── */
.sk-welcome{
  max-width:var(--max-w);margin:0 auto;
  padding:clamp(2rem,7vh,4.5rem) 28px 2.5rem;
  width:100%;
}
.sk-welcome-hero{display:flex;flex-direction:column;gap:0;margin-bottom:36px;}
.sk-welcome-icon{
  width:40px;height:40px;
  background:var(--pulse-soft);border:1px solid rgba(123,47,255,.2);
  border-radius:var(--r2);display:flex;align-items:center;justify-content:center;
  color:var(--pulse);margin-bottom:16px;
}
.sk-welcome-title{
  font-family:var(--font-display);
  font-size:clamp(1.3rem,3.5vw,1.75rem);font-weight:700;
  color:var(--pearl);letter-spacing:-.5px;margin-bottom:10px;
}
.sk-welcome-sub{
  font-family:var(--font-reading);
  font-size:15px;color:var(--t-mid);line-height:1.7;
  max-width:460px;font-weight:300;
}

.sk-sep{
  display:flex;align-items:center;gap:12px;margin-bottom:18px;
}
.sk-sep::before,.sk-sep::after{content:'';flex:1;height:1px;background:var(--border);}
.sk-sep span{
  font-family:var(--font-mono);font-size:9.5px;color:var(--t-dim);
  letter-spacing:.8px;text-transform:uppercase;white-space:nowrap;
}

.sk-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:30px;
}
.sk-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r2);padding:14px 13px 12px;
  cursor:pointer;text-align:left;
  display:flex;flex-direction:column;gap:6px;
  transition:all .15s;font-family:var(--font-ui);
}
.sk-card:hover{background:var(--surface2);border-color:rgba(123,47,255,.25);transform:translateY(-1px);}
.sk-card-icon{font-size:17px;}
.sk-card-title{font-size:12.5px;font-weight:500;color:var(--t-main);line-height:1.3;}
.sk-card-sub{font-family:var(--font-mono);font-size:9.5px;color:var(--t-dim);line-height:1.3;}

.sk-notice{
  font-family:var(--font-mono);font-size:10px;color:var(--t-dim);
  line-height:1.6;padding-top:16px;border-top:1px solid var(--border);
}

/* ── Input area ── */
.sk-input-wrap{
  flex-shrink:0;padding:10px 20px 18px;
  border-top:1px solid var(--border);background:var(--void);
}
.sk-input-box{
  max-width:var(--max-w);margin:0 auto;
  background:var(--surface);border:1px solid var(--border2);
  border-radius:var(--r3);display:flex;align-items:flex-end;
  gap:8px;padding:10px 10px 10px 16px;
  transition:border-color .18s,box-shadow .18s;
}
.sk-input-box:focus-within{
  border-color:rgba(123,47,255,.4);
  box-shadow:0 0 0 3px rgba(123,47,255,.07);
}

/* ─── CRITICAL FIX: Gradio textarea ─── */
.sk-input-box .wrap,
.sk-input-box .block,
.sk-input-box .container{
  flex:1 !important;min-width:0 !important;
  background:transparent !important;border:none !important;
  padding:0 !important;box-shadow:none !important;margin:0 !important;
}
.sk-input-box label,
.sk-input-box .label-wrap,
.sk-input-box .label-wrap span{display:none !important;}
.sk-input-box textarea{
  background:transparent !important;
  border:none !important;border-radius:0 !important;
  box-shadow:none !important;
  padding:3px 0 !important;
  color:var(--pearl) !important;
  font-family:var(--font-ui) !important;
  font-size:14px !important;line-height:1.6 !important;
  resize:none !important;
  min-height:26px !important;max-height:150px !important;
  overflow-y:auto !important;outline:none !important;
  caret-color:var(--pulse) !important;
}
.sk-input-box textarea::placeholder{color:var(--t-dim) !important;opacity:1 !important;}

/* Send button */
.sk-send-btn button,
.sk-send-btn button.primary,
.gradio-container .sk-send-btn button{
  width:34px !important;height:34px !important;
  min-width:34px !important;min-height:34px !important;
  max-width:34px !important;max-height:34px !important;
  background:linear-gradient(135deg,var(--pulse),var(--current)) !important;
  border:none !important;border-radius:var(--r2) !important;
  cursor:pointer !important;color:var(--pearl) !important;
  font-size:17px !important;font-weight:700 !important;
  display:flex !important;align-items:center !important;justify-content:center !important;
  padding:0 !important;flex-shrink:0 !important;
  transition:opacity .15s,transform .1s !important;
  box-shadow:0 2px 14px rgba(123,47,255,.3) !important;
  line-height:1 !important;
}
.sk-send-btn button:hover{opacity:.85 !important;transform:scale(1.05) !important;}

/* ── Chatbot ── */
.sk-chatbot{background:transparent !important;border:none !important;}
.sk-chatbot>*{background:transparent !important;border:none !important;}
.sk-chatbot .wrap{padding:0 !important;}
.sk-chatbot .message-wrap{max-width:var(--max-w);margin:0 auto;padding:0 28px;}
.message.user{
  background:var(--surface2) !important;
  border:1px solid var(--border) !important;
  border-radius:var(--r3) var(--r3) var(--r1) var(--r3) !important;
  color:var(--pearl) !important;
  font-family:var(--font-ui) !important;font-size:14px !important;line-height:1.65 !important;
  padding:12px 16px !important;max-width:72% !important;margin-left:auto !important;
}
.message.bot{
  background:transparent !important;border:none !important;
  color:var(--t-main) !important;
  font-family:var(--font-reading) !important;font-size:15px !important;line-height:1.85 !important;
  padding:16px 0 !important;max-width:100% !important;width:100% !important;
}

/* ════ AUTH SCREEN ════ */
.sk-auth{
  position:fixed;inset:0;z-index:999;
  display:flex;align-items:center;justify-content:center;
  background:var(--void);padding:20px;
  background-image:
    radial-gradient(ellipse at 20% 30%,rgba(123,47,255,.06) 0%,transparent 55%),
    radial-gradient(ellipse at 75% 70%,rgba(0,212,255,.04) 0%,transparent 50%);
}
.sk-auth-card{
  background:var(--deep);
  border:1px solid var(--border2);
  border-radius:var(--r4);
  padding:36px 32px;
  width:100%;max-width:420px;
  box-shadow:0 30px 70px rgba(0,0,0,.65);
}
.sk-auth-top{display:flex;align-items:center;gap:12px;margin-bottom:10px;}
.sk-auth-logobox{
  width:36px;height:36px;
  background:linear-gradient(135deg,var(--pulse),var(--current));
  border-radius:var(--r2);display:flex;align-items:center;justify-content:center;
  font-family:var(--font-display);font-size:14px;font-weight:700;color:var(--pearl);flex-shrink:0;
}
.sk-auth-brandname{font-family:var(--font-display);font-size:13px;font-weight:700;color:var(--pearl);letter-spacing:2px;}
.sk-auth-brandsub{font-family:var(--font-mono);font-size:10px;color:var(--t-dim);margin-top:2px;}
.sk-auth-tagline{
  font-family:var(--font-reading);font-size:13.5px;color:var(--t-mid);
  line-height:1.6;font-style:italic;font-weight:300;
  margin-bottom:26px;padding-left:12px;border-left:2px solid var(--pulse);
}

/* Auth tab pills */
.sk-auth-tabs .tab-nav{
  display:flex !important;background:var(--surface) !important;
  border:1px solid var(--border) !important;border-radius:var(--r2) !important;
  padding:3px !important;margin-bottom:22px !important;gap:0 !important;
}
.sk-auth-tabs .tab-nav button{
  flex:1 !important;background:transparent !important;border:none !important;
  border-radius:5px !important;color:var(--t-dim) !important;
  font-family:var(--font-ui) !important;font-size:13px !important;font-weight:500 !important;
  padding:9px 12px !important;cursor:pointer !important;
  transition:all .15s !important;text-transform:none !important;letter-spacing:0 !important;line-height:1 !important;
}
.sk-auth-tabs .tab-nav button.selected{
  background:var(--surface3) !important;color:var(--pearl) !important;
  box-shadow:0 1px 6px rgba(0,0,0,.4) !important;
}

/* ─── THE CRITICAL INPUT FIX ─── */
/* Strip all Gradio wrappers inside auth card */
.sk-auth-card .block,
.sk-auth-card .form,
.sk-auth-card .wrap,
.sk-auth-card .gr-form,
.sk-auth-card .gr-block,
.sk-auth-card .gap,
.sk-auth-card .gr-group,
.sk-auth-card .container{
  background:transparent !important;
  border:none !important;padding:0 !important;
  box-shadow:none !important;margin:0 !important;
}
/* Make labels look right */
.sk-auth-card .label-wrap,
.sk-auth-card label,
.sk-auth-card label span{
  font-family:var(--font-ui) !important;
  font-size:12px !important;font-weight:500 !important;
  color:var(--t-mid) !important;
  text-transform:none !important;letter-spacing:0 !important;
  margin-bottom:6px !important;display:block !important;
}
/* THE INPUT ITSELF — max specificity */
.gradio-container .sk-auth-card input[type=text],
.gradio-container .sk-auth-card input[type=email],
.gradio-container .sk-auth-card input[type=password],
.gradio-container .sk-auth-card input,
.sk-auth-card input[type=text],
.sk-auth-card input[type=email],
.sk-auth-card input[type=password],
.sk-auth-card input{
  display:block !important;
  width:100% !important;
  height:44px !important;
  min-height:44px !important;
  background:var(--surface) !important;
  border:1px solid var(--border2) !important;
  border-radius:var(--r2) !important;
  color:var(--pearl) !important;
  font-family:var(--font-ui) !important;
  font-size:14px !important;
  line-height:1 !important;
  padding:0 14px !important;
  outline:none !important;
  box-shadow:none !important;
  transition:border-color .18s,box-shadow .18s !important;
  cursor:text !important;
  pointer-events:all !important;
  -webkit-user-select:text !important;
  user-select:text !important;
  position:relative !important;
  z-index:10 !important;
  opacity:1 !important;
  visibility:visible !important;
  -webkit-appearance:none !important;
  appearance:none !important;
}
.gradio-container .sk-auth-card input:focus,
.sk-auth-card input:focus{
  border-color:var(--pulse) !important;
  box-shadow:0 0 0 3px rgba(123,47,255,.12) !important;
  background:var(--surface2) !important;
}
.sk-auth-card input::placeholder{color:var(--t-dim) !important;opacity:1 !important;}

/* Spacing between fields */
.sk-auth-tabs .tabitem > .gap > div,
.sk-auth-tabs .tabitem > div > div.block{
  margin-bottom:14px !important;
}

/* Auth button */
.gradio-container .sk-auth-card button.primary,
.sk-auth-card button.primary,
.sk-auth-card .primary{
  display:flex !important;align-items:center !important;justify-content:center !important;
  width:100% !important;height:44px !important;min-height:44px !important;
  background:linear-gradient(135deg,var(--pulse),var(--current)) !important;
  border:none !important;border-radius:var(--r2) !important;
  color:var(--pearl) !important;font-family:var(--font-ui) !important;
  font-size:14px !important;font-weight:600 !important;
  padding:0 20px !important;cursor:pointer !important;
  transition:opacity .15s !important;margin-top:6px !important;
  box-shadow:0 4px 18px rgba(123,47,255,.25) !important;
  letter-spacing:.2px !important;
}
.sk-auth-card button.primary:hover{opacity:.87 !important;}

.sk-auth-notice{
  margin-top:18px;padding:10px 12px;
  background:rgba(238,238,255,.02);
  border:1px solid var(--border);border-radius:var(--r1);
  font-family:var(--font-mono);font-size:10px;color:var(--t-dim);
  line-height:1.65;text-align:center;
}

.sk-status-ok{font-family:var(--font-ui);font-size:12.5px;color:var(--ok);padding:8px 0 2px;display:block;}
.sk-status-err{font-family:var(--font-ui);font-size:12.5px;color:var(--fault);padding:8px 0 2px;display:block;}

/* ════ SETTINGS ════ */
.sk-settings-overlay{
  position:fixed;inset:0;z-index:500;
  background:rgba(5,5,5,.75);
  display:flex;align-items:center;justify-content:center;padding:20px;
}
.sk-settings-box{
  background:var(--deep);border:1px solid var(--border2);
  border-radius:var(--r4);
  width:100%;max-width:400px;max-height:86vh;overflow-y:auto;
  box-shadow:0 30px 70px rgba(0,0,0,.6);
}
.sk-settings-box::-webkit-scrollbar{width:3px;}
.sk-settings-box::-webkit-scrollbar-thumb{background:var(--border2);}
.sk-settings-hd{
  display:flex;align-items:center;justify-content:space-between;
  padding:18px 22px;border-bottom:1px solid var(--border);
  position:sticky;top:0;background:var(--deep);z-index:1;
}
.sk-settings-title{
  font-family:var(--font-display);font-size:11px;font-weight:700;
  color:var(--pearl);letter-spacing:2px;
}
.sk-settings-closebtn{
  background:transparent;border:1px solid var(--border);
  border-radius:var(--r1);color:var(--t-mid);
  font-size:13px;width:28px;height:28px;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:all .12s;font-family:var(--font-ui);
}
.sk-settings-closebtn:hover{background:var(--surface3);color:var(--pearl);}
.sk-settings-body{padding:22px;display:flex;flex-direction:column;gap:26px;}
.sk-sf-section{display:flex;flex-direction:column;gap:12px;}
.sk-sf-label{
  font-family:var(--font-mono);font-size:9px;font-weight:700;
  letter-spacing:1.2px;text-transform:uppercase;color:var(--t-dim);
  padding-bottom:8px;border-bottom:1px solid var(--border);
}
.sk-sf-row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;}
.sk-sf-key{font-family:var(--font-ui);font-size:12px;color:var(--t-mid);flex-shrink:0;}
.sk-sf-val{font-family:var(--font-ui);font-size:12.5px;color:var(--t-main);text-align:right;word-break:break-all;}
.sk-mono{font-family:var(--font-mono) !important;font-size:10px !important;}
.sk-sf-input{
  display:block !important;width:100% !important;
  height:42px !important;
  background:var(--surface) !important;border:1px solid var(--border2) !important;
  border-radius:var(--r2) !important;color:var(--pearl) !important;
  font-family:var(--font-ui) !important;font-size:13.5px !important;
  padding:0 13px !important;outline:none !important;
  transition:border-color .15s !important;
  cursor:text !important;pointer-events:all !important;
  -webkit-user-select:text !important;user-select:text !important;
}
.sk-sf-input:focus{
  border-color:var(--pulse) !important;
  box-shadow:0 0 0 3px rgba(123,47,255,.1) !important;
}
.sk-sf-btn{
  background:linear-gradient(135deg,var(--pulse),var(--current));
  border:none;border-radius:var(--r2);
  color:var(--pearl);font-family:var(--font-ui);font-size:13px;font-weight:600;
  padding:9px 20px;cursor:pointer;align-self:flex-start;
  transition:opacity .15s;box-shadow:0 2px 10px rgba(123,47,255,.2);
}
.sk-sf-btn:hover{opacity:.85;}
.sk-sf-msg{font-family:var(--font-ui);font-size:12px;min-height:16px;}
.sk-sf-msg.ok{color:var(--ok);}
.sk-sf-msg.err{color:var(--fault);}
.sk-sf-notice{
  font-family:var(--font-mono);font-size:10px;color:var(--t-dim);
  line-height:1.7;padding:12px;
  background:rgba(238,238,255,.02);border:1px solid var(--border);border-radius:var(--r1);
}

/* Mobile overlay */
.sk-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:49;
}
.sk-overlay.open{display:block;}

/* ════ RESPONSIVE ════ */
@media(max-width:860px){
  .sk-sidebar{
    position:fixed;top:0;left:0;height:100%;
    transform:translateX(-100%);z-index:200;
    box-shadow:8px 0 40px rgba(0,0,0,.7);
  }
  .sk-sidebar.open{transform:translateX(0);}
  .sk-menubtn{display:flex !important;}
  .sk-grid{grid-template-columns:repeat(2,1fr);}
}
@media(max-width:600px){
  .sk-welcome{padding:1.75rem 16px 2rem;}
  .sk-auth-card{padding:28px 20px;border-radius:var(--r3);}
  .message.user{max-width:85% !important;}
  .sk-header-badge{display:none;}
  .sk-input-wrap{padding:8px 12px 16px;}
}
@media(max-width:420px){
  .sk-grid{grid-template-columns:1fr;}
  .sk-welcome-title{font-size:1.3rem;}
}
"""

JS = """
<div id="skOverlay" class="sk-overlay" onclick="sk_togglesidebar()"></div>
<script>
/* ── localStorage session persistence ── */
var _LS = 'sakina_v2';
function sk_saveSession(uid, email, name) {
    try { localStorage.setItem(_LS, JSON.stringify({uid:uid, email:email, name:name, t:Date.now()})); } catch(e) {}
}
function sk_clearSession() {
    try { localStorage.removeItem(_LS); } catch(e) {}
}
function sk_getSession() {
    try {
        var d = JSON.parse(localStorage.getItem(_LS) || 'null');
        if (!d) return null;
        if (Date.now() - d.t > 30 * 86400 * 1000) { sk_clearSession(); return null; }
        return d;
    } catch(e) { return null; }
}

/* Auto-restore session on page load */
document.addEventListener('DOMContentLoaded', function() {
    var s = sk_getSession();
    if (s && s.uid) {
        setTimeout(function() {
            var inp = document.querySelector('#skAutoLoginInput textarea, #skAutoLoginInput input');
            var btn = document.getElementById('skAutoLoginBtn');
            if (inp && btn) {
                try {
                    var proto = inp.tagName === 'TEXTAREA'
                        ? Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')
                        : Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                    if (proto) proto.set.call(inp, s.uid);
                    else inp.value = s.uid;
                } catch(e) { inp.value = s.uid; }
                inp.dispatchEvent(new Event('input', {bubbles: true}));
                setTimeout(function() { btn.click(); }, 200);
            }
        }, 700);
    }
});

/* Watch DOM for server signals */
var _obs = new MutationObserver(function(muts) {
    muts.forEach(function(m) {
        m.addedNodes.forEach(function(n) {
            if (n.nodeType !== 1) return;
            if (n.id === 'skSessionSignal') {
                try {
                    var d = JSON.parse(n.dataset.d || '{}');
                    if (d.uid) sk_saveSession(d.uid, d.email, d.name);
                } catch(e) {}
                setTimeout(function() { if (n.parentNode) n.parentNode.removeChild(n); }, 100);
            }
            if (n.id === 'skSettingsSignal') {
                try {
                    var d = JSON.parse(n.dataset.d || '{}');
                    var el = document.getElementById(d.target || '');
                    if (el) { el.textContent = d.msg; el.className = 'sk-sf-msg ' + (d.ok ? 'ok' : 'err'); }
                    if (d.ok && d.action === 'name' && d.newName) {
                        var sess = sk_getSession();
                        if (sess) sk_saveSession(sess.uid, sess.email, d.newName);
                    }
                } catch(e) {}
                setTimeout(function() { if (n.parentNode) n.parentNode.removeChild(n); }, 100);
            }
        });
    });
});
_obs.observe(document.body, {childList: true, subtree: true});

/* ── Sidebar ── */
function sk_togglesidebar() {
    var sb = document.getElementById('skSidebar');
    var ov = document.getElementById('skOverlay');
    if (sb) sb.classList.toggle('open');
    if (ov) ov.classList.toggle('open');
}
function sk_closesidebar() {
    var sb = document.getElementById('skSidebar');
    var ov = document.getElementById('skOverlay');
    if (sb) sb.classList.remove('open');
    if (ov) ov.classList.remove('open');
}

/* ── Chat ── */
function _sk_setVal(el, val) {
    try {
        var proto = el.tagName === 'TEXTAREA'
            ? Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')
            : Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
        if (proto) proto.set.call(el, val);
        else el.value = val;
    } catch(e) { el.value = val; }
    el.dispatchEvent(new Event('input', {bubbles: true}));
}
function sk_resume(sid) {
    var inp = document.querySelector('#skResumeInput textarea, #skResumeInput input');
    var btn = document.getElementById('skResumeBtn');
    if (inp && btn) {
        _sk_setVal(inp, sid);
        setTimeout(function() { btn.click(); sk_closesidebar(); }, 120);
    }
}
function sk_newchat() {
    var btn = document.getElementById('skNewChatBtn');
    if (btn) { btn.click(); sk_closesidebar(); }
}
function sk_logout() {
    sk_clearSession();
    var btn = document.getElementById('skLogoutBtn');
    if (btn) btn.click();
}
function sk_suggest(text) {
    var box = document.querySelector('.sk-input-box textarea');
    if (box) { _sk_setVal(box, text); box.focus(); }
}

/* ── Settings ── */
function sk_settings() {
    var el = document.getElementById('skSettingsOverlay');
    if (el) el.style.display = 'flex';
    sk_closesidebar();
}
function sk_closeSettings(evt) {
    if (evt === null || (evt && evt.target && evt.target.id === 'skSettingsOverlay')) {
        var el = document.getElementById('skSettingsOverlay');
        if (el) el.style.display = 'none';
    }
}
function _sk_settingsDispatch(payload) {
    var inp = document.querySelector('#skSettingsInput textarea, #skSettingsInput input');
    var btn = document.getElementById('skSettingsBtn');
    if (!inp || !btn) return;
    _sk_setVal(inp, JSON.stringify(payload));
    setTimeout(function() { btn.click(); }, 120);
}
function sk_saveName() {
    var v = ((document.getElementById('sfName') || {}).value || '').trim();
    if (!v) { var m = document.getElementById('sfNameMsg'); if (m) { m.textContent = 'Enter a name.'; m.className = 'sk-sf-msg err'; } return; }
    _sk_settingsDispatch({action: 'name', name: v, target: 'sfNameMsg'});
}
function sk_savePass() {
    var cur = ((document.getElementById('sfCurPass') || {}).value || '');
    var nw  = ((document.getElementById('sfNewPass')  || {}).value || '');
    if (!cur || !nw) { var m = document.getElementById('sfPassMsg'); if (m) { m.textContent = 'Fill in both fields.'; m.className = 'sk-sf-msg err'; } return; }
    _sk_settingsDispatch({action: 'pass', current: cur, newpass: nw, target: 'sfPassMsg'});
}
</script>
"""

# ── APP ────────────────────────────────────────────────────────────────────────
with gr.Blocks(css=CSS, title="Sakina — Hallvorn") as demo:

    sid_st      = gr.State(lambda: str(uuid.uuid4()))
    user_st     = gr.State(None)
    chatname_st = gr.State("New Conversation")
    sessions_st = gr.State([])
    active_st   = gr.State("")

    # ── AUTH ──────────────────────────────────────────────────────────────
    with gr.Group(visible=True) as auth_grp:
        gr.HTML('<div class="sk-auth"><div class="sk-auth-card">')
        gr.HTML(
            '<div class="sk-auth-top">'
            '<div class="sk-auth-logobox">S</div>'
            '<div><div class="sk-auth-brandname">SAKINA</div>'
            '<div class="sk-auth-brandsub">by Hallvorn</div></div>'
            '</div>'
            '<p class="sk-auth-tagline">Elite STEM intelligence. Every phenomenon has a scientific answer.</p>'
        )
        with gr.Tabs(elem_classes=["sk-auth-tabs"]):
            with gr.Tab("Sign in"):
                li_email = gr.Textbox(label="Email address", placeholder="you@example.com")
                li_pass  = gr.Textbox(label="Passcode", placeholder="Your passcode", type="password")
                li_btn   = gr.Button("Sign in", variant="primary")
                li_msg   = gr.HTML("")
            with gr.Tab("Create account"):
                su_name  = gr.Textbox(label="Full name", placeholder="Your full name")
                su_email = gr.Textbox(label="Email address", placeholder="you@example.com")
                su_pass  = gr.Textbox(label="Passcode (min 6 characters)", placeholder="Choose a passcode", type="password")
                su_btn   = gr.Button("Create account", variant="primary")
                su_msg   = gr.HTML("")
        gr.HTML('<div class="sk-auth-notice">Conversations may be used to improve Sakina &nbsp;·&nbsp; Inspired by Sakina Haruna</div>')
        gr.HTML('</div></div>')

    # ── APP ───────────────────────────────────────────────────────────────
    with gr.Group(visible=False) as app_grp:
        gr.HTML('<div class="sk-root">')
        sidebar_out  = gr.HTML("", elem_id="sidebarOut")
        settings_out = gr.HTML("", elem_id="settingsOut")
        gr.HTML('<div class="sk-main">')
        header_out   = gr.HTML("", elem_id="headerOut")

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
            msg_box  = gr.Textbox(placeholder="Ask Sakina anything…", show_label=False,
                                  scale=9, container=False, lines=1, max_lines=6)
            send_btn = gr.Button("↑", variant="primary", scale=1, min_width=34,
                                 elem_classes=["sk-send-btn"])
        gr.HTML('</div></div></div></div>')  # input-box, input-wrap, sk-main, sk-root

        # Hidden Gradio controls
        resume_inp    = gr.Textbox(visible=False, elem_id="skResumeInput")
        resume_btn    = gr.Button("", visible=False, elem_id="skResumeBtn")
        newchat_btn   = gr.Button("", visible=False, elem_id="skNewChatBtn")
        logout_btn    = gr.Button("", visible=False, elem_id="skLogoutBtn")
        autologin_inp = gr.Textbox(visible=False, elem_id="skAutoLoginInput")
        autologin_btn = gr.Button("", visible=False, elem_id="skAutoLoginBtn")
        settings_inp  = gr.Textbox(visible=False, elem_id="skSettingsInput")
        settings_btn  = gr.Button("", visible=False, elem_id="skSettingsBtn")

    gr.HTML(JS)

    # ── SHARED HELPERS ────────────────────────────────────────────────────
    def _session_signal(user):
        import json
        d = json.dumps({"uid": user["id"], "email": user.get("email",""), "name": user.get("full_name","")})
        d_safe = d.replace("'", "&#39;")
        return f"<div id='skSessionSignal' data-d='{d_safe}'></div>"

    def _build_app(user, sid):
        sessions = load_sessions_for_user(user["id"])
        sidebar  = build_sidebar(user, sessions, "")
        header   = build_header("New Conversation")
        welcome  = build_welcome(user.get("full_name","")) + _session_signal(user)
        settings = build_settings(user)
        return sessions, sidebar, header, welcome, settings

    # ── HANDLERS ─────────────────────────────────────────────────────────
    def do_signup(name, email, passcode):
        ok, text = register_user(email, passcode, name)
        cls = "sk-status-ok" if ok else "sk-status-err"
        return f'<span class="{cls}">{"✓" if ok else "✕"} {text}</span>'

    su_btn.click(fn=do_signup, inputs=[su_name, su_email, su_pass], outputs=[su_msg])

    def do_login(email, passcode, sid):
        user, text = login_user(email, passcode)
        if user:
            sessions, sidebar, header, welcome, settings = _build_app(user, sid)
            msg = f'<span class="sk-status-ok">✓ {text}</span>'
            return (gr.update(visible=False), gr.update(visible=True), msg, user, [],
                    sidebar, header, welcome, settings, gr.update(visible=False),
                    "New Conversation", sessions, sid, "")
        msg = f'<span class="sk-status-err">✕ {text}</span>'
        return (gr.update(visible=True), gr.update(visible=False), msg, None, [],
                "", "", "", "", gr.update(visible=False),
                "New Conversation", [], sid, "")

    li_btn.click(fn=do_login,
        inputs=[li_email, li_pass, sid_st],
        outputs=[auth_grp, app_grp, li_msg, user_st, chatbot,
                 sidebar_out, header_out, welcome_out, settings_out,
                 chatbot, chatname_st, sessions_st, sid_st, active_st])

    def do_autologin(user_id, sid):
        if not user_id or not user_id.strip():
            return (gr.update(), gr.update(), None, [], "", "", "", "",
                    gr.update(), "New Conversation", [], sid, "")
        user = get_user_by_id(user_id.strip())
        if not user:
            return (gr.update(), gr.update(), None, [], "", "", "", "",
                    gr.update(), "New Conversation", [], sid, "")
        sessions, sidebar, header, welcome, settings = _build_app(user, sid)
        return (gr.update(visible=False), gr.update(visible=True), user, [],
                sidebar, header, welcome, settings, gr.update(visible=False),
                "New Conversation", sessions, sid, "")

    autologin_btn.click(fn=do_autologin,
        inputs=[autologin_inp, sid_st],
        outputs=[auth_grp, app_grp, user_st, chatbot,
                 sidebar_out, header_out, welcome_out, settings_out,
                 chatbot, chatname_st, sessions_st, sid_st, active_st])

    def do_send(message, history, sid, user, chat_name, sessions):
        if not message or not message.strip():
            return history, "", chat_name, "", gr.update(), gr.update(), gr.update(), sessions, sid
        reply, new_name = chat_fn(message, history, sid, user, chat_name)
        new_history  = history + [(message.strip(), reply)]
        new_sessions = load_sessions_for_user(user["id"]) if user else sessions
        sidebar = build_sidebar(user, new_sessions, sid) if user else ""
        header  = build_header(new_name)
        return (new_history, "", new_name, sidebar,
                gr.update(visible=True), gr.update(visible=False), header, new_sessions, sid)

    send_btn.click(fn=do_send,
        inputs=[msg_box, chatbot, sid_st, user_st, chatname_st, sessions_st],
        outputs=[chatbot, msg_box, chatname_st, sidebar_out,
                 chatbot, welcome_out, header_out, sessions_st, sid_st])
    msg_box.submit(fn=do_send,
        inputs=[msg_box, chatbot, sid_st, user_st, chatname_st, sessions_st],
        outputs=[chatbot, msg_box, chatname_st, sidebar_out,
                 chatbot, welcome_out, header_out, sessions_st, sid_st])

    def do_resume(target_sid, user, sessions):
        if not user or not target_sid or not target_sid.strip():
            return (gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), "")
        target_sid = target_sid.strip()
        history   = load_session_history(user["id"], target_sid)
        chat_name = get_session_chat_name(user["id"], target_sid)
        sidebar   = build_sidebar(user, sessions, target_sid)
        header    = build_header(chat_name)
        return (history, target_sid, chat_name, sidebar, header,
                gr.update(visible=True), gr.update(visible=False), "")

    resume_btn.click(fn=do_resume,
        inputs=[resume_inp, user_st, sessions_st],
        outputs=[chatbot, sid_st, chatname_st, sidebar_out, header_out,
                 chatbot, welcome_out, resume_inp])

    def do_newchat(user, sessions):
        new_sid = str(uuid.uuid4())
        sidebar = build_sidebar(user, sessions, "") if user else ""
        header  = build_header("New Conversation")
        welcome = build_welcome(user.get("full_name","")) if user else ""
        return ([], new_sid, "New Conversation", sidebar, header, welcome,
                gr.update(visible=False), gr.update(visible=True))

    newchat_btn.click(fn=do_newchat,
        inputs=[user_st, sessions_st],
        outputs=[chatbot, sid_st, chatname_st, sidebar_out, header_out, welcome_out,
                 chatbot, welcome_out])

    def do_logout():
        return (gr.update(visible=True), gr.update(visible=False), None, [], "", "", "", "",
                gr.update(visible=False), "New Conversation", [], "", "")

    logout_btn.click(fn=do_logout, inputs=[],
        outputs=[auth_grp, app_grp, user_st, chatbot, sidebar_out, header_out,
                 welcome_out, settings_out, chatbot, chatname_st, sessions_st, sid_st, li_msg])

    def do_settings_update(payload_str, user):
        import json
        if not user or not payload_str or not payload_str.strip():
            return "", ""
        try:
            p = json.loads(payload_str.strip())
        except Exception:
            return "", ""
        action = p.get("action", "")
        target = p.get("target", "sfNameMsg")
        sd = {}
        if action == "name":
            ok, msg = update_user_profile(user["id"], new_name=p.get("name",""))
            sd = {"action":"name","ok":ok,"msg":msg,"target":target,"newName":p.get("name","") if ok else ""}
            if ok: user["full_name"] = p.get("name","")
        elif action == "pass":
            ok, msg = update_user_profile(user["id"], new_passcode=p.get("newpass",""), current_passcode=p.get("current",""))
            sd = {"action":"pass","ok":ok,"msg":msg,"target":target}
        else:
            return "", ""
        sd_json = json.dumps(sd).replace("'","&#39;")
        new_sessions = load_sessions_for_user(user["id"])
        sidebar  = build_sidebar(user, new_sessions, "")
        settings = build_settings(user)
        signal = f"<div id='skSettingsSignal' data-d='{sd_json}'></div>"
        return sidebar + signal, settings

    settings_btn.click(fn=do_settings_update,
        inputs=[settings_inp, user_st],
        outputs=[sidebar_out, settings_out])

# ── Launch ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
