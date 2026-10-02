# Практическая работа № 1. Прототип веб-приложения TCP RPC

- **Дисциплина**: Прикладная разработка серверных частей веб-приложений на языке Питон
- **Кафедра**: Корпоративных информационных систем, Институт информационных технологий, РТУ МИРЭА
- **Студент**: Хромченков Д. Д.
- **Группа**: ИКБО-70-24
- **Преподаватель**: Горчаков Артём Владимирович
- **Вариант**: № 22

---

## 1. Общее описание

Данный проект представляет собой прототип серверного веб-приложения с поддержкой удалённого вызова процедур (Remote Procedure Call, RPC) на основе сетевого протокола TCP. В соответствии с заданием сохранение данных на диск не производится — всё управление данными осуществляется в оперативной памяти.

Схема данных соответствует ER-диаграмме варианта 22:
- **`Session`**: сессия пользователя (`uid: int [PK]`, `timestamp: int`, `locale: str`, `user_agent: str`).
- **`Request`**: входящий запрос (`uid: int [PK]`, `timestamp: int`, `content: str`, `session: int [FK -> Session.uid]`, `triggered: int`). Связь с `Session`: «один ко многим» ($1 : N$).
- **`Answer`**: ответ/результат обработки запроса (`uid: int [PK]`, `timestamp: int`, `output: str`, `status: str`, `exception: str`, `request: int [FK -> Request.uid]`, `cache_hit: int`). Связь с `Request`: «один ко многим» ($1 : N$).

Проект состоит из трёх взаимосвязанных этапов:
1. **Этап 1 (Модель слоя доступа к данным)**: представление записей таблиц кортежами (`namedtuple`/`tuple`), 12 операций CRUD для трёх сущностей, операция выборки данных с правым внешним соединением по формуле реляционной алгебры (13-я операция), интерактивный REPL.
2. **Этап 2 (TCP RPC служба)**: бинарное обрамление пакетов (Table 22), XML-сериализация параметров и результатов, журналирование всех ответов сервера в файл `journal.log`, класс RPC-клиента `RPCClient` с именами методов, совпадающими с именами функций сервера.
3. **Этап 3 (Тестирование на основе моделей, MBT)**: верификация всех 13 методов RPC-сервера с использованием библиотеки `hypothesis` (`RuleBasedStateMachine`) и отчётом покрытия ветвей кода утилитой `coverage`.

---

## 2. Описание всех функций и настроек

### 2.1. Конфигурация и параметры (`src/constants.py`)

| Параметр | Значение по умолчанию | Описание |
|---|---|---|
| `DEFAULT_HOST` | `127.0.0.1` | Сетевой адрес TCP RPC сервера |
| `DEFAULT_PORT` | `9922` | Порт TCP RPC сервера |
| `JOURNAL_FILE` | `journal.log` | Файл журнала ответов RPC |
| `BYTE_ORDER` | `big` | Порядок байт в сетевом протоколе (Big-Endian) |
| `QUERY_TIME_WINDOW_SECONDS` | `360` (6 мин) | Временное окно фильтрации сессий $\sigma_{S.timestamp \ge now - 6\text{ min}}$ |

### 2.2. Функции слоя данных (`src/data_layer.py`)

1. `create_session(uid, timestamp, locale, user_agent) -> SessionRecord`: создание записи сессии.
2. `delete_session(uid) -> bool`: удаление сессии по первичному ключу (с проверкой отсутствия связанных запросов).
3. `get_all_sessions() -> list[SessionRecord]`: получение списка всех сессий.
4. `update_session(uid, timestamp=None, locale=None, user_agent=None) -> SessionRecord`: редактирование сессии.
5. `create_request(uid, timestamp, content, session, triggered) -> RequestRecord`: создание запроса с валидацией внешнего ключа `session`.
6. `delete_request(uid) -> bool`: удаление запроса (с проверкой отсутствия связанных ответов).
7. `get_all_requests() -> list[RequestRecord]`: получение списка всех запросов.
8. `update_request(uid, timestamp=None, content=None, session=None, triggered=None) -> RequestRecord`: редактирование запроса.
9. `create_answer(uid, timestamp, output, status, exception, request, cache_hit) -> AnswerRecord`: создание ответа с валидацией внешнего ключа `request`.
10. `delete_answer(uid) -> bool`: удаление ответа по идентификатору.
11. `get_all_answers() -> list[AnswerRecord]`: получение списка всех ответов.
12. `update_answer(uid, timestamp=None, output=None, status=None, exception=None, request=None, cache_hit=None) -> AnswerRecord`: редактирование ответа.
13. `query_sessions_requests(now=None) -> list[tuple]`: реализация формулы реляционной алгебры:
    $$\pi_{R.content, S.locale} \left( (\sigma_{S.timestamp \ge now - 6\text{ min}}(S)) \rightouterjoin_{S.uid = R.session} R \right)$$

