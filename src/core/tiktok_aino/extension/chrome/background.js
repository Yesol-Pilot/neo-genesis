const BRIDGE = "http://127.0.0.1:8757";

async function bridgeJson(path, options = {}) {
  const response = await fetch(`${BRIDGE}${path}`, options);
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `bridge_http_${response.status}`);
  }
  return payload;
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("no_active_tab");
  return tab;
}

async function sendToActive(message) {
  const tab = await activeTab();
  return chrome.tabs.sendMessage(tab.id, message);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message?.type === "bridge_health") {
      sendResponse(await bridgeJson("/health"));
      return;
    }
    if (message?.type === "load_latest") {
      const job = await bridgeJson("/latest");
      await chrome.storage.session.set({ latestJob: job });
      sendResponse(job);
      return;
    }
    if (message?.type === "open_upload") {
      const tab = await chrome.tabs.create({ url: "https://www.tiktok.com/tiktokstudio/upload" });
      sendResponse({ ok: true, tabId: tab.id });
      return;
    }
    if (message?.type === "prepare_upload") {
      const { latestJob } = await chrome.storage.session.get("latestJob");
      if (!latestJob) throw new Error("no_loaded_job");
      sendResponse(await sendToActive({ type: "prepare_upload", job: latestJob }));
      return;
    }
    if (message?.type === "collect_metrics") {
      const { latestJob } = await chrome.storage.session.get("latestJob");
      const metrics = await sendToActive({ type: "collect_studio_metrics" });
      if (latestJob) {
        metrics.latestJob = {
          run_id: latestJob.run_id,
          status: latestJob.status,
          manifest_path: latestJob.manifest_path,
          planned_publish_at_local: latestJob.planned_publish_at_local,
          schedule_status: latestJob.schedule_status,
        };
        metrics.run_id = latestJob.run_id;
      }
      const result = await bridgeJson("/metrics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(metrics),
      });
      sendResponse(result);
      return;
    }
    sendResponse({ ok: false, error: "unknown_message" });
  })().catch((error) => sendResponse({ ok: false, error: String(error.message || error) }));
  return true;
});
