"""Build the Sphinx reference and export the real applications' OpenAPI schemas.

Run from any directory with Python 3.12+. No network listener or training is started.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent


def heading(text: str, char: str = '=') -> str:
    return f'{text}\n{char * len(text)}\n\n'


def code(text: str, language: str = 'python') -> str:
    return f'.. code-block:: {language}\n\n{textwrap.indent(text, "   ")}\n\n'


def declaration(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        prefix = 'async def' if isinstance(node, ast.AsyncFunctionDef) else 'def'
        returns = f' -> {ast.unparse(node.returns)}' if node.returns else ''
        return f'{prefix} {node.name}({ast.unparse(node.args)}){returns}'
    if isinstance(node, ast.ClassDef):
        bases = ', '.join(ast.unparse(base) for base in node.bases)
        return f'class {node.name}' + (f'({bases})' if bases else '')
    return ast.unparse(node)


def build_reference() -> dict[str, str]:
    descriptions = json.loads((DOCS / 'module_descriptions.json').read_text())
    generated = DOCS / 'generated'
    generated.mkdir(exist_ok=True)
    for path in generated.glob('*.rst'):
        path.unlink()
    paths = sorted([*(ROOT / 'backend/app').rglob('*.py'),
                    *(ROOT / 'ml_service/app').rglob('*.py'),
                    ROOT / 'backend/scripts/configure_ndtp_demo.py',
                    ROOT / 'ml_service/research/vovchik/train_from_notebook.py'])
    index = heading('Справочник Python-кода')
    index += ('Сигнатуры, аннотации, поля классов и имеющиеся docstring автоматически\n'
              'извлечены из Python AST. Ссылка на исходник позволяет проверить реализацию.\n'
              'Пояснения описывают назначение модуля; скрытые методы также включены.\n\n'
              '.. toctree::\n   :maxdepth: 1\n\n')
    hashes = {}
    for path in paths:
        if path.name == '__init__.py':
            continue
        rel = path.relative_to(ROOT).as_posix()
        module = rel[:-3].replace('/', '.')
        source = path.read_text(encoding='utf-8')
        hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        tree = ast.parse(source)
        body = heading(module)
        body += descriptions[rel] + '\n\n'
        body += f':download:`Скачать исходный код <../../{rel}>`\n\n'
        for node in tree.body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body += heading(node.name, '-') + code(declaration(node))
            if ast.get_docstring(node):
                body += code(ast.get_docstring(node), 'text')
            if isinstance(node, ast.ClassDef):
                fields = [declaration(item) for item in node.body
                          if isinstance(item, (ast.AnnAssign, ast.Assign))]
                if fields:
                    body += 'Поля и константы класса:\n\n' + code('\n'.join(fields))
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        body += heading(f'{node.name}.{method.name}', '~')
                        body += code(declaration(method))
                        if ast.get_docstring(method):
                            body += code(ast.get_docstring(method), 'text')
        (generated / f'{module}.rst').write_text(body, encoding='utf-8')
        index += f'   {module}\n'
    (generated / 'index.rst').write_text(index, encoding='utf-8')
    return hashes


def export_schema(service: str, output: str) -> None:
    # Separate processes prevent the two unrelated "app" packages from colliding.
    script = '''
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
# Do not enter a context manager: lifespan would start TCP and load demo inputs.
client = TestClient(app)
for path in ('/docs', '/redoc', '/openapi.json', '/health'):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
assert client.get('/health').json() == {'status': 'ok'}
schema = client.get('/openapi.json').json()
assert schema == app.openapi()
assert schema['paths']
Path(sys.argv[1]).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
print(app.title, ':', len(schema['paths']), 'paths; Swagger, ReDoc, health OK')
'''
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    subprocess.run([sys.executable, '-c', script, str(DOCS / 'openapi' / output)],
                   cwd=ROOT / service, env=env, check=True)


def build_api() -> None:
    metadata = json.loads((DOCS / 'endpoint_descriptions.json').read_text())
    body = heading('HTTP API и Swagger')
    body += ('Спецификации экспортированы через ``app.openapi()`` из настоящих приложений.\n'
             'Типы, обязательность полей и стандартные ответы в JSON соответствуют коду.\n'
             'Для маршрутов с ответом ``dict`` схема не перечисляет все динамические поля;\n'
             'для них смотрите пояснения и реализацию в справочнике.\n\n'
             'Статические страницы Swagger ниже работают в режиме чтения. Для выполнения\n'
             'запросов используйте ``/docs`` запущенного сервиса на своей машине.\n\n')
    swagger = DOCS / 'swagger'
    swagger.mkdir(exist_ok=True)
    for service, port in [('backend', 8000), ('ml', 8001)]:
        schema = json.loads((DOCS / 'openapi' / f'{service}.json').read_text())
        body += heading(schema['info']['title'], '-')
        body += (f'* `Статический Swagger {service} <{service}-swagger.html>`_.\n'
                 f'* :download:`OpenAPI JSON <openapi/{service}.json>`.\n'
                 f'* Swagger работающего сервиса: http://localhost:{port}/docs.\n\n')
        for path, methods in schema['paths'].items():
            for method, operation in methods.items():
                if method not in {'get', 'post', 'put', 'patch', 'delete', 'options', 'head'}:
                    continue
                key = f'{method.upper()} {path}'
                body += heading(key, '~')
                body += metadata[service][key] + '\n\n'
                params = operation.get('parameters', [])
                if params:
                    body += 'Параметры:\n\n'
                    for param in params:
                        required = 'обязательный' if param.get('required') else 'необязательный'
                        body += f'* ``{param["name"]}`` ({param["in"]}, {required}).\n'
                    body += '\n'
                request = operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
                if request:
                    model = request.get('$ref', '').rsplit('/', 1)[-1]
                    body += f'Тело: JSON, модель ``{model or "см. OpenAPI"}``.\n\n'
        # Inline schema allows opening the file directly without fetch/file:// CORS.
        spec = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
        html = f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{service.upper()} — OpenAPI Metrohack</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"></head>
<body><p style="padding:16px;font-family:system-ui"><a href="api.html">К документации API</a> · Только чтение.
Для запросов откройте /docs запущенного сервиса. Интерфейс Swagger требует доступа к CDN.</p>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({{spec:{spec},dom_id:'#swagger-ui',supportedSubmitMethods:[],validatorUrl:null}});</script>
</body></html>'''
        (swagger / f'{service}-swagger.html').write_text(html, encoding='utf-8')
    body += heading('Примеры и ответы', '-')
    body += ('Без изменения состояния можно вызвать:\n\n' + code(
        'curl http://localhost:8000/health\n'
        'curl http://localhost:8000/api/v1/ndtp/status\n'
        'curl http://localhost:8000/api/v1/fleet', 'bash'))
    body += ('Пример ручного отклонения (меняет состояние демонстрационного рейса):\n\n' + code(
        'POST /api/v1/current-deviation\nContent-Type: application/json\n\n'
        '{"tr_id": "demo-trip", "cur_dev_s": 90}', 'text'))
    body += ('Этот запрос сам по себе не создаёт прогноз: нужны расписание и телеметрия.\n\n'
             '* ``422`` — ошибка проверки входных полей FastAPI/Pydantic.\n'
             '* ``400`` — некорректный контекст, горизонт или другие явно проверяемые данные\n'
             '  на маршрутах, обрабатывающих ``ValueError``.\n'
             '* ``404`` — запрошенное ТС, инцидент или плановая остановка не найдены.\n'
             '* ``503`` — HTTP-вызов ML завершился ошибкой на маршрутах, которые её перехватывают.\n\n'
             'Не все явно выбрасываемые ошибки перечислены в автоматической OpenAPI-схеме.\n'
             '``GET /health`` подтверждает ответ процесса, но не свежесть NDTP и не качество ML.\n')
    (DOCS / 'api.rst').write_text(body, encoding='utf-8')


def main() -> None:
    (DOCS / 'openapi').mkdir(exist_ok=True)
    hashes = build_reference()
    export_schema('backend', 'backend.json')
    export_schema('ml_service', 'ml.json')
    build_api()
    manifest = {'source_sha256': hashes, 'generator': 'Sphinx 8.2.3; Python AST; FastAPI app.openapi()'}
    (DOCS / 'openapi' / 'build-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    output = DOCS / '_build' / 'html'
    if output.exists():
        shutil.rmtree(output)
    subprocess.run([sys.executable, '-m', 'sphinx', '-b', 'html', '-W', '--keep-going',
                    '-d', str(DOCS / '_build' / 'doctrees'), str(DOCS), str(output)], check=True)
    site = DOCS / 'site'
    if site.exists():
        shutil.rmtree(site)
    shutil.copytree(output, site, ignore=shutil.ignore_patterns('.buildinfo'))
    (site / '.nojekyll').touch()
    print('Documentation ready:', site / 'index.html')


if __name__ == '__main__':
    main()
