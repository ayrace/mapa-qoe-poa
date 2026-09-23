# Mapa QOE POA — GitHub/Streamlit V1

Primeira versão online dedicada ao QOE.

## Conceito
- O mapa não possui filtros: todos os nodes ficam visíveis.
- Cores: vermelho <80; amarelo 80–84,9; verde >=85.
- Região e bairro são usados em rankings, não para esconder pontos do mapa.
- Radar por faixa de QOE e persistência mensal.
- Ranking de nodes por gravidade atual, portas <80 e persistência.
- Força de Trabalho inicia a organização por potencial operacional; os pesos ainda serão equalizados.

## Publicação
Envie os arquivos desta pasta para um repositório GitHub e configure o Streamlit Community Cloud para executar `streamlit_app.py`.

## Base
A V1 leva a base atual em `data/qoe_seed.json` e `data/node_meta.json`, extraída da versão de validação usada no projeto. A atualização automática pelo GitHub será a próxima etapa.
