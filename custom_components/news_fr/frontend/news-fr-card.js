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
const CARD_VERSION = "0.1.0b2";

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

function ago(iso) {
  const t = iso ? new Date(iso).getTime() : NaN;
  if (!Number.isFinite(t)) return "";
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return "à l'instant";
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`;
  if (s < 2 * 86400) return "hier";
  return new Date(t).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}
const fullDate = (iso) => {
  const d = iso ? new Date(iso) : null;
  return d && Number.isFinite(d.getTime()) ? d.toLocaleString("fr-FR", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }) : "";
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
    let ids = (this._config.entities || []).filter((id) => st[id]);
    if (!ids.length) {
      ids = Object.entries(this._hass?.entities || {}).filter(([id, e]) => e.platform === "news_fr" && st[id]).map(([id]) => id);
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
    const sig = [c.theme, this._hass.themes?.darkMode, this._tab, this._more, [...this._open].join(","), ...sources.map((s) => s.id + s.last)].join("|");
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
    const when = (a) => Date.parse(a.published || "") || 0;
    pool.sort((a, b) => when(b) - when(a));
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
          <div class="am">${esc(fullDate(a.published))}${a.author ? ` · ${esc(a.author)}` : ""}</div>
          ${url ? `<a class="read" href="${esc(url)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon>Lire l'article sur ${esc(a.src.name)}</a>` : ""}
        </div>` : "";
      return `<div class="row${open ? " open" : ""}">
        <button class="head" data-art="${esc(key)}" aria-expanded="${open}">
          <span class="rb"><span class="rm"><i style="background:${a.src.color}"></i>${esc(a.src.name)}<span class="when">${esc(ago(a.published))}</span></span>
          <span class="rt">${esc(a.title)}</span></span>
          <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
        </button>${body}</div>`;
    }).join("");

    const err = current?.error ? `<div class="warn"><ha-icon icon="mdi:alert-outline"></ha-icon>Flux de ${esc(current.name)} indisponible : ${esc(current.error)}${current.articles.length ? " (derniers titres lus affichés)" : ""}</div>` : "";
    const more = pool.length > shown.length ? `<button class="more" data-act="more"><ha-icon icon="mdi:chevron-double-down"></ha-icon>Voir plus (${pool.length - shown.length})</button>` : "";
    const updated = sources.map((s) => s.updated).filter(Boolean).sort().pop();
    const tabsHtml = tabs.length > 1 ? `<div class="tabs" role="tablist">${tabs.map((t) => `<button class="tab${t.key === this._tab ? " on" : ""}" data-tab="${esc(t.key)}" role="tab" aria-selected="${t.key === this._tab}">${t.color ? `<i style="background:${t.color}"></i>` : `<ha-icon icon="mdi:newspaper-variant-multiple-outline"></ha-icon>`}${esc(t.name)}${t.error ? `<ha-icon class="te" icon="mdi:alert-outline"></ha-icon>` : ""}</button>`).join("")}</div>` : "";
    const link = this._tab === "all" ? "" : current?.site;

    this._card(`${tabsHtml}${err}<div class="list">${rows || `<div class="none">Aucun article pour le moment.</div>`}</div>
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
console.info(`%c NEWS-FR-CARD %c ${CARD_VERSION} © Marlboro62 `, "background:#96d21f;color:#1a2434;font-weight:700", "background:#1d93e3;color:#fff");
})();
