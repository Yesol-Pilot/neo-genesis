function pageText() {
  return document.body?.innerText || "";
}

function securityBlocker() {
  const text = pageText().toLowerCase();
  const blockers = [
    "captcha",
    "verify",
    "suspicious",
    "unusual activity",
    "robot",
    "security check",
    "\ubcf4\uc548 \ud655\uc778",
    "\ube44\uc815\uc0c1",
    "\uc790\ub3d9\ud654",
    "\uc778\uc99d",
  ];
  return blockers.find((item) => text.includes(item)) || null;
}

function setNativeValue(element, value) {
  const setter =
    Object.getOwnPropertyDescriptor(element.__proto__, "value")?.set ||
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set ||
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  if (setter) setter.call(element, value);
  else element.value = value;
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function fillCaption(text) {
  const candidates = [
    ...document.querySelectorAll("textarea"),
    ...document.querySelectorAll("input[type='text']"),
    ...document.querySelectorAll("[contenteditable='true']"),
  ];
  const target =
    candidates.find((node) => {
      const label = `${node.getAttribute("aria-label") || ""} ${node.placeholder || ""}`.toLowerCase();
      return (
        label.includes("caption") ||
        label.includes("description") ||
        label.includes("\uc124\uba85") ||
        label.includes("\ucea1\uc158")
      );
    }) || candidates[0];
  if (!target) return false;
  if (target.isContentEditable) {
    target.focus();
    document.execCommand("selectAll", false);
    document.execCommand("insertText", false, text);
    target.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    setNativeValue(target, text);
  }
  return true;
}

async function attachVideo(job) {
  const input = document.querySelector("input[type='file']");
  if (!input) return { ok: false, error: "file_input_not_found" };
  const response = await fetch(job.video_url);
  if (!response.ok) return { ok: false, error: `video_fetch_${response.status}` };
  const blob = await response.blob();
  const file = new File([blob], job.filename || "aino-tiktok.mp4", { type: "video/mp4" });
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  return { ok: true, size: file.size };
}

function tryEnableAigcLabel() {
  const textTargets = [...document.querySelectorAll("button, label, div, span")];
  const target = textTargets.find((node) => {
    const text = (node.innerText || node.textContent || "").toLowerCase();
    return (
      text.includes("ai-generated") ||
      text.includes("ai generated") ||
      text.includes("ai \uc0dd\uc131")
    );
  });
  if (!target) return { ok: false, note: "aigc_label_control_not_found" };
  target.click();
  return { ok: true, note: "aigc_label_control_clicked_for_review" };
}

async function prepareUpload(job) {
  const blocker = securityBlocker();
  if (blocker) return { ok: false, blocked: true, blocker };
  const attach = await attachVideo(job);
  const captionOk = fillCaption(job.caption || "");
  const aigc = job.aigc_required ? tryEnableAigcLabel() : { ok: true, note: "aigc_not_required" };
  return {
    ok: attach.ok && captionOk,
    attach,
    captionOk,
    aigc,
    finalPostClickAllowed: false,
    reviewRequired: true,
  };
}

function pageKind() {
  const href = location.href.toLowerCase();
  const title = document.title.toLowerCase();
  if (href.includes("/studio") || title.includes("studio")) return "studio";
  if (href.includes("/upload") || title.includes("upload")) return "upload";
  if (href.includes("/analytics") || title.includes("analytics")) return "analytics";
  return "unknown";
}

function selectorHint(node) {
  if (!(node instanceof Element)) return "";
  const tag = node.tagName.toLowerCase();
  const dataE2e = node.getAttribute("data-e2e");
  const aria = node.getAttribute("aria-label");
  const role = node.getAttribute("role");
  if (dataE2e) return `${tag}[data-e2e="${dataE2e.slice(0, 80)}"]`;
  if (aria) return `${tag}[aria-label="${aria.slice(0, 80)}"]`;
  if (role) return `${tag}[role="${role.slice(0, 80)}"]`;
  const className = typeof node.className === "string" ? node.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
  return className ? `${tag}.${className}` : tag;
}

function collectMetricNodeDetails() {
  return [...document.querySelectorAll("[data-e2e], [aria-label], [role], div, span, button, a")]
    .map((node, index) => {
      const text = (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim();
      if (!text || !/\d/.test(text)) return null;
      return {
        index,
        selector_hint: selectorHint(node),
        text: text.slice(0, 500),
        aria_label: (node.getAttribute("aria-label") || "").slice(0, 200),
        data_e2e: (node.getAttribute("data-e2e") || "").slice(0, 120),
        role: (node.getAttribute("role") || "").slice(0, 80),
      };
    })
    .filter(Boolean)
    .slice(0, 400);
}

function collectStudioMetrics() {
  const text = pageText();
  const blocker = securityBlocker();
  const metricNodeDetails = collectMetricNodeDetails();
  const metricNodes = metricNodeDetails.map((node) => node.text).slice(0, 300);
  const snapshots = [
    { kind: "body_text", text: text.slice(0, 12000) },
    { kind: "metric_nodes", text: metricNodes.join("\n").slice(0, 12000) },
  ];
  const warnings = [];
  if (blocker) warnings.push(`security_blocker:${blocker}`);
  if (text.length < 500) warnings.push("sparse_body_text");
  if (metricNodes.length < 3) warnings.push("sparse_metric_nodes");
  return {
    ok: true,
    schema_version: "studio_metrics_capture_v2",
    capture_id: `studio_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    url: location.href,
    title: document.title,
    page_kind: pageKind(),
    capturedFrom: "chrome_extension",
    textSample: text.slice(0, 12000),
    text_sample: text.slice(0, 12000),
    text_length: text.length,
    metricNodes,
    metricNodeDetails,
    snapshots,
    capture_quality: {
      text_length: text.length,
      metric_nodes_count: metricNodes.length,
      has_security_blocker: Boolean(blocker),
      warnings,
    },
    security_blocker: blocker,
    warnings,
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message?.type === "prepare_upload") {
      sendResponse(await prepareUpload(message.job));
      return;
    }
    if (message?.type === "collect_studio_metrics") {
      sendResponse(collectStudioMetrics());
      return;
    }
    sendResponse({ ok: false, error: "unknown_message" });
  })().catch((error) => sendResponse({ ok: false, error: String(error.message || error) }));
  return true;
});
