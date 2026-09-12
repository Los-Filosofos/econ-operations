import { describe, expect, it } from "vitest"
import { selectOperations } from "./selectors"
import type { Equipment, Hub, Provenance } from "./schema"

const provenance: Provenance = {
  source: "nexus",
  source_id: "synthetic-equipment",
  environment: "local",
  observed_at: "2026-09-12T18:00:00Z",
  is_synthetic: true,
}
const equipment: Equipment = {
  id: "synthetic-equipment",
  code: "SYN-01",
  asset_number: null,
  name: "Synthetic equipment",
  company: null,
  project_id: null,
  project_name: null,
  driver: null,
  machinery_status: "Ocupada",
  maintenance_failure_id: null,
  maintenance_status: null,
  maintenance_is_stopped: null,
  request_ids: ["request-a", "request-b"],
  location: null,
  relation_status: "confirmed",
  relation_note: "Synthetic test",
  provenance,
  transfers: ["trip-a", "trip-a-return"].map((id) => ({
    id,
    code: id,
    status: "Custom provider status",
    request_id: "request-a",
    destination_project_id: null,
    destination_project_name: null,
    driver: null,
    provenance: { ...provenance, source: "startrack", source_id: id },
  })),
}
function request(
  id: string,
  machinery_id: string | null
): Hub["requests"][number] {
  return {
    id,
    machinery_id,
    project_id: null,
    project_name: "Same project name",
    status: "Aprobada",
    starts_on: null,
    provenance: { ...provenance, source_id: id },
  }
}

describe("operation linkage", () => {
  it("keeps multiple trips on their exact request and does not reuse a confirmed equipment link", () => {
    const rows = selectOperations({
      equipment: [equipment],
      requests: [
        request("request-a", equipment.id),
        request("request-b", equipment.id),
      ],
    })
    expect(rows[0].transfers.map(({ id }) => id)).toEqual([
      "trip-a",
      "trip-a-return",
    ])
    expect(rows[1].equipment?.relation_status).toBe("confirmed")
    expect(rows[1].transfers).toEqual([])
  })
  it("preserves unassigned and out-of-scope requests without matching by names", () => {
    const rows = selectOperations({
      equipment: [equipment],
      requests: [
        request("request-a", null),
        request("request-b", "outside-query"),
      ],
    })
    expect(rows).toHaveLength(2)
    expect(
      rows.every(
        ({ equipment: assigned, transfers }) =>
          assigned === undefined && transfers.length === 0
      )
    ).toBe(true)
  })
})
