# Cafeteria API

API REST desenvolvida em Python para gerenciar produtos do cardápio e pedidos de uma cafeteria. O projeto atende aos requisitos da avaliação: possui dois recursos com pelo menos sete campos cada, CRUD completo, três registros iniciais por recurso, persistência local e respostas com status HTTP coerentes.

## Tecnologias

- Python 3.11 ou superior
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn

Não há autenticação ou autorização, conforme solicitado no enunciado.

## Armazenamento local

Os dados são armazenados no arquivo `cafeteria.db`, criado automaticamente na raiz do projeto na primeira execução. Ao encerrar e iniciar a API novamente, os dados cadastrados continuam salvos.

O banco recebe automaticamente três produtos e três pedidos quando está vazio. Para recomeçar com os dados iniciais, encerre a API, apague `cafeteria.db` e inicie a aplicação novamente.

## Estrutura do projeto

```text
cafeteria-api/
├── app/
│   ├── routers/
│   │   ├── orders.py
│   │   └── products.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── seed.py
├── tests/
│   └── test_api.py
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
python -m uvicorn app.main:app --reload
```

Como alternativa, após instalar as dependências, execute `run.bat`.

## Como executar no Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Depois que o servidor iniciar, acesse:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Documentação ReDoc: `http://127.0.0.1:8000/redoc`

O Swagger permite testar todos os endpoints diretamente pelo navegador.

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
