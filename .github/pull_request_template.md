## O que mudou

## Como foi testado

## Padrões de projeto (`docs/padroes-de-projeto.md`)

- [ ] Cada classe nova tem uma responsabilidade que cabe em uma frase sem "e".
- [ ] Dependências entram pelo construtor (nada de `Session()`, `requests` ou `now()` dentro da regra).
- [ ] Não há `if/elif` por tipo onde um Strategy ou Factory resolveria.
- [ ] Transformações de dados são funções puras com teste.
- [ ] Tem teste usando um substituto (fake) no lugar da dependência real.

## Contratos

- [ ] Não mexi em `docs/contracts/`, ou avisei o dono da frente afetada.
