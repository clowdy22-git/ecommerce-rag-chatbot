/**
 * Shop Assistant embeddable widget.
 * Served from the same FastAPI app as the API, so it just uses relative
 * paths (/chat, /products, /feedback) - no CORS, no separate server needed.
 */
(function () {
  const scriptTag = document.currentScript;
  const API_BASE = scriptTag?.getAttribute("data-api-base") || ""; // "" = same origin
  const sessionId = "sess-" + Math.random().toString(36).slice(2, 10);

  const root = document.createElement("div");
  root.innerHTML = `
    <button id="sa-launcher" aria-label="Open shop assistant">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 8.4 8.4 0 0 1-4-1L3 20l1.1-4.4A8.5 8.5 0 1 1 21 11.5z"/>
      </svg>
    </button>
    <div id="sa-panel" role="dialog" aria-label="Shop assistant chat">
      <div id="sa-header">
        <div>
          <div class="sa-title">Shop Assistant</div>
          <div class="sa-sub">Ask about our products, orders &amp; shipping</div>
        </div>
        <button id="sa-close" aria-label="Close chat">✕</button>
      </div>
      <div id="sa-messages"></div>
      <div id="sa-inputbar">
        <textarea id="sa-input" rows="1" placeholder="Ask about a product, order, or return..."></textarea>
        <button id="sa-send">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(root);

  const launcher = document.getElementById("sa-launcher");
  const panel = document.getElementById("sa-panel");
  const closeBtn = document.getElementById("sa-close");
  const messagesEl = document.getElementById("sa-messages");
  const input = document.getElementById("sa-input");
  const sendBtn = document.getElementById("sa-send");

  let greeted = false;

  launcher.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (panel.classList.contains("open") && !greeted) {
      addBotMessage(
        "Hi! I can help with questions about our products, sizing, pricing, shipping and returns. What are you looking for?",
        null
      );
      greeted = true;
    }
  });
  closeBtn.addEventListener("click", () => panel.classList.remove("open"));

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  function addUserMessage(text) {
    const el = document.createElement("div");
    el.className = "sa-msg user";
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function addTyping() {
    const el = document.createElement("div");
    el.className = "sa-typing";
    el.id = "sa-typing-indicator";
    el.textContent = "Shop Assistant is typing...";
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function removeTyping() {
    document.getElementById("sa-typing-indicator")?.remove();
  }

  function addProductCards(sources) {
    const unique = [];
    const seenTitles = new Set();
    for (const s of sources || []) {
      if (!s.product_title || seenTitles.has(s.product_title)) continue;
      if (!s.image_url) continue;
      seenTitles.add(s.product_title);
      unique.push(s);
      if (unique.length >= 3) break;
    }
    if (unique.length === 0) return;

    const wrap = document.createElement("div");
    wrap.className = "sa-cards";
    unique.forEach((s) => {
      const card = document.createElement(s.url ? "a" : "div");
      card.className = "sa-card";
      if (s.url) {
        card.href = s.url;
        card.target = "_blank";
        card.rel = "noopener noreferrer";
      }
      card.innerHTML = `
        <img src="${s.image_url}" alt="${s.product_title}" loading="lazy" onerror="this.style.display='none'" />
        ${s.is_web ? `<div class="sa-card-badge">🌐 Online</div>` : ""}
        <div class="sa-card-title">${s.product_title}</div>
        ${s.price ? `<div class="sa-card-price">${s.price}</div>` : ""}
      `;
      wrap.appendChild(card);
    });
    messagesEl.appendChild(wrap);
  }

  function addBotMessage(text, meta) {
    const bubble = document.createElement("div");
    bubble.className = "sa-msg bot" + (meta && meta.in_domain === false ? " refused" : "");
    bubble.textContent = text;
    messagesEl.appendChild(bubble);

    if (meta && meta.sources && meta.sources.length) {
      addProductCards(meta.sources);
    }

    if (meta) {
      const confRow = document.createElement("div");
      confRow.className = "sa-confidence";
      const pct = Math.round((meta.confidence || 0) * 100);
      const low = pct < 50;
      confRow.innerHTML = `<span class="sa-conf-tag${low ? " low" : ""}">Confidence: ${pct}%</span>`;
      messagesEl.appendChild(confRow);

      if (meta.in_domain && meta.has_answer) {
        const fb = document.createElement("div");
        fb.className = "sa-feedback";
        fb.innerHTML = `<button data-rating="up">👍 Helpful</button><button data-rating="down">👎 Not helpful</button>`;
        fb.querySelectorAll("button").forEach((btn) => {
          btn.addEventListener("click", () => {
            fb.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            sendFeedback(meta, btn.dataset.rating);
          });
        });
        messagesEl.appendChild(fb);
      }
    }
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendBtn.disabled = true;
    addUserMessage(text);
    addTyping();

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, session_id: sessionId }),
      });
      removeTyping();

      if (!res.ok) {
        addBotMessage("Sorry, something went wrong on my end. Please try again in a moment.", null);
        return;
      }
      const data = await res.json();
      addBotMessage(data.answer, {
        message_id: data.message_id,
        confidence: data.confidence,
        in_domain: data.in_domain,
        has_answer: data.has_answer,
        sources: data.sources,
        query: text,
      });
    } catch (err) {
      removeTyping();
      addBotMessage("I couldn't reach the server. Please check your connection and try again.", null);
    } finally {
      sendBtn.disabled = false;
    }
  }

  async function sendFeedback(meta, rating) {
    try {
      await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: meta.message_id,
          session_id: sessionId,
          query: meta.query,
          answer: "",
          confidence: meta.confidence,
          rating,
        }),
      });
    } catch (err) {
      // best-effort
    }
  }
})();
