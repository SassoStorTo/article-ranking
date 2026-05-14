export type AppPage = "home" | "corpora" | "new-corpus" | "articles" | "executions";

export type AppRoute =
  | { page: "home" }
  | { page: "corpora"; corpusId?: string }
  | { page: "new-corpus" }
  | { page: "articles"; articleId?: string }
  | { page: "executions"; executionId?: string };

export function routeForPage(page: AppPage): AppRoute {
  if (page === "home") {
    return { page: "home" };
  }
  if (page === "corpora") {
    return { page: "corpora" };
  }
  if (page === "new-corpus") {
    return { page: "new-corpus" };
  }
  if (page === "articles") {
    return { page: "articles" };
  }
  return { page: "executions" };
}

export function pathForRoute(route: AppRoute): string {
  if (route.page === "home") {
    return "/";
  }
  if (route.page === "new-corpus") {
    return "/corpora/new";
  }
  if (route.page === "corpora") {
    return route.corpusId
      ? `/corpora/${encodeURIComponent(route.corpusId)}`
      : "/corpora";
  }
  if (route.page === "articles") {
    return route.articleId
      ? `/articles/${encodeURIComponent(route.articleId)}`
      : "/articles";
  }
  return route.executionId
    ? `/executions/${encodeURIComponent(route.executionId)}`
    : "/executions";
}

export function routeForPathname(pathname: string): AppRoute {
  const normalizedPathname = normalizePathname(pathname);
  const segments = normalizedPathname.split("/").filter(Boolean);

  try {
    if (segments.length === 0) {
      return { page: "home" };
    }
    if (segments.length === 1) {
      if (segments[0] === "corpora") {
        return { page: "corpora" };
      }
      if (segments[0] === "articles") {
        return { page: "articles" };
      }
      if (segments[0] === "executions") {
        return { page: "executions" };
      }
      return { page: "home" };
    }
    if (segments.length === 2) {
      if (segments[0] === "corpora" && segments[1] === "new") {
        return { page: "new-corpus" };
      }
      if (segments[0] === "corpora") {
        const corpusId = decodeRouteParam(segments[1]);
        return corpusId ? { corpusId, page: "corpora" } : { page: "home" };
      }
      if (segments[0] === "articles") {
        const articleId = decodeRouteParam(segments[1]);
        return articleId ? { articleId, page: "articles" } : { page: "home" };
      }
      if (segments[0] === "executions") {
        const executionId = decodeRouteParam(segments[1]);
        return executionId
          ? { executionId, page: "executions" }
          : { page: "home" };
      }
    }
  } catch {
    return { page: "home" };
  }

  return { page: "home" };
}

export function routeEquals(left: AppRoute, right: AppRoute): boolean {
  return pathForRoute(left) === pathForRoute(right);
}

function normalizePathname(pathname: string): string {
  if (pathname === "") {
    return "/";
  }
  return pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
}

function decodeRouteParam(value: string): string | null {
  const decoded = decodeURIComponent(value);
  return decoded.length > 0 ? decoded : null;
}
