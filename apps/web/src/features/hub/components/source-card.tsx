import { ArrowUpRight, BookOpen, Cable, Clock3, Database } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { formatInstant, sourceLabels } from "../format"
import type { Source } from "../schema"

export function SourceCard({ source }: { source: Source }) {
  return (
    <Card>
      <CardHeader>
        <div className="source-card-brand">
          <span className="equipment-symbol">
            {source.id === "nexus" ? (
              <Database className="size-5" />
            ) : (
              <Cable className="size-5" />
            )}
          </span>
          <div>
            <CardTitle>
              {source.id === "nexus" ? "Prisma / Nexus" : "Startrack"}
            </CardTitle>
            <CardDescription>
              {source.id === "nexus"
                ? "Información administrativa"
                : "Traslados y seguimiento"}
            </CardDescription>
          </div>
        </div>
        <CardAction>
          <Badge
            variant={source.status === "error" ? "destructive" : "outline"}
          >
            {sourceLabels[source.status]}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent>
        <p className="source-description">{source.message}</p>
        <div className="source-capabilities">
          {(source.id === "nexus"
            ? ["Maquinaria", "Solicitudes", "Mantenimiento"]
            : ["Tareas", "Motoristas", "Ubicaciones"]
          ).map((item) => (
            <Badge key={item} variant="secondary">
              {item}
            </Badge>
          ))}
        </div>
        <div className="source-links">
          <Button
            size="sm"
            variant="outline"
            render={
              <a
                href={
                  source.id === "nexus"
                    ? "https://econ-key.maic.ai/"
                    : "https://staging.gps.gt/"
                }
                target="_blank"
                rel="noopener noreferrer"
              />
            }
            nativeButton={false}
          >
            Abrir sandbox <ArrowUpRight data-icon="inline-end" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            render={
              <a
                href={
                  source.id === "nexus"
                    ? "https://econ-key.maic.ai/docs/user-manual-ECON.html"
                    : "https://support.gps-platform.com/learn/users/"
                }
                target="_blank"
                rel="noopener noreferrer"
              />
            }
            nativeButton={false}
          >
            <BookOpen data-icon="inline-start" /> Manual de{" "}
            {source.id === "nexus" ? "Nexus" : "Startrack"}
          </Button>
        </div>
      </CardContent>
      <CardFooter className="justify-between gap-3">
        <span className="footnote">
          Entorno: {source.environment === "local" ? "local" : "sandbox"}
        </span>
        <span className="footnote icon-line">
          <Clock3 className="size-3.5" />
          {formatInstant(source.observed_at)}
        </span>
      </CardFooter>
    </Card>
  )
}
