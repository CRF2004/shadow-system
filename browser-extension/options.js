/**
 * Shadow System — Browser Extension Options
 */
const DEFAULTS = {
  serverUrl: "http://localhost:8081",
  apiToken: "",
  interval: 5,
};

document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.sync.get(Object.keys(DEFAULTS), (stored) => {
    Object.keys(DEFAULTS).forEach((key) => {
      const el = document.getElementById(key);
      if (el) el.value = stored[key] ?? DEFAULTS[key];
    });
  });

  document.getElementById("save").addEventListener("click", () => {
    const data = {};
    Object.keys(DEFAULTS).forEach((key) => {
      const el = document.getElementById(key);
      if (el) data[key] = el.value;
    });

    chrome.storage.sync.set(data, () => {
      const status = document.getElementById("status");
      status.textContent = "✅ Saved!";
      setTimeout(() => { status.textContent = ""; }, 2000);
    });
  });
});
