(function () {
  var gaId = 'G-0GVNYZLEMX';
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;
  var gaScript = document.createElement('script');
  gaScript.async = true;
  gaScript.src = 'https://www.googletagmanager.com/gtag/js?id=' + gaId;
  document.head.appendChild(gaScript);
  gtag('js', new Date());
  gtag('config', gaId, {
    page_path: location.pathname,
    website_name: location.hostname
  });
})();

(function () {
  var key = 'phc_158CbBeWD8X1eNyD4xpi8VklVxsNZtx5yclocxfpgiO';
  var storageKey = 'neo_posthog_distinct_id';
  var distinctId;
  try {
    distinctId = localStorage.getItem(storageKey);
    if (!distinctId) {
      distinctId = (crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now() + '-' + Math.random().toString(36).slice(2));
      localStorage.setItem(storageKey, distinctId);
    }
  } catch (error) {
    distinctId = Date.now() + '-' + Math.random().toString(36).slice(2);
  }

  var body = JSON.stringify({
    api_key: key,
    event: '$pageview',
    distinct_id: distinctId,
    properties: {
      site_id: 'whylab',
      site_domain: location.hostname,
      audience_locale: 'en-US',
      market: 'global',
      content_vertical: 'causal_inference',
      page_type: location.pathname === '/' ? 'product' : 'guide',
      intent_cluster: 'causal_decision_intelligence',
      $current_url: location.href,
      $pathname: location.pathname,
      $process_person_profile: false,
      $lib: 'neo-sbu-direct'
    }
  });
  var url = 'https://us.i.posthog.com/i/v0/e/';
  try {
    if (navigator.sendBeacon && navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }))) return;
  } catch (error) {}
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body,
    keepalive: true
  }).catch(function () {});
})();
