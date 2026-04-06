// State — no Gradio state components, just plain JS objects
const state = {
  user: null,
  sessionId: null,
  history: [],
  chatName: "New Conversation",
  sessions: [],
};

// Auth
async function doLogin() {
  const email   = document.getElementById("liEmail").value;
  const passcode = document.getElementById("liPass").value;
  const res = await fetch("/api/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({email, passcode})
  });
  const data = await res.json();
  if (data.ok) {
    state.user = data.user;
    localStorage.setItem("sakina_user", JSON.stringify({id: data.user.id, t: Date.now()}));
    await enterApp();
  } else {
    document.getElementById("liMsg").textContent = data.msg;
  }
}

async function enterApp() {
  document.getElementById("authScreen").style.display = "none";
  document.getElementById("appShell").style.display  = "flex";
  state.sessionId = crypto.randomUUID();
  state.history   = [];
  state.chatName  = "New Conversation";
  await loadSessions();
  renderSidebar();
  renderWelcome();
}

// Chat
async function doSend() {
  const box = document.getElementById("msgBox");
  const msg = box.value.trim();
  if (!msg) return;
  box.value = "";

  appendMessage("user", msg);

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      user_id: state.user.id,
      session_id: state.sessionId,
      message: msg,
      history: state.history,
      chat_name: state.chatName,
    })
  });
  const data = await res.json();
  state.chatName = data.chat_name;
  state.history.push([msg, data.reply]);
  appendMessage("bot", data.reply);
  await loadSessions();
  renderSidebar();
}

function appendMessage(role, text) {
  const chat = document.getElementById("chatArea");
  const div  = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;  // or use a markdown renderer like marked.js
  chat.appendChild(div);
  chat.scrollIntoView({block: "end"});
}

// Sessions, sidebar, settings — all straightforward DOM manipulation
async function loadSessions() {
  const res = await fetch(`/api/sessions/${state.user.id}`);
  const data = await res.json();
  state.sessions = data.sessions;
}
