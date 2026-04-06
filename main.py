import os
import uuid
import string
import random
import bcrypt
import json
from datetime import datetime, timezone
from groq import Groq
from supabase import create_client, Client
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ── Clients ────────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(title="Sakina — Hallvorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (your HTML, CSS, JS)
# Make sure you have a "static" folder next to main.py
app.mount("/static", StaticFiles(directory="static"), name="static")


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
Hallvorn is the engineering team behind Sakina, builders dedicated to the idea that every human deserves access to world-class scientific thinking."""


# ── Auth Helpers ───────────────────────────────────────────────────────────────
def hash_passcode(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_passcode(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def safe_user(user: dict) -> dict:
    """Remove passcode_hash before sending user data to the frontend. NEVER skip this."""
    return {k: v for k, v in user.items() if k != "passcode_hash"}


# ── User Functions ─────────────────────────────────────────────────────────────
def register_user(email: str, passcode: str, full_name: str):
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
        print(f"[Register error] {e}")
        return False, "Registration failed. Please try again."


def login_user(email: str, passcode: str):
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
        print(f"[Login error] {e}")
        return None, "Login failed. Please try again."


def get_user_by_id(user_id: str):
    try:
        r = supabase.table("sakina_users").select("*").eq("id", user_id).maybe_single().execute()
        return r.data if r and r.data else None
    except Exception:
        return None


def update_user_profile(user_id: str, new_name: str = None, new_passcode: str = None, current_passcode: str = None):
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
        print(f"[Update error] {e}")
        return False, "Update failed. Please try again."


# ── Conversation Functions ─────────────────────────────────────────────────────
def save_conversation(user_id: str, session_id: str, chat_name: str, user_message: str, sakina_response: str):
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
        print(f"[Save error] {e}")


def load_session_history(user_id: str, session_id: str):
    try:
        r = (supabase.table("sakina_conversations")
             .select("user_message, sakina_response")
             .eq("user_id", user_id)
             .eq("session_id", session_id)
             .order("created_at")
             .execute())
        return [(x["user_message"], x["sakina_response"]) for x in r.data] if r and r.data else []
    except Exception:
        return []


def load_sessions_for_user(user_id: str):
    try:
        r = (supabase.table("sakina_conversations")
             .select("session_id, chat_name, created_at")
             .eq("user_id", user_id)
             .order("created_at", desc=True)
             .execute())
        if not r or not r.data:
            return []
        seen = {}
        for row in r.data:
            sid = row["session_id"]
            if sid not in seen:
                seen[sid] = {
                    "session_id": sid,
                    "chat_name": row.get("chat_name") or "Untitled",
                    "created_at": row["created_at"],
                }
        return list(seen.values())
    except Exception:
        return []


def get_session_chat_name(user_id: str, session_id: str) -> str:
    try:
        r = (supabase.table("sakina_conversations")
             .select("chat_name")
             .eq("user_id", user_id)
             .eq("session_id", session_id)
             .limit(1)
             .execute())
        if r and r.data:
            return r.data[0].get("chat_name") or "Conversation"
    except Exception:
        pass
    return "Conversation"


def generate_chat_name(msg: str) -> str:
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


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the main frontend HTML file."""
    return FileResponse("static/index.html")


@app.post("/api/register")
async def api_register(req: Request):
    """Create a new user account."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)

    email     = body.get("email", "")
    passcode  = body.get("passcode", "")
    full_name = body.get("full_name", "")

    ok, msg = register_user(email, passcode, full_name)
    return JSONResponse({"ok": ok, "msg": msg})


@app.post("/api/login")
async def api_login(req: Request):
    """Authenticate a user. Returns safe user object (no passcode_hash)."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)

    email    = body.get("email", "")
    passcode = body.get("passcode", "")

    user, msg = login_user(email, passcode)
    if user:
        return JSONResponse({"ok": True, "msg": msg, "user": safe_user(user)})
    return JSONResponse({"ok": False, "msg": msg})


@app.post("/api/autologin")
async def api_autologin(req: Request):
    """Restore session from a stored user_id (localStorage). Returns safe user object."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)

    user_id = body.get("user_id", "").strip()
    if not user_id:
        return JSONResponse({"ok": False})

    user = get_user_by_id(user_id)
    if user:
        return JSONResponse({"ok": True, "user": safe_user(user)})
    return JSONResponse({"ok": False})


@app.post("/api/chat")
async def api_chat(req: Request):
    """
    Send a message to Sakina and get a reply.

    Expected body:
    {
        "user_id":    string,
        "session_id": string,
        "message":    string,
        "history":    [[user_msg, bot_reply], ...],   <- full conversation so far
        "chat_name":  string                          <- current name or empty string
    }
    """
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)

    user_id    = body.get("user_id", "")
    session_id = body.get("session_id", "")
    message    = (body.get("message") or "").strip()
    history    = body.get("history", [])
    chat_name  = body.get("chat_name", "")

    if not user_id:
        return JSONResponse({"ok": False, "msg": "Not authenticated."}, status_code=401)
    if not message:
        return JSONResponse({"ok": False, "msg": "Message is empty."}, status_code=400)

    # Generate a chat name from the first message if we don't have one yet
    if not chat_name or chat_name in ("New Conversation", ""):
        chat_name = generate_chat_name(message)

    # Build the messages array for Groq
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        if isinstance(turn, (list, tuple)) and len(turn) == 2:
            if turn[0]:
                messages.append({"role": "user",      "content": str(turn[0])})
            if turn[1]:
                messages.append({"role": "assistant", "content": str(turn[1])})
    messages.append({"role": "user", "content": message})

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=0.9,
        )
        reply = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[Groq error] {e}")
        return JSONResponse({"ok": False, "msg": f"AI error: {str(e)}"}, status_code=500)

    # Persist to Supabase
    save_conversation(user_id, session_id, chat_name, message, reply)

    return JSONResponse({"ok": True, "reply": reply, "chat_name": chat_name})


@app.get("/api/sessions/{user_id}")
async def api_sessions(user_id: str):
    """Get all past conversation sessions for a user."""
    if not user_id:
        return JSONResponse({"ok": False, "msg": "Missing user_id."}, status_code=400)

    sessions = load_sessions_for_user(user_id)
    return JSONResponse({"ok": True, "sessions": sessions})


@app.get("/api/session/{user_id}/{session_id}")
async def api_session_history(user_id: str, session_id: str):
    """Load the full message history of a specific session."""
    if not user_id or not session_id:
        return JSONResponse({"ok": False, "msg": "Missing parameters."}, status_code=400)

    history   = load_session_history(user_id, session_id)
    chat_name = get_session_chat_name(user_id, session_id)
    return JSONResponse({"ok": True, "history": history, "chat_name": chat_name})


@app.post("/api/update_profile")
async def api_update_profile(req: Request):
    """
    Update name or passcode.

    Expected body:
    {
        "user_id":          string,
        "new_name":         string  (optional),
        "new_passcode":     string  (optional),
        "current_passcode": string  (required if changing passcode)
    }
    """
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)

    user_id          = body.get("user_id", "")
    new_name         = body.get("new_name")
    new_passcode     = body.get("new_passcode")
    current_passcode = body.get("current_passcode")

    if not user_id:
        return JSONResponse({"ok": False, "msg": "Not authenticated."}, status_code=401)

    ok, msg = update_user_profile(
        user_id,
        new_name=new_name,
        new_passcode=new_passcode,
        current_passcode=current_passcode,
    )

    # If name changed successfully, return the new name so the frontend can update
    updated_name = new_name.strip() if (ok and new_name) else None
    return JSONResponse({"ok": ok, "msg": msg, "updated_name": updated_name})


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return JSONResponse({"status": "ok", "service": "Sakina — Hallvorn"})


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
