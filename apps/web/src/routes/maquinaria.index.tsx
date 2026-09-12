import { createFileRoute } from "@tanstack/react-router"
import { EquipmentPage } from "@/features/hub/pages/equipment"
import { z } from "zod"

export const Route = createFileRoute("/maquinaria/")({
  validateSearch: z.object({
    filter: z.enum(["all", "available", "unlinked", "failure"]).default("all"),
  }),
  component: EquipmentPage,
})
