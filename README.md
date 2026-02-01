# ETH Own Movement Tracker

Проект для выделения собственных движений цены фьючерса ETH/USDT, исключая влияние BTC/USDT. Программа работает в реальном времени, получает данные с Binance и определяет чистые движения ETH, не связанные с колебаниями Bitcoin.

## 📊 Методика анализа

### Математическая модель
Пусть 

$P_t^{\text{ETH}}$ – цена фьючерса ETH/USDT в момент $t$, 

$P_t^{\text{BTC}}$ – цена фьючерса BTC/USDT в момент $t$.

Логарифмическая доходность за интервал $\Delta t$ (например, 1 минута) определяется как: 

$r_t^{\text{ETH}} = \ln\left(\frac{P_t^{\text{ETH}}}{P_{t-\Delta t}^{\text{ETH}}}\right)$, 

$r_t^{\text{BTC}} = \ln\left(\frac{P_t^{\text{BTC}}}{P_{t-\Delta t}^{\text{BTC}}}\right)$.

Для отделения движения ETH от влияния BTC используется **скользящая линейная регрессия** между логарифмическими доходностями:


$r_t^{ETH}$ = $\alpha$ + $\beta$ $\cdot$ $r_t^{BTC}$ + $\epsilon_t$


где:
- $r_t^{ETH}$ - логарифмическая доходность ETH/USDT за интервал Δt
- $r_t^{BTC}$ - логарифмическая доходность BTC/USDT за интервал Δt
- $\beta$ - коэффициент чувствительности ETH к BTC
- $\varepsilon_t$ - остаток регрессии (собственная доходность ETH)

### Индекс собственной цены
Индекс собственной цены вычисляется путем накопления остатков:

$I_t$ = $I_{t-1}$ $\cdot$ $\exp(\varepsilon_t)$, $\quad I_0$ = 100


### Параметры модели
| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| **Интервал данных** | 1 минута | Оптимальный баланс между скоростью и стабильностью |
| **Окно регрессии** | 60 минут | Соответствует горизонту оповещения (1% за 60 мин) |
| **Метод регрессии** | OLS (МНК) | Простота и вычислительная эффективность |
| **Порог оповещения** | 1% изменение индекса за 60 мин | Требование задачи |
| **Минимальное окно** | 5 точек | Стабильная оценка коэффициентов |

## 🏗️ Структура проекта
```
ETH_own_movement/
├── src/ # Исходный код
│ ├── stream/ # Работа с потоковыми данными
│ │ └── binance_ws.py # WebSocket клиент для Binance
│ ├── models/ # Математические модели
│ │ ├── regression.py # Скользящая линейная регрессия
│ │ └── own_price_tracker.py # Трекер собственной цены
│ ├── alert/ # Логика оповещений
│ │ └── alert_manager.py # Менеджер оповещений
│ └── db/ # Работа с базой данных
│ ├── database.py # Подключение к БД
│ ├── models.py # SQLAlchemy модели
│ └── crud.py # CRUD операции
├── tests/ # Тесты
├── config/ # Конфигурация
│ └── settings.py # Настройки приложения
├── docker/ # Docker конфигурации
│ └── postgres/ # Инициализация PostgreSQL
├── main.py # Основное приложение
├── demo.py # Демо-режим с генерацией данных
├── Dockerfile # Docker образ приложения
├── docker-compose.yml # Docker Compose конфигурация
├── requirements.txt # Зависимости Python
├── pytest.ini # Конфигурация тестов
└── .env.example # Шаблон переменных окружения
```

## 🚀 Установка и запуск

### Запуск через Docker Compose

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/LexaSolovev/ETH_own_movement.git
cd ETH_own_movement

# 2. Настройте окружение
cp .env.example .env
# При необходимости отредактируйте .env

# 3. Запустите приложение
docker-compose up --build

