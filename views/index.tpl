<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RTL-433 Sensor Bridge</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
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
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Model</th>
            <th>Ch</th>
            <th>Temp</th>
            <th>Hum</th>
            <th>Battery</th>
            <th>Last seen</th>
            <th class="col-follow">Follow</th>
          </tr>
        </thead>
        <tbody>
          % for s in sensors:
          <tr class="sensor-row {{'row-followed' if s['follow'] else ''}} {{'row-battery-low' if s['battery_ok'] == 0 else ''}}"
              data-id="{{s['id']}}">

            <td class="col-id"><code>{{s['id']}}</code></td>

            <td class="col-name">
              <span class="name-display">{{s['name']}}</span>
              <input class="name-input" type="text" value="{{s['name']}}"
                     style="display:none" maxlength="40">
              <button class="btn-edit" title="Edit name" onclick="editName(this)">✎</button>
              <button class="btn-save" title="Save name" onclick="saveName(this)"
                      style="display:none">✔</button>
            </td>

            <td class="col-model">{{s['model']}}</td>
            <td class="col-ch">{{s['channel']}}</td>

            <td class="col-temp">
              % if s['temperature_C'] is not None:
                <span class="val-temp">{{s['temperature_C']}}°C</span>
              % else:
                <span class="na">—</span>
              % end
            </td>

            <td class="col-hum">
              % if s['humidity'] is not None:
                <span class="val-hum">{{s['humidity']}}%</span>
              % else:
                <span class="na">—</span>
              % end
            </td>

            <td class="col-battery">
              % if s['battery_ok'] == 0:
                <span class="badge badge-low">LOW</span>
              % else:
                <span class="badge badge-ok">OK</span>
              % end
            </td>

            <td class="col-time">{{s['last_reception']}}</td>

            <td class="col-follow">
              <label class="toggle">
                <input type="checkbox" {{'checked' if s['follow'] else ''}}
                       onchange="toggleFollow(this, '{{s['id']}}')">
                <span class="slider"></span>
              </label>
            </td>

          </tr>
          % end
        </tbody>
      </table>
    </div>
    % else:
    <div class="empty-state">
      <div class="empty-icon">◎</div>
      <p>No sensors detected yet.</p>
      <p class="empty-sub">Sensors will appear here after the first scan cycle.</p>
    </div>
    % end
  </main>

  <div id="toast" class="toast"></div>

  <script>
const BASE = window.location.pathname.replace(/\/$/, '');

function toggleFollow(checkbox, sensorId) {
  const follow = checkbox.checked;
  const row    = checkbox.closest("tr");
  fetch(`${BASE}/api/sensor/${sensorId}/follow`, {
    method : "POST",
    headers: { "Content-Type": "application/json" },
    body   : JSON.stringify({ follow }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === "ok") {
      row.classList.toggle("row-followed", follow);
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

function saveName(btn) {
  const td       = btn.closest("td");
  const row      = td.closest("tr");
  const sensorId = row.dataset.id;
  const display  = td.querySelector(".name-display");
  const input    = td.querySelector(".name-input");
  const editBtn  = td.querySelector(".btn-edit");
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
      const t = document.getElementById("toast");
      t.textContent = msg;
      t.className   = "toast show" + (isError ? " toast-error" : "");
      clearTimeout(t._timer);
      t._timer = setTimeout(() => { t.className = "toast"; }, 3000);
    }

    document.addEventListener("keydown", e => {
      if (e.key === "Enter" && document.activeElement.classList.contains("name-input")) {
        const btn = document.activeElement.closest("td").querySelector(".btn-save");
        if (btn) btn.click();
      }
    });
  </script>
</body>
</html>
