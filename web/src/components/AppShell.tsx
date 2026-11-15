import { Bot, PackageCheck, PackagePlus, Pill, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { Role } from "../api/types";
import { podeVerFarmacia } from "../domain/operacoes";

export type PageId = "solicitar" | "entregas" | "farmacia" | "painel";

interface Item {
  id: PageId;
  label: string;
  Icon: LucideIcon;
  visivelPara: (role: Role) => boolean;
}

const PARA_TODOS = () => true;

const ITEMS: Item[] = [
  { id: "solicitar", label: "Solicitar", Icon: PackagePlus, visivelPara: PARA_TODOS },
  { id: "entregas", label: "Minhas entregas", Icon: PackageCheck, visivelPara: PARA_TODOS },
  { id: "farmacia", label: "Farmácia", Icon: Pill, visivelPara: podeVerFarmacia },
  { id: "painel", label: "Painel", Icon: Bot, visivelPara: PARA_TODOS },
];

interface Props {
  active: PageId;
  role: Role;
  onNavigate: (page: PageId) => void;
  children: ReactNode;
}

function NavButton({ id, label, Icon, active, onNavigate, vertical }: Item & Pick<Props, "active" | "onNavigate"> & { vertical: boolean }) {
  const isActive = active === id;
  const color = isActive ? "text-azul-600" : "text-neutro-400";
  return (
    <button
      type="button"
      aria-label={label}
      aria-current={isActive ? "page" : undefined}
      onClick={() => onNavigate(id)}
      className={`flex min-h-controle min-w-controle items-center justify-center rounded-controle ${color} ${vertical ? "w-12" : "flex-1 flex-col gap-0.5 text-xs"} ${isActive ? "bg-azul-50" : ""}`}
    >
      <Icon size={24} aria-hidden="true" />
      {!vertical && <span aria-hidden="true">{label}</span>}
    </button>
  );
}

export function AppShell({ active, role, onNavigate, children }: Props) {
  const itens = ITEMS.filter((item) => item.visivelPara(role));
  return (
    <div className="min-h-screen md:pl-[72px]">
      <nav className="hidden border-r border-neutro-100 bg-branco md:fixed md:inset-y-0 md:left-0 md:flex md:w-[72px] md:flex-col md:items-center md:gap-2 md:pt-6">
        {itens.map((item) => (
          <NavButton key={item.id} {...item} active={active} onNavigate={onNavigate} vertical />
        ))}
      </nav>
      <main className="mx-auto max-w-[1280px] px-4 pb-24 pt-4 md:px-6 md:pb-6">{children}</main>
      <nav className="fixed inset-x-0 bottom-0 flex border-t border-neutro-100 bg-branco px-2 py-1 md:hidden">
        {itens.map((item) => (
          <NavButton key={item.id} {...item} active={active} onNavigate={onNavigate} vertical={false} />
        ))}
      </nav>
    </div>
  );
}
