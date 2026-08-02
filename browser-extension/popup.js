/**
 * Shadow System — Browser Extension Popup
 */
document.addEventListener("DOMContentLoaded", () => {
  const bg = chrome.runtime;

  bg.sendMessage({ type: "getStats" }, (stats) => {
    if (!stats) return;

    document.getElementById("serverUrl").textContent = stats.serverUrl || "--";

    const tokenEl = document.getElementById("tokenStatus");
    if (stats.apiTokenSet) {
      tokenEl.innerHTML = '<span class="status-dot on"></span>Configured';
    } else {
      tokenEl.innerHTML = '<span class="status-dot off"></span>Not set';
    }

    document.getElementById("sessionMinutes").textContent =
      `${stats.sessionMinutes} min`;
    document.getElementById("siteCount").textContent =
      `${stats.trackedSites?.length || 0}`;
    document.getElementById("totalMinutes").textContent =
      `${stats.totalMinutes} min`;
    document.getElementById("intervalDisplay").textContent =
      `${stats.interval} min`;

    const siteList = document.getElementById("siteList");
    if (stats.trackedSites?.length > 0) {
      siteList.innerHTML = stats.trackedSites
        .slice(0, 10)
        .map(
          (s) =>
            `<div class="site-item">🔹 <span class="cat">[${s.category}]</span> ${s.hostname} — ${Math.round(s.totalMs / 60000)} min</div>`
        )
        .join("");
      if (stats.trackedSites.length > 10) {
        siteList.innerHTML +=
          `<div class="site-item" style="color:#666">... +${stats.trackedSites.length - 10} more</div>`;
      }
    } else {
      siteList.innerHTML =
        '<div class="site-item" style="color:#666">No sites tracked yet.</div>';
    }
  });

  document.getElementById("openOptions").addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });
});
