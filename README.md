# Weather-Aware Truck Routing Backend

Django REST API that plans truck routes, checks the weather each route will meet, and recommends the safest one.

- Live API: https://weather-aware-t-routing-backend.vercel.app/api/
- API docs: https://weather-aware-t-routing-backend.vercel.app/api/docs/
- Frontend: https://weather-aware-t-routing.vercel.app
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## What it does

- Finds up to 3 alternative routes (OSRM).
- Places checkpoints every 10, 25 or 50 miles and calculates the truck's ETA at each.
- Gets the forecast at each checkpoint's ETA (Open-Meteo).
- Rates wind, rain and snow risk, including truck load rules.
- Recommends a route and explains why.
- Saves trips and serves a 48-hour weather heatmap.

Stack: Python 3.10+, Django 5.2, Django REST Framework. Database: PostgreSQL in production, SQLite locally if no database is configured. Place search uses Photon. No API keys needed.

## Risk rules

| Risk | Wind (mph) | Rain (in/hr) | Snow (in/hr) |
|---|---|---|---|
| Low | under 25 | under 0.10 | under 0.5 |
| Moderate | 25 to under 35 | 0.10 to under 0.25 | 0.5 to under 1.0 |
| High | 35 to under 45 | 0.25 to under 0.50 | 1.0 to under 2.0 |
| Severe | 45 to under 55 | 0.50 to 1.00 | 2.0 to 3.0 |
| No Travel | 55 or more | over 1.00 | over 3.0 |

A checkpoint takes the worst of the three.

Load rules:
- Wind 45–54 mph with a load over 30,000 lb is No Travel.
- Wind 35–44 mph with a load over 40,000 lb is Severe.

Missing forecast data is marked unknown, never Low.

Routes are ranked by fewest No Travel miles, then Severe, then unknown, then High miles, then lowest average risk, then shortest time.

## Setup

```bash
git clone https://github.com/kiani007/weather-aware-t-routing-backend.git
cd weather-aware-t-routing-backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The API runs at http://127.0.0.1:8000/api/.

Main settings in `.env`:

| Variable | Example |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` |
| `DJANGO_SECRET_KEY` | any long random string |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `DATABASE_URL` | `postgres://user:pass@host:5432/watr` (optional locally, SQLite is used if unset) |

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Health check |
| GET | `/api/geocoding/search/?q=Denver` | Place search |
| POST | `/api/trips/` | Plan a trip |
| GET | `/api/trips/{id}/` | Get a saved trip |
| GET | `/api/trips/{id}/heatmap/` | 48-hour weather frames around the routes |

Example request:

```bash
curl -X POST https://weather-aware-t-routing-backend.vercel.app/api/trips/ \
  -H "Content-Type: application/json" \
  -d '{"origin": {"label": "Chicago, IL", "lat": 41.88, "lon": -87.62},
       "destination": {"label": "St. Louis, MO", "lat": 38.63, "lon": -90.20},
       "departure_at": "2026-12-01T14:00:00Z",
       "load_weight_lb": 35000,
       "sample_interval_mi": 25}'
```

Example response (a real trip, shortened to one of its 3 routes and two of its checkpoints):

```json
{
  "id": "e8eb14dc-ed1f-4e28-be3c-b48df36cd43f",
  "origin_label": "Dallas, TX",
  "destination_label": "Houston, TX",
  "departure_at": "2026-11-27T23:00:00Z",
  "load_weight_lb": 35000,
  "sample_interval_mi": 25,
  "routes": [
    {
      "name": "Route A",
      "distance_mi": 238.3,
      "duration_s": 15151.0,
      "arrival_at": "2026-11-28T03:12:30.548211Z",
      "risk_miles": { "low": 238.3, "moderate": 0.0, "high": 0.0, "severe": 0.0, "no_travel": 0.0 },
      "unknown_miles": 0.0,
      "average_risk": 0.0,
      "max_risk": { "value": 0, "key": "low", "label": "Low" },
      "forecast_coverage": 1.0,
      "is_recommended": true,
      "recommendation_reason": "Equal weather risk and the shortest travel time (4.2 h vs 5.0 h on the next best route).",
      "checkpoints": [
        {
          "mile_marker": 0.0,
          "eta": "2026-11-27T23:00:00Z",
          "wind_mph": 7.6, "rain_in_hr": 0.0, "snow_in_hr": 0.0,
          "risk": { "value": 0, "key": "low", "label": "Low" },
          "reasons": []
        },
        {
          "mile_marker": 25.0,
          "eta": "2026-11-27T23:28:53.787835Z",
          "wind_mph": 10.237, "rain_in_hr": 0.0, "snow_in_hr": 0.0,
          "risk": { "value": 0, "key": "low", "label": "Low" },
          "reasons": []
        }
      ]
    }
  ]
}
```

When a value can't be verified, `risk`, `max_risk` and `average_risk` are `null`.

## Tests

```bash
python manage.py test --settings=config.settings.test
```

## Deployment

Deployed on Vercel with a Neon PostgreSQL database. The build command in `vercel.json` runs the migrations on every deploy.

Set these in Vercel:
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS=.vercel.app`
- `DATABASE_URL`

## Limitations

- **External services:** routes and weather come from free public services (OSRM, Open-Meteo). If they are down or rate-limited, planning fails with a clear error.
- **Forecast horizon:** departures are limited to the next 7 days.
- **Truck routing:** OSRM uses a car profile. Truck speed is capped at 65 mph, but height, weight and hazmat restrictions are not considered.
- **Traffic:** ETAs use typical travel times, not real-time traffic.
