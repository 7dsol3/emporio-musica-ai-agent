"use strict";
const $ = (selector) => document.querySelector(selector);
const language = window.EmporioLanguage;
const t = (key) => language.text(key);
const node = (tag, cls, text) => { const element = document.createElement(tag); if (cls) element.className = cls; if (text !== undefined) element.textContent = text; return element; };
let conversation = [], busy = false, currentView = "chat";

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : t("genericError"));
  return data;
}
function toast(message) { $("#toast").textContent = message; $("#toast").hidden = false; window.setTimeout(() => { $("#toast").hidden = true; }, 3500); }
function scrollChat() { const area = $(".conversation-area"); area.scrollTop = area.scrollHeight; }
function sourceLink(source, cls) {
  const link = node(source.type === "policy" ? "a" : "span", cls, source.label);
  if (source.type === "policy") { link.href = "/manual#page=" + source.page; link.target = "_blank"; link.rel = "noopener"; }
  return link;
}
function appendMessage(role, text, result = null) {
  $("#welcome").hidden = true;
  const item = node("article", "message " + role), label = node("div", "role");
  if (role === "assistant") { const icon = node("img"); icon.src = "/static/mark.svg"; icon.alt = ""; label.append(icon); }
  label.append(node("span", "", t(role === "user" ? "customer" : "assistant")));
  item.append(label, node("div", "message-text", text));
  if (result && result.sources.length) {
    const refs = node("div", "message-meta");
    result.sources.forEach(source => refs.append(sourceLink(source, "source-chip")));
    item.append(refs);
  }
  if (result && result.tools.length) {
    const details = node("details", "tool-details");
    details.append(node("summary", "", t("checked")));
    details.append(node("p", "", result.tools.map(t => t.tool.replaceAll("_", " ") + ": " + t.status.replaceAll("_", " ")).join(" · ")));
    details.append(node("p", "", (result.mode === "openai_compatible" ? "Model-selected tools" : result.mode === "local_fallback" ? "Local rules used after model fallback" : "Konaet local rules") + " · " + Math.round(result.latency_ms) + " ms · Evidence " + result.audit_hash.slice(0, 12)));
    item.append(details);
  }
  $("#messages").append(item); scrollChat();
}
let verified = false;
function setVerified(value) { verified = value; $("#verify-label").textContent = t(value ? "verified" : "verify"); }
async function send(text) {
  text = text.trim(); if (!text || busy) return;
  showView("chat"); busy = true; $("#send-button").disabled = true; $("#chat-error").hidden = true;
  $("#message-input").value = ""; $("#message-input").style.height = "auto";
  appendMessage("user", text); conversation.push({ role: "user", content: text });
  const typing = node("div", "typing", t("checking")); $("#messages").append(typing); scrollChat();
  try {
    const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text, locale: language.locale }) });
    typing.remove(); appendMessage("assistant", result.message, result); conversation.push({ role: "assistant", content: result.message });
    if (!result.human_service.open_now && result.human_service.next_scheduled_opening) {
      const next = new Date(result.human_service.next_scheduled_opening);
      $("#connection-label").textContent = t("humanReturns") + new Intl.DateTimeFormat(language.locale === "pt" ? "pt-BR" : "en-US", { timeZone: "America/Campo_Grande", weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }).format(next) + t("cityTime");
    }
    $("#latest-sources").replaceChildren();
    if (result.sources.length) result.sources.forEach(source => $("#latest-sources").append(sourceLink(source, "source-ref")));
    else $("#latest-sources").append(node("p", "muted small", t("noFacts")));
    $("#latest-mode").textContent = t(result.mode === "openai_compatible" ? "model" : result.mode === "local_fallback" ? "fallback" : "local");
  } catch (error) {
    typing.remove(); $("#chat-error").textContent = error.message; $("#chat-error").hidden = false;
    $("#message-input").value = text;
    conversation.pop(); $("#messages").lastElementChild?.remove();
    if (!conversation.length) $("#welcome").hidden = false;
  } finally { busy = false; $("#send-button").disabled = false; $("#message-input").focus(); }
}
function showView(view) {
  currentView = view;
  for (const name of ["chat", "catalog", "policies"]) $("#" + name + "-view").hidden = name !== view;
  document.querySelectorAll("[data-view]").forEach(button => button.classList.toggle("active", button.dataset.view === view));
  if (view === "catalog") loadCatalog();
  if (view === "policies") loadPolicies();
}
async function loadCatalog() {
  $("#catalog-count").textContent = t("catalogLoading");
  const params = new URLSearchParams();
  if ($("#catalog-query").value.trim()) params.set("query", $("#catalog-query").value.trim());
  if ($("#catalog-category").value) params.set("category_id", $("#catalog-category").value);
  try {
    const result = await api("/api/catalog?" + params);
    $("#catalog-count").textContent = result.total_matches ? (language.locale === "pt" ? "Mostrando " + result.products.length + " de " + result.total_matches + " instrumentos. Refine a busca para encontrar um modelo específico." : "Showing " + result.products.length + " of " + result.total_matches + " matching instruments. Narrow the search to find a specific model.") : t("noProducts");
    $("#catalog-grid").replaceChildren();
    for (const product of result.products) {
      const card = node("article", "product-card"); card.append(node("div", "category", product.category), node("h3", "", product.name));
      const price = node("div", "product-price");
      if (product.discount_percent) price.append(node("span", "product-original", currency(product.price_cents)));
      price.append(document.createTextNode(currency(product.sale_cents))); card.append(price);
      card.append(node("span", "stock-tag" + (product.available ? "" : " unavailable"), product.available ? t("inStock") + (product.discount_percent ? " · " + product.discount_percent + t("off") : "") : "○ " + (language.locale === "pt" ? ({ active: "sem estoque", discontinued: "descontinuado", coming_soon: "em breve" })[product.status] : product.status.replaceAll("_", " ") + (product.status === "active" ? " · out of stock" : ""))));
      const ask = node("button", "", t("askProduct")); ask.addEventListener("click", () => send((language.locale === "pt" ? "Qual o preço e a disponibilidade de " : "Tell me the price and availability of ") + product.name + ".")); card.append(ask);
      $("#catalog-grid").append(card);
    }
  } catch (error) { $("#catalog-count").textContent = error.message; }
}
function currency(cents) { return new Intl.NumberFormat(language.locale === "pt" ? "pt-BR" : "en-US", { style: "currency", currency: "BRL" }).format(cents / 100); }
async function loadPolicies() {
  try {
    const cards = await api("/api/policies?locale=" + language.locale); $("#policy-list").replaceChildren();
    for (const card of cards) {
      const details = node("details"); details.append(node("summary", "", card.title), node("p", "", card.summary));
      const link = node("a", "text-link", t("readManual") + card.pages.join(", ") + " ↗"); link.href = "/manual#page=" + card.pages[0]; link.target = "_blank"; link.rel = "noopener"; details.append(link); $("#policy-list").append(details);
    }
  } catch (error) { toast(error.message); }
}
$("#chat-form").addEventListener("submit", event => { event.preventDefault(); send($("#message-input").value); });
$("#message-input").addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(event.target.value); } });
$("#message-input").addEventListener("input", event => { event.target.style.height = "auto"; event.target.style.height = Math.min(event.target.scrollHeight, 125) + "px"; });
document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => send(button.dataset.prompt)));
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
document.querySelectorAll("[data-close]").forEach(button => button.addEventListener("click", () => $("#" + button.dataset.close).close()));
$("#catalog-form").addEventListener("submit", event => { event.preventDefault(); loadCatalog(); });
$("#about-button").addEventListener("click", () => $("#about-dialog").showModal());
$("#verify-button").addEventListener("click", () => { $("#verify-result").textContent = ""; $("#verify-dialog").showModal(); });
$("#verify-form").addEventListener("submit", async event => {
  event.preventDefault(); const button = event.target.querySelector("[type=submit]"); button.disabled = true;
  try {
    const result = await api("/api/verify", { method: "POST", body: JSON.stringify({ order_id: Number($("#order-id").value), email: $("#purchase-email").value }) });
    $("#verify-result").textContent = t(result.verified ? "verifiedToast" : "verifyFailed"); setVerified(result.verified); $("#purchase-email").value = "";
    if (result.verified) { const order = $("#order-id").value; $("#verify-dialog").close(); toast(t("verifiedToast")); send((language.locale === "pt" ? "Qual é o status do pedido #" : "What is the status of order #") + order + "?"); }
  } catch (error) { $("#verify-result").textContent = error.message; } finally { button.disabled = false; }
});
$("#new-chat").addEventListener("click", async () => {
  if (busy) return;
  try { await api("/api/session", { method: "DELETE" }); conversation = []; $("#messages").replaceChildren(); $("#welcome").hidden = false; $("#chat-error").hidden = true; setVerified(false); showView("chat"); $("#latest-sources").replaceChildren(node("p", "muted small", t("refs"))); toast(t("cleared")); } catch (error) { toast(error.message); }
});
$("#export-button").addEventListener("click", () => {
  if (!conversation.length) { toast(t("noExport")); return; }
  const text = "# Empório da Música - Conversation\n\n" + conversation.map(m => "**" + (m.role === "user" ? "Customer" : "Assistant") + ":** " + m.content).join("\n\n");
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" })); const anchor = node("a"); anchor.href = url; anchor.download = "emporio-conversation.md"; anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
});
async function initialize() {
  try {
    const [health, session] = await Promise.all([api("/api/health"), api("/api/session")]);
    $("#connection-label").textContent = t("ready"); $("#product-count").textContent = health.counts.products;
    if (health.provider !== "local") $("#latest-mode").textContent = t("configured");
    conversation = session.history; conversation.forEach(m => appendMessage(m.role, m.content)); setVerified(session.verified);
  } catch (error) { $("#connection-label").textContent = t("offline"); $("#chat-error").textContent = error.message; $("#chat-error").hidden = false; }
}
$("#language-select").addEventListener("change", (event) => { language.set(event.target.value); setVerified(verified); $("#connection-label").textContent = t("ready"); $("#latest-mode").textContent = t("local"); if (currentView === "catalog") loadCatalog(); if (currentView === "policies") loadPolicies(); });
language.apply();
initialize();
