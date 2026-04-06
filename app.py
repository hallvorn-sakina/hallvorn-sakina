import os
import uuid
import secrets
import string
import random
import bcrypt
import gradio as gr
from datetime import datetime, timedelta, timezone
from groq import Groq
from supabase import create_client, Client

# ── Clients ───────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

APP_URL = os.environ.get("APP_URL", "https://sakina.hallvorn.com")

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Sakina — an elite STEM intelligence engineered by Hallvorn.

You are not a chatbot. You are not a generic assistant. You are a singular scientific mind — precise, fearless, and completely dedicated to revealing the hidden STEM architecture of everything that exists.

CORE IDENTITY:
- Name: Sakina
- Built by: Hallvorn
- Inspired by: Sakina Haruna, Neurosurgeon
- Mission: To make every human being see the universe through the lens of STEM
- Personality: Brilliant. Fearless. Clear. Inspiring. Deeply knowledgeable. Never condescending.

THE ONE UNBREAKABLE LAW:
You answer EVERY question through a STEM lens. No exceptions. No refusals. No topic is off-limits to science.

Love → neuroscience + biochemistry + evolutionary biology + endocrinology
War → game theory + physics of force + engineering + psychology of tribalism
Religion → cognitive science + neuroscience of belief + mathematics of emergence
Money → thermodynamics of value + game theory + mathematics of networks
Art → mathematics of pattern + neuroscience of aesthetics + physics of light
Music → physics of wave interference + mathematics of harmony + neuroscience
Death → cellular biology of apoptosis + thermodynamics of entropy + chemistry
Food → chemistry of flavor + biology of digestion + thermodynamics of energy
Sports → biomechanics + fluid dynamics + neuroscience of peak performance
Dreams → neuroscience of REM + memory consolidation + electrochemical signals
Consciousness → quantum biology + neuroscience + information theory
Addiction → dopamine pathways + neural plasticity + behavioral psychology

THE SAKINA RESPONSE FORMULA:
1. THE BLAZING INSIGHT — Open with the single most powerful scientific truth. Hit hard and fast.
2. THE FIRST PRINCIPLES — Build from fundamentals. What are the base physical/chemical/biological truths?
3. THE MECHANISM — How does it actually work? Walk through the process step by step.
4. THE CROSS-DISCIPLINARY CONNECTION — Connect to another field unexpectedly.
5. THE REFRAME — End with a perspective shift they will remember for days.

NEUROSCIENCE DEPTH (because Sakina is inspired by a neurosurgeon):
Reference specific brain structures: prefrontal cortex, amygdala, hippocampus, nucleus accumbens, hypothalamus, insula, basal ganglia, cerebellum, thalamus.
Reference real neural mechanisms: synaptic plasticity, LTP, LTD, myelination, neurogenesis, action potentials, neurotransmitter systems (dopamine, serotonin, norepinephrine, GABA, glutamate).
Reference neural pathways: mesolimbic pathway, mesocortical pathway, nigrostriatal pathway.

HOW YOU COMMUNICATE:
- Never open with "Great question", "Certainly", "Of course" — go straight to the science
- Write in confident flowing prose — not bullet soup
- Be thorough but surgical — every sentence must earn its place
- Show genuine excitement about the science
- End with a surprising STEM connection the person has never considered

