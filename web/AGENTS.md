# web/AGENTS.md — sistema web responsivo (dono: Vieira)

Stack: React + Vite + TypeScript + Tailwind v3, Vitest + Testing Library, MSW para simular a API. Os padrões de projeto da disciplina ficam em `src/domain/` e `src/apresentacao/`; siga o padrão que já existe lá. Guia geral: [`docs/padroes-de-projeto.md`](../docs/padroes-de-projeto.md) (Adapter, Observer, Builder, Strategy e funções puras já estão aplicados; novas telas reaproveitam esses blocos).

## Comandos

```bash
cd web
npm install
npm test -- --run
npm run dev
npm run build
```

## Regras (do design system)

- **Sem hex solto:** só classes do preset (`bg-azul-500`, `text-vermelho-600`, `rounded-card`...) ou `var(--azul-500)`.
- **Vermelho só para:** prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro.
- **Um botão primário por tela.** Status nunca só por cor: sempre cor + ícone ou texto.
- **Mobile-first;** alvo de toque mínimo de 44 px (`min-h-controle`).
- Números com `tabular-nums`. Texto em português, *sentence case*, botão com verbo curto ("Solicitar medicamento"), sem "por favor".
- Ícones: `lucide-react`.

## Telas

| Aba | Página | O que faz |
|---|---|---|
| Solicitar | `SolicitarPage` | Formulário de pedido (Builder) |
| Minhas entregas | `MinhasEntregasPage` | Lista e botão "Confirmar recebimento" (`POST /deliveries/{id}/confirm-receipt`) |
| Estoque | `EstoquePage` | Abas Saldos (`StockLevelBar`, `GET /stock`) e Histórico (`MovementLogRow`, `GET /movements`) |
| Painel | `PainelPage` | `RobotStatusCard`, `TelemetryPanel`, fila e entregas em andamento, alertas e botão de parada de emergência (só `admin` e `farmaceutico`; `POST /robot/estop`) |

O papel vem de `GET /me` logo depois do login (`App.tsx`).

## Dados

Consuma só a API do contrato (`docs/contracts/openapi.yaml`). Enquanto o backend não estiver pronto, use os handlers MSW em `src/api/mocks/`.

- **Modo demo:** `npm run dev:demo` liga o MSW no navegador. Usuários `medico1`, `farmaceutico1` e `admin`, senha `demo`. O robô simulado (`src/api/mocks/robo.ts`) percorre todos os estados com os corpos de `docs/contracts/examples/robot-telemetry.json`.
- **Telemetria ao vivo:** `TelemetriaCliente` (`src/domain/TelemetriaCliente.ts`, Observer) abre `WS /ws/telemetry?token=<JWT>` (o navegador não manda cabeçalho num WebSocket), reconecta com espera de 1 s a 10 s e avisa os observers, com os estados `sessao_expirada` (fechamento 1008) e `desistiu` (10 tentativas sem sucesso); `useTelemetria` liga isso ao React e devolve também `semSinal`. A URL do WebSocket sai de `ApiClient.telemetryStreamUrl()` (mesma base de `VITE_API_URL`, com `http` trocado por `ws`).
- **Sem sinal:** `semSinal(t, agora, limiteMs = 10_000)` (`src/domain/telemetria.ts`) vale para `updated_at` velho, inválido ou de antes de 2000 (o backend responde 1970 até o robô postar). O hook reavalia a cada 1 s; sem sinal, o `PainelPage` trata a telemetria como ausente (cartão "Sem sinal do robô", sem alerta de bateria nem de emergência). A conta compara o relógio do navegador com o `updated_at` do servidor: com os relógios a mais de 10 s de diferença o Painel fica sempre sem sinal.
- **Chegada estimada:** a telemetria não traz a velocidade; `velocidadeDoPerfil(prioridade)` (`src/domain/telemetria.ts`) usa a do perfil da entrega em curso (crítica 1,0, média 0,8, rotina 0,5 m/s, como em `docs/contracts/robot-protocol.md`; sem entrega, o perfil médio) e só aparece quando o estado navega (`A_CAMINHO` ou `VOLTANDO`: `EstadoRoboStrategy.navegando`), porque nos outros a rota é a última planejada. O robô real cruza a uns 0,55 m/s, então a estimativa de `crítica` e `média` é otimista.
- **Atualização sozinha:** `MinhasEntregasPage` recarrega a lista a cada 5 s (`intervaloMs`) e o seletor da `SolicitarPage` recarrega o estoque depois de cada pedido; "Confirmar recebimento" só aparece para quem pediu (`solicitanteId`) ou admin.
- **Build:** os mocks leem `docs/contracts/examples/robot-telemetry.json`, fora de `web/`; um build só com o contexto `web/` precisa do monorepo.
- **Reaproveitar no app instalável:** `ApiClient`/`HttpApiClient`, `TelemetriaCliente`, `lerTelemetria`, `enquadrar` (`src/domain/mapa.ts`), `estadoRoboDe`, `RobotStatusCard` e `BotaoEmergencia`.
- **Testes:** troque o WebSocket por `fabricaDeSockets()` (`src/test/SocketFalso.ts`); toda chamada HTTP nova precisa de handler MSW (`onUnhandledFrame: "error"`).
