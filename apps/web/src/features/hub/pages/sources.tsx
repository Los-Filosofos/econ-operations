import { Database, Link2, ShieldCheck } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { HubBoundary, PageHeading, SourceCard } from "../components"
import { formatInstant } from "../format"

export function SourcesPage() {
  return (
    <>
      <PageHeading
        eyebrow="CALIDAD DE LA INFORMACIÓN"
        title="Fuentes y trazabilidad"
        description="Conoce de dónde provienen los datos y qué se pudo consultar."
      />
      <HubBoundary>
        {(hub) => (
          <>
            <div className="source-grid">
              {hub.sources.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </div>
            <div className="source-grid">
              <Card>
                <CardHeader>
                  <CardTitle>Alcance de esta consulta</CardTitle>
                  <CardDescription>{hub.scope.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <dl className="detail-grid">
                    <div>
                      <dt>Origen seleccionado</dt>
                      <dd>
                        {hub.mode === "fixture"
                          ? "Ejemplos sintéticos locales"
                          : "Conexión en vivo al sandbox"}
                      </dd>
                    </div>
                    <div>
                      <dt>Lectura</dt>
                      <dd>
                        {hub.scope.complete
                          ? "Completa para este alcance"
                          : "Parcial o no disponible"}
                      </dd>
                    </div>
                    <div>
                      <dt>Equipos recibidos</dt>
                      <dd>
                        {hub.scope.equipment_returned} de{" "}
                        {hub.scope.equipment_total ?? "total no confirmado"}
                      </dd>
                    </div>
                    <div>
                      <dt>Solicitudes recibidas</dt>
                      <dd>
                        {hub.scope.requests_returned} de{" "}
                        {hub.scope.requests_total ?? "total no confirmado"}
                      </dd>
                    </div>
                    <div>
                      <dt>Fecha de los datos</dt>
                      <dd>{formatInstant(hub.data_as_of)}</dd>
                    </div>
                    <div>
                      <dt>Fecha de consulta al hub</dt>
                      <dd>{formatInstant(hub.generated_at)}</dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Reglas de confianza</CardTitle>
                  <CardDescription>
                    Lo que acompaña cada dato en el hub.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="trust-list">
                    <div>
                      <Database className="size-5" />
                      <p>
                        <strong>El origen permanece visible</strong>Fuente, ID,
                        entorno y fecha se conservan en cada registro.
                      </p>
                    </div>
                    <div>
                      <Link2 className="size-5" />
                      <p>
                        <strong>Los vínculos necesitan evidencia</strong>Un
                        nombre coincidente o una ubicación no confirman una
                        relación.
                      </p>
                    </div>
                    <div>
                      <ShieldCheck className="size-5" />
                      <p>
                        <strong>Los faltantes se muestran como tales</strong>Una
                        fuente no disponible no se sustituye con ejemplos
                        locales.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </HubBoundary>
    </>
  )
}
