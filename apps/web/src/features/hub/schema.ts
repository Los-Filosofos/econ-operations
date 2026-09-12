import { z } from "zod"

export const dataModeSchema = z.enum(["fixture", "live"])
export const hubSearchSchema = z.object({
  mode: dataModeSchema.default("fixture"),
  q: z.string().trim().max(100).default(""),
})
const sourceId = z.enum(["nexus", "startrack"])
const nullableText = z.string().nullable()
const instant = z.iso.datetime({ offset: true })

export const provenanceSchema = z.object({
  source: sourceId,
  source_id: z.string(),
  environment: z.enum(["local", "sandbox"]),
  observed_at: instant,
  is_synthetic: z.boolean(),
})

export const sourceSchema = z.object({
  id: sourceId,
  label: z.string(),
  status: z.enum([
    "fixture",
    "connected",
    "partial",
    "not_configured",
    "disabled",
    "error",
  ]),
  environment: z.enum(["local", "sandbox"]),
  observed_at: instant.nullable(),
  message: z.string(),
})

export const equipmentSchema = z.object({
  id: z.string(),
  code: nullableText,
  asset_number: nullableText,
  name: z.string(),
  company: nullableText,
  project_id: nullableText,
  project_name: nullableText,
  driver: nullableText,
  machinery_status: z.string(),
  maintenance_failure_id: nullableText,
  maintenance_status: nullableText,
  maintenance_is_stopped: z.boolean().nullable(),
  request_ids: z.array(z.string()),
  transfers: z.array(
    z.object({
      id: z.string(),
      code: z.string(),
      status: z.string(),
      request_id: nullableText,
      destination_project_id: nullableText,
      destination_project_name: nullableText,
      driver: nullableText,
      provenance: provenanceSchema,
    })
  ),
  location: z
    .object({
      label: z.string(),
      observed_at: instant,
      provenance: provenanceSchema,
    })
    .nullable(),
  relation_status: z.enum(["confirmed", "candidate", "unlinked"]),
  relation_note: z.string(),
  provenance: provenanceSchema,
})

export const alertSchema = z.object({
  id: z.string(),
  code: z.string(),
  severity: z.enum(["info", "warning", "critical"]),
  title: z.string(),
  description: z.string(),
  owner: z.string(),
  equipment_id: nullableText,
  request_id: nullableText,
  evidence: z.array(z.string()),
})

export const hubSchema = z.object({
  schema_version: z.literal("1.0"),
  mode: dataModeSchema,
  generated_at: instant,
  data_as_of: instant.nullable(),
  sources: z.array(sourceSchema),
  scope: z.object({
    search: z.string(),
    bounded: z.boolean(),
    equipment_total: z.number().int().nonnegative().nullable(),
    requests_total: z.number().int().nonnegative().nullable(),
    equipment_returned: z.number().int().nonnegative(),
    requests_returned: z.number().int().nonnegative(),
    complete: z.boolean(),
    description: z.string(),
  }),
  summary: z.object({
    equipment_count: z.number().int().nonnegative().nullable(),
    administratively_available: z.number().int().nonnegative().nullable(),
    active_failures: z.number().int().nonnegative().nullable(),
    stopped_equipment: z.number().int().nonnegative().nullable(),
    unlinked_equipment: z.number().int().nonnegative().nullable(),
    alerts_count: z.number().int().nonnegative().nullable(),
  }),
  equipment: z.array(equipmentSchema),
  requests: z.array(
    z.object({
      id: z.string(),
      project_id: nullableText,
      project_name: nullableText,
      machinery_id: nullableText,
      status: z.string(),
      starts_on: nullableText,
      provenance: provenanceSchema,
    })
  ),
  alerts: z.array(alertSchema),
})

export type DataMode = z.infer<typeof dataModeSchema>
export type Provenance = z.infer<typeof provenanceSchema>
export type Equipment = z.infer<typeof equipmentSchema>
export type HubAlert = z.infer<typeof alertSchema>
export type Source = z.infer<typeof sourceSchema>
export type Hub = z.infer<typeof hubSchema>
