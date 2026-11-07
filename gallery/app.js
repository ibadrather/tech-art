// tech-art gallery: faceted browser for window.POSTERS (written by src/gallery.py).
// All state lives in the URL hash — #q=lidar&in=drone/camera,robots&sort=name&p=drone/camera/hover —
// so filtered views and posters are linkable and back / forward work.

const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const label = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

const POSTERS = (window.POSTERS || []).map((p, i) => ({
  ...p,
  order: i,
  path: p.group ? `${p.series}/${p.group}` : p.series,
  text: `${p.name} ${p.series} ${p.group} ${p.idea}`.toLowerCase(),
}));
const byId = new Map(POSTERS.map((p) => [p.id, p]));
const SERIES = [...new Set(POSTERS.map((p) => p.series))];
const GROUPS = Object.fromEntries(SERIES.map((s) => [s, [...new Set(POSTERS.filter((p) => p.series === s && p.group).map((p) => p.group))]]));
const PATHS = SERIES.flatMap((s) => [s, ...GROUPS[s].map((g) => `${s}/${g}`)]);
const pathLabel = (path) => path.split("/").map(label).join(" / ");

const SORTS = {
  featured: (a, b) => a.order - b.order,
  name: (a, b) => a.name.localeCompare(b.name),
  "name-desc": (a, b) => b.name.localeCompare(a.name),
  collection: (a, b) => a.path.localeCompare(b.path) || a.name.localeCompare(b.name),
};

const ICON = {
  x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>',
  down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11m-5-5 5 5 5-5M5 20h14"/></svg>',
};

const state = { q: "", paths: new Set(), sort: "featured", poster: "" };
let shown = [];

// ── URL ⇄ state ───────────────────────────────────────────
function readHash() {
  const raw = location.hash.slice(1);
  const h = new URLSearchParams(raw.includes("=") ? raw : raw ? `in=${raw}` : ""); // old links: #drone/link
  state.q = h.get("q") || "";
  state.paths = new Set((h.get("in") || "").split(",").filter((x) => PATHS.includes(x)));
  state.sort = SORTS[h.get("sort")] ? h.get("sort") : "featured";
  state.poster = byId.has(h.get("p")) ? h.get("p") : "";
}

function hashFor(s = state) {
  const parts = [];
  if (s.q) parts.push(["q", s.q]);
  if (s.paths.size) parts.push(["in", ordered(s.paths).join(",")]);
  if (s.sort !== "featured") parts.push(["sort", s.sort]);
  if (s.poster) parts.push(["p", s.poster]);
  return parts.map(([k, v]) => `${k}=${encodeURIComponent(v).replace(/%2F/g, "/").replace(/%2C/g, ",")}`).join("&");
}

function commit(mode = "push", data = null) {
  const hash = hashFor();
  if (hash === location.hash.slice(1)) return;
  const url = hash ? `#${hash}` : location.pathname + location.search;
  try {
    history[mode === "push" ? "pushState" : "replaceState"](data, "", url);
  } catch {
    location.hash = hash; // file:// in some browsers
  }
}

const ordered = (paths) => [...paths].sort((a, b) => PATHS.indexOf(a) - PATHS.indexOf(b));

// ── filtering ─────────────────────────────────────────────
const matchesQuery = (p) => state.q.toLowerCase().split(/\s+/).filter(Boolean).every((t) => p.text.includes(t));
const matchesPaths = (p) => !state.paths.size || state.paths.has(p.series) || state.paths.has(p.path);

function togglePath(path) {
  const [s, g] = path.split("/");
  const P = state.paths, groups = GROUPS[s];
  if (!g) {
    const full = P.has(s);
    groups.forEach((x) => P.delete(`${s}/${x}`));
    full ? P.delete(s) : P.add(s);
  } else if (P.has(s)) {
    P.delete(s);
    groups.filter((x) => x !== g).forEach((x) => P.add(`${s}/${x}`));
  } else if (P.has(path)) {
    P.delete(path);
  } else {
    P.add(path);
    if (groups.every((x) => P.has(`${s}/${x}`))) {
      groups.forEach((x) => P.delete(`${s}/${x}`));
      P.add(s);
    }
  }
}

// ── elements ──────────────────────────────────────────────
const app = $("#app"), grid = $("#grid"), tree = $("#tree"), q = $("#q"), sortSel = $("#sort");
const filters = $("#filters"), scrim = $("#scrim"), detail = $("#detail"), dImg = $("#d-img"), stage = $("#stage");
const expanded = new Set();

