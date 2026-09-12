import { formatInstant } from "../format"
import type { Provenance } from "../schema"

export function ProvenanceBlock({ provenance }: { provenance: Provenance }) {
  return (
    <dl className="provenance-grid">
      <div>
        <dt>Fuente</dt>
        <dd>
          {provenance.source === "nexus" ? "Prisma / Nexus" : "Startrack"}
        </dd>
      </div>
      <div>
        <dt>Entorno</dt>
        <dd>
          {provenance.environment === "local"
            ? "Local · ejemplo sintético"
            : "Sandbox"}
        </dd>
      </div>
      <div>
        <dt>ID en la fuente</dt>
        <dd className="mono break-all">{provenance.source_id}</dd>
      </div>
      <div>
        <dt>Fecha de lectura</dt>
        <dd>{formatInstant(provenance.observed_at)} · UTC−6</dd>
      </div>
    </dl>
  )
}
