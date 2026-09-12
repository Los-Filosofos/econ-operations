import { afterEach, describe, expect, it, vi } from "vitest"
import { fetchHub, hubQueryOptions } from "./api"
import { hubSchema, hubSearchSchema, type Hub } from "./schema"

const unavailable: Hub = {
  schema_version: "1.0",
  mode: "live",
  generated_at: "2026-09-12T18:00:00Z",
  data_as_of: null,
  sources: [
    {
      id: "nexus",
      label: "Nexus",
      status: "disabled",
      environment: "sandbox",
      observed_at: null,
      message: "Live disabled",
    },
  ],
  scope: {
    search: "",
    bounded: true,
    equipment_total: null,
    requests_total: null,
    equipment_returned: 0,
    requests_returned: 0,
    complete: false,
    description: "Unavailable",
  },
  summary: {
    equipment_count: null,
    administratively_available: null,
    active_failures: null,
    stopped_equipment: null,
    unlinked_equipment: null,
    alerts_count: null,
  },
  equipment: [],
  requests: [],
  alerts: [],
}

afterEach(() => vi.unstubAllGlobals())

describe("API data provenance boundary", () => {
  it("preserves missing metrics when a live source is disabled", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json(unavailable))
    )
    const result = await fetchHub("live")
    expect(result.summary.equipment_count).toBeNull()
    expect(result.summary.alerts_count).toBeNull()
    expect(result.equipment).toEqual([])
    expect(result.sources[0].status).toBe("disabled")
  })
  it("rejects fixture data returned for a live query", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(Response.json({ ...unavailable, mode: "fixture" }))
    )
    await expect(fetchHub("live")).rejects.toThrow("origen solicitado")
  })
  it("makes no fixture fallback request after a network failure", async () => {
    const request = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
    vi.stubGlobal("fetch", request)
    await expect(fetchHub("live")).rejects.toThrow("No pudimos conectar")
    expect(request).toHaveBeenCalledTimes(1)
    expect(request.mock.calls[0][0]).toContain("mode=live")
  })
  it("forwards cancellation and separates mode and search cache entries", async () => {
    const request = vi.fn().mockResolvedValue(Response.json(unavailable))
    vi.stubGlobal("fetch", request)
    const controller = new AbortController()
    await fetchHub("live", "RE-03 & Zeta", controller.signal)
    const [url, options] = request.mock.calls[0]
    expect(new URL(url, "https://hub.example").searchParams.get("search")).toBe(
      "RE-03 & Zeta"
    )
    expect(options.signal).toBe(controller.signal)
    expect(options.credentials).toBe("omit")
    expect(hubQueryOptions("live", "RE-03").queryKey).not.toEqual(
      hubQueryOptions("fixture", "RE-03").queryKey
    )
    expect(hubQueryOptions("live", "RE-03").queryKey).not.toEqual(
      hubQueryOptions("live", "EX-02").queryKey
    )
  })
  it("rejects incompatible schemas before rendering", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json({ ...unavailable, schema_version: "2.0" })
        )
    )
    await expect(fetchHub("live")).rejects.toThrow("contrato")
    expect(
      hubSchema.safeParse({ ...unavailable, generated_at: "unknown" }).success
    ).toBe(false)
  })
  it("does not turn invalid modes into local examples", () => {
    expect(hubSearchSchema.parse({}).mode).toBe("fixture")
    expect(hubSearchSchema.safeParse({ mode: "production" }).success).toBe(
      false
    )
    expect(
      hubSearchSchema.safeParse({ mode: "live", q: "x".repeat(101) }).success
    ).toBe(false)
  })
})