# 4. Для фонового режима
docker-compose up --build -d
docker-compose logs -f app
```

### Демо-режим (без реальных данных)

```bash
python demo.py
```

## ⚙️ Конфигурация
### Основные настройки в .env

    # База данных
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=eth_btc
    DB_USER=user
    DB_PASSWORD=password
    DB_URL=postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}
    
    # Логирование
    LOG_LEVEL=INFO
    
    # Binance WebSocket
    BINANCE_WS_URL=wss://stream.binance.com:9443/ws


### Параметры регрессии (config/settings.py)

    WINDOW_SIZE=60 - размер окна регрессии (в минутах)
    ALERT_THRESHOLD=0.01 - порог оповещения (1%)
    MIN_WINDOW_FOR_REGRESSION=5 - минимальное количество точек для расчета
    ALERT_COOLDOWN_MINUTES=5 - задержка между оповещениями

## 🧪 Тестирование
```bash
# Запуск всех тестов
pytest -v
```
```bash
# Запуск тестов с покрытием
pytest --cov=src --cov-report=html
```

## 📈 Пример работы

### Вывод при успешном старте:
```
app-1  | 2026-01-19 20:49:31,102 - src.models.regression - INFO - Initialized RollingRegression with window size: 60
app-1  | 2026-01-19 20:49:31,121 - src.models.own_price_tracker - INFO - Initialized OwnPriceTracker with initial index: 100.0
app-1  | 2026-01-19 20:49:31,121 - src.alert.alert_manager - INFO - Initialized AlertManager with cooldown: 5 minutes
app-1  | 2026-01-19 20:49:31,122 - __main__ - INFO - ETH Own Movement App initialized
app-1  | 2026-01-19 20:49:31,427 - src.db.database - INFO - Database connection established
app-1  | 2026-01-19 20:49:31,427 - __main__ - INFO - Database connected
app-1  | 2026-01-19 20:49:31,427 - __main__ - INFO - Starting ETH Own Movement Tracker...
app-1  | 2026-01-19 20:49:31,427 - src.stream.binance_ws - INFO - Connecting to WebSocket: wss://stream.binance.com:9443/ws
app-1  | 2026-01-19 20:49:32,705 - src.stream.binance_ws - INFO - Subscribed to streams: ['ethusdt@kline_1m', 'btcusdt@kline_1m']
app-1  | 2026-01-19 21:00:00,248 - __main__ - INFO - Status: Index=99.9860, Beta=0.0426, Epsilon=-0.000085, Window=10
```

### Оповещение при достижении порога

```
============================================================
ALERT: Собственная цена ETH изменилась на 1.05% за последние 60 минут (росте).
Текущий индекс: 101.05
Порог: 1.0%
Time: 2026-01-17 16:12:00
============================================================
```

## 🔧 Технические детали
### Архитектура

- **ООП подход**: Каждый компонент инкапсулирован в отдельный класс

- **Асинхронность**: Использование asyncio для работы с WebSocket и БД

- **Модульность**: Четкое разделение на слои (поток данных, модели, оповещения, БД)

### Производительность

- **Алгоритмическая сложность**: O(1) для обновления регрессии, O(n) для расчета (n=60)

- **Память**: Используется дэк (deque) фиксированного размера для скользящего окна

- **Сеть**: WebSocket с автоматическим переподключением при обрыве

### Надежность

- **Обработка ошибок**: Комплексная обработка исключений для всех компонентов

- **Логирование**: Подробное логирование в консоль и файл

- **Восстановление**: Автоматический перезапуск при сбоях соединения

## 🗄️ База данных

### Схема данных

```sql
-- Ценовые бары
CREATE TABLE price_bars (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(20,8),
    high DECIMAL(20,8),
    low DECIMAL(20,8),
    close DECIMAL(20,8),
    volume DECIMAL(30,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Результаты регрессии
CREATE TABLE regression_results (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    alpha DECIMAL(20,8),
    beta DECIMAL(20,8),
    epsilon DECIMAL(20,8),
    own_price_index DECIMAL(20,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Оповещения
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    message TEXT NOT NULL,
    change_percent DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
## 🔍 Мониторинг

### Просмотр логов

```bash
# Логи приложения
tail -f logs/app.log

# Логи Docker контейнеров
docker-compose logs -f app
docker-compose logs -f db

# Просмотр последних 100 строк
docker-compose logs --tail=100 app
```

## 📚 API Binance

### Проект использует публичный WebSocket API Binance:

- **URL**: wss://stream.binance.com:9443/ws

- **Потоки**: ethusdt@kline_1m, btcusdt@kline_1m

- **Данные**: Ценовые бары (open, high, low, close, volume) каждую минуту
