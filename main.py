
import os
import uuid
import string
import random
import bcrypt
import json
from datetime import datetime, timezone, timedelta
from groq import Groq
from supabase import create_client, Client
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATABASE SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Run in Supabase SQL editor:
#
# -- 1. Soft-delete columns (skip if already done):
#    ALTER TABLE sakina_conversations
#      ADD COLUMN IF NOT EXISTS is_deleted  BOOLEAN     DEFAULT FALSE,
#      ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ DEFAULT NULL;
#    CREATE INDEX IF NOT EXISTS idx_conv_soft_delete
#      ON sakina_conversations(user_id, is_deleted, deleted_at);
#
# -- 2. Permanent training archive (no PII, never purged):
#    CREATE TABLE IF NOT EXISTS sakina_training_archive (
#      id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
#      archived_at TIMESTAMPTZ DEFAULT NOW(),
#      session_id  TEXT,
#      chat_name   TEXT,
#      turns       JSONB,
#      turn_count  INT,
#      model_used  TEXT        DEFAULT 'llama-3.3-70b-versatile',
#      source      TEXT        DEFAULT 'user_deletion'
#    );
#
# -- 3. HOW TO GET YOUR PURGE_SECRET:
#    Run in terminal:
#      python -c "import secrets; print(secrets.token_hex(32))"
#    Or: openssl rand -hex 32
#    Add as env var: PURGE_SECRET=<the value>
#    Set up cron-job.org:
#      Method: POST  /  URL: https://your-app.com/api/internal/purge
#      Header: X-Purge-Secret: <value>  /  Time: 03:00 UTC daily
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

app = FastAPI(title="Sakina — Hallvorn")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")


def generate_sakina_id() -> str:
    now   = datetime.now(timezone.utc)
    ts    = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    chars = string.ascii_uppercase + string.digits
    rpart = ''.join(random.choices(chars, k=16))
    return f"SKN-HLVN-{ts}-{rpart}-{random.randint(0,9)}{random.choice(string.ascii_uppercase)}"


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
- Use precise scientific vocabulary but always anchor it with intuition
- Never say "great question", "certainly", or "of course"

DATA TRANSPARENCY:
Your conversations with Sakina are stored and may be used to improve the system. Sakina is built on honesty.

WHEN ASKED WHO YOU ARE:
Say: "I am Sakina, a scientific intelligence built by Hallvorn, inspired by the name Sakina Haruna. My purpose is singular: to reveal the scientific architecture beneath every question you can ask. Ask me anything."

