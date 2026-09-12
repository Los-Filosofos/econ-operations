import { queryOptions, useQuery } from "@tanstack/react-query"
import { useSearch } from "@tanstack/react-router"

import { hubSchema, type DataMode } from "./schema"

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")

export async function fetchHub(
  mode: DataMode,
  search = "",
  signal?: AbortSignal
) {
  let response: Response
  try {
    const params = new URLSearchParams({ mode, search })
    response = await fetch(`${apiBase}/api/v1/hub?${params}`, {
      signal,
      headers: { Accept: "application/json" },
      credentials: "omit",
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new Error(
      "No pudimos conectar con el hub. Comprueba la disponibilidad del servicio e inténtalo de nuevo.",
      { cause: error }
    )
  }
  if (!response.ok) {
    throw new Error(
      `El servicio no pudo completar la consulta (HTTP ${response.status}). Vuelve a intentarlo.`
    )
  }
  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new Error(
      "El servicio no devolvió una respuesta válida. Revisa la dirección de la API."
    )
  }
  const result = hubSchema.safeParse(body)
  if (!result.success || result.data.mode !== mode) {
    throw new Error(
      "La respuesta no coincide con el contrato o con el origen solicitado. No se muestran datos sin validar."
    )
  }
  return result.data
}

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
