import { createFileRoute } from "@tanstack/react-router"
import { SourcesPage } from "@/features/hub/pages/sources"

export const Route = createFileRoute("/fuentes")({ component: SourcesPage })
