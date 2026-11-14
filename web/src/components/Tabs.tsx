import type { KeyboardEvent } from "react";

export interface Aba {
  id: string;
  rotulo: string;
}

interface Props {
  abas: Aba[];
  ativa: string;
  onChange: (id: string) => void;
  rotulo: string;
}

// Abas de texto com sublinhado azul-500 de 2 px na ativa (DS §10).
// Padrão ARIA de abas: ids "aba-<id>" / "painel-<id>", tabindex móvel e setas, Home e End.
export function Tabs({ abas, ativa, onChange, rotulo }: Props) {
  function aoTeclar(e: KeyboardEvent<HTMLDivElement>) {
    const atual = abas.findIndex((a) => a.id === ativa);
    const destino = {
      ArrowRight: (atual + 1) % abas.length,
      ArrowLeft: (atual - 1 + abas.length) % abas.length,
      Home: 0,
      End: abas.length - 1,
    }[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    onChange(abas[destino].id);
    document.getElementById(`aba-${abas[destino].id}`)?.focus();
  }

  return (
    <div role="tablist" aria-label={rotulo} onKeyDown={aoTeclar} className="flex gap-4 border-b border-neutro-100">
      {abas.map((aba) => {
        const selecionada = aba.id === ativa;
        return (
          <button
            key={aba.id}
            type="button"
            role="tab"
            id={`aba-${aba.id}`}
            aria-controls={`painel-${aba.id}`}
            tabIndex={selecionada ? 0 : -1}
            aria-selected={selecionada}
            onClick={() => onChange(aba.id)}
            className={`min-h-controle border-b-2 px-1 text-sm font-semibold ${
              selecionada ? "border-azul-500 text-azul-600" : "border-transparent text-neutro-500"
            }`}
          >
            {aba.rotulo}
          </button>
        );
      })}
    </div>
  );
}
