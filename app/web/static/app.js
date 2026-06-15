"use strict";
// snapvoice API-Playground – ruft die gehaerteten /playground/* Endpunkte auf
// derselben Origin auf. Kein API-Key im Browser. Ergebnisse werden per DOM
// (textContent) gerendert, nie per innerHTML mit Eingabedaten.

const $ = (sel, root = document) => root.querySelector(sel);

function el(tag, props = {}, children = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v);
  }
  for (const c of [].concat(children)) if (c) n.appendChild(c);
  return n;
}

function setBusy(btn, busy) {
  btn.disabled = busy;
  if (busy) { btn.dataset.label = btn.textContent; btn.textContent = "… bitte warten"; }
  else if (btn.dataset.label) { btn.textContent = btn.dataset.label; }
}

function showSpinner(box, msg) {
  box.hidden = false;
  box.replaceChildren(el("p", { class: "spin", text: msg }));
}

function renderError(box, msg) {
  box.hidden = false;
  box.replaceChildren(
    el("span", { class: "verdict bad" }, [el("span", { class: "dot" }), el("span", { text: "Fehler" })]),
    el("p", { class: "note", text: msg })
  );
}

function verdict(ok, label) {
  return el("span", { class: "verdict " + (ok ? "ok" : "bad") },
    [el("span", { class: "dot" }), el("span", { text: label })]);
}

function metaRow(k, v) {
  return el("div", {}, [
    el("span", { class: "k", text: k }),
    el("span", { class: "v" + (k === "Beleg-Hash" ? " hash" : ""), text: String(v) }),
  ]);
}

function findingList(title, items, warn) {
  if (!items || !items.length) return null;
  const box = el("div", { class: "findings" }, [el("h4", { text: title })]);
  for (const f of items) {
    const head = [];
    if (f.code) head.push(el("span", { class: "code", text: f.code }));
    head.push(el("span", { text: f.message || "" }));
    const node = el("div", { class: "finding" + (warn ? " warn" : "") }, head);
    if (f.location) node.appendChild(el("span", { class: "loc", text: f.location }));
    box.appendChild(node);
  }
  return box;
}

/* ===================== API-Key & Credits ===================== */
const apikeyInput = $("#apikey");
const accStatus = $("#acc-status");
const accCredits = $("#acc-credits");
const KEY_STORE = "snapvoice_api_key";
let creditLimit = 120;
let keyOk = false;                 // true ⇒ Run-Buttons aktiv (gültiger Key, oder Dev ohne Keys)
const vRunBtn = $("#validate-run");
const gRunBtn = $("#generate-run");

function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function getKey() { return apikeyInput.value.trim(); }
function keyHeaders() { const k = getKey(); return k ? { "X-API-Key": k } : {}; }

function setStatus(kind, text) { accStatus.className = "acc-status " + kind; accStatus.textContent = text; }
function setCredits(used, limit) {
  creditLimit = limit || creditLimit;
  if (used === null || used === undefined) {
    accCredits.textContent = "Verbrauchte Credits: –/" + creditLimit;
    accCredits.classList.remove("low");
  } else {
    accCredits.textContent = "Verbrauchte Credits: " + used + "/" + creditLimit;
    accCredits.classList.toggle("low", used >= creditLimit);
  }
}

// Kein anonymes Testen: Run-Buttons nur bei gültigem Key (bzw. lokal ohne Key-System) aktiv.
function updateRunButtons() {
  vRunBtn.disabled = !keyOk;
  gRunBtn.disabled = !keyOk;
  const t = keyOk ? "" : "Bitte oben einen gültigen API-Key eingeben";
  vRunBtn.title = t;
  gRunBtn.title = t;
}

async function refreshCredits() {
  const k = getKey();
  try {
    const res = await fetch("/playground/credits", { headers: k ? { "X-API-Key": k } : {} });
    const d = await res.json().catch(() => null);
    if (!d) { setStatus("bad", "Status nicht abrufbar"); keyOk = false; }
    else if (d.configured === false) {            // kein Key-System (lokale Entwicklung)
      setStatus("neutral", "Kein Key nötig (Dev)"); setCredits(null, creditLimit); keyOk = true;
    } else if (!k) {
      setStatus("bad", "API-Key erforderlich"); setCredits(null, d.limit); keyOk = false;
    } else if (!d.valid) {
      setStatus("bad", "Ungültiger API-Key"); setCredits(null, d.limit); keyOk = false;
    } else {
      setStatus("ok", "API-Key gültig"); setCredits(d.used, d.limit); keyOk = true;
    }
  } catch (e) { setStatus("bad", "Status nicht abrufbar"); keyOk = false; }
  updateRunButtons();
}

