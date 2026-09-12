import { queryOptions, useQuery } from "@tanstack/react-query"
import { useSearch } from "@tanstack/react-router"
import { fetchHub } from "./api"
import type { DataMode } from "./schema"

export function hubQueryOptions(mode: DataMode, search: string) {
  return queryOptions({
    queryKey: ["hub", mode, search],
    queryFn: ({ signal }) => fetchHub(mode, search, signal),
    staleTime: 60_000,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useHub() {
  const { mode, q } = useSearch({ from: "__root__" })
  return useQuery(hubQueryOptions(mode, q))
}
