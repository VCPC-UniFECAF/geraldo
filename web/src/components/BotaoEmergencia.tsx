import { CircleCheck, Siren } from "lucide-react";
import type { Role } from "../api/types";
import { podeAcionarEstop } from "../domain/operacoes";
import { Button } from "./Button";

interface Props {
  role: Role;
  ativo: boolean;
  ocupado: boolean;
  onAlternar: (ativar: boolean) => void;
}

// Vermelho só ao acionar a parada (DS §2). Desligar é uma ação calma: variante secundária.
export function BotaoEmergencia({ role, ativo, ocupado, onAlternar }: Props) {
  if (!podeAcionarEstop(role)) return null;
  if (ativo) {
    return (
      <Button variant="secundario" size="lg" className="w-full md:w-auto" disabled={ocupado} onClick={() => onAlternar(false)}>
        <CircleCheck size={20} aria-hidden="true" />
        Desligar parada de emergência
      </Button>
    );
  }
  return (
    <Button variant="perigo" size="lg" className="w-full md:w-auto" disabled={ocupado} onClick={() => onAlternar(true)}>
      <Siren size={20} aria-hidden="true" />
      Parada de emergência
    </Button>
  );
}
