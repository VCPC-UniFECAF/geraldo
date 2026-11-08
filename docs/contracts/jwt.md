# JWT

Assinado com **HS256**. O segredo vem da variável de ambiente `GERALDO_JWT_SECRET` (nunca do repositório).

| Claim | Tipo | Descrição |
|---|---|---|
| `sub` | string | id do usuário |
| `role` | string | `medico`, `enfermeiro`, `farmaceutico`, `admin` ou `robo` |
| `exp` | número | expiração (Unix); padrão de 60 minutos |
| `jti` | string | id único do token |

Regras de validação (backend):
- aceitar **somente** `HS256` (rejeitar `none` e qualquer outro algoritmo);
- exigir `exp`, `sub`, `role` e `jti`;
- token ausente, inválido ou expirado → `401`; papel sem permissão → `403`.

Cabeçalho: `Authorization: Bearer <token>`.
