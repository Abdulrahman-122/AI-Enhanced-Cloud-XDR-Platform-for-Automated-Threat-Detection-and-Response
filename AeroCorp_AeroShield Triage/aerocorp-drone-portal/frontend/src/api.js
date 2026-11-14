import { useEffect, useState } from "react";

export class ApiError extends Error {
  constructor(status, detail, data) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

export async function api(path, { method = "GET", body, token, signal } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* non-JSON body */
  }

  if (!response.ok) {
    const d = data?.detail;
    const detail =
      typeof d === "string" ? d : Array.isArray(d) ? d.map((item) => item.msg).join(" ") : `Request failed (${response.status}).`;
    throw new ApiError(response.status, detail, data);
  }
  return data;
}

/**
 * GET helper for components. Pass null as the path to skip the request.
 *
 * The state remembers which path it belongs to, so a component never receives the previous path's
 * data or error while a new path is loading (including the first render after the path changes).
 */
export function useApi(path, { token, reload = 0 } = {}) {
  const [state, setState] = useState({ path: null, data: null, error: null });

  useEffect(() => {
    if (!path) {
      setState({ path: null, data: null, error: null });
      return undefined;
    }
    const controller = new AbortController();
    setState((previous) => ({ path, data: previous.path === path ? previous.data : null, error: null }));
    api(path, { token, signal: controller.signal })
      .then((data) => setState({ path, data, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError") setState({ path, data: null, error });
      });
    return () => controller.abort();
  }, [path, token, reload]); // `reload` changes after a save, so the same path is fetched again

  if (!path) return { data: null, error: null, loading: false };
  const current = state.path === path;
  return {
    data: current ? state.data : null,
    error: current ? state.error : null,
    loading: !current || (state.data === null && state.error === null),
  };
}
