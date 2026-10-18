// AI chat: keeps the conversation in the page only (nothing is persisted) and streams
// replies from the server as server-sent events over a POST fetch.
(() => {
  const urls = window.CHAT_URLS;
  const els = {
    model: document.getElementById("model"),
    log: document.getElementById("log"),
    status: document.getElementById("status"),
    form: document.getElementById("composer"),
    prompt: document.getElementById("prompt"),
    send: document.getElementById("send"),
    stop: document.getElementById("stop"),
    newChat: document.getElementById("new-chat"),
  };
  const csrfToken = els.form.querySelector("[name=csrfmiddlewaretoken]").value;

  let messages = [];
  let controller = null;

  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    div.textContent = text;
    els.log.appendChild(div);
    div.scrollIntoView({ block: "end" });
    return div;
  }

  function setBusy(busy) {
    els.send.disabled = busy;
    els.stop.hidden = !busy;
    els.prompt.disabled = busy;
  }

  async function loadModels() {
    try {
      const res = await fetch(urls.models);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not load models");
      els.model.innerHTML = "";
      for (const name of data.models) {
        const opt = document.createElement("option");
        opt.value = opt.textContent = name;
        if (name === data.default) opt.selected = true;
        els.model.appendChild(opt);
      }
      els.model.disabled = data.models.length === 0;
      if (data.models.length === 0) els.status.textContent = "No AI models are available.";
    } catch (err) {
      els.model.innerHTML = "<option>Unavailable</option>";
      els.status.textContent = err.message;
    }
  }

  // Parse "event: x\ndata: {...}\n\n" blocks out of a growing text buffer.
  function* parseEvents(buffer) {
    let idx;
    while ((idx = buffer.text.indexOf("\n\n")) !== -1) {
      const block = buffer.text.slice(0, idx);
      buffer.text = buffer.text.slice(idx + 2);
      let kind = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) kind = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      yield { kind, data: data ? JSON.parse(data) : {} };
    }
  }

  async function send(text) {
    messages.push({ role: "user", content: text });
    addMessage("user", text);
    const reply = addMessage("assistant", "");
    let replyText = "";
    setBusy(true);
    els.status.textContent = "Sending…";
    controller = new AbortController();

    try {
      const res = await fetch(urls.stream, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({ model: els.model.value, messages }),
        signal: controller.signal,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `Request failed (${res.status})`);
      }
      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      const buffer = { text: "" };
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer.text += value;
        for (const ev of parseEvents(buffer)) {
          if (ev.kind === "queued") els.status.textContent = `Waiting in line (position ${ev.data.position})…`;
          else if (ev.kind === "started") els.status.textContent = "Generating…";
          else if (ev.kind === "thinking") els.status.textContent = "Thinking…";
          else if (ev.kind === "token") {
            replyText += ev.data.text;
            reply.textContent = replyText;
            els.status.textContent = "Generating…";
          } else if (ev.kind === "error") throw new Error(ev.data.text);
        }
      }
      messages.push({ role: "assistant", content: replyText });
      els.status.textContent = "";
    } catch (err) {
      if (err.name === "AbortError") {
        els.status.textContent = "Stopped.";
        if (replyText) messages.push({ role: "assistant", content: replyText });
        else messages.pop();
      } else {
        reply.remove();
        messages.pop();
        addMessage("error", err.message);
        els.status.textContent = "";
      }
    } finally {
      controller = null;
      setBusy(false);
      els.prompt.focus();
    }
  }

  els.form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = els.prompt.value.trim();
    if (!text || controller) return;
    els.prompt.value = "";
    send(text);
  });
  els.prompt.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      els.form.requestSubmit();
    }
  });
  els.stop.addEventListener("click", () => controller && controller.abort());
  els.newChat.addEventListener("click", () => {
    if (controller) controller.abort();
    messages = [];
    els.log.innerHTML = "";
    els.status.textContent = "";
    els.prompt.focus();
  });

  loadModels();
})();
