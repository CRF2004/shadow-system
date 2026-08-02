/**
 * Shadow System — Browser Extension Background Script
 *
 * Tracks active tab URL/category and sends learning activity to
 * the Shadow System game engine at configurable intervals.
 *
 * Configuration (stored in chrome.storage.sync):
 *   - serverUrl:  Shadow System API base URL (default: http://localhost:8081)
 *   - apiToken:   API token for authentication
 *   - interval:   Report interval in minutes (default: 5)
 *
 * Learning categories (by domain pattern):
 *   - coding:    github.com, stackoverflow.com, etc.
 *   - research:  arxiv.org, scholar.google.com, paperswithcode.com, etc.
 *   - reading:   medium.com, dev.to, blog.*, etc.
 *   - learning:  coursera.org, udemy.com, youtube.com (educational), etc.
 */

const DEFAULT_CONFIG = {
  serverUrl: "http://localhost:8081",
  apiToken: "",
  interval: 5,
};

let config = { ...DEFAULT_CONFIG };
let sessionStart = Date.now();
let trackedSites = {};

// ── Initialization ──────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(Object.keys(DEFAULT_CONFIG), (stored) => {
    config = { ...DEFAULT_CONFIG, ...stored };
  });
  createAlarm();
});

chrome.storage.onChanged.addListener((changes) => {
  for (const [key, { newValue }] of Object.entries(changes)) {
    if (key in config) config[key] = newValue;
  }
  createAlarm();
});

// ── Alarm-based reporting ────────────────────────────────────────────────

function createAlarm() {
  chrome.alarms.clear("reportActivity");
  chrome.alarms.create("reportActivity", { periodInMinutes: config.interval });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "reportActivity") {
    reportActivity();
  }
});

// ── Activity tracking ────────────────────────────────────────────────────

chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    if (tab?.url) trackSite(tab.url);
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab?.url) {
    trackSite(tab.url);
  }
});

function trackSite(url) {
  const hostname = new URL(url).hostname;
  const category = classifySite(hostname);
  if (category === "ignore") return;

  const now = Date.now();
  const key = `${hostname}::${category}`;
  if (!trackedSites[key]) {
    trackedSites[key] = { hostname, category, totalMs: 0, lastSeen: now };
  }
  trackedSites[key].lastSeen = now;
}

/**
 * Classify a hostname into a learning category.
 * Returns "ignore" for non-productive sites (social media, entertainment).
 */
function classifySite(hostname) {
  const patterns = [
    // Coding
    { category: "coding", domains: ["github.com", "gitlab.com", "stackoverflow.com",
      "stackexchange.com", "codeberg.org", "npmjs.com", "pypi.org", "docs.python.org",
      "developer.mozilla.org", "react.dev", "nextjs.org"] },
    // Research
    { category: "research", domains: ["arxiv.org", "scholar.google.com",
      "paperswithcode.com", "semanticscholar.org", "openreview.net",
      "pubmed.ncbi.nlm.nih.gov", "ieeexplore.ieee.org", "acm.org",
      "nature.com", "science.org", "springer.com", "elsevier.com"] },
    // Reading & learning
    { category: "reading", domains: ["medium.com", "dev.to", "blog.",
      "substack.com", "newsletter.", "wikipedia.org"] },
    // Online learning
    { category: "learning", domains: ["coursera.org", "udemy.com", "edx.org",
      "youtube.com", "youtu.be", "mit.edu", "stanford.edu", "classcentral.com"] },
    // Documentation
    { category: "research", domains: ["readthedocs.io", "docs.", "kubernetes.io",
      "docker.com", "microsoft.com/en-us"] },
  ];

  for (const { category, domains } of patterns) {
    for (const domain of domains) {
      if (domain.endsWith(".")) {
        if (hostname.startsWith(domain) || hostname.includes(domain.slice(0, -1))) {
          return category;
        }
      } else if (hostname === domain || hostname.endsWith("." + domain)) {
        return category;
      }
    }
  }

  // Entertainment/social: always ignore
  const ignoreDomains = [
    "twitter.com", "x.com", "facebook.com", "instagram.com", "tiktok.com",
    "reddit.com", "bilibili.com", "netflix.com", "youtube.com",
  ];
  for (const d of ignoreDomains) {
    if (hostname === d || hostname.endsWith("." + d)) return "ignore";
  }

  // Default: track as reading (conservative)
  return "reading";
}

// ── API reporting ────────────────────────────────────────────────────────

async function reportActivity() {
  const now = Date.now();
  // Calculate time spent per site since last report
  for (const key of Object.keys(trackedSites)) {
    const site = trackedSites[key];
    const elapsed = Math.max(0, now - site.lastSeen);
    site.totalMs += elapsed;
    site.lastSeen = now;
  }

  const totalLearningSeconds = Object.values(trackedSites)
    .reduce((sum, s) => sum + s.totalMs, 0) / 1000;

  if (totalLearningSeconds < 60) return; // Skip if less than 1 minute

  const payload = {
    source: "browser-extension",
    total_seconds: Math.round(totalLearningSeconds),
    sites: Object.values(trackedSites).map((s) => ({
      hostname: s.hostname,
      category: s.category,
      seconds: Math.round(s.totalMs / 1000),
    })),
  };

  try {
    const resp = await fetch(`${config.serverUrl}/api/activities?token=${config.apiToken}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      trackedSites = {}; // Reset after successful report
      sessionStart = Date.now();
    }
  } catch (err) {
    console.warn("[Shadow System] Failed to report activity:", err.message);
  }
}

// ── Popup bridge ─────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "getStats") {
    const totalSites = Object.keys(trackedSites).length;
    const totalTime = Object.values(trackedSites).reduce(
      (sum, s) => sum + s.totalMs, 0
    );
    sendResponse({
      serverUrl: config.serverUrl,
      apiTokenSet: !!config.apiToken,
      interval: config.interval,
      trackedSites: Object.values(trackedSites),
      totalMinutes: Math.round(totalTime / 60000),
      sessionMinutes: Math.round((Date.now() - sessionStart) / 60000),
    });
  }
  return true;
});