function setImg(img, p) {
  img.onerror = () => { if (!img.src.endsWith(p.png)) img.src = p.png; }; // thumbs not built yet
  img.onload = () => img.classList.add("in");
  img.src = p.thumb || p.png;
}

const cards = new Map(POSTERS.map((p) => {
  const el = document.createElement("article");
  el.className = "card";
  el.innerHTML = `
    <a class="card-link" href="#p=${esc(p.id)}">
      <div class="media"><img loading="lazy" decoding="async" alt="" width="576" height="720"></div>
      <div class="meta">
        <h3>${esc(p.name)}</h3>
        <p class="path">${esc(p.path)}</p>
        <p class="idea-line">${esc(p.idea)}</p>
      </div>
    </a>
    <div class="quick">
      <a href="${esc(p.svg)}" download title="Download SVG">${ICON.down}SVG</a>
      <a href="${esc(p.png)}" download title="Download PNG">${ICON.down}PNG</a>
    </div>`;
  setImg($("img", el), p);
  $(".card-link", el).addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault();
    openPoster(p.id);
  });
  return [p.id, el];
}));

function checkRow(path, name, twisty) {
  return `
    <div class="row" data-row="${path}">
      <label class="check"><input type="checkbox" data-path="${path}"><span class="name">${esc(name)}</span></label>
      <span class="n"></span>
      ${twisty ? `<button class="twisty" aria-expanded="false" aria-controls="t-${path}" aria-label="Show ${esc(name)} groups">${ICON.chevron}</button>` : '<span class="twisty-spacer"></span>'}
    </div>`;
}

tree.innerHTML = SERIES.map((s) => `
  <li>
    ${checkRow(s, label(s), GROUPS[s].length > 0)}
    ${GROUPS[s].length ? `<ul id="t-${s}" hidden>${GROUPS[s].map((g) => `<li>${checkRow(`${s}/${g}`, label(g), false)}</li>`).join("")}</ul>` : ""}
  </li>`).join("");

// ── render ────────────────────────────────────────────────
function render() {
  if (q.value !== state.q) q.value = state.q;
  sortSel.value = state.sort;

  const inQuery = POSTERS.filter(matchesQuery);
  shown = inQuery.filter(matchesPaths).sort(SORTS[state.sort]);

  // tree: checked / partial / counts within the current search
  for (const path of PATHS) {
    const [s, g] = path.split("/");
    const input = tree.querySelector(`input[data-path="${path}"]`);
    const n = inQuery.filter((p) => (g ? p.path === path : p.series === s)).length;
    const partial = !g && !state.paths.has(s) && GROUPS[s].some((x) => state.paths.has(`${s}/${x}`));
    input.checked = state.paths.has(path) || (!!g && state.paths.has(s));
    input.indeterminate = partial;
    const row = input.closest(".row");
    row.querySelector(".n").textContent = n;
    row.classList.toggle("zero", n === 0);
    if (!g && GROUPS[s].length) {
      if (partial) expanded.add(s);
      const open = expanded.has(s);
      row.querySelector(".twisty").setAttribute("aria-expanded", open);
      $(`#t-${s}`).hidden = !open;
    }
  }

  grid.replaceChildren(...shown.map((p) => cards.get(p.id)));
  $("#empty").hidden = shown.length > 0;

  // heading, breadcrumb, count
  const paths = ordered(state.paths);
  const one = paths.length === 1 ? paths[0] : "";
  const [s, g] = one.split("/");
  $("#title").textContent = !paths.length ? "All posters" : one ? label(g || s) : "Your selection";
  document.title = `${$("#title").textContent} · tech-art`;

  const crumbs = [`<li>${paths.length ? '<button data-crumb="">All posters</button>' : '<span aria-current="page">All posters</span>'}</li>`];
  if (one && g) crumbs.push(`<li><button data-crumb="${s}">${label(s)}</button></li>`, `<li><span aria-current="page">${label(g)}</span></li>`);
  else if (one) crumbs.push(`<li><span aria-current="page">${label(s)}</span></li>`);
  else if (paths.length) crumbs.push(`<li><span aria-current="page">${plural(paths.length, "collection")}</span></li>`);
  $("#crumbs").innerHTML = crumbs.join("");

  $("#count").innerHTML = `<b>${shown.length}</b> of ${plural(POSTERS.length, "poster")}` + (state.q ? ` matching “${esc(state.q)}”` : "");
  $("#total").textContent = `${POSTERS.length} posters · ${SERIES.length} collections`;

  // active chips
  const chips = paths.map((path) => `<button class="chip" data-remove="${path}" aria-label="Remove ${esc(pathLabel(path))}">${esc(pathLabel(path))}${ICON.x}</button>`);
  if (state.q) chips.push(`<button class="chip" data-remove-q aria-label="Clear search"><span>Search:</span>“${esc(state.q)}”${ICON.x}</button>`);
  if (chips.length) chips.push('<button class="link" data-action="clear">Clear all</button>');
  $("#active").innerHTML = chips.join("");

  const n = paths.length + (state.q ? 1 : 0);
  $("#badge").hidden = !n;
  $("#badge").textContent = n;
  $("#clear-side").hidden = !n;
  $("#apply").textContent = `Show ${plural(shown.length, "result")}`;

  state.poster ? showDetail() : hideDetail();
}

