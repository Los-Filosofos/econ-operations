import { createFileRoute } from "@tanstack/react-router"
import { RequestsPage } from "@/features/hub/pages/requests"

export const Route = createFileRoute("/solicitudes")({
  component: RequestsPage,
})
