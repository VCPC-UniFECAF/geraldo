import { CircleCheck, Siren } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Role } from "../api/types";
import { podeAcionarEstop } from "../domain/operacoes";
import { Button } from "./Button";

interface Props {
  role: Role;
  ativo: boolean;
  ocupado: boolean;
  onAlternar: (ativar: boolean) => void;
}

// Vermelho só ao acionar a parada (DS §2). Acionar é de um toque (atrasar uma parada é pior que acionar sem querer);
// desligar religa o robô, então pede confirmação. O foco inicial fica em Cancelar: Enter sem querer não religa nada.
export function BotaoEmergencia({ role, ativo, ocupado, onAlternar }: Props) {
  const [confirmando, setConfirmando] = useState(false);
  const botaoDesligar = useRef<HTMLButtonElement>(null);
  const botaoCancelar = useRef<HTMLButtonElement>(null);
  const abriu = useRef(false);

  useEffect(() => {
    if (confirmando) {
      abriu.current = true;
      botaoCancelar.current?.focus();
    } else if (abriu.current) {
      abriu.current = false;
      botaoDesligar.current?.focus();
    }
  }, [confirmando]);

  // Se a parada some por fora com o diálogo aberto, ele fecha de vez (não reabre quando voltar).
  useEffect(() => {
    if (!ativo) setConfirmando(false);
  }, [ativo]);

  if (!podeAcionarEstop(role)) return null;
  if (ativo && confirmando) {
    return (
      <div
        role="alertdialog"
        aria-label="Confirmar o desligamento da parada de emergência"
        className="grid gap-3 rounded-card border border-neutro-200 bg-branco p-4"
        onKeyDown={(e) => e.key === "Escape" && setConfirmando(false)}
      >
        <p className="text-sm">Desligar a parada de emergência religa o robô. Confirmar?</p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="primario"
            disabled={ocupado}
            onClick={() => {
              setConfirmando(false);
              onAlternar(false);
            }}
          >
            Confirmar
          </Button>
          <Button ref={botaoCancelar} variant="fantasma" onClick={() => setConfirmando(false)}>
            Cancelar
          </Button>
        </div>
      </div>
    );
  }
  if (ativo) {
    return (
      <Button ref={botaoDesligar} variant="secundario" size="lg" className="w-full md:w-auto" disabled={ocupado} onClick={() => setConfirmando(true)}>
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
