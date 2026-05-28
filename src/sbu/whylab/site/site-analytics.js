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
  var endpoint = 'https://us.i.posthog.com/i/v0/e/';
  var baseProperties = {
    site_id: 'whylab',
    site_domain: location.hostname,
    audience_locale: 'en-US',
    market: 'global',
    content_vertical: 'causal_inference',
    page_type: location.pathname === '/' ? 'product' : 'guide',
    intent_cluster: 'causal_decision_intelligence'
  };
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

  function sendPosthog(eventName, properties) {
    var body = JSON.stringify({
      api_key: key,
      event: eventName,
      distinct_id: distinctId,
      properties: Object.assign({}, baseProperties, {
      $current_url: location.href,
      $pathname: location.pathname,
      $process_person_profile: false,
      $lib: 'neo-sbu-direct'
      }, properties || {})
    });

    try {
      if (navigator.sendBeacon && navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }))) return;
    } catch (error) {}
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body,
      keepalive: true
    }).catch(function () {});
  }

  function ctaElement(target) {
    if (!target || !target.closest) return null;
    return target.closest('[data-cta], .cta, .cta-main, .cta-ghost, .cta-sm');
  }

  function ctaIdFor(el) {
    if (el.getAttribute('data-cta')) return el.getAttribute('data-cta');
    var href = el.getAttribute('href') || 'no-destination';
    var label = (el.textContent || 'cta').replace(/\s+/g, '-').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 48);
    return 'auto-' + label + '-' + href.replace(/[^a-z0-9]/gi, '').slice(0, 24).toLowerCase();
  }

  document.addEventListener('click', function (event) {
    var el = ctaElement(event.target);
    if (!el) return;
    var href = el.getAttribute('href') || '';
    var isExternal = href.indexOf('http') === 0 && href.indexOf(location.hostname) === -1;
    var ctaId = ctaIdFor(el);
    sendPosthog('cta_click', {
      cta_id: ctaId,
      cta_label: (el.textContent || ctaId).replace(/\s+/g, ' ').trim().slice(0, 120),
      destination_url: href,
      destination_type: isExternal ? 'external' : 'internal',
      capture_source: 'site_analytics_delegate'
    });
  }, true);

  sendPosthog('$pageview');
})();
