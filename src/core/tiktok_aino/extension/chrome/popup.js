const statusBox = document.getElementById("status");

function show(payload) {
  statusBox.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

async function send(type) {
  const response = await chrome.runtime.sendMessage({ type });
  show(response);
}

document.getElementById("health").addEventListener("click", () => send("bridge_health"));
document.getElementById("load").addEventListener("click", () => send("load_latest"));
document.getElementById("openUpload").addEventListener("click", () => send("open_upload"));
document.getElementById("prepare").addEventListener("click", () => send("prepare_upload"));
document.getElementById("metrics").addEventListener("click", () => send("collect_metrics"));
