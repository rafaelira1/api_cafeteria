# Cafeteria API

API REST desenvolvida em Python para gerenciar produtos do cardápio e pedidos de uma cafeteria. O projeto possui dois recursos com pelo menos sete campos cada, CRUD completo, três registros iniciais por recurso, persistência local e respostas com status HTTP coerentes.

## Tecnologias

- Python 3.11 ou superior
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn

A autenticação utiliza JWT em cookie HttpOnly. Produtos e pedidos continuam públicos nesta etapa; a integração de autenticação e permissões nesses recursos fica para os demais integrantes.

## Armazenamento local

Os dados são armazenados no arquivo `cafeteria.db`, criado automaticamente na raiz do projeto na primeira execução. Ao encerrar e iniciar a API novamente, os dados cadastrados continuam salvos.

O banco recebe automaticamente três produtos e três pedidos quando está vazio. Para recomeçar com os dados iniciais, encerre a API, apague `cafeteria.db` e inicie a aplicação novamente.

## Estrutura do projeto

```text
cafeteria-api/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── rate_limit.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── orders.py
│   │   └── products.py
│   ├── create_demo_users.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── seed.py
├── estoque_api/
│   ├── main.py
│   └── requirements.txt
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_auth.py
│   └── test_auth_setup.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── run.bat
└── run.sh
```

## Como executar no Windows

Abra o terminal na pasta do projeto e execute:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; from dotenv import set_key; set_key('.env', 'AUTH_JWT_SECRET', secrets.token_urlsafe(48))"
python -m uvicorn app.main:app --reload --env-file .env
```

Copie e gere a chave somente na primeira configuração. Preserve um `.env` existente. Os scripts `run.bat` e `run.sh` exigem que as variáveis já estejam exportadas no ambiente; os comandos acima carregam o arquivo explicitamente.

## Como executar no Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; from dotenv import set_key; set_key('.env', 'AUTH_JWT_SECRET', secrets.token_urlsafe(48))"
python -m uvicorn app.main:app --reload --env-file .env
```

Depois que o servidor iniciar, acesse:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Documentação ReDoc: `http://127.0.0.1:8000/redoc`

O Swagger permite testar os CRUDs diretamente pelo navegador. Para o fluxo com cookies e CSRF, use os exemplos de autenticação abaixo.

## Recursos e campos

### Product (`/products`)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `description` | String ou null | Descrição opcional do produto, com até 1.000 caracteres (somente Product) |
| `id` | Integer | Identificador gerado automaticamente |
| `name` | String | Nome do produto |
| `category` | String | Categoria do item |
| `price` | Float | Preço de venda, maior que zero |
| `size` | String | Tamanho ou unidade do produto |
| `is_available` | Boolean | Indica se está disponível |
| `calories` | Integer | Calorias estimadas, igual ou maior que zero |

### Order (`/orders`)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | Integer | Identificador gerado automaticamente |
| `customer_name` | String | Nome do cliente |
| `table_number` | Integer | Número da mesa, maior que zero |
| `payment_method` | String | Forma de pagamento |
| `total_amount` | Float | Valor calculado automaticamente pelo preço do produto vezes a quantidade |
| `quantity` | Integer | Quantidade do produto, maior que zero |
| `status` | String | Estado do pedido: `pending`, `preparing`, `ready`, `delivered` ou `cancelled` |
| `is_takeaway` | Boolean | Indica se o pedido é para viagem |
| `product_id` | Integer | Identificador de um produto existente |

Um produto pode estar relacionado a vários pedidos. Um pedido referencia exatamente um produto por meio de `product_id`.

## Endpoints

| Método | Rota | Ação | Sucesso |
| --- | --- | --- | --- |
| `GET` | `/products` | Listar todos os produtos | `200 OK` |
| `GET` | `/products/{id}` | Mostrar um produto | `200 OK` |
| `POST` | `/products` | Criar um produto | `201 Created` |
| `PUT` | `/products/{id}` | Substituir todos os dados de um produto | `200 OK` |
| `PATCH` | `/products/{id}` | Editar campos específicos de um produto | `200 OK` |
| `DELETE` | `/products/{id}` | Apagar um produto | `204 No Content` |
| `GET` | `/orders` | Listar todos os pedidos | `200 OK` |
| `GET` | `/orders/{id}` | Mostrar um pedido | `200 OK` |
| `POST` | `/orders` | Criar um pedido | `201 Created` |
| `PUT` | `/orders/{id}` | Substituir todos os dados de um pedido | `200 OK` |
| `PATCH` | `/orders/{id}` | Editar campos específicos de um pedido | `200 OK` |
| `DELETE` | `/orders/{id}` | Apagar um pedido | `204 No Content` |
| `GET` | `/health` | Verificar se a API está ativa | `200 OK` |

