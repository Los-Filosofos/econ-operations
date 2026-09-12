import { Badge } from "@/components/ui/badge"
import { originalState } from "../format"

export function StatusBadge({
  status,
  stopped = false,
}: {
  status: string | null
  stopped?: boolean
}) {
  return (
    <Badge variant={stopped ? "destructive" : status ? "secondary" : "outline"}>
      {originalState(status)}
    </Badge>
  )
}