// ── detail view ───────────────────────────────────────────
let lastPoster = "", lastFocus = null;
const navList = () => (shown.some((p) => p.id === state.poster) ? shown : POSTERS);

function openPoster(id) {
  state.poster = id;
  commit("push", { detail: true });
  render();
}

function step(d) {
  const list = navList();
  const i = list.findIndex((p) => p.id === state.poster);
  state.poster = list[(i + d + list.length) % list.length].id;
  commit("replace", history.state);
  render();
}

function closeDetail() {
  if (history.state?.detail) return history.back(); // popstate re-renders
  state.poster = "";
  commit("replace");
  render();
}

function showDetail() {
  const p = byId.get(state.poster);
  const list = navList(), i = list.indexOf(p);
  const opening = detail.hidden;

  if (p.id !== lastPoster) {
    lastPoster = p.id;
    dImg.alt = `${p.name} — ${p.idea}`;
    setImg(dImg, p);
    const hi = new Image(); // swap the thumbnail for the full poster once it's in
    hi.onload = () => { if (lastPoster === p.id) dImg.src = p.png; };
    hi.src = p.png;
    [-1, 1].forEach((d) => (new Image().src = list[(i + d + list.length) % list.length].thumb));

    $("#d-title").textContent = p.name;
    $("#d-idea").textContent = p.idea;
    $("#d-series").textContent = label(p.series);
    $("#d-group").textContent = p.group ? label(p.group) : "—";
    $("#d-path").innerHTML = esc(p.svg.replace(/^\.\.\//, "")).replaceAll("/", "/<wbr>");
    $("#d-svg").href = p.svg;
    $("#d-png").href = p.png;
    $("#d-open").href = p.png;
    $("#d-crumbs").innerHTML = [
      '<li><button data-crumb="">All posters</button></li>',
      `<li><button data-crumb="${p.series}">${label(p.series)}</button></li>`,
      p.group ? `<li><button data-crumb="${p.path}">${label(p.group)}</button></li>` : "",
      `<li><span aria-current="page">${esc(p.name)}</span></li>`,
    ].join("");

    const related = POSTERS.filter((x) => x.path === p.path && x.id !== p.id).slice(0, 8);
    $("#related").hidden = !related.length;
    $("#related-title").textContent = `More in ${pathLabel(p.path)}`;
    $("#strip").replaceChildren(...related.map((x) => {
      const b = document.createElement("button");
      b.dataset.goto = x.id;
      b.innerHTML = `<img alt="" loading="lazy"><span>${esc(x.name)}</span>`;
      setImg($("img", b), x);
      return b;
    }));
    $(".panel", detail).scrollTop = 0;
    if (!opening) detail.scrollTop = 0;
  }
  $("#d-pos").textContent = `${i + 1} / ${list.length}`;

  if (opening) {
    lastFocus = document.activeElement;
    detail.hidden = false;
    app.inert = true;
    document.documentElement.classList.add("lock");
    detail.scrollTop = 0;
    detail.focus({ preventScroll: true });
  }
}

function hideDetail() {
  if (detail.hidden) return;
  if (document.fullscreenElement) document.exitFullscreen();
  detail.hidden = true;
  app.inert = false;
  document.documentElement.classList.remove("lock");
  const card = cards.get(lastPoster);
  (card?.isConnected ? $(".card-link", card) : lastFocus)?.focus({ preventScroll: false });
  lastPoster = "";
}

function fullscreen() {
  document.fullscreenElement ? document.exitFullscreen() : stage.requestFullscreen?.();
}

// ── filter drawer (narrow screens) ────────────────────────
function openFilters() {
  filters.classList.add("open");
  scrim.hidden = false;
  document.documentElement.classList.add("lock");
  $(".drawer-close", filters).focus();
}
function closeFilters() {
  if (!filters.classList.contains("open")) return;
  filters.classList.remove("open");
  scrim.hidden = true;
  document.documentElement.classList.remove("lock");
  $(".filters-btn").focus();
}
matchMedia("(min-width: 901px)").addEventListener("change", (e) => e.matches && closeFilters());

// ── misc ──────────────────────────────────────────────────
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 1800);
}
async function copy(text, what) {
  try {
    await navigator.clipboard.writeText(text);
    toast(`${what} copied`);
  } catch {
    toast(`Couldn’t copy — ${text}`);
  }
}

