"use strict";

/* Read-only, destination-aware routing canvas. No routing mutation or demo data. */
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const PAGE = "routing-flow";
  const POLL_MS = 5000;
  const OUTPUT_LOGOS = { teams: "/ui/icons/routing-teams.svg", slack: "/ui/icons/routing-slack.svg" };
  const ICONS = {
    flow: "M4 4h5v5H4z M15 15h5v5h-5z M6.5 9v8.5H15 M17.5 15V6.5H9",
    filter: "M3 4h18l-7 8v7l-4 2v-9z",
    pulse: "M2 12h5l3-8 4 16 3-8h5",
    clock: "M12 8v5l3 2 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
    fit: "M8 3H3v5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M8 8h8v8H8z",
  };
  let data = null, signature = "", timer = null, controller = null;
  let generation = 0, paused = false, range = "15m", zoom = 1, busy = false;
  let owner = null, selected = null, seen = new Set(), allHistory = false;
  let pulseFrame = null, pulses = [], edgePaths = new Map(), resizeFrame = null;

  function el(tag, cls = "", text = "") {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== "") n.textContent = String(text);
    return n;
  }
  function svg(tag, attrs = {}) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => n.setAttribute(key, String(value)));
    return n;
  }
  function icon(name) {
    const n = svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", class: "rf-icon" });
    n.append(svg("path", { d: ICONS[name] || ICONS.flow, fill: "none", stroke: "currentColor", "stroke-width": 1.6, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    return n;
  }
  function button(text, action, cls = "rf-control") {
    const n = el("button", cls, text);
    n.type = "button";
    n.addEventListener("click", action);
    return n;
  }
  function dot(kind = "") { return el("span", `rf-dot ${kind}`); }
  function metricText(value) { return value === null || value === undefined ? "—" : Number(value).toLocaleString(); }
  function active() { return Boolean(state.user && state.currentView === PAGE && !document.hidden && !paused); }
  function linkKey(route, destination) { return JSON.stringify([route, destination]); }
  function destinationLogo(destination) {
    const path = OUTPUT_LOGOS[destination.output_type];
    if (!path) return outputIcon(destination.output_type);
    const image = el("img", "rf-brand-icon");
    image.src = path;
    image.alt = "";
    return image;
  }

  VIEW_TITLES[PAGE] = "Routing Flow";
  const nav = button("", () => {}, "nav-item");
  nav.dataset.view = PAGE;
  nav.append(icon("flow"), el("span", "", "Routing Flow"));
  document.querySelector('#primary-nav [data-view="dashboard"]').after(nav);
  const section = el("section", "view rf-page");
  section.id = "view-routing-flow";
  section.dataset.page = PAGE;
  section.hidden = true;
  section.innerHTML = `
    <div class="rf-toolbar">
      <div><h2>Routing Flow <span class="rf-badge">Read-only</span></h2><p>Automatically mapped from existing configuration</p></div>
      <div class="rf-controls"><span id="rf-live" class="rf-live" role="status">Loading overview…</span><button id="rf-pause" class="rf-control" type="button">Pause live</button><label class="rf-range"><span class="sr-only">History window</span><select id="rf-range"><option value="15m">Last 15 minutes</option><option value="1h">Last hour</option><option value="1d">Last 24 hours</option></select></label></div>
    </div>
    <p class="rf-scope">Delivery counts use the latest attempt per delivery. One source event can reach multiple destinations.</p>
    <div id="rf-error" class="rf-error" role="alert" hidden></div>
    <div id="rf-metrics" class="rf-metrics"></div>
    <div class="rf-canvas">
      <div id="rf-empty" class="rf-empty" hidden></div>
      <div id="rf-graph" class="rf-graph"><svg id="rf-edges" class="rf-edges" aria-hidden="true"></svg></div>
      <div class="rf-canvas-footer"><div class="rf-controls"><div class="rf-zoom"><button id="rf-minus" type="button" aria-label="Zoom out">−</button><span id="rf-zoom-value">100%</span><button id="rf-plus" type="button" aria-label="Zoom in">+</button></div><button id="rf-fit" class="rf-control" type="button">Fit to view</button></div><small id="rf-counts"></small><svg id="rf-minimap" class="rf-minimap" viewBox="0 0 130 46" role="img" aria-label="Routing overview minimap"></svg></div>
    </div>
    <div class="rf-history"><div class="rf-history-heading"><h3>Recent Deliveries</h3><button id="rf-history-toggle" class="rf-control" type="button">View all</button></div><div class="rf-table-scroll"><table><thead><tr><th>Time</th><th>Integration</th><th>Destination</th><th>Status</th><th>Attempt</th></tr></thead><tbody id="rf-history-body"></tbody></table></div><p id="rf-history-empty" class="rf-empty" hidden>No deliveries recorded in this window.</p></div>
    <p class="rf-footnote">Refreshes every 5 seconds while visible. Source-event and filtered-out totals are not recorded by the current pipeline.</p>
  `;
  byId("view-dashboard").after(section);
  const $ = id => section.querySelector(`#${id}`);
  $("rf-fit").prepend(icon("fit"));
  const dialog = el("dialog", "rf-dialog");
  dialog.setAttribute("aria-labelledby", "rf-details-title");
  const dialogTop = el("div", "rf-dialog-top"), dialogTitle = el("h2");
  dialogTitle.id = "rf-details-title";
  const dialogBody = el("div", "rf-dialog-body");
  const close = button("×", () => dialog.close());
  close.setAttribute("aria-label", "Close routing details");
  dialogTop.append(dialogTitle, close);
  dialog.append(dialogTop, dialogBody);
  document.body.append(dialog);
  dialog.addEventListener("close", () => { selected = null; drawEdges(); });

  function detailRow(label, value) {
    const row = el("div", "rf-detail-row");
    row.append(el("span", "", label), el("strong", "", value));
    return row;
  }
  function policyLines(link) {
    const entries = [];
    for (const p of link.policies) {
      const prefix = link.fallback ? `${p.name}: ` : "";
      if (!p.configured) { if (!link.fallback) entries.push("All notifications"); continue; }
      if (!p.enabled) { entries.push(`${prefix}Filter disabled · all notifications`); continue; }
      const clauses = p.legacy_clauses.length ? p.legacy_clauses : [p.rules];
      const summary = clauses.map(c => Object.entries(c).map(([key, values]) => `${p.labels[key] || key.replaceAll("_", " ")}: ${values.join(", ")}`).join(" AND ")).join(" OR ");
      entries.push(prefix + summary);
    }
    return entries.length ? entries : ["All notifications"];
  }
  function activePolicies(link) {
    return (link.policies || []).filter(p => !p.restricted && p.configured && p.enabled);
  }
  function activePolicyLines(link) {
    const policies = activePolicies(link);
    return policies.length ? policyLines({ ...link, policies }) : [];
  }
  function showDetails(kind, identity) {
    if (!data) return;
    selected = { kind, identity };
    dialogBody.replaceChildren();
    if (kind === "route") {
      const route = data.routes.find(r => r.id === identity);
      dialogTitle.textContent = route.integration_name;
      dialogBody.append(detailRow("Route", route.name), detailRow("Input", route.input_type || "Any input"), detailRow("State", route.enabled ? "Enabled" : "Disabled"));
      const targets = data.links.filter(l => l.route_id === identity);
      for (const link of targets) {
        const d = data.destinations.find(d => d.id === link.destination_id);
        dialogBody.append(detailRow(d.name, policyLines(link).join("; ")));
      }
      if (!targets.length) dialogBody.append(detailRow("Assignment", "No visible destination assigned"));
    } else if (kind === "destination") {
      const d = data.destinations.find(d => d.id === identity);
      dialogTitle.textContent = d.name;
      dialogBody.append(detailRow("Platform", OUTPUT_NAMES[d.output_type] || d.output_type), detailRow("Channel", d.channel || "Not labelled"), detailRow("State", d.enabled ? "Enabled" : "Disabled"));
      data.links.filter(l => l.destination_id === identity).forEach(l => {
        const r = data.routes.find(r => r.id === l.route_id);
        dialogBody.append(detailRow(r.name, policyLines(l).join("; ")));
      });
      ["delivered", "pending", "failed"].forEach(k => dialogBody.append(detailRow(k === "pending" ? "Retry scheduled" : capitalize(k), metricText(d.metrics[k]))));
    } else {
      const link = data.links.find(l => linkKey(l.route_id, l.destination_id) === identity);
      const r = data.routes.find(r => r.id === link.route_id), d = data.destinations.find(d => d.id === link.destination_id);
      dialogTitle.textContent = `${r.integration_name} → ${d.name}`;
      dialogBody.append(detailRow("Route", r.name), detailRow("Filtering scope", "This destination and integration"), detailRow("Connection", link.enabled ? "Enabled" : "Disabled"));
      activePolicyLines(link).forEach((line, i) => dialogBody.append(detailRow(`Filter ${i + 1}`, line)));
      if (link.fallback) dialogBody.append(detailRow("Fallback", "Only when no dedicated route matches"));
    }
    dialogBody.append(el("p", "rf-detail-note", "Read-only snapshot. Configuration remains in Destinations and Filtering."));
    drawEdges();
    if (!dialog.open) dialog.showModal();
  }

  function createNode(kind, identity, row, span, label) {
    const node = button("", () => showDetails(kind, identity), `rf-node rf-${kind}`);
    node.dataset.kind = kind;
    node.dataset.identity = identity;
    node.dataset.focusKey = `${kind}:${identity}`;
    node.setAttribute("aria-label", label);
    node.style.gridColumn = String({ route: 1, filter: 2, destination: 3 }[kind]);
    node.style.gridRow = `${row} / span ${span}`;
    $("rf-graph").append(node);
    return node;
  }
  function renderMetrics() {
    $("rf-metrics").replaceChildren();
    const spec = [["received", "Received", "Source events", "pulse"], ["delivered", "Delivered", "Destination deliveries", "green"], ["filtered", "Filtered out", "Events not routed", "filter"], ["pending", "Retry scheduled", "Latest recorded status", "amber"], ["failed", "Failed", "Terminal failures", "red"]];
    for (const [key, label, note, symbol] of spec) {
      const box = el("div", "rf-metric"), content = el("div");
      box.append(["pulse", "filter"].includes(symbol) ? icon(symbol) : dot(symbol));
      content.append(el("strong", "", metricText(data.metrics[key])), el("span", "", label), el("small", "", data.metrics[key] === null ? "Not recorded" : note));
      box.append(content);
      $("rf-metrics").append(box);
    }
  }
  function renderGraph() {
    const graph = $("rf-graph");
    graph.querySelectorAll(":scope > :not(svg)").forEach(n => n.remove());
    const rows = Math.max(data.routes.reduce((n, r) => n + Math.max(1, data.links.filter(l => l.route_id === r.id).length), 0), data.destinations.length, 1);
    [["Integration routes", "Event sources with configured routes"], ["Active filters", "Per destination and integration"], ["Destinations", "Alert channels receiving events"]].forEach(([a, b]) => {
      const head = el("div", "rf-column-heading", a); head.append(el("small", "", b)); graph.append(head);
    });
    let row = 2;
    for (const r of data.routes) {
      const links = data.links.filter(l => l.route_id === r.id), span = Math.max(links.length, 1);
      const node = createNode("route", r.id, row, span, `${r.integration_name}: ${r.name}. View details`);
      node.classList.toggle("rf-disabled", !r.enabled);
      node.append(sourceIcon(r.source));
      const text = el("div", "rf-node-copy");
      text.append(el("strong", "", r.integration_name), el("small", "", r.name), el("span", r.enabled ? "rf-green" : "rf-muted", `${r.enabled ? "Enabled" : "Disabled"} · ${r.input_type || "Any input"}`));
      node.append(text);
      if (!links.length) {
        const blank = el("div", "rf-unassigned", "No visible destination assigned");
        blank.style.gridRow = String(row); blank.style.gridColumn = "2"; graph.append(blank);
      }
      for (const [index, link] of links.entries()) {
        const lines = activePolicyLines(link);
        if (!lines.length) continue;
        const key = linkKey(r.id, link.destination_id), filter = createNode("filter", key, row + index, 1, `${r.integration_name} filter for ${data.destinations.find(d => d.id === link.destination_id).name}`);
        filter.classList.toggle("rf-disabled", !link.enabled);
        const badge = el("span", "rf-funnel"); badge.append(icon("filter"));
        const copy = el("div", "rf-node-copy");
        copy.append(el("strong", "", lines[0]), el("small", "", lines.length > 1 ? `+${lines.length - 1} policies · inspect details` : data.destinations.find(d => d.id === link.destination_id).name));
        filter.append(badge, copy);
      }
      row += span;
    }
    data.destinations.forEach((d, i) => {
      const start = Math.floor(i * rows / data.destinations.length), end = Math.floor((i + 1) * rows / data.destinations.length);
      const node = createNode("destination", d.id, start + 2, Math.max(1, end - start), `${d.name}. View destination details`);
      node.classList.toggle("rf-disabled", !d.enabled);
      const top = el("div", "rf-destination-top"), copy = el("div", "rf-node-copy");
      copy.append(el("strong", "", d.name), el("small", "", d.channel || OUTPUT_NAMES[d.output_type] || d.output_type));
      top.append(destinationLogo(d), copy);
      const counts = el("div", "rf-destination-metrics");
      [["delivered", "delivered", "green"], ["pending", "retry scheduled", "amber"], ["failed", "failed", "red"]].forEach(([k, label, color]) => {
        const n = el("span", `rf-${color}`); n.append(dot(color), document.createTextNode(`${metricText(d.metrics[k])} ${label}`)); counts.append(n);
      });
      node.append(top, counts, el("small", "rf-last", `${d.enabled ? "Enabled" : "Disabled"} · ${d.route_ids.length} assigned routes`));
    });
    $("rf-empty").hidden = Boolean(data.routes.length || data.destinations.length);
    $("rf-empty").textContent = "No visible routes or destinations yet. This overview reflects configuration from Destinations and Filtering.";
    graph.hidden = !(data.routes.length || data.destinations.length);
    $("rf-counts").textContent = `${data.routes.length} routes · ${data.links.length} connections · ${data.destinations.length} destinations`;
    drawEdges();
  }
  function renderHistory() {
    const body = $("rf-history-body"); body.replaceChildren();
    const items = allHistory ? data.history : data.history.slice(0, 4);
    for (const item of items) {
      const row = el("tr"), time = el("td", "", formatTime(item.completed_at || item.created_at));
      const source = el("td"), sourceWrap = el("span", "rf-history-identity"); sourceWrap.append(sourceIcon(item.source), document.createTextNode(friendlyName(item.source))); source.append(sourceWrap);
      const target = el("td"), dest = data.destinations.find(d => d.id === item.destination_id);
      if (dest) { const wrap = el("span", "rf-history-identity"); wrap.append(destinationLogo(dest), document.createTextNode(dest.name)); target.append(wrap); }
      else target.textContent = "Removed or unavailable";
      const label = { delivered: "Delivered", retry_scheduled: "Retry scheduled", failed: "Failed" }[item.outcome] || item.outcome;
      const status = el("td", {delivered:"rf-green", retry_scheduled:"rf-amber", failed:"rf-red"}[item.outcome] || "", label);
      row.append(time, source, target, status, el("td", "", item.attempt_number)); body.append(row);
    }
    $("rf-history-empty").hidden = Boolean(items.length);
    $("rf-history-toggle").textContent = allHistory ? "Show less" : `View all (${data.history.length})`;
    $("rf-history-toggle").disabled = data.history.length <= 4;
  }
  function render() {
    const focusKey = document.activeElement?.dataset?.focusKey;
    renderMetrics(); renderGraph(); renderHistory();
    if (focusKey) Array.from(section.querySelectorAll("[data-focus-key]")).find(n => n.dataset.focusKey === focusKey)?.focus({ preventScroll: true });
    if (dialog.open && selected) {
      const found = selected.kind === "route" ? data.routes.some(r => r.id === selected.identity) : selected.kind === "destination" ? data.destinations.some(d => d.id === selected.identity) : data.links.some(l => linkKey(l.route_id,l.destination_id) === selected.identity && activePolicies(l).length);
      if (found) showDetails(selected.kind, selected.identity); else dialog.close();
    }
  }

  function nodeFor(kind, id) { return Array.from($("rf-graph").querySelectorAll(`.rf-${kind}`)).find(n => n.dataset.identity === id); }
  function relevant(link) {
    return !selected || (selected.kind === "route" && selected.identity === link.route_id) || (selected.kind === "destination" && selected.identity === link.destination_id) || (selected.kind === "filter" && selected.identity === linkKey(link.route_id, link.destination_id));
  }
  function drawEdges() {
    stopPulses();
    if (!data || section.hidden) return;
    const graph = $("rf-graph"), edges = $("rf-edges"); edges.replaceChildren(); edgePaths = new Map();
    if (graph.hidden || graph.clientWidth === 0 || window.innerWidth <= 640) return;
    edges.setAttribute("viewBox", `0 0 ${graph.clientWidth} ${graph.clientHeight}`);
    const defs = svg("defs"), marker = svg("marker", { id:"rf-arrow", viewBox:"0 0 8 8", refX:7, refY:4, markerWidth:7, markerHeight:7, orient:"auto" });
    marker.append(svg("path", {d:"M0 0 L8 4 L0 8 Z", fill:"currentColor"})); defs.append(marker); edges.append(defs);
    for (const link of data.links) {
      const key = linkKey(link.route_id, link.destination_id), route = nodeFor("route", link.route_id), filter = nodeFor("filter", key), destination = nodeFor("destination", link.destination_id);
      if (!route || !destination) continue;
      const paths = [];
      const pairs = filter ? [[route,filter],[filter,destination]] : [[route,destination]];
      for (const [a, b] of pairs) {
        const x = a.offsetLeft+a.offsetWidth, y = a.offsetTop+a.offsetHeight/2, xx=b.offsetLeft, yy=b.offsetTop+b.offsetHeight/2, bend=(xx-x)*.52;
        const path = svg("path", {d:`M${x} ${y} C${x+bend} ${y} ${xx-bend} ${yy} ${xx} ${yy}`, class:`rf-edge${!link.enabled?" rf-off":""}${relevant(link)?"":" rf-dim"}`, "marker-end":"url(#rf-arrow)"});
        edges.append(path); paths.push(path);
      }
      edgePaths.set(key, paths);
    }
    const mini = $("rf-minimap"); mini.replaceChildren();
    for (const paths of edgePaths.values()) for (const p of paths) {
      const copy = p.cloneNode(); copy.removeAttribute("marker-end"); copy.setAttribute("transform",`scale(${130/graph.clientWidth} ${46/graph.clientHeight})`); mini.append(copy);
    }
    graph.querySelectorAll(".rf-node").forEach(n=>mini.append(svg("rect", {x:n.offsetLeft/graph.clientWidth*130,y:n.offsetTop/graph.clientHeight*46,width:n.offsetWidth/graph.clientWidth*130,height:Math.max(2,n.offsetHeight/graph.clientHeight*46),rx:1})));
  }
  function stopPulses() {
    if (pulseFrame !== null) cancelAnimationFrame(pulseFrame);
    pulseFrame = null; pulses.forEach(p=>p.dot.remove()); pulses=[];
  }
  function animateAttempts(items) {
    if (!active() || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const started = performance.now();
    for (const item of items.slice(0,12)) {
      const paths = edgePaths.get(linkKey(item.route_id,item.destination_id));
      if (!paths?.length) continue;
      const circle = svg("circle", {r:3.2,class:`rf-particle ${item.outcome==='failed'?'rf-failed-particle':''}`});
      $("rf-edges").append(circle); pulses.push({dot:circle,paths,started});
    }
    function frame(now) {
      if (!active()) { stopPulses(); return; }
      pulses = pulses.filter(p=>{const elapsed=(now-p.started)/1600;if(elapsed>=1){p.dot.remove();return false;}const scaled=elapsed*p.paths.length,index=Math.min(p.paths.length-1,Math.floor(scaled)),progress=scaled-index,path=p.paths[index];const pt=path.getPointAtLength(path.getTotalLength()*progress);p.dot.setAttribute("cx",pt.x);p.dot.setAttribute("cy",pt.y);return true;});
      pulseFrame = pulses.length ? requestAnimationFrame(frame) : null;
    }
    if (pulses.length && pulseFrame===null) pulseFrame=requestAnimationFrame(frame);
  }

  function invalidate() {
    generation++; clearTimeout(timer); timer=null;
    if (controller) controller.abort(); controller=null;
    stopPulses();
  }
  function clearPrivateData() {
    data=null; signature=""; owner=null; seen=new Set();
    $("rf-metrics").replaceChildren(); $("rf-history-body").replaceChildren();
    $("rf-graph").querySelectorAll(":scope > :not(svg)").forEach(n=>n.remove());
    $("rf-edges").replaceChildren(); $("rf-minimap").replaceChildren();
    $("rf-counts").textContent=""; $("rf-error").hidden=true;
    if(dialog.open) dialog.close();
  }
  async function refresh() {
    if (!active() || busy) return;
    if(owner!==state.user.id){clearPrivateData();owner=state.user.id;}
    busy=true;
    const token=generation, userId=state.user.id, requestRange=range;
    const abort=new AbortController(); controller=abort;
    const timeout=setTimeout(()=>abort.abort(),20000);
    try {
      const response=await fetch(`${API}/routing-flow/${range}`,{method:"GET",credentials:"same-origin",cache:"no-store",headers:{Accept:"application/json"},signal:abort.signal});
      if(response.status===401){expireSession();return;}
      if(!response.ok) throw new Error(`Overview request failed (${response.status}).`);
      const next=await response.json();
      if(token!==generation || !active() || state.user?.id!==userId || requestRange!==range) return;
      if(!Array.isArray(next.routes)||!Array.isArray(next.destinations)||!Array.isArray(next.links)||!Array.isArray(next.history)||!next.metrics) throw new Error("The overview response is invalid.");
      const fresh=data?next.history.filter(h=>!seen.has(h.id)):[];
      seen=new Set(next.history.map(h=>h.id));
      const nextSignature=JSON.stringify({...next,generated_at:0,since:0});data=next;
      if(nextSignature!==signature){signature=nextSignature;render();}
      $("rf-live").textContent=`● Live · updated ${formatTime(next.generated_at)}`;
      $("rf-live").classList.remove("rf-stale");
      $("rf-error").hidden=!next.errors?.length;
      $("rf-error").textContent=(next.errors||[]).map(e=>`${e.component}: ${e.message}`).join(" · ");
      animateAttempts(fresh);
    } catch(error) {
      if(token!==generation || !active()) return;
      $("rf-live").textContent="● Connection interrupted";$("rf-live").classList.add("rf-stale");
      $("rf-error").hidden=false;
      $("rf-error").textContent=`${error.name==='AbortError'?'Overview request timed out.':error.message} ${data?'Showing the last successful snapshot.':'No overview loaded.'} Retrying automatically.`;
    } finally {
      clearTimeout(timeout);if(controller===abort)controller=null;busy=false;
      if(active()) timer=setTimeout(refresh,token===generation?POLL_MS:0);
    }
  }
  function sync() {
    invalidate();
    if(!state.user){clearPrivateData();return;}
    if(!active())return;
    requestAnimationFrame(drawEdges);refresh();
  }
  const previousNavigate=navigate;
  navigate=function routingFlowNavigate(view,historyMode="push") {
    // The regional catalog caches Dashboard on the shared title element. A new
    // view outside that catalog must not inherit its previous translation key.
    if(view===PAGE) delete byId("page-title").dataset.i18nSource;
    const result=previousNavigate(view,historyMode);sync();return result;
  };
  const previousExpire=expireSession;
  expireSession=function routingFlowExpireSession(){invalidate();clearPrivateData();return previousExpire();};
  document.addEventListener("visibilitychange",sync);
  $("rf-pause").addEventListener("click",()=>{paused=!paused;$("rf-pause").textContent=paused?"Resume live":"Pause live";$("rf-live").textContent=paused?"Ⅱ Paused · snapshot frozen":"Reconnecting…";sync();});
  $("rf-range").addEventListener("change",()=>{range=$("rf-range").value;signature="";invalidate();clearPrivateData();$("rf-live").textContent=paused?"Paused · resume to load this range":"Loading window…";refresh();});
  function setZoom(value){zoom=Math.min(1,Math.max(.7,Math.round(value*10)/10));$("rf-graph").style.transform=`scale(${zoom})`;$("rf-zoom-value").textContent=`${Math.round(zoom*100)}%`;$("rf-plus").disabled=zoom===1;$("rf-minus").disabled=zoom===.7;}
  $("rf-minus").addEventListener("click",()=>setZoom(zoom-.1));$("rf-plus").addEventListener("click",()=>setZoom(zoom+.1));$("rf-fit").addEventListener("click",()=>setZoom(1));
  $("rf-history-toggle").addEventListener("click",()=>{allHistory=!allHistory;if(data)renderHistory();});
  new ResizeObserver(()=>{if(resizeFrame!==null)cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=null;drawEdges();});}).observe($("rf-graph"));
  setZoom(1);sync();
})();