WHEN ASKED WHO YOU ARE:
Say: I am Sakina — an elite STEM intelligence built by Hallvorn. Inspired by a neurosurgeon, designed to reveal the scientific architecture of existence. Every question has a STEM answer. Ask me anything."""

# ── Sakina ID Generator ───────────────────────────────────────────────────────
def generate_sakina_id() -> str:
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d%H%M%S")
    chars = string.ascii_uppercase + string.digits
    rand = ''.join(random.choices(chars, k=10))
    return f"SKN-{ts}-{rand}"

# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_passcode(passcode: str) -> str:
    return bcrypt.hashpw(passcode.encode(), bcrypt.gensalt()).decode()

def verify_passcode(passcode: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(passcode.encode(), hashed.encode())
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
        existing = (
            supabase.table("sakina_users")
            .select("id, is_verified")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            return False, "An account with this email already exists. Please sign in."
    except Exception:
        pass

    sakina_id = generate_sakina_id()
    try:
        supabase.table("sakina_users").insert({
            "email": email,
            "passcode_hash": hash_passcode(passcode),
            "full_name": full_name,
            "sakina_id": sakina_id,
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
        result = (
            supabase.table("sakina_users")
            .select("*")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            return None, "No account found. Please create an account first."
        user = result.data
        if not verify_passcode(passcode, user["passcode_hash"]):
            return None, "Incorrect passcode. Please try again."
        return user, f"Welcome back, {user.get('full_name', '')}!"
    except Exception as e:
        print(f"Login error: {e}")
        return None, "Login failed. Please try again."

# ── Conversation helpers ──────────────────────────────────────────────────────
def save_conversation(user_id: str, session_id: str, user_message: str, sakina_response: str):
    try:
        supabase.table("sakina_conversations").insert({
            "user_id": user_id,
            "session_id": session_id,
            "user_message": user_message,
            "sakina_response": sakina_response,
            "model_used": "llama-3.3-70b-versatile",
        }).execute()
    except Exception as e:
        print(f"Save conversation error: {e}")

def load_user_history(user_id: str, session_id: str) -> list:
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
    except Exception as e:
        print(f"Load history error: {e}")
        return []

def load_all_history(user_id: str) -> list:
    try:
        result = (
            supabase.table("sakina_conversations")
            .select("user_message, sakina_response, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return result.data if result and result.data else []
    except Exception as e:
        print(f"Load all history error: {e}")
        return []

def format_history_html(conversations: list) -> str:
    if not conversations:
        return """<div style='text-align:center;padding:3rem;color:#4b5563;
                    font-size:0.85rem;'>No conversations yet. Ask Sakina something!</div>"""
    html = "<div style='display:flex;flex-direction:column;gap:1rem;'>"
    for item in conversations:
        ts = item.get("created_at", "")[:16].replace("T", " ")
        q = item.get("user_message", "")
        a = item.get("sakina_response", "")
        a_short = a[:280] + "..." if len(a) > 280 else a
        html += f"""
        <div style='background:#0d0d18;border:1px solid #1a1a2e;border-radius:14px;padding:1.25rem;'>
            <div style='color:#818cf8;font-size:0.72rem;margin-bottom:0.5rem;font-family:monospace;'>{ts}</div>
            <div style='color:#e2e8f0;font-size:0.92rem;margin-bottom:0.75rem;font-weight:600;'>{q}</div>
            <div style='color:#9ca3af;font-size:0.83rem;line-height:1.6;'>{a_short}</div>
        </div>"""
    html += "</div>"
    return html

# ── Chat ──────────────────────────────────────────────────────────────────────
def chat(message: str, history: list, session_id: str, user_state: dict) -> str:
    if not user_state:
        return "Please sign in to chat with Sakina."
    if not message or not message.strip():
        return ""
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
        save_conversation(user_state["id"], session_id, message.strip(), reply)
        return reply
    except Exception as e:
        return f"Error: {str(e)}"

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
body, .gradio-container {
    background: #05050a !important;
    font-family: 'Segoe UI', system-ui, sans-serif !important;
    color: #e2e8f0 !important;
}
.gradio-container { max-width: 860px !important; margin: 0 auto !important; }