Possíveis respostas de erro:

- `404 Not Found`: produto ou pedido inexistente.
- `409 Conflict`: tentativa de apagar um produto que possui pedidos vinculados.
- `422 Unprocessable Entity`: corpo JSON ausente, incompleto ou com valores inválidos.

## Exemplos de uso

### Listar produtos

```bash
curl http://127.0.0.1:8000/products
```

### Mostrar um produto

```bash
curl http://127.0.0.1:8000/products/1
```

### Criar um produto

```bash
curl -X POST http://127.0.0.1:8000/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cappuccino",
    "description": "Café com leite vaporizado e espuma cremosa.",
    "category": "Bebidas",
    "price": 9.5,
    "size": "250ml",
    "is_available": true,
    "calories": 120
  }'
```

### Editar parcialmente um produto

```bash
curl -X PATCH http://127.0.0.1:8000/products/4 \
  -H "Content-Type: application/json" \
  -d '{"price": 10.0, "is_available": false}'
```

### Substituir um produto

```bash
curl -X PUT http://127.0.0.1:8000/products/4 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cappuccino Grande",
    "category": "Bebidas",
    "price": 12.0,
    "size": "350ml",
    "is_available": true,
    "calories": 170
  }'
```

### Apagar um produto

```bash
curl -X DELETE http://127.0.0.1:8000/products/4
```

Um produto que tenha pedidos vinculados não pode ser apagado. Primeiro apague ou altere os pedidos relacionados.

### Listar pedidos

```bash
curl http://127.0.0.1:8000/orders
```

### Mostrar um pedido

```bash
curl http://127.0.0.1:8000/orders/1
```

### Criar um pedido

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Daniel Rocha",
    "table_number": 5,
    "payment_method": "Pix",
    "quantity": 2,
    "status": "pending",
    "is_takeaway": false,
    "product_id": 1
  }'
```

O valor de `product_id` precisa corresponder a um produto já cadastrado. O campo `total_amount` não deve ser enviado: a API calcula o valor usando o preço atual do produto multiplicado por `quantity`.

### Editar parcialmente um pedido

```bash
curl -X PATCH http://127.0.0.1:8000/orders/4 \
  -H "Content-Type: application/json" \
  -d '{"payment_method": "Cartão", "quantity": 3, "status": "preparing", "is_takeaway": true}'
```

### Substituir um pedido

```bash
curl -X PUT http://127.0.0.1:8000/orders/4 \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Daniel Rocha",
    "table_number": 8,
    "payment_method": "Cartão",
    "quantity": 2,
    "status": "ready",
    "is_takeaway": true,
    "product_id": 2
  }'
```

### Apagar um pedido

```bash
curl -X DELETE http://127.0.0.1:8000/orders/4
```

## Testes automatizados

Instale as dependências de desenvolvimento e execute os testes:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Os testes utilizam um banco SQLite separado, validam os dois CRUDs, os três registros iniciais, os principais erros e as regras de validação.

Os testes de autenticação configuram chaves temporárias e bancos isolados, sem exigir segredos reais no `.env`.

## Autenticação

### Configuração

Execute os comandos de instalação e configuração acima na pasta que contém `app/`. O arquivo `.env.example` habilita HTTP **somente para desenvolvimento local**, de forma explícita. Não contém chave de assinatura: gere uma chave aleatória conforme os comandos acima. Para gerar uma chave separadamente, use `python -c "import secrets; print(secrets.token_urlsafe(48))"` e configure o resultado em `AUTH_JWT_SECRET`.

| Variável | Configuração |
| --- | --- |
| `AUTH_JWT_SECRET` | Obrigatória. Chave aleatória em base64url, com pelo menos 32 bytes decodificados; sem valor padrão. Não compartilhe nem versione o `.env`. |
| `AUTH_ENVIRONMENT` | `production` por padrão; `development` permite a opção local abaixo. |
| `AUTH_ALLOW_INSECURE_HTTP` | `false` por padrão. `true` exige `development` e limita HTTP a `localhost`, `127.0.0.1` ou `::1`. |
| `AUTH_ALLOWED_ORIGINS` | Obrigatória. Origens completas, separadas por vírgula, com esquema e porta quando utilizada, sem caminhos ou curingas. Exemplo local: `http://127.0.0.1:8000,http://localhost:8000`. |
| `AUTH_TOKEN_TTL_MINUTES` | `30` por padrão; aceita de `1` a `60`. |
| `AUTH_LOGIN_MAX_ATTEMPTS` | `5` tentativas por IP por janela, por padrão. |
| `AUTH_LOGIN_WINDOW_SECONDS` | Janela de `60` segundos por padrão. |
| `DATABASE_URL` | Opcional; utiliza o SQLite existente em `sqlite:///./cafeteria.db` por padrão. |

