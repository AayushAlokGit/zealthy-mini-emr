"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: boolean;
  reload: () => void;
}

/**
 * Fetch `path` and track loading/error, with a `reload()` to refetch.
 * Pass `null` as the path to skip fetching (e.g. data that loads lazily when a
 * panel is opened); the request fires once the path becomes a string.
 */
export function useApi<T>(path: string | null): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [error, setError] = useState(false);
  const [key, setKey] = useState(0);

  useEffect(() => {
    if (path === null) return;
    // `cancelled` ignores a response that arrives after this effect is torn
    // down — i.e. after `path`/`key` changed or the component unmounted — so a
    // slow, stale request can't overwrite newer data (an out-of-order race).
    let cancelled = false;
    api
      .get<T>(path)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, key]);

  const reload = useCallback(() => setKey((k) => k + 1), []);
  return { data, loading, error, reload };
}