### 2.3. Спецификация TCP RPC протокола (Таблица 22)

**Порядок байт**: от старшего к младшему (Big-Endian).

**Структура запроса**:
- Байт 0 (1 байт): Код операции (`op_code`: 1..13).
- Байты 1..3 (3 байта): Размер тела запроса в байтах.
- Байты 4.. (длина тела): Тело запроса в формате XML (UTF-8).

**Структура ответа**:
- Байты 0..4 (5 байт): Размер тела ответа в байтах.
- Байт 5 (1 байт): Код операции (`op_code`: 1..13).
- Байты 6.. (длина тела): Тело ответа в формате XML (UTF-8).

---

## 3. Описание команд для сборки проекта и запуска тестов

### 3.1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3.2. Автоматический единый запуск проверок
- **Windows (cmd/powershell)**:
  ```cmd
  run.bat
  ```
- **Linux/macOS (bash)**:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```
- **С использованием Makefile**:
  ```bash
  make all
  ```

### 3.3. Раздельный запуск этапов
- **Проверка оформления кода (PEP8 / flake8)**:
  ```bash
  flake8 --max-line-length=79 src tests
  ```
- **Демонстрация Этапа 1 (REPL и слой данных)**:
  ```bash
  python -m src.demo_repl
  ```
- **Интерактивный вход в консоль REPL**:
  ```bash
  python -m src.repl
  ```
- **Демонстрация Этапа 2 (TCP RPC сервер и клиент)**:
  ```bash
  python -m src.demo_client
  ```
- **Запуск standalone RPC сервера**:
  ```bash
  python -m src.server
  ```
- **Демонстрация Этапа 3 (Hypothesis MBT + покрытие coverage)**:
  ```bash
  python -m coverage run --branch -m pytest tests/test_mbt.py -v
  python -m coverage report -m
  ```

---

## 4. Примеры использования

### 4.1. Работа с интерактивным REPL (Этап 1)
```text
variant22> add-session 1 1700000000 ru-RU Chrome/120
Session created: SessionRecord(uid=1, timestamp=1700000000, locale='ru-RU', user_agent='Chrome/120')

variant22> add-request 10 1700000050 "SELECT 1" 1 1
Request created: RequestRecord(uid=10, timestamp=1700000050, content='SELECT 1', session=1, triggered=1)

variant22> add-answer 100 1700000060 ok 200 None 10 1
Answer created: AnswerRecord(uid=100, timestamp=1700000060, output='ok', status='200', exception='None', request=10, cache_hit=1)

variant22> query-join 1700000100
Query result (content, locale) (1): [('SELECT 1', 'ru-RU')]
```

### 4.2. Использование RPC-клиента в Python коде (Этап 2)
```python
from src.client import RPCClient

with RPCClient(host="127.0.0.1", port=9922) as client:
    # 1. Создание сессии и запроса
    s = client.create_session(1, 1700000000, "ru-RU", "Mozilla/5.0")
    r = client.create_request(10, 1700000050, "GET /api/v1", 1, 1)

    # 2. Выполнение реляционной выборки
    results = client.query_sessions_requests(now=1700000200)
    print(results)  # [('GET /api/v1', 'ru-RU')]

    # 3. Удаление
    client.delete_request(10)
    client.delete_session(1)
```

### 4.3. Пример записи журнала RPC (`journal.log`)
```text
[2026-10-02T19:50:33.366632] Client: 127.0.0.1:50062 | OpCode: 1 | Length: 148 | Body: <response><status>success</status><result><tuple><int>1</int><int>1700000000</int><str>ru-RU</str><str>Mozilla/5.0</str></tuple></result></response>
```