// Credit-Header einer Antwort live in die Anzeige uebernehmen (sonst /credits nachladen).
function syncCredits(res) {
  const lim = res.headers.get("X-Credits-Limit");
  const used = res.headers.get("X-Credits-Used");
  if (lim && used !== null) {
    setStatus("ok", "API-Key gültig");
    setCredits(parseInt(used, 10), parseInt(lim, 10));
    keyOk = true;
    updateRunButtons();
  } else if (getKey()) {
    refreshCredits();
  }
}

apikeyInput.addEventListener("input", debounce(() => {
  localStorage.setItem(KEY_STORE, getKey());
  refreshCredits();
}, 400));

/* ===================== Tabs ===================== */
for (const tab of document.querySelectorAll(".tab")) {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("is-active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("is-active"));
    tab.classList.add("is-active");
    $("#" + tab.dataset.panel).classList.add("is-active");
  });
}

/* ===================== Validate ===================== */
const vXml = $("#validate-xml");
const vFile = $("#validate-file");
const vHint = $("#validate-loaded");
const vResult = $("#validate-result");
let validatePendingFile = null; // gesetzt, wenn ein PDF-Beispiel geladen wurde

function setActiveChip(chip) {
  document.querySelectorAll("#validate-samples .chip").forEach(c => c.classList.remove("is-active"));
  if (chip) chip.classList.add("is-active");
}

for (const chip of document.querySelectorAll("#validate-samples .chip")) {
  chip.addEventListener("click", () => loadValidateSample(chip.dataset.key, chip));
}

async function loadValidateSample(key, chip) {
  setActiveChip(chip);
  vHint.textContent = "Lade Beispiel …";
  try {
    const res = await fetch("/playground/samples/" + encodeURIComponent(key));
    if (!res.ok) { vHint.textContent = "Beispiel konnte nicht geladen werden."; return; }
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("pdf")) {
      const blob = await res.blob();
      const name = key + ".pdf";
      validatePendingFile = new File([blob], name, { type: "application/pdf" });
      vXml.value = "";
      vFile.value = "";
      vHint.textContent = "PDF-Beispiel geladen (" + name + ") — jetzt auf „Prüfen“.";
    } else {
      vXml.value = await res.text();
      validatePendingFile = null;
      vFile.value = "";
      vHint.textContent = "Beispiel geladen — Sie können es bearbeiten und „Prüfen“.";
    }
  } catch (e) {
    vHint.textContent = "Netzwerkfehler beim Laden: " + e.message;
  }
}

// Eigene Eingabe hat Vorrang: sobald getippt/Datei gewählt wird, PDF-Beispiel verwerfen.
vXml.addEventListener("input", () => { if (vXml.value) { validatePendingFile = null; setActiveChip(null); } });
vFile.addEventListener("change", () => {
  if (vFile.files && vFile.files[0]) {
    validatePendingFile = null; setActiveChip(null);
    vHint.textContent = "Datei gewählt: " + vFile.files[0].name;
  }
});

$("#validate-reset").addEventListener("click", () => {
  vXml.value = ""; vFile.value = ""; validatePendingFile = null;
  setActiveChip(null); vHint.textContent = ""; vResult.hidden = true;
});

$("#validate-run").addEventListener("click", runValidate);

async function runValidate() {
  if (!keyOk) { renderError(vResult, "Bitte oben einen gültigen API-Key eingeben."); return; }
  let file;
  if (vFile.files && vFile.files[0]) file = vFile.files[0];
  else if (validatePendingFile) file = validatePendingFile;
  else {
    const text = vXml.value.trim();
    if (!text) { renderError(vResult, "Bitte ein Beispiel laden, XML einfügen oder eine Datei wählen."); return; }
    file = new File([text], "eingabe.xml", { type: "application/xml" });
  }
  const fd = new FormData();
  fd.append("file", file);
  const btn = $("#validate-run");
  setBusy(btn, true);
  showSpinner(vResult, "Wird geprüft …");
  try {
    const res = await fetch("/playground/validate", { method: "POST", body: fd, headers: keyHeaders() });
    syncCredits(res);
    const data = await res.json().catch(() => null);
    if (res.ok && data) renderValidate(data);
    else renderError(vResult, (data && data.detail) || ("Fehler " + res.status));
  } catch (e) {
    renderError(vResult, "Netzwerkfehler: " + e.message);
  } finally {
    setBusy(btn, false);
  }
}

