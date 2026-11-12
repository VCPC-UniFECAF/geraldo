# Hospital 3D (maquete) — design

Data: 2026-11-12. Dono: Samuel (`robot/` e `modelos-3d/`). Branch: `feat/robo-hospital-3d`.

## Objetivo

Trocar o hospital de caixas brancas do Gazebo por uma maquete 3D realista: pisos e paredes com materiais, mobiliário (macas, leitos, bancos, balcões, equipamentos) e obstáculos de corredor. A maquete nasce no Blender, é regenerável por script e alimenta o Gazebo sem mudar o comportamento do Nav2 além dos obstáculos fixos de corredor.

## Decisões já tomadas

1. **Destino:** maquete no Blender (`.blend` e renders) **e** o mesmo visual no Gazebo, com colisão simples.
2. **Linguagem visual:** realista neutro (paredes claras, pisos de hospital, inox, cortinas azul-hospitalar). Sem teto na maquete e no Gazebo, para a câmera aérea funcionar.
3. **Obstáculos:** uma maca spawnável em tempo de execução (cenário "maca bloqueando" da demo) mais obstáculos fixos de corredor com colisão, sem fechar nenhuma rota. O restante do mobiliário é só visual.
4. **Abordagem:** script em Blender lendo a mesma fonte de verdade (`hospital.yaml`); sem modelar à mão e sem baixar modelos de terceiros.
5. **Cores:** a regra 6 do `AGENTS.md` vale para a interface; as cores da maquete ficam num único dicionário `PALETA` em `modelos-3d/build_hospital.py`.

## Arquitetura

```
hospital.yaml (+ furniture, obstacles, stretcher)
   └─► gen_hospital.py ─► hospital.sdf, mapa do Nav2, waypoints, locais.json, hospital_layout.json, maca.sdf
                              └─► build_hospital.py (Blender) ─► hospital.blend + renders
                                       └─► export_hospital_mesh.py ─► OBJ/MTL em geraldo_description/meshes/hospital/
```

O Python do Blender 5.2 **não tem PyYAML** (numpy tem). Por isso o `gen_hospital.py` escreve `robot/hospital/hospital_layout.json` (paredes, vãos de porta, retângulos das salas com `kind`, mobiliário, obstáculos, pose da maca) e o `build_hospital.py` lê só esse JSON.

### `hospital.yaml` (versão 2)

Novos blocos, todos opcionais para não quebrar quem lê a v1:

```yaml
furniture:            # só visual
  - { room: enfermaria214, type: leito, xy: [26, 4], yaw: 90 }
obstacles:            # colisão em caixa; entram no mapa do Nav2
  - { type: cadeira_rodas, xy: [20, 26.5], yaw: 0, size: [0.7, 0.7] }
stretcher: { xy: [23, 29], yaw: 0, size: [2.0, 0.8] }   # pose de spawn da maca
```

`type` precisa existir no registro de peças do `build_hospital.py`; tipo desconhecido falha com mensagem em português que diz o tipo e os válidos.

### Peças e arquivos

| Arquivo | Papel |
|---|---|
| `modelos-3d/build_hospital.py` | Registro `tipo → função` (Factory, sem `if/elif`), `PALETA`, posicionamento a partir do JSON; gera `hospital.blend` e as vistas de render |
| `modelos-3d/hospital.blend`, `modelos-3d/renders/hospital_*.png` | Cena editável e renders de referência (aérea e por zona) |
| `robot/scripts/export_hospital_mesh.py` | Exporta OBJ + MTL: `hospital_estrutura` (piso, paredes, rodapés, portas), `hospital_mobiliario`, `hospital_obstaculos` e `maca` (separada). Mesmas convenções do `export_blender_mesh.py` (Z para cima, metros) |
| `robot/hospital/gen_hospital.py` | SDF com o visual por malha (`package://geraldo_description/meshes/hospital/...`), paredes com colisão invisível em caixa, obstáculos com colisão e entrada no mapa, `maca.sdf` spawnável |
| `robot/hospital/hospital_layout.json` | Gerado; não editar à mão |

### Conteúdo por área (só visual, salvo corredores)

Recepção: balcão, fileiras de bancos, TV, plantas. Consultórios 1 e 2: mesa, cadeiras, maca de exame, armário, pia. Pronto-socorro: 4 macas com cortinas, balcão de triagem, carrinho de emergência. Farmácia: estantes com caixas, balcão, doca da base do robô. Banco de sangue: geladeiras, bancada, poltrona de coleta. Apoio: prateleiras com lençóis, carrinho. Centro cirúrgico: mesa cirúrgica, foco, mesa de instrumentos, pia. UTI: 4 leitos com monitor e bomba de infusão. Enfermarias 214 e 215: 6 leitos cada, mesa de cabeceira, posto de enfermagem. Corredores: bancos encostados, extintores, placas.

Obstáculos fixos com colisão (laterais dos corredores): cadeira de rodas, carrinho de medicação, placa "piso molhado", carrinho de lençóis.

### Materiais

Paredes off-white com rodapé cinza e faixa de proteção; piso vinílico cinza-claro nos corredores, porcelanato branco-gelo nas salas clínicas, madeira clara na recepção; inox escovado nos equipamentos; tecido azul-hospitalar nas cortinas; cruz vermelha e sinalização em cor saturada. Materiais PBR simples (cor, rugosidade, metal), sem texturas de imagem, para o OBJ/MTL levá-los sem perda.

## Regras de posicionamento

- Todo móvel fica dentro do retângulo da sua sala.
- Faixa livre de 1,2 m entre cada porta e o waypoint da sala; nenhum móvel nela nem sobre waypoint (o mobiliário não tem colisão, o robô não pode atravessá-lo visualmente).
- Obstáculos fixos ficam nas laterais dos corredores e não fecham rota: os 10 pontos continuam alcançáveis, e com a maca spawnada ainda existe rota alternativa.
- Orçamento de geometria: uns 500 mil triângulos no total, mobiliário em baixo poliedro.

## Testes

Primeiro o teste, ver falhar, depois implementar.

- `robot/hospital/tests/test_gen_hospital.py` (sem Blender): móveis dentro das salas; faixas porta→waypoint livres; 10 pontos alcançáveis com os obstáculos no mapa; rota alternativa com a maca; SDF referencia só malhas existentes; `hospital_layout.json` coerente com o YAML; tipo desconhecido gera erro claro.
- `robot/scripts/tests/test_hospital_meshes.py` (sem Blender): `.obj` e `.mtl` existem, cabem em 46 × 30 m, usam só materiais da `PALETA`.
- `robot/scripts/tests/test_export_hospital_meshes.py` (com Blender, pulado sem ele): regenera as malhas do `hospital.blend` e compara com as salvas, como o `test_export_meshes.py`.

## Verificação de pronto

- Renders e screenshots do Blender pelo MCP: vista aérea e cada zona.
- `python -m pytest tools robot -q` verde.
- Gazebo carrega o mundo (headless e com tela).
- Varredura dos 10 pontos termina em `TODOS OS PONTOS OK`.
- Maca spawnada em tempo de execução e desvio do Nav2 observado.

## Entrega

Commits pequenos em português; `robot/AGENTS.md` e `modelos-3d/README.md` atualizados; nenhum contrato muda (sem tópico ROS, endpoint ou campo novo); PR da branch `feat/robo-hospital-3d`.

## Fora do escopo

Teto, pessoas e obstáculos em movimento, texturas de imagem, modelos de terceiros (Gazebo Fuel), mudança de contrato.
