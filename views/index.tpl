<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RTL-433 Sensor Bridge</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg         : #0d0f12;
      --bg-surface : #141720;
      --bg-card    : #181c25;
      --bg-followed: #0d1a20;
      --border     : #252a35;
      --border-dim : #1e222d;
      --accent     : #00c8a0;
      --accent-dim : #007a62;
      --warn       : #f59e0b;
      --danger     : #ef4444;
      --text       : #c8cdd8;
      --text-dim   : #5a6070;
      --text-bright: #edf0f5;
      --key        : #7ab8d4;
      --val        : #c8cdd8;
      --val-num    : #e8a87c;
      --val-bool-t : #00c8a0;
      --val-bool-f : #5a6070;
      --mono       : "IBM Plex Mono", monospace;
      --sans       : "IBM Plex Sans", sans-serif;
      --radius     : 4px;
    }

    body {
      background : var(--bg);
      color      : var(--text);
      font-family: var(--mono);
      font-size  : 13px;
      min-height : 100vh;
      line-height: 1.6;
    }

    /* ── Header ── */
    header {
      background   : var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding      : 16px 24px;
      position     : sticky;
      top          : 0;
      z-index      : 10;
    }

    .header-inner {
      display        : flex;
      align-items    : center;
      justify-content: space-between;
      max-width      : 900px;
      margin         : 0 auto;
    }

    .header-title {
      display    : flex;
      align-items: center;
      gap        : 12px;
    }

    .header-icon { font-size: 24px; color: var(--accent); }

    h1 {
      font-size     : 15px;
      font-weight   : 600;
      color         : var(--text-bright);
      letter-spacing: 0.03em;
    }

    .header-sub {
      font-size     : 10px;
      color         : var(--text-dim);
      letter-spacing: 0.06em;
      margin-top    : 2px;
    }

    .header-stats { display: flex; gap: 24px; }

    .stat { display: flex; flex-direction: column; align-items: flex-end; }

    .stat-val {
      font-size  : 20px;
      font-weight: 600;
      color      : var(--text-bright);
      line-height: 1;
    }

    .stat-label {
      font-size     : 9px;
      color         : var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-top    : 2px;
    }

    .stat-warn .stat-val { color: var(--warn); }

    /* ── Main ── */
    main {
      max-width: 900px;
      margin   : 0 auto;
      padding  : 24px;
    }

    /* ── Sensor card ── */
    .sensor-card {
      background   : var(--bg-card);
      border       : 1px solid var(--border);
      border-radius: var(--radius);
      margin-bottom: 16px;
      overflow     : hidden;
    }

    .sensor-card.followed {
      border-left: 3px solid var(--accent-dim);
      background : var(--bg-followed);
    }

    .sensor-card.battery-low {
      border-left: 3px solid var(--danger);
    }

    /* ── Card header ── */
    .card-header {
      display        : flex;
      align-items    : center;
      justify-content: space-between;
      padding        : 10px 16px;
      background     : rgba(255,255,255,0.02);
      border-bottom  : 1px solid var(--border-dim);
      gap            : 12px;
    }

    .sensor-id {
      color      : var(--accent);
      font-weight: 600;
      font-size  : 14px;
      flex-shrink: 0;
    }

    .sensor-id::after { content: ":"; color: var(--text-dim); }

    /* Name editing */
    .name-wrap {
      display    : flex;
      align-items: center;
      gap        : 6px;
      flex       : 1;
    }

    .name-display {
      color      : var(--text-bright);
      font-weight: 500;
      font-size  : 13px;
    }

    .name-input {
      background   : #0a0c10;
      border       : 1px solid var(--accent-dim);
      color        : var(--text-bright);
      font-family  : var(--mono);
      font-size    : 13px;
      padding      : 2px 8px;
      border-radius: 3px;
      outline      : none;
      width        : 220px;
      display      : none;
    }

    .name-input:focus { border-color: var(--accent); }

    .btn-edit, .btn-save {
      background   : transparent;
      border       : none;
      cursor       : pointer;
      color        : var(--text-dim);
      font-size    : 13px;
      padding      : 2px 5px;
      border-radius: 3px;
      transition   : color 0.15s;
    }

    .btn-edit:hover { color: var(--accent); }
    .btn-save       { color: var(--accent); display: none; }
    .btn-save:hover { color: #00ffcc; }

    /* Follow toggle */
    .follow-wrap {
      display    : flex;
      align-items: center;
      gap        : 8px;
      flex-shrink: 0;
    }

    .follow-label {
      font-size     : 10px;
      color         : var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .toggle {
      display : inline-block;
      position: relative;
      width   : 36px;
      height  : 18px;
      cursor  : pointer;
    }

    .toggle input { opacity: 0; width: 0; height: 0; position: absolute; }

    .slider {
      position     : absolute;
      inset        : 0;
      background   : #1a1e28;
      border       : 1px solid var(--border);
      border-radius: 18px;
      transition   : 0.2s;
    }

    .slider::before {
      content      : "";
      position     : absolute;
      left         : 2px;
      top          : 50%;
      transform    : translateY(-50%);
      width        : 12px;
      height       : 12px;
      background   : var(--text-dim);
      border-radius: 50%;
      transition   : 0.2s;
    }

    .toggle input:checked + .slider {
      background  : #0a1f18;
      border-color: var(--accent-dim);
    }

    .toggle input:checked + .slider::before {
      background: var(--accent);
      left      : 20px;
      box-shadow: 0 0 5px var(--accent);
    }

    /* ── YAML body ── */
    .yaml-body {
      padding: 8px 16px;
    }

    .yaml-line {
      display    : flex;
      gap        : 0;
      line-height: 1.3;
      white-space: nowrap;
    }

    .yaml-indent { color: transparent; user-select: none; }

    .yaml-key {
      color      : var(--key);
      flex-shrink: 0;
    }

    .yaml-colon {
      color      : var(--text-dim);
      margin-right: 1ch;
      flex-shrink: 0;
    }

    .yaml-val-str  { color: var(--val); }
    .yaml-val-num  { color: var(--val-num); }
    .yaml-val-true { color: var(--val-bool-t); font-weight: 500; }
    .yaml-val-false{ color: var(--val-bool-f); }
    .yaml-val-null { color: var(--text-dim); font-style: italic; }

    .badge-low {
      display      : inline-block;
      font-size    : 9px;
      font-weight  : 600;
      padding      : 1px 6px;
      border-radius: 3px;
      background   : #1f0a0a;
      color        : var(--danger);
      border       : 1px solid #7a2020;
      margin-left  : 8px;
      vertical-align: middle;
      animation    : pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.5; }
    }

    /* ── Empty state ── */
    .empty-state {
      text-align: center;
      padding   : 80px 20px;
      color     : var(--text-dim);
    }

    /* ── Toast ── */
    .toast {
      position      : fixed;
      bottom        : 24px;
      left          : 50%;
      transform     : translateX(-50%) translateY(20px);
      background    : var(--bg-surface);
      border        : 1px solid var(--accent-dim);
      color         : var(--text-bright);
      font-size     : 12px;
      padding       : 8px 20px;
      border-radius : var(--radius);
      opacity       : 0;
      pointer-events: none;
      transition    : opacity 0.25s, transform 0.25s;
      white-space   : nowrap;
      z-index       : 100;
    }

    .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    .toast.toast-error { border-color: var(--danger); color: var(--danger); }

    @media (max-width: 600px) {
      main { padding: 12px; }
      .yaml-body { padding: 8px 12px; }
    }
  </style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="header-title">
      <span class="header-icon">◈</span>
      <div>
        <h1>RTL-433 Sensor Bridge</h1>
        <p class="header-sub">433 MHz device registry &amp; configuration</p>
      </div>
    </div>
    <div class="header-stats">
      <div class="stat">
        <span class="stat-val">{{len(sensors)}}</span>
        <span class="stat-label">devices</span>
      </div>
      <div class="stat">
        <span class="stat-val">{{sum(1 for s in sensors if s['follow'])}}</span>
        <span class="stat-label">followed</span>
      </div>
      % low_bat = sum(1 for s in sensors if s['battery_ok'] == 0)
      <div class="stat {{'stat-warn' if low_bat > 0 else ''}}">
        <span class="stat-val">{{low_bat}}</span>
        <span class="stat-label">low battery</span>
      </div>
    </div>
  </div>
</header>

<main>
  % if sensors:
    % for s in sensors:
    <div class="sensor-card {{'followed' if s['follow'] else ''}} {{'battery-low' if s['battery_ok'] == 0 else ''}}"
         data-id="{{s['id']}}">

      <!-- Card header: id, name, follow toggle -->
      <div class="card-header">
        <span class="sensor-id">{{s['id']}}</span>

        <div class="name-wrap">
          <span class="name-display">{{s['name']}}</span>
          <input class="name-input" type="text" value="{{s['name']}}" maxlength="40">
          <button class="btn-edit" title="Edit name" onclick="editName(this)">✎</button>
          <button class="btn-save" title="Save name" onclick="saveName(this)">✔</button>
        </div>

        <div class="follow-wrap">
          <span class="follow-label">follow</span>
          <label class="toggle">
            <input type="checkbox" {{'checked' if s['follow'] else ''}}
                   onchange="toggleFollow(this, '{{s['id']}}')">
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <!-- YAML body: all native rtl_433 fields -->
      <div class="yaml-body">
        % for key, val in s['raw'].items():
        <div class="yaml-line">
          <span class="yaml-indent">  </span>
          <span class="yaml-key">{{key}}</span><span class="yaml-colon">:</span>
          % if val is None:
            <span class="yaml-val-null">null</span>
          % elif val is True:
            <span class="yaml-val-true">true</span>
          % elif val is False:
            <span class="yaml-val-false">false</span>
          % elif isinstance(val, (int, float)):
            <span class="yaml-val-num">{{val}}</span>
            % if key == 'battery_ok' and val == 0:
              <span class="badge-low">LOW</span>
            % end
          % else:
            <span class="yaml-val-str">'{{val}}'</span>
          % end
        </div>
        % end
      </div>

    </div>
    % end
  % else:
  <div class="empty-state">
    <p>No sensors detected yet.</p>
    <p style="font-size:11px;margin-top:8px;color:#2e3340">
      Sensors will appear here after the first scan cycle.
    </p>
  </div>
  % end
</main>

<div id="toast" class="toast"></div>

<script>
  const BASE = window.location.pathname.replace(/\/$/, '');

  function toggleFollow(checkbox, sensorId) {
    const follow = checkbox.checked;
    const card   = checkbox.closest(".sensor-card");
    fetch(`${BASE}/api/sensor/${sensorId}/follow`, {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ follow }),
    })
    .then(r => r.json())
    .then(data => {
      if (data.status === "ok") {
        card.classList.toggle("followed", follow);
        showToast(follow
          ? `Sensor ${sensorId} is now followed.`
          : `Sensor ${sensorId} unfollowed.`);
      } else {
        checkbox.checked = !follow;
        showToast("Error: " + data.message, true);
      }
    })
    .catch(() => { checkbox.checked = !follow; showToast("Network error.", true); });
  }

  function editName(btn) {
    const wrap    = btn.closest(".name-wrap");
    const display = wrap.querySelector(".name-display");
    const input   = wrap.querySelector(".name-input");
    const saveBtn = wrap.querySelector(".btn-save");
    display.style.display = "none";
    btn.style.display     = "none";
    input.style.display   = "inline-block";
    saveBtn.style.display = "inline-block";
    input.focus();
    input.select();
  }

  function saveName(btn) {
    const wrap     = btn.closest(".name-wrap");
    const card     = btn.closest(".sensor-card");
    const sensorId = card.dataset.id;
    const display  = wrap.querySelector(".name-display");
    const input    = wrap.querySelector(".name-input");
    const editBtn  = wrap.querySelector(".btn-edit");
    const name     = input.value.trim();
    if (!name) { showToast("Name cannot be empty.", true); return; }
    fetch(`${BASE}/api/sensor/${sensorId}/name`, {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ name }),
    })
    .then(r => r.json())
    .then(data => {
      if (data.status === "ok") {
        display.textContent   = data.name;
        display.style.display = "inline";
        input.style.display   = "none";
        btn.style.display     = "none";
        editBtn.style.display = "inline-block";
        showToast("Name updated.");
      } else {
        showToast("Error: " + data.message, true);
      }
    })
    .catch(() => showToast("Network error.", true));
  }

  function showToast(msg, isError = false) {
    const t  = document.getElementById("toast");
    t.textContent = msg;
    t.className   = "toast show" + (isError ? " toast-error" : "");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.className = "toast"; }, 3000);
  }

  document.addEventListener("keydown", e => {
    if (e.key === "Enter" &&
        document.activeElement.classList.contains("name-input")) {
      const btn = document.activeElement
                    .closest(".name-wrap")
                    .querySelector(".btn-save");
      if (btn) btn.click();
    }
  });
</script>
</body>
</html>
