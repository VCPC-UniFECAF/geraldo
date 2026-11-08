# security/AGENTS.md — pentest e qualidade (dono: Pedro)

Escopo: atacar **somente o ambiente local** (`http://localhost:8000`). Nunca contra hosts externos.

## Ataques demonstráveis (cinco)

1. Requisição falsificada (sem `Authorization`, ou com papel forjado).
2. JWT adulterado, expirado ou com `alg: none`.
3. Escalada de papel (enfermaria pedindo prioridade crítica; outro usuário confirmando o recebimento de uma entrega alheia).
4. Injeção nos campos (SQL, texto malicioso em `item_id`, `dest_id`).
5. Injeção de obstáculo falso na telemetria.

Cada ataque tem: script em `security/attacks/`, teste automatizado que falha antes da mitigação e passa depois, e uma seção no relatório `security/RELATORIO.md` (antes/depois).

Padrões de código: [`docs/padroes-de-projeto.md`](../docs/padroes-de-projeto.md). O `MockRobot` recebe o cliente HTTP e o `sleep` pelo construtor (DIP) e usa os mesmos nomes de método (`login`, `next_task`, `report`) do `BackendClient` do robô real; o robô de mentira e o `fake_backend` obedecem ao contrato do backend verdadeiro (LSP).

## Também é seu

CI em `.github/workflows/`, teste de contrato em `backend/tests/test_contract.py`, robô de mentira em `tools/mock_robot.py` e a coleção de requests em `security/requests/`.