Para HTTPS, use `AUTH_ENVIRONMENT=production`, `AUTH_ALLOW_INSECURE_HTTP=false` e origens explícitas com `https://`. O cookie é `Secure` por padrão; HTTP local exige as duas opções de desenvolvimento. A configuração inválida ou a ausência da chave impede a inicialização. A lista de origens valida as requisições de autenticação; **não habilita CORS**. Nenhum middleware CORS com credenciais foi acrescentado.

O JWT é assinado com HS256, com algoritmo aceito fixado pelo servidor. Contém `sub`, `iat`, `exp`, `jti` e `role`, além de emissor e público. O servidor valida a assinatura e os claims e consulta o banco para obter o usuário ativo e seu perfil atual. O `Max-Age` do cookie acompanha a validade do token. Não há retorno do JWT em JSON, armazenamento em `localStorage` ou autenticação por cabeçalho `Authorization`.

As respostas de usuário contêm somente `id`, `name`, `email`, `role`, `is_active` e `created_at`. O email é validado, normalizado e único. A senha de cadastro aceita de 12 a 128 caracteres, não pode conter somente espaços, é preservada exatamente como enviada e armazenada como hash Argon2id; espaços não são removidos silenciosamente. O cadastro público sempre cria `customer`; enviar `role` ou outros campos não previstos resulta em `422`.

A tabela `users` é criada pela estrutura SQLAlchemy existente sem apagar ou recriar o banco. Não é necessário excluir `cafeteria.db` para adicionar a autenticação. Nenhum usuário administrativo é criado automaticamente.

### Usuários locais de demonstração

Com o ambiente virtual ativo, execute explicitamente:

```bash
python -m app.create_demo_users --env-file .env
```

O comando solicita nome, email e senha para cada perfil: `admin`, `staff` e `customer`. As senhas são solicitadas sem exibição pelo terminal, com confirmação, e não são recebidas por argumentos da linha de comando. Os três cadastros são feitos em uma transação; emails existentes não são sobrescritos. Sem `--env-file`, configure as variáveis no ambiente antes de executar. Os perfis são apenas a base para autorização futura; este comando não cria gerenciamento administrativo de usuários.

### Endpoints e CSRF

| Método | Rota | Comportamento |
| --- | --- | --- |
| `GET` | `/auth/csrf` | Retorna `{"csrf_token": "..."}` e define os cookies necessários ao CSRF. |
| `POST` | `/auth/register` | Recebe `name`, `email` e `password`; cadastra cliente e retorna `201`, sem iniciar login. |
| `POST` | `/auth/login` | Recebe `email` e `password`; retorna usuário seguro, define o cookie JWT e renova o CSRF. |
| `GET` | `/auth/me` | Retorna o usuário autenticado usando `get_current_user`. |
| `POST` | `/auth/logout` | Retorna `204` e remove os cookies de autenticação, CSRF e pré-autenticação. |

Cadastro, login e logout exigem `Origin` presente e permitido, os cookies recebidos e o token no cabeçalho `X-CSRF-Token`. Primeiro obtenha o token em `/auth/csrf`, inclusive antes de cadastrar ou entrar. Após o login, obtenha o token novamente: o anterior deixa de corresponder à autenticação atual.

