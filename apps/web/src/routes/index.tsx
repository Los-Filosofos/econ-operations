import { createFileRoute } from "@tanstack/react-router"
import { OverviewPage } from "@/features/hub/pages/overview"

export const Route = createFileRoute("/")({ component: OverviewPage })
