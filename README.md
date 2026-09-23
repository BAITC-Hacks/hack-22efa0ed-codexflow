# CodexFlow — умный подбор подрядчиков

Командный репозиторий хакатона. Backend, исходный каталог и тесты находятся в
[`recommendation-logic/`](recommendation-logic/README.md) — «логика подбора».

Из корня репозитория:

```powershell
cd recommendation-logic
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m uvicorn src.api:app --reload
```

Интерактивная документация: http://127.0.0.1:8000/docs

Сценарии команды для демонстрации: [docs/demo-cases.md](docs/demo-cases.md).

Сайт после запуска: http://127.0.0.1:8000/ui/

Для подготовки README и защиты: [результаты проверки ТЗ и описание пайплайна](docs/acceptance-report.md),
[инструкция по интеграции и запуску](recommendation-logic/HANDOFF.md).
