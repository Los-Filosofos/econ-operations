(() => {
  "use strict";

  const viewStates = new Map();
  // Zooming out is still available, but the initial mobile flow keeps exact node diameters.
  const MIN_SCALE = 0.62;
  const MAX_SCALE = 2.4;

  const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));

  function syncShell() {
    const shell = document.querySelector(".application-shell");
    const graph = document.querySelector(".operations-graph");
    if (shell) {
      shell.classList.toggle("graph-mode", Boolean(graph));
      if (graph) {
        shell.style.setProperty(
          "--graph-shell-bg",
          getComputedStyle(graph).getPropertyValue("--graph-bg")
        );
      } else {
        shell.style.removeProperty("--graph-shell-bg");
      }
    }
    if (graph) mount(graph);
  }

  function mount(root) {
    if (root.dataset.graphMounted === "true") return;
    root.dataset.graphMounted = "true";
    const viewport = root.querySelector(".operations-graph-viewport");
    const world = root.querySelector(".operations-graph-world");
    if (!viewport || !world) return;

    const key = root.dataset.layoutKey || "operations";
    const width = Number(world.dataset.worldWidth || 1);
    const height = Number(world.dataset.worldHeight || 1);
    let state = viewStates.get(key) || { x: 0, y: 0, scale: 1 };
    let dragging = false;
    let pointer = null;
    let start = null;
    let lastSelected = null;
    let observedSize = null;

    function focusDetail(detail) {
      requestAnimationFrame(() => detail?.querySelector("[data-graph-close]")?.focus());
    }

    function draw() {
      world.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
      viewStates.set(key, { ...state });
    }

    function center() {
      const bounds = viewport.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      const fitScale = Math.min(
        (bounds.width - 56) / width,
        (bounds.height - 56) / height,
        1
      );
      const firstProject = root.querySelector(".graph-node--place");
      const projectX = Number.parseFloat(firstProject?.style.left || "");
      const mobileFlowStart = bounds.width < 600 && fitScale < 1 && Number.isFinite(projectX);
      const preserveNodeScale = fitScale >= 0.82;
      const scale = mobileFlowStart || preserveNodeScale
        ? 1
        : clamp(fitScale, MIN_SCALE, MAX_SCALE);
      state = {
        scale,
        x: mobileFlowStart ? 68 - projectX * scale : (bounds.width - width * scale) / 2,
        y: (bounds.height - height * scale) / 2,
      };
      draw();
    }

    function zoom(nextScale, clientX, clientY) {
      const bounds = viewport.getBoundingClientRect();
      const scale = clamp(nextScale, MIN_SCALE, MAX_SCALE);
      const anchorX = clientX == null ? bounds.width / 2 : clientX - bounds.left;
      const anchorY = clientY == null ? bounds.height / 2 : clientY - bounds.top;
      const worldX = (anchorX - state.x) / state.scale;
      const worldY = (anchorY - state.y) / state.scale;
      state = {
        scale,
        x: anchorX - worldX * scale,
        y: anchorY - worldY * scale,
      };
      draw();
    }

    function reveal(placeKey) {
      if (placeKey) root.dataset.expandedPlace = placeKey;
      else root.removeAttribute("data-expanded-place");
      root.querySelectorAll(".graph-node--machine").forEach((node) => {
        const places = (node.dataset.places || "").split("|").filter(Boolean);
        const visible = node.dataset.alwaysVisible === "true" || places.includes(placeKey);
        node.classList.toggle("is-expanded", visible);
        node.setAttribute("aria-hidden", visible ? "false" : "true");
        node.tabIndex = visible ? 0 : -1;
      });
      root.querySelectorAll(".graph-edge").forEach((edge) => {
        const visible =
          edge.classList.contains("graph-edge--active") ||
          (placeKey && (edge.dataset.source === placeKey || edge.dataset.target === placeKey));
        edge.classList.toggle("is-expanded", Boolean(visible));
        const control = edge.querySelector(".graph-edge-label");
        if (control) control.tabIndex = visible ? 0 : -1;
      });
    }

    function select(nodeKey, returnFocus = false) {
      const connected = new Set(nodeKey ? [nodeKey] : []);
      const selectedNode = [...root.querySelectorAll(".graph-node")].find(
        (node) => node.dataset.nodeKey === nodeKey
      );
      const placeKey =
        selectedNode?.dataset.nodeKind === "place"
          ? nodeKey
          : (selectedNode?.dataset.places || "").split("|").find(Boolean);
      reveal(placeKey || null);
      root.querySelectorAll(".graph-edge-label").forEach((control) => {
        control.setAttribute("aria-pressed", "false");
      });
      root.querySelectorAll("[data-edge-detail]").forEach((detail) => {
        detail.hidden = true;
        detail.setAttribute("aria-hidden", "true");
      });
      root.removeAttribute("data-edge-selection");
      root.querySelectorAll(".graph-edge").forEach((edge) => {
        const active = Boolean(
          nodeKey && (edge.dataset.source === nodeKey || edge.dataset.target === nodeKey)
        );
        edge.classList.toggle("is-connected", active);
        edge.classList.toggle("is-dimmed", Boolean(nodeKey) && !active);
        if (active) {
          connected.add(edge.dataset.source);
          connected.add(edge.dataset.target);
        }
      });
      root.querySelectorAll(".graph-node").forEach((node) => {
        const selected = node.dataset.nodeKey === nodeKey;
        node.classList.toggle("is-selected", selected);
        node.classList.toggle("is-dimmed", Boolean(nodeKey) && !connected.has(node.dataset.nodeKey));
        node.setAttribute("aria-pressed", selected ? "true" : "false");
        if (selected) lastSelected = node;
      });
      let openDetail = null;
      root.querySelectorAll(".graph-detail").forEach((detail) => {
        const open = detail.dataset.nodeDetail === nodeKey;
        detail.hidden = !open;
        detail.setAttribute("aria-hidden", open ? "false" : "true");
        if (open) openDetail = detail;
      });
      if (nodeKey) {
        root.dataset.selection = nodeKey;
        focusDetail(openDetail);
      } else {
        root.removeAttribute("data-selection");
      }
      if (!nodeKey && returnFocus && lastSelected) lastSelected.focus();
    }

    function selectEdge(edgeKey) {
      select(null, false);
      const edge = [...root.querySelectorAll(".graph-edge")].find(
        (candidate) => candidate.dataset.edgeKey === edgeKey
      );
      if (!edge) return;
      const endpoints = new Set([edge.dataset.source, edge.dataset.target]);
      const placeKeys = new Set(
        [...root.querySelectorAll(".graph-node--place")].map((node) => node.dataset.nodeKey)
      );
      const placeKey = [...endpoints].find((key) => placeKeys.has(key));
      reveal(placeKey || null);
      root.querySelectorAll(".graph-edge").forEach((candidate) => {
        const selected = candidate === edge;
        candidate.classList.toggle("is-connected", selected);
        candidate.classList.toggle("is-dimmed", !selected);
      });
      root.querySelectorAll(".graph-node").forEach((node) => {
        node.classList.toggle("is-dimmed", !endpoints.has(node.dataset.nodeKey));
        node.classList.remove("is-selected");
        node.setAttribute("aria-pressed", "false");
      });
      root.querySelectorAll(".graph-edge-label").forEach((control) => {
        const selected = control.dataset.edgeSelect === edgeKey;
        control.setAttribute("aria-pressed", selected ? "true" : "false");
        if (selected) lastSelected = control;
      });
      let openDetail = null;
      root.querySelectorAll("[data-edge-detail]").forEach((detail) => {
        const open = detail.dataset.edgeDetail === edgeKey;
        detail.hidden = !open;
        detail.setAttribute("aria-hidden", open ? "false" : "true");
        if (open) openDetail = detail;
      });
      root.dataset.edgeSelection = edgeKey;
      focusDetail(openDetail);
    }

    viewport.addEventListener("wheel", (event) => {
      event.preventDefault();
      zoom(state.scale * (event.deltaY < 0 ? 1.12 : 0.89), event.clientX, event.clientY);
    }, { passive: false });

    viewport.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button, .graph-detail")) return;
      dragging = true;
      pointer = event.pointerId;
      start = { x: event.clientX, y: event.clientY, panX: state.x, panY: state.y };
      viewport.classList.add("is-panning");
      viewport.setPointerCapture(pointer);
    });
    viewport.addEventListener("pointermove", (event) => {
      if (!dragging || event.pointerId !== pointer) return;
      state.x = start.panX + event.clientX - start.x;
      state.y = start.panY + event.clientY - start.y;
      draw();
    });
    const endPan = (event) => {
      if (!dragging || event.pointerId !== pointer) return;
      dragging = false;
      viewport.classList.remove("is-panning");
      if (viewport.hasPointerCapture(pointer)) viewport.releasePointerCapture(pointer);
    };
    viewport.addEventListener("pointerup", endPan);
    viewport.addEventListener("pointercancel", endPan);

    viewport.addEventListener("keydown", (event) => {
      if (event.target !== viewport) return;
      if (["+", "="].includes(event.key)) {
        event.preventDefault();
        zoom(state.scale * 1.15);
      } else if (event.key === "-") {
        event.preventDefault();
        zoom(state.scale * 0.87);
      } else if (event.key === "0") {
        event.preventDefault();
        center();
      }
    });

    root.addEventListener("click", (event) => {
      const close = event.target.closest("[data-graph-close]");
      if (close) {
        select(null, true);
        return;
      }
      const node = event.target.closest(".graph-node");
      if (node) {
        if (
          node.dataset.nodeKind === "place" &&
          root.dataset.selection === node.dataset.nodeKey
        ) {
          select(null, true);
          return;
        }
        select(node.dataset.nodeKey);
        return;
      }
      const edge = event.target.closest("[data-edge-select]");
      if (edge) {
        selectEdge(edge.dataset.edgeSelect);
        return;
      }
      const control = event.target.closest("[data-graph-control]");
      if (!control) return;
      const action = control.dataset.graphControl;
      if (action === "in") zoom(state.scale * 1.15);
      if (action === "out") zoom(state.scale * 0.87);
      if (action === "center") center();
      if (action === "refresh") document.getElementById("refresh")?.click();
    });
    root.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && (root.dataset.selection || root.dataset.edgeSelection)) {
        event.preventDefault();
        select(null, true);
      }
    });

    const resizeObserver = new ResizeObserver((entries) => {
      const bounds = entries[0]?.contentRect;
      if (!bounds?.width || !bounds?.height) return;
      const size = `${Math.round(bounds.width)}x${Math.round(bounds.height)}`;
      if (observedSize && observedSize !== size) center();
      observedSize = size;
    });
    resizeObserver.observe(viewport);

    reveal(null);
    if (viewStates.has(key)) draw();
    else requestAnimationFrame(center);
  }

  const observer = new MutationObserver(syncShell);
  const start = () => {
    observer.observe(document.body, { childList: true, subtree: true });
    syncShell();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
