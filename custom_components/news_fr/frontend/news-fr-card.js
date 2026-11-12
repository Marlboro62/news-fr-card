/*
 * Carte Actualités France — custom:news-fr-card
 *
 * Affiche les capteurs de l'intégration Actualités France (non officielle) : titres des médias français.
 * Un clic sur un titre déroule l'image et le résumé publiés dans le flux RSS, avec un lien vers l'article.
 * Chargée automatiquement par l'intégration : aucune ressource à ajouter.
 *
 * © 2026 Marlboro62.
 */
(() => {
const CARD_VERSION = "0.1.2";

const DEFAULTS = {
  title: "Actualités",
  entities: [],
  max_items: 10,
  show_all: true,
  show_images: true,
  theme: "v2",
};

// Couleur de chaque média dans la carte (pastille et onglet)
const COLORS = ["#1d93e3", "#e5484d", "#f0a33a", "#96d21f", "#a77bf3", "#25c2a0", "#ff7eb6", "#8fa0b8", "#ffd23f", "#4cc3ff", "#ff8c42", "#c0e862"];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (typeof u === "string" && /^https?:\/\/[^\s"'<>]+$/.test(u) ? u : "");
const store = {
  get(k, d) { try { const v = JSON.parse(window.localStorage.getItem(k)); return v ?? d; } catch (e) { return d; } },
  set(k, v) { try { window.localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* stockage indisponible */ } },
};

function ago(iso, dateOnly) {
  const t = iso ? new Date(iso).getTime() : NaN;
  if (!Number.isFinite(t)) return "";
  if (dateOnly) {  // jour seulement (date tirée de l'adresse de l'article)
    const d = new Date(t), today = new Date();
    const days = Math.round((new Date(today.getFullYear(), today.getMonth(), today.getDate()) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000);
    return days <= 0 ? "aujourd'hui" : days === 1 ? "hier" : d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  }
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return "à l'instant";
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`;
  if (s < 2 * 86400) return "hier";
  return new Date(t).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}
const fullDate = (iso, dateOnly) => {
  const d = iso ? new Date(iso) : null;
  if (!d || !Number.isFinite(d.getTime())) return "";
  return dateOnly ? d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })
    : d.toLocaleString("fr-FR", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
};

/** Capteur « Alerte enlèvement » de l'intégration, s'il est actif. */
function alertState(hass) {
  if (!hass) return null;
  const id = Object.keys(hass.entities || {}).find((e) => e.startsWith("binary_sensor.") && hass.entities[e].platform === "news_fr");
  const st = id && hass.states[id];
  return st && st.state === "on" ? st : null;
}

/* ------------------------------------------------ Alerte Enlèvement : fenêtre
 * Ouverte par-dessus Home Assistant, quelle que soit la vue affichée et sur chaque appareil, sans option pour la
 * désactiver. « J'ai pris connaissance » la ferme pour cette alerte, sur cet appareil.
 */
const kidnapPopup = {
  started: false,
  start() {
    if (this.started || typeof document === "undefined") return;
    this.started = true;
    setInterval(() => this.check(), 5000);
    this.check();
  },
  check() {
    const hass = document.querySelector("home-assistant")?.hass;
    const st = alertState(hass);
    const a = st?.attributes || {};
    const key = `news-fr:alerte-vue:${a.alert_id || ""}`;
    if (!st || store.get(key, false)) { if (!st) this.close(); return; }
    if (document.getElementById("news-fr-kidnap")) return;
    const img = safeUrl(a.image), url = safeUrl(a.url);
    const box = document.createElement("div");
    box.id = "news-fr-kidnap";
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-labelledby", "news-fr-kidnap-t");
    box.innerHTML = `<style>
      #news-fr-kidnap { position: fixed; inset: 0; z-index: 2147483000; display: grid; place-items: center; padding: 16px;
        background: rgba(0,0,0,.72); font-family: Roboto, "Segoe UI", sans-serif; }
      #news-fr-kidnap .k { width: min(520px, 100%); max-height: calc(100vh - 32px); overflow: auto; border-radius: 18px;
        background: #1a2434; color: #e7edf5; border: 3px solid #e5484d; box-shadow: 0 20px 60px rgba(0,0,0,.6); }
      #news-fr-kidnap .h { display: flex; align-items: center; gap: 10px; padding: 14px 18px; background: #b3261e; color: #fff;
        font-size: 1.15rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
      #news-fr-kidnap .b { padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
      #news-fr-kidnap img { width: 100%; max-height: 300px; object-fit: contain; border-radius: 10px; background: #0d1624; }
      #news-fr-kidnap .t { font-size: 1.05rem; font-weight: 700; line-height: 1.35; }
      #news-fr-kidnap p { margin: 0; line-height: 1.5; font-size: .92rem; }
      #news-fr-kidnap .tel { padding: 10px 12px; border-radius: 10px; background: #2b1416; border: 1px solid #e5484d; font-size: .95rem; }
      #news-fr-kidnap .tel b { font-size: 1.3rem; color: #ff8a80; }
      #news-fr-kidnap .m { font-size: .76rem; color: #8fa0b8; }
      #news-fr-kidnap .a { display: flex; gap: 10px; flex-wrap: wrap; padding: 0 18px 18px; }
      #news-fr-kidnap .a a, #news-fr-kidnap .a button { flex: 1 1 180px; padding: 10px 14px; border-radius: 999px; font: inherit;
        font-weight: 700; font-size: .9rem; text-align: center; text-decoration: none; cursor: pointer; }
      #news-fr-kidnap .a a { background: #e5484d; color: #fff; border: 0; }
      #news-fr-kidnap .a button { background: none; color: #e7edf5; border: 1px solid #8fa0b8; }
      #news-fr-kidnap :focus-visible { outline: 3px solid #ffd23f; outline-offset: 2px; }
    </style>
    <div class="k">
      <div class="h">⚠️ Alerte enlèvement</div>
      <div class="b">
        ${img ? `<img src="${esc(img)}" alt="Photo diffusée avec l'alerte" referrerpolicy="no-referrer">` : ""}
        <div class="t" id="news-fr-kidnap-t">${esc(a.title || "Une alerte enlèvement est en cours.")}</div>
        ${a.summary ? `<p>${esc(a.summary)}</p>` : ""}
        <div class="tel">Si vous avez une information : <b>appelez le 197</b><br>N'intervenez pas vous-même.</div>
        <div class="m">Diffusée par ${esc((a.sources || [a.source]).filter(Boolean).join(", "))}${a.since ? ` · depuis ${esc(fullDate(a.since))}` : ""}</div>
      </div>
      <div class="a">
        ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Lire l'alerte</a>` : ""}
        <button type="button">J'ai pris connaissance</button>
      </div>
    </div>`;
    box.querySelector("button").addEventListener("click", () => { store.set(key, true); this.close(); });
    document.body.appendChild(box);
    box.querySelector("button").focus();
  },
  close() {
    document.getElementById("news-fr-kidnap")?.remove();
  },
};

class NewsFrCard extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  /** Éditeur visuel : formulaire de Home Assistant. */
  static getConfigForm() {
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "entities", selector: { entity: { multiple: true, filter: { integration: "news_fr" } } } },
        { name: "max_items", selector: { number: { min: 3, max: 50, mode: "box" } } },
        { type: "grid", name: "", schema: [
          { name: "show_all", selector: { boolean: {} } },
          { name: "show_images", selector: { boolean: {} } },
        ] },
        { name: "theme", selector: { select: { mode: "dropdown", options: [
          { value: "v2", label: "Bleu nuit (style des cartes MyElectricalData)" },
          { value: "auto", label: "Bleu nuit, clair si Home Assistant est en mode clair" },
          { value: "ha", label: "Thème de Home Assistant" }] } } },
      ],
      computeLabel: (s) => ({
        title: "Titre",
        entities: "Médias affichés (vide : tous les médias de l'intégration, dans cet ordre)",
        max_items: "Nombre de titres affichés (« Voir plus » pour la suite)",
        show_all: "Onglet « À la une » (tous les médias mélangés, du plus récent au plus ancien)",
        show_images: "Image de l'article quand on le déroule",
        theme: "Couleurs de la carte",
      }[s.name]),
    };
  }

  setConfig(config) {
    this._config = { ...DEFAULTS, ...(config || {}) };
    this._open = this._open || new Set();
    this._more = 0;
    this._sig = null;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => this._click(ev));
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    clearInterval(this._tick);
    this._tick = setInterval(() => { this._sig = null; this._render(); }, 60000);  // « il y a 5 min » à jour
  }

  disconnectedCallback() {
    clearInterval(this._tick);
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: 12, rows: "auto", min_columns: 6 };
  }

  /** Capteurs de l'intégration : ceux de la configuration, sinon tous. */
  _sources() {
    const st = this._hass?.states || {};
    // capteurs des médias seulement (l'alerte enlèvement est un binary_sensor, affiché à part)
    let ids = (this._config.entities || []).filter((id) => id.startsWith("sensor.") && st[id]);
    if (!ids.length) {
      ids = Object.entries(this._hass?.entities || {}).filter(([id, e]) => e.platform === "news_fr" && id.startsWith("sensor.") && st[id]).map(([id]) => id);
    }
    return ids.map((id, i) => {
      const s = st[id], a = s.attributes || {};
      return { id, i, name: a.friendly_name?.replace(/^Actualités France\s*/i, "") || id, color: COLORS[i % COLORS.length],
        site: safeUrl(a.site), error: a.error, updated: a.updated, articles: Array.isArray(a.articles) ? a.articles : [], last: s.last_updated };
    });
  }

  _click(ev) {
    const tab = ev.target.closest?.("[data-tab]");
    if (tab) { this._tab = tab.dataset.tab; this._more = 0; store.set("news-fr:tab", this._tab); this._sig = null; this._render(); return; }
    if (ev.target.closest?.("[data-act=more]")) { this._more += Number(this._config.max_items) || 10; this._sig = null; this._render(); return; }
    const row = ev.target.closest?.("[data-art]");
    if (row && !ev.target.closest("a")) {
      const id = row.dataset.art;
      if (this._open.has(id)) this._open.delete(id); else this._open.add(id);
      this._sig = null;
      this._render();
    }
  }

  _themeClass() {
    const t = this._config.theme;
    if (t === "ha") return "th-ha";
    if (t === "auto" && this._hass?.themes?.darkMode === false) return "light";
    return "";
  }

  _render() {
    if (!this._config || !this._hass || !this.shadowRoot) return;
    const c = this._config;
    const sources = this._sources();
    const kid = alertState(this._hass);
    const sig = [kid?.last_changed, kid?.attributes?.alert_id, c.theme, this._hass.themes?.darkMode, this._tab, this._more, [...this._open].join(","), ...sources.map((s) => s.id + s.last)].join("|");
    if (sig === this._sig) return;
    this._sig = sig;

    if (!sources.length) {
      this._card(`<div class="empty"><b>Intégration Actualités France introuvable</b>Ajoutez-la dans Paramètres › Appareils et services › Ajouter une intégration › Actualités France.</div>`);
      return;
    }
    const tabs = [...(c.show_all !== false && sources.length > 1 ? [{ key: "all", name: "À la une" }] : []), ...sources.map((s) => ({ key: s.id, name: s.name, color: s.color, error: s.error }))];
    if (!this._tab) this._tab = store.get("news-fr:tab", tabs[0].key);
    if (!tabs.some((t) => t.key === this._tab)) this._tab = tabs[0].key;

    const pool = this._tab === "all"
      ? sources.flatMap((s) => s.articles.map((a) => ({ ...a, src: s })))
      : sources.filter((s) => s.id === this._tab).flatMap((s) => s.articles.map((a) => ({ ...a, src: s })));
    // articles sans date : après les articles datés, dans l'ordre du flux
    const when = (a) => Date.parse(a.published || "") || 0;
    pool.forEach((a, i) => { a._i = i; });
    pool.sort((a, b) => when(b) - when(a) || a._i - b._i);
    const max = (Number(c.max_items) || 10) + this._more;
    const shown = pool.slice(0, max);
    const current = sources.find((s) => s.id === this._tab);

    const rows = shown.map((a) => {
      const key = `${a.src.id}:${a.id}`;
      const open = this._open.has(key);
      const url = safeUrl(a.url);
      const img = c.show_images !== false ? safeUrl(a.image) : "";
      const body = open ? `<div class="art">
          ${img ? `<img class="pic" src="${esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
          <p class="sum">${a.summary ? esc(a.summary) : `<i>Pas de résumé dans le flux de ${esc(a.src.name)}.</i>`}</p>
          <div class="am">${esc(fullDate(a.published, a.date_only))}${a.author ? ` · ${esc(a.author)}` : ""}</div>
          ${url ? `<a class="read" href="${esc(url)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon>Lire l'article sur ${esc(a.src.name)}</a>` : ""}
        </div>` : "";
      return `<div class="row${open ? " open" : ""}">
        <button class="head" data-art="${esc(key)}" aria-expanded="${open}">
          <span class="rb"><span class="rm"><i style="background:${a.src.color}"></i>${esc(a.src.name)}${ago(a.published, a.date_only) ? `<span class="when">${esc(ago(a.published, a.date_only))}</span>` : ""}</span>
          <span class="rt">${esc(a.title)}</span></span>
          <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
        </button>${body}</div>`;
    }).join("");

    const al = alertState(this._hass);
    const banner = al ? `<a class="kid" href="${esc(safeUrl(al.attributes.url) || "#")}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:account-alert"></ha-icon><span><b>Alerte enlèvement en cours</b>${esc(al.attributes.title || "")}<small>Information : appelez le 197</small></span></a>` : "";
    const err = current?.error ? `<div class="warn"><ha-icon icon="mdi:alert-outline"></ha-icon>Flux de ${esc(current.name)} indisponible : ${esc(current.error)}${current.articles.length ? " (derniers titres lus affichés)" : ""}</div>` : "";
    const more = pool.length > shown.length ? `<button class="more" data-act="more"><ha-icon icon="mdi:chevron-double-down"></ha-icon>Voir plus (${pool.length - shown.length})</button>` : "";
    const updated = sources.map((s) => s.updated).filter(Boolean).sort().pop();
    const tabsHtml = tabs.length > 1 ? `<div class="tabs" role="tablist">${tabs.map((t) => `<button class="tab${t.key === this._tab ? " on" : ""}" data-tab="${esc(t.key)}" role="tab" aria-selected="${t.key === this._tab}">${t.color ? `<i style="background:${t.color}"></i>` : `<ha-icon icon="mdi:newspaper-variant-multiple-outline"></ha-icon>`}${esc(t.name)}${t.error ? `<ha-icon class="te" icon="mdi:alert-outline"></ha-icon>` : ""}</button>`).join("")}</div>` : "";
    const link = this._tab === "all" ? "" : current?.site;

    this._card(`${banner}${tabsHtml}${err}<div class="list">${rows || `<div class="none">Aucun article pour le moment.</div>`}</div>
      <div class="foot">${more || "<span></span>"}<span>${updated ? `Mis à jour ${esc(ago(updated))} · ` : ""}Intégration non officielle · v${CARD_VERSION} © Marlboro62</span></div>`,
      this._tab === "all" ? "Tous les médias" : current?.name || "", link);
  }

  _card(body, sub = "", link = "") {
    const c = this._config;
    this.shadowRoot.innerHTML = `${STYLE}<ha-card class="${this._themeClass()}">
      <header><div class="brand"><span class="logo"><ha-icon icon="mdi:newspaper-variant-outline"></ha-icon></span>
        <div><div class="title">${esc(c.title || DEFAULTS.title)}</div>${sub ? `<div class="sub">${esc(sub)}</div>` : ""}</div></div>
        ${link ? `<a class="go" href="${esc(link)}" target="_blank" rel="noopener noreferrer" title="Ouvrir le site" aria-label="Ouvrir le site"><ha-icon icon="mdi:open-in-new"></ha-icon></a>` : ""}</header>
      ${body}</ha-card>`;
  }
}

const STYLE = `<style>
:host {
  --f-bg: #1a2434; --f-surface: #212d40; --f-line: #2f3d55; --f-text: #e7edf5; --f-muted: #8fa0b8;
  --f-accent: #1d93e3; --f-warn: #f0a33a; --f-on-accent: #fff;
}
ha-card { display: block; background: var(--f-bg); color: var(--f-text); border: 1px solid var(--f-line); border-radius: 18px; overflow: hidden; }
ha-card.light { --f-bg: #f4f6fa; --f-surface: #e8edf4; --f-line: #d3dbe6; --f-text: #1a2434; --f-muted: #5b6b82; --f-accent: #1673b8; --f-warn: #b35619; }
ha-card.th-ha { --f-bg: var(--ha-card-background, var(--card-background-color)); --f-surface: color-mix(in srgb, var(--primary-text-color, #000) 6%, transparent);
  --f-line: var(--divider-color, rgba(127,127,127,.25)); --f-text: var(--primary-text-color); --f-muted: var(--secondary-text-color);
  --f-accent: var(--primary-color, #1d93e3); --f-on-accent: var(--text-primary-color, #fff); border-radius: var(--ha-card-border-radius, 12px); }
header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px 8px; }
.brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.logo { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: color-mix(in srgb, var(--f-accent) 18%, transparent); flex: none; }
.logo ha-icon { --mdc-icon-size: 22px; color: var(--f-accent); }
.title { font-size: 1.1rem; font-weight: 700; }
.sub { font-size: .76rem; color: var(--f-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.go { color: var(--f-muted); display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; }
.go:hover, .go:focus-visible { color: var(--f-accent); background: var(--f-surface); outline: none; }
.tabs { display: flex; gap: 6px; padding: 4px 12px 8px; flex-wrap: wrap; }
.tab { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--f-line);
  background: var(--f-surface); color: var(--f-text); font: inherit; font-size: .82rem; cursor: pointer; }
.tab i { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.tab ha-icon { --mdc-icon-size: 16px; color: var(--f-muted); }
.tab ha-icon.te { color: var(--f-warn); --mdc-icon-size: 14px; }
.tab.on { background: var(--f-accent); border-color: var(--f-accent); color: var(--f-on-accent); }
.tab.on ha-icon:not(.te) { color: var(--f-on-accent); }
.tab:focus-visible, .head:focus-visible, .more:focus-visible, .read:focus-visible { outline: 2px solid var(--f-accent); outline-offset: 2px; }
.kid { display: flex; gap: 10px; align-items: center; margin: 0 12px 10px; padding: 10px 12px; border-radius: 12px; background: #b3261e; color: #fff; text-decoration: none; }
.kid ha-icon { --mdc-icon-size: 26px; flex: none; }
.kid span { display: flex; flex-direction: column; gap: 2px; font-size: .84rem; line-height: 1.3; }
.kid b { font-size: .95rem; text-transform: uppercase; letter-spacing: .03em; }
.kid small { font-size: .74rem; opacity: .9; }
.warn { display: flex; align-items: center; gap: 6px; margin: 0 12px 8px; padding: 8px 10px; border-radius: 10px; font-size: .78rem;
  color: var(--f-warn); border: 1px solid color-mix(in srgb, var(--f-warn) 50%, var(--f-line)); }
.warn ha-icon { --mdc-icon-size: 16px; flex: none; }
.list { display: flex; flex-direction: column; gap: 6px; padding: 0 12px; }
.row { border-radius: 12px; background: var(--f-surface); border: 1px solid transparent; }
.row:hover, .row.open { border-color: var(--f-line); }
.head { display: flex; gap: 10px; align-items: center; width: 100%; padding: 9px 10px; background: none; border: 0; color: inherit;
  font: inherit; text-align: left; cursor: pointer; border-radius: 12px; }
.rb { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 3px; }
.rm { display: flex; align-items: center; gap: 6px; font-size: .72rem; color: var(--f-muted); }
.rm i { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.when::before { content: "·"; margin-right: 6px; }
.rt { font-size: .9rem; font-weight: 600; line-height: 1.3; }
.chev { --mdc-icon-size: 20px; color: var(--f-muted); flex: none; transition: transform .2s; }
.row.open .chev { transform: rotate(180deg); color: var(--f-accent); }
.art { padding: 0 12px 12px; display: flex; flex-direction: column; gap: 8px; }
.pic { width: 100%; max-height: 220px; object-fit: cover; border-radius: 10px; background: var(--f-line); }
.sum { margin: 0; font-size: .86rem; line-height: 1.5; color: var(--f-text); }
.sum i { color: var(--f-muted); }
.am { font-size: .74rem; color: var(--f-muted); }
.read { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px;
  background: var(--f-accent); color: var(--f-on-accent); text-decoration: none; font-size: .8rem; font-weight: 600; }
.read ha-icon { --mdc-icon-size: 16px; }
.none, .empty { padding: 14px 4px; font-size: .86rem; color: var(--f-muted); }
.empty { display: flex; flex-direction: column; gap: 6px; padding: 4px 16px 16px; }
.empty b { color: var(--f-text); }
.more { display: inline-flex; align-items: center; gap: 4px; background: none; border: 1px solid var(--f-line); color: var(--f-text);
  border-radius: 999px; padding: 4px 10px; font: inherit; font-size: .74rem; cursor: pointer; }
.more ha-icon { --mdc-icon-size: 15px; color: var(--f-accent); }
.foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 14px 12px; font-size: .72rem; color: var(--f-muted); }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>`;

if (!customElements.get("news-fr-card")) customElements.define("news-fr-card", NewsFrCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "news-fr-card")) {
  window.customCards.push({
    type: "news-fr-card",
    name: "Actualités France",
    description: "Titres des médias français (Le Monde, BFMTV, CNews, Le Parisien…) ; un clic déroule le résumé et le lien vers l'article.",
    preview: true,
    documentationURL: "https://github.com/Marlboro62/news-fr-card",
  });
}
kidnapPopup.start();
console.info(`%c NEWS-FR-CARD %c ${CARD_VERSION} © Marlboro62 `, "background:#96d21f;color:#1a2434;font-weight:700", "background:#1d93e3;color:#fff");
})();
