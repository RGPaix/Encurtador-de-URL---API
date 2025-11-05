import random
import string
import time
from flask import Flask, request, redirect, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram

app = Flask(__name__)

# 1) Instrumentação automática (cria /metrics)
metrics = PrometheusMetrics(app)

# 2) Métricas customizadas de negócio
links_criados_total = Counter(
    'links_criados_total',
    'Total de novos links encurtados criados.'
)
redirecionamentos_total = Counter(
    'redirecionamentos_total',
    'Total de links redirecionados.'
)

# 3) (Opcional) histograma manual de latência com nome conhecido
request_latency_histogram = Histogram(
    'app_request_latency_seconds',
    'Latência das requisições da aplicação (segundos)',
    ['method', 'endpoint']
)

# "banco de dados" em memória
url_db = {}

def gerar_codigo_curto(tamanho=6):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(tamanho))

# Middleware simples para observar latência (usa o histogram acima)
@app.before_request
def _before_request():
    request._start_time = time.time()

@app.after_request
def _after_request(response):
    try:
        elapsed = time.time() - request._start_time
        # labels: method e endpoint (path)
        endpoint = request.path
        request_latency_histogram.labels(method=request.method, endpoint=endpoint).observe(elapsed)
    except Exception:
        pass
    return response

@app.route('/encurtar', methods=['POST'])
def encurtar_url():
    dados = request.get_json()
    if not dados or 'url_longa' not in dados:
        return jsonify({"erro": "URL longa não fornecida"}), 400
    url_longa = dados['url_longa']
    codigo_curto = gerar_codigo_curto()
    # Garantir unicidade (extremamente raro)
    while codigo_curto in url_db:
        codigo_curto = gerar_codigo_curto()
    url_db[codigo_curto] = url_longa
    links_criados_total.inc()
    return jsonify({
        "url_longa": url_longa,
        "url_curta": f"{request.host_url}{codigo_curto}"
    }), 201

@app.route('/<string:codigo_curto>', methods=['GET'])
def redirecionar(codigo_curto):
    url_longa = url_db.get(codigo_curto)
    if url_longa:
        redirecionamentos_total.inc()
        return redirect(url_longa, code=302)
    else:
        return jsonify({"erro": "URL curta não encontrada"}), 404

@app.route('/api/links', methods=['GET'])
def listar_links():
    return jsonify(url_db)

if __name__ == '__main__':
    # Para desenvolvimento local
    app.run(debug=True, host='0.0.0.0', port=5000)
