/* AG Grid's Markdown renderer emits ordinary anchors. Keep internal row links
 * inside Dash so the shell and per-browser reading survive opening a detail.
 * Sidebar links and dcc.Link already implement their own navigation.
 */
document.addEventListener("click", function (event) {
  if (event.defaultPrevented || event.button !== 0 ||
      event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  const anchor = event.target.closest && event.target.closest(".econ-grid a[href]");
  if (!anchor || anchor.hasAttribute("download") ||
      (anchor.target && anchor.target !== "_self")) return;
  const url = new URL(anchor.href, window.location.href);
  if (url.origin !== window.location.origin ||
      !/^\/(?:solicitudes|maquinaria|operaciones)(?:\/|$)/.test(url.pathname)) return;
  event.preventDefault();
  window.history.pushState({}, "", url.pathname + url.search + url.hash);
  window.dispatchEvent(new CustomEvent("_dashprivate_pushstate"));
  window.scrollTo(0, 0);
});
