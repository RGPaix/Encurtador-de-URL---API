Atividade Prática: Observabilidade em uma API Python/Flask
Cenário:
Sua equipe decidiu adotar Python e Flask para um novo microsserviço: um "Encurtador de URLs". O serviço será simples, mas espera-se que
ele receba um alto volume de tráfego de redirecionamento. Por isso, implementar um sistema de observabilidade desde o primeiro dia é um
requisito crítico.
Sua missão é criar este serviço em Flask e construir um "Painel de Controle" (dashboard) em tempo real com Prometheus e Grafana para
monitorar a saúde, a performance e as métricas de negócio (links criados e redirecionados) da API.
Objetivos da Atividade:
1. Desenvolver uma API RESTful simples usando Python e Flask.
2. Instrumentar a aplicação Flask para expor métricas no formato Prometheus usando a biblioteca prometheus-flask-exporter .
3. Configurar um ambiente local de monitoramento com Prometheus e Grafana usando Docker Compose.
4. Conectar o Prometheus para coletar métricas da API Flask.
5. Construir um dashboard no Grafana para visualizar métricas de performance (latência, throughput) e métricas de negócio customizadas.
Etapa 1: Instrumentando a Aplicação (O Alvo)
Nesta etapa, você irá criar a API Flask e adicionar as bibliotecas necessárias para que ela comece a expor métricas.
Instruções:
1. Prepare o Ambiente Python:
Crie uma nova pasta para o projeto (ex: encurtador-flask ).
É altamente recomendado criar um ambiente virtual:
python -m venv venv
source venv/bin/activate # No Windows: venv\Scripts\activate
Crie um arquivo chamado requirements.txt e adicione as dependências:
flask
prometheus-flask-exporter
Instale as dependências: pip install -r requirements.txt
2. Crie a Aplicação Flask ( app.py ):
Crie um arquivo app.py na raiz do projeto. Este será nosso serviço. Para simplificar, usaremos um dicionário em memória como
"banco de dados".
Cole o seguinte código:
import random
import string
from flask import Flask, request, redirect, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter # Importa o Counter
app = Flask(__name__)
# 1. INSTRUMENTAÇÃO:
# Registra a aplicação Flask no exportador de métricas.
# Isso automaticamente cria o endpoint /metrics e rastreia
# requisições (latência, total, erros).
metrics = PrometheusMetrics(app)
# 2. MÉTRICAS CUSTOMIZADAS:
# Criamos contadores específicos para nosso negócio.
links_criados_total = Counter('links_criados_total', 'Total de novos links encurtados criados.')
redirecionamentos_total = Counter('redirecionamentos_total', 'Total de links redirecionados.')
# Nosso "banco de dados" em memória
url_db = {}
def gerar_codigo_curto(tamanho=6):
"""Gera um código aleatório de letras e números."""
caracteres = string.ascii_letters + string.digits
return ''.join(random.choice(caracteres) for _ in range(tamanho))
@app.route('/encurtar', methods=['POST'])
def encurtar_url():
"""Cria um novo link curto."""
dados = request.get_json()
if not dados or 'url_longa' not in dados:
return jsonify({"erro": "URL longa não fornecida"}), 400
url_longa = dados['url_longa']
codigo_curto = gerar_codigo_curto()
# Garante que o código não exista (raro, mas possível)
while codigo_curto in url_db:
codigo_curto = gerar_codigo_curto()
url_db[codigo_curto] = url_longa
# INCREMENTA A MÉTRICA DE NEGÓCIO
links_criados_total.inc()
return jsonify({
"url_longa": url_longa,
"url_curta": f"{request.host_url}{codigo_curto}"
}), 201
@app.route('/<string:codigo_curto>', methods=['GET'])
def redirecionar(codigo_curto):
"""Redireciona para a URL longa."""
url_longa = url_db.get(codigo_curto)
if url_longa:
# INCREMENTA A MÉTRICA DE NEGÓCIO
redirecionamentos_total.inc()
return redirect(url_longa, code=302)
else:
return jsonify({"erro": "URL curta não encontrada"}), 404
@app.route('/api/links', methods=['GET'])
def listar_links():
"""Endpoint auxiliar para ver o 'banco de dados'."""
return jsonify(url_db)
# O endpoint /metrics é criado automaticamente pelo 'PrometheusMetrics(app)'
if __name__ == '__main__':
app.run(debug=True, host='0.0.0.0', port=5000)
3. Validação (Checkpoint):
Inicie sua aplicação Flask: flask run --host=0.0.0.0 --port=5000
Em outro terminal, teste a API:
curl -X POST http://localhost:5000/encurtar -H "Content-Type: application/json" -d '{"url_longa":"https://www.google.com"}'
(Pegue o código curto retornado e acesse http://localhost:5000/<codigo_curto> no seu navegador. Você deve ser
redirecionado para o Google).
Verifique as métricas: Acesse http://localhost:5000/metrics . Você deve ver uma longa lista de métricas, incluindo as métricas
padrão do Flask ( flask_http_... ) e as nossas métricas customizadas ( links_criados_total e redirecionamentos_total ).
Etapa 2: Configurando o Ambiente de Coleta
Esta etapa é quase idêntica à da aula anterior, mas vamos ajustar o prometheus.yml para "raspar" (scrape) as métricas da nossa nova
aplicação Flask.
Instruções:
1. Crie o Arquivo de Configuração do Prometheus:
Na raiz do seu projeto, crie um arquivo chamado prometheus.yml .
Atenção às mudanças: O job_name é novo, o metrics_path mudou para /metrics (padrão do Flask) e a porta do targets mudou
para 5000 (padrão do Flask).
global:
scrape_interval: 15s
scrape_configs:
- job_name: 'flask-url-shortener'
metrics_path: '/metrics' # O endpoint padrão do prometheus-flask-exporter
static_configs:
- targets: ['host.docker.internal:5000'] # Aponta para a porta 5000
2. Crie o Arquivo Docker Compose:
Na raiz do seu projeto, crie um arquivo docker-compose.yml (este arquivo é idêntico ao da aula anterior, pois apenas sobe o
Prometheus e o Grafana).
version: '3.8'
services:
prometheus:
image: prom/prometheus:latest
container_name: prometheus
ports:
- "9090:9090"
volumes:
- ./prometheus.yml:/etc/prometheus/prometheus.yml
grafana:
image: grafana/grafana-oss:latest
container_name: grafana
ports:
- "3000:3000"
depends_on:
- prometheus
3. Inicie o Ambiente de Monitoramento:
No seu terminal (com a aplicação Flask ainda rodando em outro terminal), execute: docker-compose up -d
4. Validação (Checkpoint):
Acesse http://localhost:9090 (Prometheus). Vá para "Status" > "Targets". Você deve ver seu job flask-url-shortener com o
estado "UP" (verde).
Etapa 3: Criando o Dashboard de Observabilidade
Vamos construir nosso painel de controle no Grafana, agora usando as métricas expostas pela biblioteca Python.
Instruções:
1. Configure a Fonte de Dados no Grafana:
Acesse http://localhost:3000 (login: admin / admin ).
No menu (ícone de engrenagem), vá para "Data sources".
Adicione uma nova fonte de dados Prometheus.
Na URL, digite http://prometheus:9090 .
Clique em "Save & test".
2. Crie o Dashboard:
No menu (ícone de +), clique em "New Dashboard" e "Add visualization".
Crie os seguintes painéis:
Painel 1: Métricas de Negócio - Links Criados (Total)
Título: Total de Links Criados
Query (PromQL): links_criados_total
Visualização: Stat (Estatística).
Validação: Use o Postman para criar novos links e veja este número aumentar.
Painel 2: Métricas de Negócio - Redirecionamentos por Minuto
Título: Redirecionamentos por Minuto
Query (PromQL): rate(redirecionamentos_total[1m]) * 60
Visualização: Time series (gráfico de tempo).
Validação: Acesse seus links curtos no navegador várias vezes e veja este gráfico subir.
Painel 3: Performance da API - Requisições por Segundo (Throughput)
Título: Requisições por Segundo (Todos Endpoints)
Query (PromQL): rate(flask_http_requests_total[1m])
Visualização: Time series.
Painel 4: Performance da API - Latência (P95)
Título: Latência P95 (95% das requisições são mais rápidas que...)
Query (PromQL): histogram_quantile(0.95, sum(rate(flask_http_requests_latency_seconds_bucket[1m])) by (le))
Visualização: Time series.
Painel 5: Análise de Erros - Erros por Status (Ex: 404)
Título: Erros 404 por Minuto
Query (PromQL): rate(flask_http_requests_total{status="404"}[1m])
Visualização: Time series.
Validação: Tente acessar um link curto que não existe (ex: http://localhost:5000/naoexiste ) e veja este gráfico registrar o erro.
3. Salve o Dashboard: Dê um nome ao seu dashboard (ex: "Encurtador de URL - API") e salve-o.
Critérios de Entrega
Para concluir a atividade, você deve entregar:
1. O link para o seu repositório no GitHub, contendo:
O arquivo app.py com a API Flask e as métricas customizadas.
O arquivo requirements.txt .
O arquivo prometheus.yml configurado para a porta 5000 e o path /metrics .
O arquivo docker-compose.yml .
2. Um screenshot do seu dashboard final do Grafana, mostrando todos os painéis funcionais (Pelo menos os 5 painéis da Etapa 3)
