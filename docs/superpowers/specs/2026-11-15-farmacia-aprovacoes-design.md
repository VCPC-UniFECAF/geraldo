# Aba Farmácia: estoque só para farmacêutico e admin, aprovação e recusa de pedidos críticos

Data: 15/11/2026. Aprovado pelo Samuel no chat (brainstorming de 15/11).

## Problema

- Todas as abas da web (Solicitar, Minhas entregas, Estoque, Painel) aparecem para qualquer conta; o estoque de todos os locais e o histórico de movimentações não são assunto de médico nem de enfermeiro.
- Pedido de prioridade `critica` nasce em `PENDENTE_APROVACAO` e só o farmacêutico aprova (`POST /deliveries/{id}/approve`), mas a web não tem tela para isso: na demo, um pedido crítico fica parado.
- Não existe recusa: `POST /deliveries/{id}/cancel` é só do solicitante ou do admin.

## Decisões

1. A aba **Estoque** vira **Farmácia** e só aparece para `farmaceutico` e `admin`. Médico e enfermeiro ficam com Solicitar, Minhas entregas e Painel. (`GET /stock` continua aberto a qualquer usuário logado: o formulário de Solicitar usa.)
2. A aba Farmácia tem duas seções: **Aprovações** (no topo) e **Estoque** (saldos e histórico, como hoje).
3. **Aprovações** lista as entregas em `PENDENTE_APROVACAO` (o `GET /deliveries` já devolve todas para `farmaceutico` e `admin`), com número, itens, origem → destino e há quanto tempo foi pedida; recarrega a cada 5 s, como Minhas entregas.
   - `farmaceutico`: botão **Aprovar** (primário) e **Recusar** (abre um campo de motivo, 3 a 200 caracteres, e pede confirmação).
   - `admin`: a mesma lista, sem botões, com a nota "Só o farmacêutico aprova ou recusa pedidos críticos."
4. **Recusa** por endpoint novo `POST /deliveries/{id}/reject` (contrato primeiro):
   - só `farmaceutico`; corpo `{"reason": string}` (3 a 200 caracteres, sem espaços nas pontas);
   - `200` com a `Delivery`; `401`; `403` para outro papel; `404` se não existe; `409` se não está em `PENDENTE_APROVACAO`; `422` com motivo inválido;
   - status final `CANCELADA` (o enum **não** muda), estorna a reserva com `ESTORNO` como o cancelamento, avisa os observers;
   - a `Delivery` ganha o campo opcional `cancel_reason: string | null` (preenchido só na recusa). O `RobotTask` herda o campo opcional; o dispatcher ignora campos que não usa.
5. No backend, a recusa é um Command próprio (`RejectDelivery`, no molde do `ApproveDelivery`); router fino com `require_roles(Role.farmaceutico)`. Sem `if/elif` por papel no `/cancel`.
6. Em **Minhas entregas**, uma entrega recusada mostra "Recusada pela farmácia: <motivo>".
7. Design system: texto em português, sem hex solto, vermelho só para erro (recusar não é vermelho), alvo de 44 px, um botão primário por linha.

## Entrega

- **PR A (contrato):** `docs/contracts/openapi.yaml` (operação nova e `cancel_reason`) e a lista de operações de `tools/tests/test_contracts.py`, com aviso a Erik, Vieira e Pedro.
- **PR B (código), empilhado no A:** esta spec, backend e web. O teste de contrato do backend exige exatamente as operações do contrato, então **A e B são mergeados em sequência** (A, depois B), para a `main` não ficar vermelha entre os dois.

## Verificação

- Suítes: backend, web (testes e build) e `python3 -m pytest tools robot -q`; TDD com RED registrado.
- No navegador com o backend real (e o robô no Gazebo): medico1 pede um crítico; farmaceutico1 vê na Farmácia e aprova; o robô sai; um segundo crítico é recusado com motivo; medico1 vê o motivo em Minhas entregas; o estoque mostra o `ESTORNO`; medico1 não vê a aba Farmácia; admin vê a fila sem botões.

## Fora do escopo

Status novo `RECUSADA`; recusa de prioridades `media` e `rotina`; notificação ao solicitante fora da web.
