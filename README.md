# СУЗ — «Проект в рынке», итерация 1

Дашборд проекта: ползунки цены и темпа продаж, ФР и LLCR, пересчитанные финмоделью (xlsx), графики нашего проекта и конкурентов по кварталам. ТЗ: `docs/TZ_SUZ_iteration1.md`, исходный прототип: `prototype/`.

## Состав

| Сервис | Что делает |
|---|---|
| `frontend/` | React + TypeScript + Vite; в продакшне — nginx, он же проксирует `/api` |
| `backend/` | FastAPI: вход (JWT), объекты, модель, конкуренты, сценарии пользователей, пересчёт |
| `calc-worker/` | Aspose.Cells: держит книгу модели открытой, пересчитывает сценарий за 2,5–4,5 с |
| `db` | PostgreSQL 16 |
| `config/cell_map.yaml` | адреса ячеек и правила поиска строк модели — менять здесь, не в коде |

Данные модели читаются из файла при загрузке; ФР и LLCR после изменения ползунков считает сама модель (calc-worker), графики обновляются сразу на клиенте. Сверка движка с Excel — `backend/tests/golden/results.md`.

## Развёртывание на сервере

Нужен VPS с Ubuntu 22.04/24.04, **2–4 vCPU, 8 ГБ ОЗУ** (книга в памяти воркера ~1,7 ГБ), 20 ГБ диска.

```bash
curl -fsSL https://get.docker.com | sh
git clone <repo> suz && cd suz
cp .env.example .env          # заполнить пароли; JWT_SECRET: openssl rand -hex 32
mkdir -p data && cp /путь/к/модели.xlsx data/model.xlsx
docker compose up -d --build
```

Сайт откроется на `http://<IP сервера>` (порт — `HTTP_PORT` в `.env`). При первом старте модель из `data/model.xlsx` импортируется автоматически, воркер прогревается ~20 с. Вход — `ADMIN_LOGIN` / `ADMIN_PASSWORD` из `.env`.

Новая версия модели: войти администратором → дашборд → «Загрузить новую версию модели». Файл проверяется (листы, строки, итоги площади, пересчёт движком против значений Excel), ошибки показываются с адресами ячеек.

Пользователи:

```bash
docker compose exec backend python -m app.cli add-user ivanov            # обычный
docker compose exec backend python -m app.cli add-user petrov --admin    # администратор
docker compose exec backend python -m app.cli set-password ivanov
```

Конкуренты (сейчас демо-данные из `backend/seeds/competitors.json`) заменяются администратором через `PUT /api/projects/{id}/competitors` тем же JSON-форматом.

HTTPS: поставить перед `web` Caddy или certbot с доменом; `HTTP_PORT` сменить на внутренний.

## Разработка

```bash
# calc-worker
cd calc-worker && pip install -r requirements.txt && MODEL_DIR=../data/models uvicorn app:app --port 8001
# backend (SQLite по умолчанию)
cd backend && pip install -r requirements.txt
JWT_SECRET=dev ADMIN_LOGIN=admin ADMIN_PASSWORD=admin12345 MODEL_DIR=../data/models SEED_MODEL=../data/model.xlsx uvicorn app.main:app --port 8000
# frontend
cd frontend && npm install && npm run dev      # http://localhost:5173, /api проксируется на :8000
```

Тесты:

```bash
cd backend && MODEL_PATH=../data/model.xlsx pytest tests      # API, парсер, эталонные сценарии пересчёта
cd frontend && npm test                                       # логика ползунков
cd frontend && E2E_PASSWORD=... npx playwright test           # критерии приёмки ТЗ против запущенного стека
```

## Не входит в итерацию 1

Вкладка «Рынок», разделы «Учетные записи», «Проекты конкурентов», «Внутренние объекты», виртуальный помощник, уведомления. Открытые вопросы к заказчику — ТЗ, раздел 10.
