# 🔗 Atividade Prática: Observabilidade em uma API Python/Flask

## 📋 Cenário

Sua equipe decidiu adotar Python e Flask para um novo microsserviço: um **"Encurtador de URLs"**. O serviço será simples, mas espera-se que ele receba um alto volume de tráfego de redirecionamento. Por isso, implementar um sistema de observabilidade desde o primeiro dia é um requisito crítico.

Sua missão é criar este serviço em Flask e construir um "Painel de Controle" (dashboard) em tempo real com Prometheus e Grafana para monitorar a saúde, a performance e as métricas de negócio (links criados e redirecionados) da API.

## 🎯 Objetivos da Atividade

1. Desenvolver uma API RESTful simples usando Python e Flask
2. Instrumentar a aplicação Flask para expor métricas no formato Prometheus usando a biblioteca `prometheus-flask-exporter`
3. Configurar um ambiente local de monitoramento com Prometheus e Grafana usando Docker Compose
4. Conectar o Prometheus para coletar métricas da API Flask
5. Construir um dashboard no Grafana para visualizar métricas de performance (latência, throughput) e métricas de negócio customizadas

---

## 📁 Estrutura do Projeto

```
encurtador-flask/
├── app.py
├── requirements.txt
├── prometheus.yml
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

# 🚀 Etapa 1: Instrumentando a Aplicação

Nesta etapa, você irá criar a API Flask e adicionar as bibliotecas necessárias para que ela comece a expor métricas.

## 1️⃣ Prepare o Ambiente Python

```bash
# Criar pasta do projeto
mkdir encurtador-flask
cd encurtador-flask

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# No Linux/Mac:
source venv/bin/activate

# No Windows:
venv\Scripts\activate
```

## 2️⃣ Criar arquivo requirements.txt

Crie um arquivo chamado `requirements.txt` com as seguintes dependências:

```
flask
prometheus-flask-exporter
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## 3️⃣ Criar a Aplicação Flask (app.py)

Crie um arquivo `app.py` na raiz do projeto com o seguinte código:

```python
import random
import string
from flask import Flask, request, redirect, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter

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
```

## 4️⃣ Validação (Checkpoint)

Inicie sua aplicação Flask:

```bash
python app.py
# ou
flask run --host=0.0.0.0 --port=5000
```

Em outro terminal, teste a API:

```bash
curl -X POST http://localhost:5000/encurtar \
  -H "Content-Type: application/json" \
  -d '{"url_longa":"https://www.google.com"}'
```

**Resposta esperada:**
```json
{
  "url_longa": "https://www.google.com",
  "url_curta": "http://localhost:5000/AbCd12"
}
```

Pegue o código curto retornado e acesse `http://localhost:5000/<codigo_curto>` no navegador. Você deve ser redirecionado para o Google.

**Verifique as métricas:**

Acesse `http://localhost:5000/metrics`. Você deve ver uma longa lista de métricas, incluindo:
- Métricas padrão do Flask (`flask_http_...`)
- Métricas customizadas (`links_criados_total` e `redirecionamentos_total`)

---

# 🐳 Etapa 2: Configurando o Ambiente de Coleta

Esta etapa configura o Prometheus para coletar as métricas da aplicação Flask.

## 1️⃣ Criar arquivo prometheus.yml

Na raiz do seu projeto, crie um arquivo chamado `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'flask-url-shortener'
    metrics_path: '/metrics'  # O endpoint padrão do prometheus-flask-exporter
    static_configs:
      - targets: ['host.docker.internal:5000']  # Aponta para a porta 5000
```

## 2️⃣ Criar arquivo docker-compose.yml

Na raiz do seu projeto, crie um arquivo `docker-compose.yml`:

```yaml
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
```

## 3️⃣ Iniciar o Ambiente de Monitoramento

No seu terminal (com a aplicação Flask ainda rodando em outro terminal), execute:

```bash
docker-compose up -d
```

Verificar se os containers estão rodando:

```bash
docker-compose ps
```

## 4️⃣ Validação (Checkpoint)

Acesse `http://localhost:9090` (Prometheus).

Vá para **"Status" > "Targets"**.

Você deve ver seu job `flask-url-shortener` com o estado **"UP"** (verde).

---

# 📊 Etapa 3: Criando o Dashboard de Observabilidade

Vamos construir nosso painel de controle no Grafana, usando as métricas expostas pela biblioteca Python.

## 1️⃣ Configure a Fonte de Dados no Grafana

1. Acesse `http://localhost:3000` (login: `admin` / senha: `admin`)
2. No menu lateral, vá para **"Connections" → "Data sources"**
3. Clique em **"Add data source"**
4. Selecione **"Prometheus"**
5. Na URL, digite: `http://prometheus:9090`
6. Clique em **"Save & test"**

Você deve ver: ✅ "Successfully queried the Prometheus API"

## 2️⃣ Criar o Dashboard

1. No menu lateral, clique em **"Dashboards"**
2. Clique em **"New" → "New Dashboard"**
3. Clique em **"Add visualization"**
4. Selecione o data source **"Prometheus"**

### 📈 Painel 1: Métricas de Negócio - Links Criados (Total)

- **Título:** Total de Links Criados
- **Query (PromQL):** `links_criados_total`
- **Visualização:** Stat (Estatística)