O CSRF utiliza double-submit assinado com HMAC. Antes do login, sua assinatura está vinculada a um cookie de pré-autenticação HttpOnly assinado; depois do login, fica vinculada ao `jti` do JWT. Copiar um token CSRF de outra autenticação não satisfaz essa vinculação. `/auth/csrf` também permite recuperar o fluxo quando encontra um JWT inválido ou expirado: remove o cookie de autenticação e prepara um novo fluxo anônimo.

Os cookies são exclusivos do host, com `Path=/` e `SameSite=Lax`. Em HTTPS, os nomes são `__Host-cafeteria_auth`, `__Host-cafeteria_csrf` e `__Host-cafeteria_preauth`, com `Secure`; no modo HTTP local, são `cafeteria_auth`, `cafeteria_csrf` e `cafeteria_preauth`. Autenticação e pré-autenticação usam `HttpOnly`. O token CSRF é disponibilizado separadamente no JSON e no cookie CSRF, que não é HttpOnly. `SameSite` complementa a verificação do token e da origem.

Erros: `401` para autenticação ausente, inválida, expirada ou usuário inexistente/inativo; `403` para CSRF/origem inválidos; `409` para email já cadastrado; `422` para entradas inválidas; `429` para excesso de tentativas de login, com `Retry-After`. Login incorreto usa a mesma mensagem genérica para email inexistente, senha incorreta e usuário inativo.

### Exemplo completo com curl

Use Bash, Git Bash no Windows ou terminal equivalente, com Python e curl disponíveis. No PowerShell, o executável é `curl.exe`; a sintaxe de variáveis e pipes do exemplo abaixo é de Bash. Execute com a configuração HTTP local do `.env.example`, mantendo o mesmo host durante todo o fluxo:

```bash
BASE=http://127.0.0.1:8000
ORIGIN=http://127.0.0.1:8000
JAR=cookies-auth.txt

# 1. Preparar cookies e obter CSRF antes da autenticação.
CSRF=$(curl -fsS -c "$JAR" -H "Origin: $ORIGIN" "$BASE/auth/csrf" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["csrf_token"])')

# 2. Cadastrar. Python solicita a senha sem exibi-la ou gravá-la no histórico.
# Use a mesma senha no login; o email abaixo é apenas um exemplo de cliente.
python -c 'import getpass,json; print(json.dumps({"name":"Cliente de teste","email":"cliente@example.com","password":getpass.getpass("Senha de cadastro (12..128 caracteres): ")}))' \
  | curl -sS -b "$JAR" -c "$JAR" -X POST "$BASE/auth/register" \
    -H "Origin: $ORIGIN" -H "X-CSRF-Token: $CSRF" \
    -H 'Content-Type: application/json' --data-binary @-

# 3. Entrar. O JWT é recebido somente como cookie HttpOnly.
python -c 'import getpass,json; print(json.dumps({"email":"cliente@example.com","password":getpass.getpass("Senha de login: ")}))' \
  | curl -sS -b "$JAR" -c "$JAR" -X POST "$BASE/auth/login" \
    -H "Origin: $ORIGIN" -H "X-CSRF-Token: $CSRF" \
    -H 'Content-Type: application/json' --data-binary @-

# 4. Consultar o usuário autenticado.
curl -sS -b "$JAR" "$BASE/auth/me"

# 5. Obter o CSRF vinculado à autenticação iniciada pelo login.
CSRF=$(curl -fsS -b "$JAR" -c "$JAR" -H "Origin: $ORIGIN" "$BASE/auth/csrf" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["csrf_token"])')

# 6. Sair e confirmar que /auth/me retorna 401.
curl -sS -i -b "$JAR" -c "$JAR" -X POST "$BASE/auth/logout" \
  -H "Origin: $ORIGIN" -H "X-CSRF-Token: $CSRF"
curl -sS -i -b "$JAR" "$BASE/auth/me"
```

O arquivo de cookies contém credenciais: mantenha-o local e apague-o ao terminar. Repetir o cadastro com o mesmo email produz `409`; nesse caso, continue diretamente pelo login. No Postman, mantenha o cookie jar habilitado, obtenha `csrf_token` pelo GET, copie-o para `X-CSRF-Token` e configure `Origin` nos POSTs. Atualize o token após o login e não configure Bearer Auth.

### Expiração e limites

