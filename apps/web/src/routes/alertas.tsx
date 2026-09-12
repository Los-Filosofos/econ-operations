import { createFileRoute } from "@tanstack/react-router"
import { AlertsPage } from "@/features/hub/pages/alerts"

export const Route = createFileRoute("/alertas")({ component: AlertsPage })
