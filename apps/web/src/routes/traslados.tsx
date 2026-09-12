import { createFileRoute } from "@tanstack/react-router"
import { TransfersPage } from "@/features/hub/pages/transfers"

export const Route = createFileRoute("/traslados")({ component: TransfersPage })
