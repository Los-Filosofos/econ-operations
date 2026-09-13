// Simple Hash Router

export class Router {
  constructor(routes, notFoundHandler) {
    this.routes = routes;
    this.notFound = notFoundHandler || (() => console.warn('Route not found'));
    this.currentPath = null;

    window.addEventListener('hashchange', () => this.resolve());
  }

  init() {
    this.resolve();
  }

  navigate(path) {
    window.location.hash = path;
  }

  resolve() {
    const rawHash = window.location.hash.slice(1) || '/';
    const [path, queryString] = rawHash.split('?');
    const params = new URLSearchParams(queryString || '');

    this.currentPath = path;

    // Check exact matches first
    if (this.routes[path]) {
      this.routes[path]({ params });
      return;
    }

    // Check parameterized routes (e.g. /solicitudes/:id)
    for (const [pattern, handler] of Object.entries(this.routes)) {
      if (pattern.includes(':')) {
        const regex = new RegExp('^' + pattern.replace(/:([a-zA-Z0-9_]+)/g, '(?<$1>[^/]+)') + '$');
        const match = path.match(regex);
        if (match) {
          handler({ params, routeParams: match.groups });
          return;
        }
      }
    }

    this.notFound(path);
  }
}