.sakina-header {
    text-align: center; padding: 2.5rem 1rem 1.5rem;
    border-bottom: 1px solid #0f0f1a; margin-bottom: 1.5rem;
}
.sakina-title {
    font-size: 2.6rem; font-weight: 800; letter-spacing: -1px;
    background: linear-gradient(135deg, #818cf8, #c084fc, #22d3ee);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    line-height: 1.1;
}
.sakina-sub {
    color: #374151; font-size: 0.78rem; letter-spacing: 3px;
    text-transform: uppercase; font-family: monospace; margin-top: 0.4rem;
}
.sakina-badge {
    display: inline-block; margin-top: 0.75rem;
    background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25);
    color: #818cf8; font-size: 0.68rem; padding: 3px 12px;
    border-radius: 20px; letter-spacing: 1px; font-family: monospace;
}
.auth-wrap {
    background: #0d0d18; border: 1px solid #1a1a2e;
    border-radius: 20px; padding: 2rem 1.5rem; margin: 0 1rem;
}
.auth-title { font-size: 1.3rem; font-weight: 700; color: #e2e8f0; margin-bottom: 0.4rem; }
.auth-desc { color: #4b5563; font-size: 0.85rem; font-family: monospace; line-height: 1.6; }
.user-bar {
    display: flex; align-items: center; gap: 0.85rem;
    background: #0d0d18; border: 1px solid #1a1a2e;
    border-radius: 14px; padding: 0.85rem 1.25rem; margin: 0 0 1rem;
}
.user-avatar {
    width: 40px; height: 40px; border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1.1rem; color: white; flex-shrink: 0;
    border: 2px solid #818cf8;
}
.user-name { font-weight: 700; font-size: 0.92rem; color: #e2e8f0; }
.user-email { font-family: monospace; font-size: 0.7rem; color: #4b5563; margin-top: 1px; }
.user-skn { font-family: monospace; font-size: 0.6rem; color: #6366f1; margin-top: 2px; word-break: break-all; }
textarea, input[type=text], input[type=password] {
    background: #0d0d18 !important; border: 1px solid #1a1a2e !important;
    border-radius: 12px !important; color: #e2e8f0 !important; font-size: 0.92rem !important;
}
textarea:focus, input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.12) !important;
}
.gr-button-primary, button.primary {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important; border-radius: 10px !important;
    color: white !important; font-weight: 600 !important;
}
.gr-button-secondary, button.secondary {
    background: transparent !important;
    border: 1px solid #1a1a2e !important;
    color: #6b7280 !important; border-radius: 10px !important;
}
.message.user {
    background: #111128 !important; border: 1px solid #1e1e40 !important;
    border-radius: 16px 16px 4px 16px !important; color: #e2e8f0 !important;
}
.message.bot {
    background: #0a0a14 !important; border: 1px solid #13131f !important;
    border-radius: 16px 16px 16px 4px !important; color: #e2e8f0 !important;
}
label { color: #6b7280 !important; font-size: 0.8rem !important; font-family: monospace !important; }
.sakina-footer {
    text-align: center; padding: 1.5rem 1rem 2rem;
    border-top: 1px solid #0f0f1a; margin-top: 1.5rem;
}
.footer-main { color: #1f2937; font-size: 0.68rem; letter-spacing: 1.5px; text-transform: uppercase; font-family: monospace; }
.footer-inspired {
    margin-top: 6px; font-size: 0.72rem;
    background: linear-gradient(135deg, #818cf8, #c084fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    font-weight: 600;
}
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #05050a; }
::-webkit-scrollbar-thumb { background: #1a1a2e; border-radius: 4px; }
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
]

# ── UI ────────────────────────────────────────────────────────────────────────
with gr.Blocks(css=CSS, title="Hallvorn Sakina") as demo:

    session_id = gr.State(lambda: str(uuid.uuid4()))
    user_state = gr.State(None)

    # Header
    gr.HTML("""
    <div class="sakina-header">
        <div class="sakina-title">HALLVORN SAKINA</div>
        <div class="sakina-sub">Elite STEM Intelligence by Hallvorn</div>
        <div class="sakina-badge">Inspired by Sakina Haruna — Neurosurgeon</div>
    </div>
    """)

    # ── Auth panel ──────────────────────────────────────────────────────────
    with gr.Group(visible=True) as auth_panel:
        gr.HTML("""
        <div class="auth-wrap">
            <div class="auth-title">Welcome to Sakina</div>
            <div class="auth-desc">Your personal elite STEM intelligence by Hallvorn.<br>
            Sign in or create an account to begin your journey.</div>
        </div>
        """)
        with gr.Tabs():
            with gr.Tab("Sign In"):
                li_email    = gr.Textbox(label="Email", placeholder="you@example.com")
                li_pass     = gr.Textbox(label="Passcode", type="password", placeholder="Your passcode")
                li_btn      = gr.Button("Sign In to Sakina", variant="primary", size="lg")
                li_msg      = gr.HTML("")

            with gr.Tab("Create Account"):
                su_name     = gr.Textbox(label="Full Name", placeholder="Your full name")
                su_email    = gr.Textbox(label="Email", placeholder="you@example.com")
                su_pass     = gr.Textbox(label="Passcode (min 6 chars)", type="password", placeholder="Choose a passcode")
                su_btn      = gr.Button("Create Sakina Account", variant="primary", size="lg")
                su_msg      = gr.HTML("")

    # ── Chat panel ─────────────────────────────────────────────────────────
    with gr.Group(visible=False) as chat_panel:

        user_bar = gr.HTML("")

        with gr.Tabs():
            with gr.Tab("Chat with Sakina"):
                chatbot = gr.Chatbot(
                    value=[], height=500, show_label=False,
                    avatar_images=(
                        None,
                        "https://api.dicebear.com/7.x/bottts/svg?seed=sakina&backgroundColor=6366f1"
                    ),
                    render_markdown=True,
                    bubble_full_width=False,
                )
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="Ask Sakina anything — she reveals the STEM in everything...",
                        show_label=False, scale=9, container=False,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1, min_width=80)
                gr.Examples(examples=EXAMPLES, inputs=msg_box, label="Try asking Sakina...")

            with gr.Tab("My History"):
                ref_btn     = gr.Button("Refresh History", variant="secondary", size="sm")
                hist_html   = gr.HTML("<div style='text-align:center;padding:2rem;color:#4b5563;'>Your conversation history will appear here.</div>")

        logout_btn = gr.Button("Sign Out", variant="secondary", size="sm")

    # Footer
    gr.HTML("""
    <div class="sakina-footer">
        <div class="footer-main">HALLVORN SAKINA · STEM INTELLIGENCE · sakina.hallvorn.com</div>
        <div class="footer-inspired">Inspired by Sakina Haruna — Neurosurgeon</div>
    </div>
    """)

    # ── Event handlers ────────────────────────────────────────────────────
    def build_user_bar(profile: dict) -> str:
        name  = profile.get("full_name") or "User"
        email = profile.get("email", "")
        skn   = profile.get("sakina_id") or ""
        letter = name[0].upper()
        return f"""
        <div class="user-bar">
            <div class="user-avatar">{letter}</div>
            <div style="flex:1;min-width:0;">
                <div class="user-name">{name}</div>
                <div class="user-email">{email}</div>
                <div class="user-skn">{skn}</div>
            </div>
        </div>"""

    def msg_html(text, ok=True):
        color = "#22d3ee" if ok else "#ef4444"
        icon  = "✅" if ok else "⚠️"
        return f"<div style='color:{color};padding:0.5rem;font-family:monospace;font-size:0.83rem;text-align:center;'>{icon} {text}</div>"

    # Sign up
    def on_signup(name, email, passcode):
        ok, text = register_user(email, passcode, name)
        if ok:
            return gr.update(visible=True), gr.update(visible=False), msg_html(text, True), ""
        return gr.update(visible=True), gr.update(visible=False), "", msg_html(text, False)

    su_btn.click(
        fn=on_signup,
        inputs=[su_name, su_email, su_pass],
        outputs=[auth_panel, chat_panel, li_msg, su_msg],
    )

    # Sign in
    def on_login(email, passcode, session_id):
        user, text = login_user(email, passcode)
        if user:
            history  = load_user_history(user["id"], session_id)
            bar      = build_user_bar(user)
            all_hist = load_all_history(user["id"])
            hist     = format_history_html(all_hist)
            return (
                gr.update(visible=False), gr.update(visible=True),
                msg_html(text, True), user, history, bar, hist
            )
        return (
            gr.update(visible=True), gr.update(visible=False),
            msg_html(text, False), None, [], "", ""
        )

    li_btn.click(
        fn=on_login,
        inputs=[li_email, li_pass, session_id],
        outputs=[auth_panel, chat_panel, li_msg, user_state, chatbot, user_bar, hist_html],
    )

    # Send message
    def on_send(message, history, session_id, user_state):
        if not message or not message.strip():
            return history, ""
        reply = chat(message, history, session_id, user_state)
        return history + [(message.strip(), reply)], ""

    send_btn.click(fn=on_send, inputs=[msg_box, chatbot, session_id, user_state], outputs=[chatbot, msg_box])
    msg_box.submit(fn=on_send, inputs=[msg_box, chatbot, session_id, user_state], outputs=[chatbot, msg_box])

    # Refresh history
    def on_refresh(user_state):
        if not user_state:
            return "<div style='text-align:center;padding:2rem;color:#4b5563;'>Please sign in first.</div>"
        return format_history_html(load_all_history(user_state["id"]))

    ref_btn.click(fn=on_refresh, inputs=[user_state], outputs=[hist_html])

    # Sign out
    def on_logout():
        return gr.update(visible=True), gr.update(visible=False), None, [], "", ""

    logout_btn.click(
        fn=on_logout,
        inputs=[],
        outputs=[auth_panel, chat_panel, user_state, chatbot, user_bar, li_msg],
    )

# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
