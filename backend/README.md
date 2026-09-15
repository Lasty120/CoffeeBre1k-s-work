# GEOSCAN Mission Planning API — Backend

## Локальный запуск

### 1. Клонируй репозиторий и перейди в папку backend

```bash
cd backend
```

### 2. Создай виртуальное окружение и активируй его

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 3. Установи зависимости

```bash
pip install -r requirements.txt
```

### 4. Скопируй файл переменных окружения

```bash
cp .env.example .env
```

Менять ничего не нужно — значения по умолчанию подходят для локальной разработки.

### 5. Запусти сервер

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Проверка через Swagger UI

Открой в браузере: **http://localhost:8000/docs**

Там доступны:
- `POST /api/v1/missions/plan` — основной эндпоинт
- `GET /health` — health-check

---

## Быстрая проверка через curl

### Health check

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Валидный запрос планирования (минимальный пример)

```bash
curl -s -X POST http://localhost:8000/api/v1/missions/plan \
  -H "Content-Type: application/json" \
  -d '{
    "survey_area": {
      "type": "Polygon",
      "coordinates": [[
        [37.60, 55.75],
        [37.65, 55.75],
        [37.65, 55.78],
        [37.60, 55.78],
        [37.60, 55.75]
      ]]
    },
    "no_fly_zones": [],
    "home_points": [
      {
        "id": "hp-1",
        "geometry": {"type": "Point", "coordinates": [37.60, 55.75]}
      }
    ],
    "drones": [
      {
        "id": "drone-1",
        "model": "Geoscan 201",
        "kind": "fixed_wing",
        "max_flight_time_min": 90,
        "cruise_speed_mps": 18.0,
        "max_wind_speed_mps": 12.0,
        "max_altitude_agl_m": 200.0,
        "supported_survey_types": ["RGB"],
        "home_point_id": "hp-1"
      }
    ],
    "wind": {"speed_mps": 3.5, "direction_deg": 270.0},
    "survey_type": "RGB",
    "optimization_criterion": "min_time"
  }' | python -m json.tool
```

### Невалидный запрос → ожидаем HTTP 422

```bash
curl -s -X POST http://localhost:8000/api/v1/missions/plan \
  -H "Content-Type: application/json" \
  -d '{"bad": "payload"}' | python -m json.tool
```

---

## Структура проекта

```
backend/
├── main.py                  # Точка входа: FastAPI, CORS, роутеры
├── requirements.txt
├── .env.example
│
├── core/
│   ├── config.py            # Settings (pydantic-settings, .env)
│   └── logging_config.py    # setup_logging() — вызывается один раз из main.py
│
├── schemas/
│   ├── enums.py             # SurveyType, OptimizationCriterion
│   ├── geo.py               # GeoJSON-примитивы (Point, Polygon, LineString, …)
│   ├── drone.py             # DroneSpec, DroneKind
│   ├── wind.py              # WindParams
│   ├── mission_request.py   # MissionPlanningRequest, HomePoint
│   └── mission_response.py  # MissionPlanningResponse, DroneFlightPlan
│
└── api/
    └── v1/
        └── missions.py      # POST /api/v1/missions/plan (заглушка Phase 1)
```

---

## Архитектурные заметки

### `ConfigDict(frozen=True)` в GeoJSON-моделях

Все геометрии (`PointGeometry`, `PolygonGeometry` и др.) объявлены с
`model_config = ConfigDict(frozen=True)`. Это делает экземпляры **неизменяемыми**
после создания — аналог `frozen=True` в `@dataclass`. Последствия:

- Попытка `point.coordinates = (...)` после создания поднимает `TypeError` — защита от случайных мутаций в алгоритме.
- Объекты можно использовать как ключи словаря или элементы множества.
- Pydantic кэширует `__hash__`, что даёт небольшой прирост скорости при повторной валидации.
- **Компромисс:** чтобы «изменить» геометрию — создай новый экземпляр.

### Координаты LineStringGeometry — почему три числа?

`LineStringGeometry.coordinates` хранит тройки `(longitude, latitude, altitude_m)`.  
Третье число — **высота в метрах** (над эллипсоидом WGS-84, приближённо AMSL),  
а не время и не порядковый номер. Это стандарт **RFC 7946, §3.1.1**:

> "A position is an array of numbers. There MUST be two or more elements.
> The first two elements are longitude and latitude. Altitude or elevation
> MAY be included as an optional third element."

Leaflet и OpenLayers игнорируют третий элемент при рендеринге на плоской карте,
но он нужен для экспорта в KML/GeoJSON и будущей 3D-визуализации.

### Почему `home_points` вынесены из `DroneSpec`?

Самолётного типа БВС (Геоскан 201, 801) взлетают и садятся на **разных** площадках,
а мультикоптеры — на одной. Модель `HomePoint { id, geometry }` позволяет одной точке
обслуживать несколько дронов, не дублируя координаты. `DroneSpec.home_point_id` — это
ссылка по ID. Если `home_point_id == null`, планировщик использует первую точку из списка.
