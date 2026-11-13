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
export function Tabs({ abas, ativa, onChange, rotulo }: Props) {
  return (
    <div role="tablist" aria-label={rotulo} className="flex gap-4 border-b border-neutro-100">
      {abas.map((aba) => {
        const selecionada = aba.id === ativa;
        return (
          <button
            key={aba.id}
            type="button"
            role="tab"
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