O token expira em 30 minutos por padrão; não há refresh token, tabela de sessões nem lista de revogação. Logout remove os cookies do navegador, mas **não invalida uma cópia do JWT**: ela continua válida até expirar, enquanto o usuário existir e estiver ativo. Alterar a chave também invalida todos os tokens assinados anteriormente. O perfil é lido novamente do banco a cada autenticação, em vez de confiar no perfil antigo do JWT.

O limitador de login fica na memória, por IP, é protegido para uso por threads e conta tentativas válidas e inválidas. Cada processo mantém seu próprio contador; reinicializações o apagam, e múltiplos workers não compartilham o limite. Ele usa o IP visto pela aplicação e não confia em `X-Forwarded-For`; clientes atrás de um mesmo proxy podem compartilhar a cota. Uma instalação com vários processos precisará de limitação compartilhada, fora do escopo desta etapa.

`HttpOnly` impede que JavaScript leia o cookie de autenticação, mas não elimina XSS: código malicioso executado na origem ainda pode realizar requisições autenticadas e obter CSRF. Senhas e tokens não devem ser registrados em logs.

O enunciado acadêmico proíbe Bearer Token. JWT em cookie continua sendo uma credencial por posse, embora não use o cabeçalho `Authorization: Bearer`. A aceitação dessa técnica depende do professor; esta implementação não afirma aprovação acadêmica.

Referências técnicas: [API do PyJWT](https://pyjwt.readthedocs.io/en/stable/api.html), [API do argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/api.html) e [proteção CSRF da OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

### Integração para os demais integrantes

Estão disponíveis `app.models.User`, `UserRole`, os schemas seguros de autenticação e as dependências `get_current_user` e `require_csrf`. Exemplo para um **endpoint futuro**, sem alterar produtos e pedidos nesta entrega:

```python
from fastapi import Depends

from app.auth.dependencies import get_current_user, require_csrf
from app.models import User


@router.get("/recurso-futuro")
def consultar(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role}


@router.post("/recurso-futuro", dependencies=[Depends(require_csrf)])
def alterar(user: User = Depends(get_current_user)):
    # Aplicar aqui as regras do recurso e a autorização definidas pela equipe.
    return {"user_id": user.id}
```

`get_current_user` valida somente o cookie JWT, confirma existência/atividade no banco e entrega o perfil atual. Combine-a com `require_csrf` nas futuras operações autenticadas que alterarem dados. Matriz de permissões, propriedade de pedidos, proteção dos CRUDs existentes e administração de usuários ficam para os colegas.

## Integração com a API de estoque

A cafeteria consulta uma segunda API, a `estoque_api` (pasta `estoque_api/`), que guarda a quantidade de ingredientes de cada produto. Os dados dela ficam em memória e o id do estoque é o mesmo id do produto.

Para rodar as duas APIs localmente, em dois terminais:

```bash
python -m uvicorn estoque_api.main:app --port 8001
python -m uvicorn app.main:app --reload --env-file .env
```

A variável `ESTOQUE_API_URL` aponta para a API de estoque (`http://127.0.0.1:8001` no `.env.example`). Se ela estiver vazia a integração fica desligada e a cafeteria funciona como antes.

Onde a cafeteria usa o estoque:

- `GET /products/{id}/estoque`: busca o produto no banco local e o estoque na API externa, e devolve os dois juntos com o campo `can_sell` (produto ativo no cardápio e com estoque maior que zero).
- `POST /orders`: antes de criar o pedido consulta o estoque (`GET /estoque/{id}`) e depois desconta a quantidade (`POST /estoque/{id}/baixa`). Com estoque insuficiente retorna `409`.
- Se a API de estoque estiver fora do ar, retorna `503`.

Endpoints da API de estoque: `GET /estoque`, `GET /estoque/{product_id}` e `POST /estoque/{product_id}/baixa` com `{"quantity": 2}`.

Exemplo:

```bash
curl http://127.0.0.1:8000/products/1/estoque
```

## Publicação no GitHub

Na raiz deste projeto, execute:

```bash
git init
git add .
git commit -m "Cria API REST da cafeteria"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
git push -u origin main
```

Substitua `SEU_USUARIO` e `NOME_DO_REPOSITORIO` pelos dados do repositório criado no GitHub. O arquivo `.gitignore` evita o envio do banco local e do ambiente virtual.
