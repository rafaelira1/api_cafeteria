# Cafeteria API

API REST desenvolvida em Python para gerenciar produtos do cardápio e pedidos de uma cafeteria. O projeto possui dois recursos com pelo menos sete campos cada, CRUD completo, três registros iniciais por recurso, persistência local e respostas com status HTTP coerentes.

Versão publicada: [Cafeteria API](https://cafeteria-api-k9jm.onrender.com), [Swagger](https://cafeteria-api-k9jm.onrender.com/docs) e [Estoque API](https://cafeteria-estoque.onrender.com). A documentação de apresentação e os diagramas estão em [Apresentação](Apresentacao/READMEAp.md).

## Tecnologias

- Python 3.12, definido em `.python-version`
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn

A autenticação utiliza JWT em cookie HttpOnly. O cardápio (`GET /products`) é público e o resto exige login, com permissões por perfil (veja a seção Permissões).

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
│   │   ├── products.py
│   │   └── stock.py
│   ├── bootstrap_demo_users.py
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
│   ├── test_auth_setup.py
│   ├── test_estoque.py
│   └── test_permissions.py
├── .env.example
├── .gitignore
├── .python-version
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
| `GET` | `/products/{id}/estoque` | Consultar produto e estoque externo, como staff ou admin | `200 OK` |
| `POST` | `/products` | Criar um produto | `201 Created` |
| `PUT` | `/products/{id}` | Substituir todos os dados de um produto | `200 OK` |
| `PATCH` | `/products/{id}` | Editar campos específicos de um produto | `200 OK` |
| `DELETE` | `/products/{id}` | Apagar um produto | `204 No Content` |
| `GET` | `/orders` | Listar os pedidos permitidos ao perfil | `200 OK` |
| `GET` | `/orders/{id}` | Mostrar um pedido | `200 OK` |
| `POST` | `/orders` | Criar um pedido | `201 Created` |
| `PUT` | `/orders/{id}` | Substituir todos os dados de um pedido | `200 OK` |
| `PATCH` | `/orders/{id}` | Editar campos específicos de um pedido | `200 OK` |
| `DELETE` | `/orders/{id}` | Apagar um pedido | `204 No Content` |
| `GET` | `/health` | Verificar se a API está ativa | `200 OK` |

Possíveis respostas de erro:

- `401 Unauthorized`: sem login.
- `403 Forbidden`: perfil sem permissão ou CSRF inválido.
- `404 Not Found`: produto ou pedido inexistente.
- `409 Conflict`: tentativa de apagar um produto que possui pedidos vinculados.
- `422 Unprocessable Entity`: corpo JSON ausente, incompleto ou com valores inválidos.

## Permissões

Existem três perfis: `admin`, `staff` (funcionário) e `customer` (cliente). Quem se cadastra pela API sempre vira `customer`. As contas de demonstração dos três perfis podem ser criadas pelo comando `create_demo_users` ou automaticamente na inicialização, com `DEMO_USERS_ENABLED=true` e as credenciais configuradas no ambiente.

| Rota | Sem login | customer | staff | admin |
| --- | --- | --- | --- | --- |
| `GET /products` e `GET /products/{id}` | sim | sim | sim | sim |
| `POST`, `PUT`, `PATCH`, `DELETE /products` | 401 | 403 | 403 | sim |
| `GET /products/{id}/estoque` | 401 | 403 | sim | sim |
| `GET /orders` | 401 | só os dele | todos | todos |
| `GET /orders/{id}` | 401 | só se for dele (senão 403) | sim | sim |
| `POST /orders` | 401 | sim | sim | sim |
| `PATCH /orders/{id}` | 401 | 403 | sim | sim |
| `PUT` e `DELETE /orders/{id}` | 401 | 403 | 403 | sim |

Regras:

- O pedido guarda quem o criou (`user_id`). Pedidos do seed ficam sem dono, então só staff e admin enxergam.
- As rotas que alteram dados (`POST`, `PUT`, `PATCH`, `DELETE`) também exigem o CSRF, igual ao login: cabeçalhos `Origin` e `X-CSRF-Token` mais o cookie.
- Ordem das verificações: primeiro o login (401), depois o perfil (403) e por último o CSRF (403).
- O perfil é lido do banco a cada requisição, então mudar o perfil de um usuário vale na hora.
- Ao subir a API em um banco que já existe, a coluna `user_id` é adicionada na tabela de pedidos sem apagar nada.

Exemplo de erros (depois de logar como `customer`, com `$JAR` e `$CSRF` do exemplo de autenticação):

```bash
# sem cookie: 401
curl -i http://127.0.0.1:8000/orders

# cliente tentando apagar produto: 403
curl -i -b "$JAR" -X DELETE http://127.0.0.1:8000/products/1   -H "Origin: $ORIGIN" -H "X-CSRF-Token: $CSRF"

# cliente criando pedido: 201
curl -i -b "$JAR" -X POST http://127.0.0.1:8000/orders   -H "Origin: $ORIGIN" -H "X-CSRF-Token: $CSRF" -H "Content-Type: application/json"   -d '{"customer_name":"Ana","table_number":3,"payment_method":"Pix","quantity":1,"is_takeaway":false,"product_id":1}'
```

Os exemplos de curl da seção Exemplos de uso mostram só o corpo das requisições. As que alteram dados precisam do login e do CSRF como acima.

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
| `ESTOQUE_API_URL` | URL base da API de estoque. Vazia desliga a integração; em produção, aponta para a URL HTTPS do serviço de estoque. |
| `DEMO_USERS_ENABLED` | `false` por padrão. Com `true`, habilita o bootstrap dos usuários de demonstração na inicialização. |
| `DEMO_ADMIN_EMAIL` | Email da conta admin de demonstração; obrigatório quando o bootstrap está habilitado. |
| `DEMO_ADMIN_PASSWORD` | Senha da conta admin de demonstração, com 12 a 128 caracteres. |
| `DEMO_STAFF_EMAIL` | Email da conta staff de demonstração; obrigatório quando o bootstrap está habilitado. |
| `DEMO_STAFF_PASSWORD` | Senha da conta staff de demonstração, com 12 a 128 caracteres. |
| `DEMO_CUSTOMER_EMAIL` | Email da conta customer de demonstração; obrigatório quando o bootstrap está habilitado. |
| `DEMO_CUSTOMER_PASSWORD` | Senha da conta customer de demonstração, com 12 a 128 caracteres. |

Para HTTPS, use `AUTH_ENVIRONMENT=production`, `AUTH_ALLOW_INSECURE_HTTP=false` e origens explícitas com `https://`. O cookie é `Secure` por padrão; HTTP local exige as duas opções de desenvolvimento. A configuração inválida ou a ausência da chave impede a inicialização. A lista de origens valida as requisições de autenticação; **não habilita CORS**. Nenhum middleware CORS com credenciais foi acrescentado.

O JWT é assinado com HS256, com algoritmo aceito fixado pelo servidor. Contém `sub`, `iat`, `exp`, `jti` e `role`, além de emissor e público. O servidor valida a assinatura e os claims e consulta o banco para obter o usuário ativo e seu perfil atual. O `Max-Age` do cookie acompanha a validade do token. Não há retorno do JWT em JSON, armazenamento em `localStorage` ou autenticação por cabeçalho `Authorization`.

As respostas de usuário contêm somente `id`, `name`, `email`, `role`, `is_active` e `created_at`. O email é validado, normalizado e único. A senha de cadastro aceita de 12 a 128 caracteres, não pode conter somente espaços, é preservada exatamente como enviada e armazenada como hash Argon2id; espaços não são removidos silenciosamente. O cadastro público sempre cria `customer`; enviar `role` ou outros campos não previstos resulta em `422`.

A tabela `users` é criada pela estrutura SQLAlchemy existente sem apagar ou recriar o banco. Não é necessário excluir `cafeteria.db` para adicionar a autenticação. O bootstrap de demonstração fica desabilitado por padrão; sua ativação é explícita, pela variável `DEMO_USERS_ENABLED`.

### Usuários de demonstração

Com o ambiente virtual ativo, execute explicitamente:

```bash
python -m app.create_demo_users --env-file .env
```

O comando solicita nome, email e senha para cada perfil: `admin`, `staff` e `customer`. As senhas são solicitadas sem exibição pelo terminal, com confirmação, e não são recebidas por argumentos da linha de comando. Os três cadastros são feitos em uma transação; emails existentes não são sobrescritos. Sem `--env-file`, configure as variáveis no ambiente antes de executar. Os perfis são usados nas regras da seção Permissões; este comando não cria gerenciamento administrativo de usuários.

A criação automática é feita por `app/bootstrap_demo_users.py`, chamado no `lifespan` de `app/main.py`, após a criação e migração das tabelas e antes do seed de produtos e pedidos. Para utilizá-la, configure `DEMO_USERS_ENABLED=true` e os seis valores de email e senha da tabela acima. No ambiente local, salve esses valores no `.env` e inicie com `--env-file .env`; no Render, configure-os na página **Environment** do serviço da cafeteria.

Os três emails devem ser diferentes. A rotina valida todas as configurações antes de inserir, aplica o mesmo hash Argon2id da autenticação e cria somente contas ausentes. Contas existentes conservam nome, senha e perfil: alterar a senha na variável não troca a senha já salva. Um email existente com perfil incompatível ou conta inativa impede a inicialização, sem promover usuários automaticamente. As credenciais da demonstração publicada são fornecidas pela equipe e não são armazenadas neste README.

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

### Uso das dependências de autenticação

Estão disponíveis `app.models.User`, `UserRole`, os schemas seguros de autenticação e as dependências `get_current_user` e `require_csrf`. Exemplo de reutilização em um **novo endpoint**:

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

`get_current_user` valida somente o cookie JWT, confirma existência/atividade no banco e entrega o perfil atual. Combine-a com `require_csrf` nas futuras operações autenticadas que alterarem dados. A matriz de permissões e a proteção dos CRUDs estão na seção [Permissões](#permissões). Não existe gerenciamento de usuários pela API.

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

Exemplo, após entrar como staff ou admin e preparar `$JAR` conforme o fluxo de autenticação:

```bash
curl -b "$JAR" http://127.0.0.1:8000/products/1/estoque
```

## Deploy no Render

As duas APIs estão publicadas em serviços separados, a partir deste mesmo repositório:

| Serviço | URL | Documentação | Saúde |
| --- | --- | --- | --- |
| Cafeteria API | [API](https://cafeteria-api-k9jm.onrender.com) | [Swagger](https://cafeteria-api-k9jm.onrender.com/docs) | [`/health`](https://cafeteria-api-k9jm.onrender.com/health) |
| Estoque API | [API](https://cafeteria-estoque.onrender.com) | [Swagger](https://cafeteria-estoque.onrender.com/docs) | [`/health`](https://cafeteria-estoque.onrender.com/health) |

### Configuração dos serviços

No painel do Render, crie dois **Web Services**, selecionando este repositório. Em ambos, use **Python 3**, branch `main`, **Root Directory** vazio, plano **Free** e **Health Check Path** `/health`. O arquivo `.python-version` fixa a série Python 3.12.

| Configuração | Cafeteria API | Estoque API |
| --- | --- | --- |
| Build Command | `pip install -r requirements.txt` | `pip install -r estoque_api/requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` | `uvicorn estoque_api.main:app --host 0.0.0.0 --port $PORT --workers 1` |

Publique primeiro o estoque e confira seu `/health`; depois configure e publique a cafeteria. O `$PORT` é fornecido pelo Render. O mock usa um worker porque seu estoque fica em memória e cada processo manteria quantidades independentes.

### Variáveis de produção

Na página **Environment** da cafeteria, configure:

| Variável | Valor |
| --- | --- |
| `AUTH_ENVIRONMENT` | `production` |
| `AUTH_ALLOW_INSECURE_HTTP` | `false` |
| `AUTH_ALLOWED_ORIGINS` | `https://cafeteria-api-k9jm.onrender.com` |
| `AUTH_JWT_SECRET` | Chave aleatória em base64url, gerada com o comando abaixo. |
| `DATABASE_URL` | `sqlite:///./cafeteria.db` |
| `ESTOQUE_API_URL` | `https://cafeteria-estoque.onrender.com` |
| `DEMO_USERS_ENABLED` | `true` |
| `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD` | Email e senha da conta admin de demonstração. |
| `DEMO_STAFF_EMAIL`, `DEMO_STAFF_PASSWORD` | Email e senha da conta staff de demonstração. |
| `DEMO_CUSTOMER_EMAIL`, `DEMO_CUSTOMER_PASSWORD` | Email e senha da conta customer de demonstração. |

Para gerar a chave, execute localmente com o ambiente virtual ativo e copie somente o resultado para `AUTH_JWT_SECRET` no Render:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

No PowerShell, também pode usar `..venvScriptspython.exe` no lugar de `python`. A origem deve ser a URL base da cafeteria, sem `/` final ou caminho; a URL do estoque também deve ser somente a base, sem `/estoque`. O serviço de estoque atual não exige essas variáveis de autenticação. Depois de salvar os valores no painel, faça um novo deploy para aplicá-los.

### Como testar a versão publicada

1. Abra os endpoints `/health` das duas APIs e aguarde a resposta `{"status":"ok"}`.
2. No Postman, mantenha os cookies habilitados e faça `GET https://cafeteria-api-k9jm.onrender.com/auth/csrf`, com `Origin: https://cafeteria-api-k9jm.onrender.com`.
3. Copie o `csrf_token` e faça `POST /auth/login` na mesma base, com email e senha da conta de demonstração, os cookies recebidos e os headers `Origin`, `X-CSRF-Token` e `Content-Type: application/json`.
4. Consulte `GET /auth/me` para conferir a conta e o perfil autenticados. Após o login, obtenha um novo CSRF antes de criar ou alterar dados.
5. Repita os testes de autorização e integração da tabela abaixo. Ao trocar de perfil, faça novo login e confirme a conta em `/auth/me`.
6. Para conferir o logout, faça `POST /auth/logout` com cookies, origem e CSRF atualizados; o resultado esperado é `204` e, depois, `401` em `/auth/me`.

Os exemplos de curl da seção Autenticação também podem ser usados online, substituindo as definições de `BASE` e `ORIGIN` por:

```bash
BASE=https://cafeteria-api-k9jm.onrender.com
ORIGIN=https://cafeteria-api-k9jm.onrender.com
```

Em HTTPS, confira nos headers `Set-Cookie` da resposta de login o nome `__Host-cafeteria_auth`, os atributos `Secure`, `HttpOnly`, `Path=/`, `SameSite=lax` e a ausência de `Domain`. O gerenciador de cookies do Postman não suporta `SameSite` nem valida as regras dos prefixos `__Host-`; use o header da resposta para inspecionar os atributos e o navegador para conferir sua aceitação.

### Testes de autorização e integração validados

Os seguintes fluxos foram validados manualmente no ambiente publicado:

| Teste | Resultado |
| --- | --- |
| Admin e staff consultando `GET /products/1/estoque` | `200 OK`, com produto local e estoque externo. |
| Customer consultando `GET /products/1/estoque` | `403 Forbidden`. |
| Customer criando `POST /orders` para um produto disponível | `201 Created`, com redução da quantidade na API de estoque. |
| Customer consultando `GET /orders` | Somente pedidos vinculados à própria conta. |

Para repetir a conferência da baixa, anote `stock.quantity` como staff, crie um pedido como customer e consulte o estoque novamente como staff. Sem outras alterações ou reinícios durante o teste, a diferença deve ser a quantidade pedida. Os três pedidos do seed ficam sem dono e não aparecem para customer.

### Dados e reinicialização

O SQLite do serviço gratuito fica no sistema de arquivos efêmero do Render: reinícios, novos deploys e suspensão por inatividade apagam as alterações locais. Na subida, o `lifespan` cria as tabelas, aplica as migrações e executa o bootstrap dos usuários e o seed de produtos e pedidos. Com as variáveis de demonstração preenchidas, as contas e os dados iniciais são reconstruídos; pedidos criados durante os testes podem desaparecer.

O estoque é um dicionário em memória e volta às quantidades iniciais quando o mock reinicia, independentemente do banco da cafeteria. Antes da apresentação, abra o `/health` do estoque e espere responder; em seguida, faça o mesmo com a cafeteria. O cliente HTTP atual tem timeout de 5 segundos e pode retornar `503` enquanto o serviço externo ainda estiver iniciando.

Referências: [FastAPI no Render](https://render.com/docs/deploy-fastapi), [variáveis de ambiente](https://render.com/docs/configure-environment-variables), [limitações do plano gratuito](https://render.com/docs/free) e [cookies no Postman](https://learning.postman.com/docs/use/send-requests/response-data/cookies/).

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