**Validação:** Use o Postman ou curl para criar novos links e veja este número aumentar.

### 📈 Painel 2: Métricas de Negócio - Redirecionamentos por Minuto

- **Título:** Redirecionamentos por Minuto
- **Query (PromQL):** `rate(redirecionamentos_total[1m]) * 60`
- **Visualização:** Time series (gráfico de tempo)

**Validação:** Acesse seus links curtos no navegador várias vezes e veja este gráfico subir.

### 📈 Painel 3: Performance da API - Requisições por Segundo (Throughput)

- **Título:** Requisições por Segundo (Todos Endpoints)
- **Query (PromQL):** `rate(flask_http_request_duration_seconds_count[1m])`
- **Visualização:** Time series

**Queries alternativas:**
```promql
sum(rate(flask_http_request_duration_seconds_count[1m]))
```

### 📈 Painel 4: Performance da API - Latência (P95)

- **Título:** Latência P95 (95% das requisições são mais rápidas que...)
- **Query (PromQL):** `histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket[1m])) by (le))`
- **Visualização:** Time series

**Query alternativa (latência média):**
```promql
rate(flask_http_request_duration_seconds_sum[1m]) / rate(flask_http_request_duration_seconds_count[1m])
```

### 📈 Painel 5: Análise de Erros - Erros por Status (Ex: 404)

- **Título:** Erros 404 por Minuto
- **Query (PromQL):** `rate(flask_http_request_duration_seconds_count{status="404"}[1m]) * 60`
- **Visualização:** Time series

**Validação:** Tente acessar um link curto que não existe (ex: `http://localhost:5000/naoexiste`) e veja este gráfico registrar o erro.

## 3️⃣ Salvar o Dashboard

1. Clique no ícone de **disquete** (Save) no topo
2. Dê um nome ao dashboard: **"Encurtador de URL - API"**
3. Clique em **"Save"**

---

# 🧪 Gerando Dados para Teste

## Criar múltiplos links (PowerShell):

```powershell
1..10 | ForEach-Object {
    $body = @{ url_longa = "https://site$_.com" } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:5000/encurtar" -Method POST -Body $body -ContentType "application/json"
}
```

## Criar múltiplos links (Bash/Linux/Mac):

```bash
for i in {1..10}; do
  curl -X POST http://localhost:5000/encurtar \
    -H "Content-Type: application/json" \
    -d "{\"url_longa\":\"https://site$i.com\"}"
done
```

## Gerar erros 404 (PowerShell):

```powershell
1..20 | ForEach-Object {
    try { Invoke-WebRequest -Uri "http://localhost:5000/naoexiste$_" } catch {}
}
```

## Gerar erros 404 (Bash):

```bash
for i in {1..20}; do
  curl http://localhost:5000/naoexiste$i
done
```

---

# 📦 Critérios de Entrega

Para concluir a atividade, você deve entregar:

## 1️⃣ Link para o repositório no GitHub contendo:

- ✅ O arquivo `app.py` com a API Flask e as métricas customizadas
- ✅ O arquivo `requirements.txt`
- ✅ O arquivo `prometheus.yml` configurado para a porta 5000 e o path `/metrics`
- ✅ O arquivo `docker-compose.yml`
- ✅ Arquivo `.gitignore` (para excluir venv, __pycache__, etc.)
- ✅ Arquivo `README.md` com documentação

## 2️⃣ Screenshot do dashboard do Grafana

Um screenshot do seu dashboard final do Grafana, mostrando **todos os 5 painéis funcionais** da Etapa 3.

---

# 🔧 Comandos Úteis

## Iniciar a aplicação:
```bash
python app.py
```

## Iniciar Docker Compose:
```bash
docker-compose up -d
```

## Ver logs dos containers:
```bash
docker-compose logs -f
```

## Parar os serviços:
```bash
docker-compose down
```

## Verificar métricas:
```bash
curl http://localhost:5000/metrics
```

---

# 📸 URLs Importantes

- **API Flask:** http://localhost:5000
- **Métricas:** http://localhost:5000/metrics
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)

---

# 🆘 Troubleshooting

### Problema: Prometheus não encontra a aplicação Flask
**Solução:** Verifique se o Flask está rodando em `http://localhost:5000/metrics`

### Problema: Painéis do Grafana aparecem vazios
**Solução:** 
- Gere tráfego na aplicação
- Aguarde 1-2 minutos para o Prometheus coletar dados
- Ajuste o time range do Grafana para os últimos 15 minutos

### Problema: Docker não inicia
**Solução:** Verifique se as portas 3000 e 9090 não estão em uso

### Problema: Métricas não aparecem
**Solução:** Verifique no Prometheus (Status → Targets) se o target está "UP"

---

# 📚 Tecnologias Utilizadas

- **Python 3.x**
- **Flask** - Framework web
- **prometheus-flask-exporter** - Instrumentação de métricas
- **Prometheus** - Sistema de monitoramento e alertas
- **Grafana** - Plataforma de visualização de dados
- **Docker Compose** - Orquestração de containers

---

# 👨‍💻 Autor

Rodrigo Paixão - Atividade de Observabilidade com Flask, Prometheus e Grafana

---

# 📄 Licença

Este projeto foi desenvolvido para fins educacionais.