function renderValidate(d) {
  vResult.hidden = false;
  const parts = [verdict(d.valid, d.valid ? "GÜLTIG" : "UNGÜLTIG")];

  const meta = el("div", { class: "meta" });
  const add = (k, v) => { if (v !== null && v !== undefined && v !== "") meta.appendChild(metaRow(k, v)); };
  add("Eingabe", d.input_type === "pdf" ? "PDF (ZUGFeRD/Factur-X)" : "XML");
  add("Format", d.format);
  add("Dokumenttyp", d.document_type);
  add("Profil", d.profile);
  add("Version", d.version);
  add("Validator", d.validator);
  add("Regelwerk", d.ruleset_version);
  if (d.input_sha256) add("Beleg-Hash", d.input_sha256.slice(0, 24) + "…");
  parts.push(meta);

  const errs = findingList("Fehler", d.errors, false);
  const warns = findingList("Warnungen", d.warnings, true);
  if (errs) parts.push(errs);
  if (warns) parts.push(warns);
  if (d.valid && !warns) parts.push(el("p", { class: "note", text: "Keine Beanstandungen — diese Rechnung ist konform." }));

  vResult.replaceChildren(...parts);
}

/* ===================== Generate ===================== */
const gJson = $("#generate-json");
const gResult = $("#generate-result");

$("#generate-load").addEventListener("click", loadInvoiceSample);
$("#generate-reset").addEventListener("click", () => { gJson.value = ""; gResult.hidden = true; });
$("#generate-run").addEventListener("click", runGenerate);

async function loadInvoiceSample() {
  try {
    const res = await fetch("/playground/samples/invoice-json");
    if (res.ok) gJson.value = await res.text();
  } catch (e) { /* still */ }
}

async function runGenerate() {
  if (!keyOk) { renderError(gResult, "Bitte oben einen gültigen API-Key eingeben."); return; }
  const text = gJson.value.trim();
  if (!text) { renderError(gResult, "Bitte JSON eingeben oder das Beispiel laden."); return; }
  const btn = $("#generate-run");
  setBusy(btn, true);
  showSpinner(gResult, "Wird erzeugt und intern validiert …");
  try {
    const res = await fetch("/playground/generate", {
      method: "POST", headers: { "Content-Type": "application/json", ...keyHeaders() }, body: text,
    });
    syncCredits(res);
    const data = await res.json().catch(() => null);
    if (data && "valid" in data) renderGenerate(data);
    else renderError(gResult, (data && data.detail) || ("Fehler " + res.status));
  } catch (e) {
    renderError(gResult, "Netzwerkfehler: " + e.message);
  } finally {
    setBusy(btn, false);
  }
}

function renderGenerate(d) {
  gResult.hidden = false;

  if (d.valid) {
    const meta = el("div", { class: "meta" });
    if (d.validator) meta.appendChild(metaRow("Validator", d.validator));
    if (d.ruleset_version) meta.appendChild(metaRow("Regelwerk", d.ruleset_version));

    const fname = (d.invoice_number || "rechnung") + ".xml";
    const dl = el("button", { class: "btn mini", text: "XML herunterladen" });
    dl.addEventListener("click", () => {
      const blob = new Blob([d.xml], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const a = el("a", { href: url, download: fname });
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    });
    const copy = el("button", { class: "btn ghost mini", text: "Kopieren" });
    copy.addEventListener("click", () => navigator.clipboard && navigator.clipboard.writeText(d.xml));

    gResult.replaceChildren(
      verdict(true, "GÜLTIGE XRECHNUNG ERZEUGT"),
      meta,
      el("div", { class: "actions" }, [dl, copy]),
      el("pre", { class: "xml", text: d.xml })
    );
    return;
  }

  // Ungültig: entweder Schema- (Pydantic) oder Validierungs-Fehler (KoSIT-Regeln).
  if (d.error_type === "schema") {
    const items = (d.errors || []).map(e => ({ code: e.loc, message: e.msg }));
    gResult.replaceChildren(
      verdict(false, "EINGABE UNGÜLTIG"),
      el("p", { class: "note", text: "Das JSON entspricht nicht dem Rechnungsschema:" }),
      findingList("Schema-Fehler", items, false) || el("span")
    );
  } else {
    gResult.replaceChildren(
      verdict(false, "NICHT KONFORM"),
      el("p", { class: "note", text: "Die erzeugte Rechnung hat die interne Validierung nicht bestanden:" }),
      findingList("Fehler", d.errors, false) || el("span")
    );
  }
}

// Komfort: Generate-Beispiel direkt vorbefuellen.
loadInvoiceSample();

// API-Key aus dem letzten Besuch wiederherstellen + Credits anzeigen.
const savedKey = localStorage.getItem(KEY_STORE);
if (savedKey) apikeyInput.value = savedKey;
refreshCredits();
