import {
  Bell,
  Boxes,
  Cable,
  ClipboardList,
  LayoutDashboard,
  Route,
} from "lucide-react"

export const navigation = [
  { to: "/", title: "Vista general", icon: LayoutDashboard, index: "01" },
  { to: "/maquinaria", title: "Maquinaria", icon: Boxes, index: "02" },
  {
    to: "/solicitudes",
    title: "Solicitudes",
    icon: ClipboardList,
    index: "03",
  },
  { to: "/traslados", title: "Traslados", icon: Route, index: "04" },
  { to: "/alertas", title: "Centro de atención", icon: Bell, index: "05" },
  { to: "/fuentes", title: "Fuentes y trazabilidad", icon: Cable, index: "06" },
] as const

export function currentSection(pathname: string) {
  return (
    navigation.find(({ to }) =>
      to === "/" ? pathname === "/" : pathname.startsWith(to)
    ) ?? navigation[0]
  )
}