function setDensity(d) {
  grid.dataset.density = d;
  document.querySelectorAll("[data-density]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.density === d));
  try { localStorage.setItem("tech-art:density", d); } catch {}
}
let savedDensity = "comfortable";
try { savedDensity = localStorage.getItem("tech-art:density") || savedDensity; } catch {}
setDensity(savedDensity);

// ── events ────────────────────────────────────────────────
const actions = {
  reset: () => { state.paths.clear(); state.q = ""; },
  clear: () => { state.paths.clear(); state.q = ""; },
  "open-filters": openFilters,
  "close-filters": closeFilters,
  "close-detail": closeDetail,
  prev: () => step(-1),
  next: () => step(1),
  fullscreen,
  "copy-link": () => copy(location.href, "Link"),
  "copy-path": () => copy($("#d-path").textContent, "Path"),
};

document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-action],[data-crumb],[data-remove],[data-remove-q],[data-goto],[data-density],.twisty");
  if (!t) return;
  if (t.dataset.action) {
    e.preventDefault();
    const filterChange = ["reset", "clear"].includes(t.dataset.action);
    actions[t.dataset.action]();
    if (filterChange) { commit(); render(); }
  } else if (t.dataset.crumb !== undefined) {
    state.paths = new Set(t.dataset.crumb ? [t.dataset.crumb] : []);
    if (state.poster) { state.poster = ""; commit("replace"); } else commit();
    render();
    if (detail.hidden) window.scrollTo({ top: 0 });
  } else if (t.dataset.remove) {
    state.paths.delete(t.dataset.remove);
    commit(); render();
  } else if (t.dataset.removeQ !== undefined) {
    state.q = "";
    commit(); render();
  } else if (t.dataset.goto) {
    state.poster = t.dataset.goto;
    commit("replace", history.state);
    render();
  } else if (t.dataset.density) {
    setDensity(t.dataset.density);
  } else if (t.classList.contains("twisty")) {
    const s = t.closest(".row").dataset.row;
    expanded.has(s) ? expanded.delete(s) : expanded.add(s);
    render();
  }
});

tree.addEventListener("change", (e) => {
  const path = e.target.dataset.path;
  if (!path) return;
  togglePath(path);
  if (!path.includes("/") && GROUPS[path].length && state.paths.has(path)) expanded.add(path);
  commit(); render();
});

q.addEventListener("input", () => {
  state.q = q.value.trim() ? q.value : "";
  commit("replace"); render();
});
q.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { q.value ? (q.value = "", q.dispatchEvent(new Event("input"))) : q.blur(); }
  if (e.key === "Enter") { q.blur(); grid.scrollIntoView({ block: "start", behavior: "smooth" }); }
});
sortSel.addEventListener("change", () => { state.sort = sortSel.value; commit("replace"); render(); });

dImg.addEventListener("click", () => (document.fullscreenElement ? step(1) : fullscreen()));

document.addEventListener("keydown", (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName);
  if (!detail.hidden) {
    if (e.key === "Escape" && !document.fullscreenElement) closeDetail();
    else if (e.key === "ArrowRight") step(1);
    else if (e.key === "ArrowLeft") step(-1);
    else if (e.key === "f") fullscreen();
    else return;
    e.preventDefault();
  } else if (filters.classList.contains("open") && e.key === "Escape") {
    closeFilters();
  } else if (e.key === "/" && !typing) {
    e.preventDefault();
    q.focus();
    q.select();
  }
});

let touchX = null; // swipe between posters on phones
stage.addEventListener("touchstart", (e) => (touchX = e.touches[0].clientX), { passive: true });
stage.addEventListener("touchend", (e) => {
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1);
});

const sync = () => { readHash(); render(); };
window.addEventListener("popstate", sync);
window.addEventListener("hashchange", sync);
sync();
