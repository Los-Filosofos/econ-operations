import { useState, type FormEvent } from "react"
import { useLocation, useNavigate, useSearch } from "@tanstack/react-router"
import { ArrowRight, ChevronRight, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { currentSection } from "./navigation"

function WorkspaceSearch({ initialValue }: { initialValue: string }) {
  const [value, setValue] = useState(initialValue)
  const navigate = useNavigate()
  function submit(event: FormEvent) {
    event.preventDefault()
    void navigate({
      to: ".",
      search: (previous) => ({ ...previous, q: value.trim() }),
    })
  }
  return (
    <form onSubmit={submit} className="workspace-search" role="search">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="hub-search" className="sr-only">
            Buscar equipo o proyecto
          </FieldLabel>
          <InputGroup>
            <InputGroupInput
              id="hub-search"
              placeholder="Buscar equipo o proyecto…"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              maxLength={100}
            />
            <InputGroupAddon>
              <Search />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                type="submit"
                size="icon-xs"
                aria-label="Buscar"
              >
                <ArrowRight />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </FieldGroup>
    </form>
  )
}

export function WorkspaceHeader() {
  const { q } = useSearch({ from: "__root__" })
  const { pathname } = useLocation()
  const section = currentSection(pathname)
  return (
    <header className="workspace-header">
      <div className="header-left">
        <SidebarTrigger aria-label="Abrir o cerrar navegación" />
        <Separator orientation="vertical" className="h-4" />
        <span className="header-breadcrumb">
          Operaciones <ChevronRight className="size-3" />
          <strong>{section.title}</strong>
        </span>
      </div>
      <WorkspaceSearch key={q} initialValue={q} />
      <Badge variant="outline">Solo lectura</Badge>
    </header>
  )
}