WHEN ASKED ABOUT HALLVORN:
Hallvorn is the engineering team behind Sakina, dedicated to the idea that every human deserves world-class scientific thinking."""


def hash_passcode(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_passcode(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "passcode_hash"}


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
            "email": email, "passcode_hash": hash_passcode(passcode),
            "full_name": full_name, "sakina_id": generate_sakina_id(), "is_verified": True,
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
        print(f"[Update error] {e}")
        return False, "Update failed. Please try again."


def save_conversation(user_id, session_id, chat_name, user_message, sakina_response):
    try:
        supabase.table("sakina_conversations").insert({
            "user_id": user_id, "session_id": session_id, "chat_name": chat_name,
            "user_message": user_message, "sakina_response": sakina_response,
            "model_used": "llama-3.3-70b-versatile", "is_deleted": False, "deleted_at": None,
        }).execute()
    except Exception as e:
        print(f"[Save error] {e}")


def load_session_history(user_id, session_id):
    try:
        r = (supabase.table("sakina_conversations")
             .select("user_message, sakina_response")
             .eq("user_id", user_id).eq("session_id", session_id)
             .eq("is_deleted", False).order("created_at").execute())
        return [(x["user_message"], x["sakina_response"]) for x in r.data] if r and r.data else []
    except Exception:
        return []


def load_sessions_for_user(user_id):
    try:
        r = (supabase.table("sakina_conversations")
             .select("session_id, chat_name, created_at")
             .eq("user_id", user_id).eq("is_deleted", False)
             .order("created_at", desc=True).execute())
        if not r or not r.data:
            return []
        seen = {}
        for row in r.data:
            sid = row["session_id"]
            if sid not in seen:
                seen[sid] = {"session_id": sid,
                             "chat_name": row.get("chat_name") or "Untitled",
                             "created_at": row["created_at"]}
        return list(seen.values())
    except Exception:
        return []


def load_deleted_sessions_for_user(user_id):
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        r = (supabase.table("sakina_conversations")
             .select("session_id, chat_name, deleted_at")
             .eq("user_id", user_id).eq("is_deleted", True)
             .gt("deleted_at", cutoff).order("deleted_at", desc=True).execute())
        if not r or not r.data:
            return []
        seen = {}
        for row in r.data:
            sid = row["session_id"]
            if sid not in seen:
                seen[sid] = {"session_id": sid,
                             "chat_name": row.get("chat_name") or "Untitled",
                             "deleted_at": row["deleted_at"]}
        return list(seen.values())
    except Exception:
        return []


def get_session_chat_name(user_id, session_id):
    try:
        r = (supabase.table("sakina_conversations").select("chat_name")
             .eq("user_id", user_id).eq("session_id", session_id).limit(1).execute())
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


def build_messages(history, message):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        if isinstance(turn, (list, tuple)) and len(turn) == 2:
            if turn[0]:
                msgs.append({"role": "user", "content": str(turn[0])})
            if turn[1]:
                msgs.append({"role": "assistant", "content": str(turn[1])})
    msgs.append({"role": "user", "content": message})
    return msgs


def archive_session_for_training(user_id, session_id, source="user_deletion"):
    """
    Copy a session into sakina_training_archive before deletion/purge.

    WHAT IS STORED: session_id, chat_name, turns (Q&A pairs), model, source.
    WHAT IS NEVER STORED: user_id, email, full_name — zero PII.
    This table is NEVER purged. It is your permanent training dataset.

    source values:
      'user_deletion' — user deleted via UI (30-day window then purged from conversations)
      'auto_purge'    — called during nightly purge job (backup in case user_deletion was missed)
      'manual'        — admin-triggered
    """
    try:
        r = (supabase.table("sakina_conversations")
             .select("user_message, sakina_response, chat_name, model_used, created_at")
             .eq("user_id", user_id).eq("session_id", session_id)
             .order("created_at").execute())
        if not r or not r.data:
            return
        rows = r.data
        chat_name = rows[0].get("chat_name") or "Untitled"
        model = rows[0].get("model_used") or "llama-3.3-70b-versatile"
        turns = [{"user": row["user_message"], "assistant": row["sakina_response"]}
                 for row in rows if row.get("user_message") and row.get("sakina_response")]
        if not turns:
            return
        existing = (supabase.table("sakina_training_archive").select("id")
                    .eq("session_id", session_id).maybe_single().execute())
        if existing and existing.data:
            return  # already archived
        supabase.table("sakina_training_archive").insert({
            "session_id": session_id, "chat_name": chat_name,
            "turns": turns, "turn_count": len(turns),
            "model_used": model, "source": source,
        }).execute()
        print(f"[Archive] session={session_id} turns={len(turns)} source={source}")
    except Exception as e:
        print(f"[Archive error] session={session_id}: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/register")
async def api_register(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)
    ok, msg = register_user(body.get("email",""), body.get("passcode",""), body.get("full_name",""))
    return JSONResponse({"ok": ok, "msg": msg})


@app.post("/api/login")
async def api_login(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)
    user, msg = login_user(body.get("email",""), body.get("passcode",""))
    if user:
        return JSONResponse({"ok": True, "msg": msg, "user": safe_user(user)})
    return JSONResponse({"ok": False, "msg": msg})


@app.post("/api/autologin")
async def api_autologin(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)
    user_id = body.get("user_id","").strip()
    if not user_id:
        return JSONResponse({"ok": False})
    user = get_user_by_id(user_id)
    if user:
        return JSONResponse({"ok": True, "user": safe_user(user)})
    return JSONResponse({"ok": False})


@app.post("/api/chat")
async def api_chat(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)
    user_id    = body.get("user_id","")
    session_id = body.get("session_id","")
    message    = (body.get("message") or "").strip()
    history    = body.get("history",[])
    chat_name  = body.get("chat_name","")
    if not user_id:
        return JSONResponse({"ok": False, "msg": "Not authenticated."}, status_code=401)
    if not message:
        return JSONResponse({"ok": False, "msg": "Message is empty."}, status_code=400)
    if not chat_name or chat_name in ("New Conversation",""):
        chat_name = generate_chat_name(message)
    try:
        resp  = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", messages=build_messages(history, message),
            max_tokens=2048, temperature=0.7, top_p=0.9)
        reply = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[Groq error] {e}")
        return JSONResponse({"ok": False, "msg": f"AI error: {str(e)}"}, status_code=500)
    save_conversation(user_id, session_id, chat_name, message, reply)
    return JSONResponse({"ok": True, "reply": reply, "chat_name": chat_name})


@app.post("/api/chat/stream")
async def api_chat_stream(req: Request):
    try:
        body = await req.json()
    except Exception:
        async def err():
            yield "data: [ERROR]:Invalid request body.\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    user_id    = body.get("user_id","")
    session_id = body.get("session_id","")
    message    = (body.get("message") or "").strip()
    history    = body.get("history",[])
    chat_name  = body.get("chat_name","")

    if not user_id or not message:
        async def err():
            yield "data: [ERROR]:Missing user_id or message.\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    if not chat_name or chat_name in ("New Conversation",""):
        chat_name = generate_chat_name(message)

    async def generate():
        full_reply = []
        try:
            yield f"data: [NAME]:{chat_name}\n\n"
            stream = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=build_messages(history, message),
                max_tokens=2048, temperature=0.7, top_p=0.9, stream=True)
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_reply.append(delta)
                    safe = delta.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
            yield "data: [DONE]\n\n"
            save_conversation(user_id, session_id, chat_name, message, "".join(full_reply))
        except Exception as e:
            print(f"[Stream error] {e}")
            yield f"data: [ERROR]:{str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no",
                                      "Access-Control-Allow-Origin":"*"})


@app.get("/api/sessions/{user_id}")
async def api_sessions(user_id: str):
    if not user_id:
        return JSONResponse({"ok": False, "msg": "Missing user_id."}, status_code=400)
    return JSONResponse({"ok": True, "sessions": load_sessions_for_user(user_id)})


@app.get("/api/sessions/{user_id}/deleted")
async def api_deleted_sessions(user_id: str):
    if not user_id:
        return JSONResponse({"ok": False, "msg": "Missing user_id."}, status_code=400)
    return JSONResponse({"ok": True, "sessions": load_deleted_sessions_for_user(user_id)})


@app.get("/api/session/{user_id}/{session_id}")
async def api_session_history(user_id: str, session_id: str):
    if not user_id or not session_id:
        return JSONResponse({"ok": False, "msg": "Missing parameters."}, status_code=400)
    history   = load_session_history(user_id, session_id)
    chat_name = get_session_chat_name(user_id, session_id)
    return JSONResponse({"ok": True, "history": history, "chat_name": chat_name})


@app.delete("/api/session/{user_id}/{session_id}")
async def api_delete_session(user_id: str, session_id: str):
    """
    Soft-delete flow:
      1. Archive to sakina_training_archive immediately (no PII, kept forever).
      2. Mark is_deleted=True so users cannot see it anymore.
      3. After 30 days the nightly purge permanently removes it from
         sakina_conversations — the training archive is NEVER touched.
    """
    if not user_id or not session_id:
        return JSONResponse({"ok": False, "msg": "Missing parameters."}, status_code=400)
    try:
        archive_session_for_training(user_id, session_id, source="user_deletion")
        supabase.table("sakina_conversations").update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("user_id", user_id).eq("session_id", session_id).execute()
        return JSONResponse({"ok": True, "msg": "Conversation deleted. It can be restored within 30 days."})
    except Exception as e:
        print(f"[Soft delete error] {e}")
        return JSONResponse({"ok": False, "msg": "Delete failed."}, status_code=500)


@app.post("/api/session/{user_id}/{session_id}/restore")
async def api_restore_session(user_id: str, session_id: str):
    if not user_id or not session_id:
        return JSONResponse({"ok": False, "msg": "Missing parameters."}, status_code=400)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        check  = (supabase.table("sakina_conversations").select("id")
                  .eq("user_id", user_id).eq("session_id", session_id)
                  .eq("is_deleted", True).gt("deleted_at", cutoff).limit(1).execute())
        if not check or not check.data:
            return JSONResponse({"ok": False,
                                 "msg": "Conversation not found or recovery window has expired."},
                                status_code=404)
        supabase.table("sakina_conversations").update(
            {"is_deleted": False, "deleted_at": None}
        ).eq("user_id", user_id).eq("session_id", session_id).execute()
        return JSONResponse({"ok": True, "msg": "Conversation restored successfully."})
    except Exception as e:
        print(f"[Restore error] {e}")
        return JSONResponse({"ok": False, "msg": "Restore failed."}, status_code=500)


@app.post("/api/internal/purge")
async def api_purge_deleted(req: Request):
    """
    Nightly purge — permanently delete conversations soft-deleted 30+ days ago.

    HOW TO GET YOUR PURGE_SECRET:
      python -c "import secrets; print(secrets.token_hex(32))"
      or: openssl rand -hex 32
    Set env var PURGE_SECRET=<value> on your hosting platform.

    Set up daily cron at cron-job.org (free):
      Method: POST
      URL:    https://your-app.com/api/internal/purge
      Header: X-Purge-Secret: <value>
      Time:   03:00 UTC

    Flow:
      1. Find sessions soft-deleted 30+ days ago.
      2. Archive any not-yet-archived (safety net).
      3. Permanently DELETE from sakina_conversations.
      4. sakina_training_archive is NEVER touched.
    """
    secret   = req.headers.get("X-Purge-Secret","")
    expected = os.environ.get("PURGE_SECRET","")
    if not expected:
        return JSONResponse({"ok": False, "msg": "PURGE_SECRET not configured."}, status_code=503)
    if secret != expected:
        return JSONResponse({"ok": False, "msg": "Unauthorized."}, status_code=401)
    try:
        cutoff   = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        to_purge = (supabase.table("sakina_conversations")
                    .select("user_id, session_id")
                    .eq("is_deleted", True).lt("deleted_at", cutoff).execute())
        if not to_purge or not to_purge.data:
            return JSONResponse({"ok": True, "msg": "Nothing to purge.", "deleted": 0, "archived": 0})
        seen: dict = {}
        for row in to_purge.data:
            sid = row["session_id"]
            if sid not in seen:
                seen[sid] = row["user_id"]
        for sid, uid in seen.items():
            archive_session_for_training(uid, sid, source="auto_purge")
        result = (supabase.table("sakina_conversations")
                  .delete().eq("is_deleted", True).lt("deleted_at", cutoff).execute())
        deleted_count  = len(result.data) if result and result.data else 0
        archived_count = len(seen)
        print(f"[Purge] deleted={deleted_count} rows, archived={archived_count} sessions")
        return JSONResponse({"ok": True,
                             "msg": f"Purge complete. {deleted_count} rows removed. {archived_count} sessions in training archive.",
                             "deleted": deleted_count, "archived": archived_count})
    except Exception as e:
        print(f"[Purge error] {e}")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/update_profile")
async def api_update_profile(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid request body."}, status_code=400)
    user_id = body.get("user_id","")
    if not user_id:
        return JSONResponse({"ok": False, "msg": "Not authenticated."}, status_code=401)
    ok, msg = update_user_profile(user_id, new_name=body.get("new_name"),
                                  new_passcode=body.get("new_passcode"),
                                  current_passcode=body.get("current_passcode"))
    updated_name = body.get("new_name","").strip() if ok and body.get("new_name") else None
    return JSONResponse({"ok": ok, "msg": msg, "updated_name": updated_name})


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "Sakina — Hallvorn"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
