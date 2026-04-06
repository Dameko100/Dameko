# Dameko News Bot

Automatización que monitorea noticias del mundo real en tiempo real y envía alertas por Telegram con mercados de predicción relacionados en [Polymarket](https://polymarket.com).

## ¿Qué hace?

- Monitorea **RSS feeds** de decenas de fuentes (Reuters, BBC, NYT, TechCrunch, CoinTelegraph, etc.)
- Opcionalmente usa **NewsAPI** para cobertura más amplia
- Extrae palabras clave de cada noticia y **busca mercados activos en Polymarket**
- Envía **alertas por Telegram** con:
  - Título y resumen de la noticia
  - Link a la fuente original
  - Lista de mercados de Polymarket relacionados con sus probabilidades actuales
- **Digest diario** con los mercados más activos de Polymarket
- **SQLite** para evitar notificaciones duplicadas

## Categorías cubiertas

| Emoji | Categoría |
|-------|-----------|
| 💰 | Finanzas (Fed, bolsa, commodities) |
| 💻 | Tecnología |
| 🏛️ | Política y elecciones |
| ⚔️ | Conflictos y guerras |
| 🤖 | Inteligencia Artificial |
| ₿ | Crypto |
| 🌍 | Noticias mundiales |

## Ejemplo de alerta

```
⚔️ Wars Conflicts

*Ukraine and Russia reach ceasefire deal*

_Negotiators announced a preliminary ceasefire agreement..._

🔗 Leer noticia
📡 Fuente: Reuters

─────────────────────────
📊 Mercados relacionados en Polymarket:

• Will Ukraine-Russia ceasefire hold through 2025?
  └ Yes: 34% / No: 66% | Vol: $2,450,000
• Will Putin resign in 2025?
  └ Yes: 8% / No: 92% | Vol: $890,000
```

## Setup

### 1. Clonar y configurar entorno

```bash
git clone <repo>
cd Dameko
python -m venv venv
source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Crear bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Escribe `/newbot` y sigue las instrucciones
3. Guarda el **token** que te da
4. Envía un mensaje a tu bot y luego visita:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   para obtener tu **chat_id**

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tu editor y rellena los valores
```

Variables requeridas:
- `TELEGRAM_BOT_TOKEN` — token de tu bot
- `TELEGRAM_CHAT_ID` — tu chat ID personal o de grupo

Variables opcionales:
- `NEWSAPI_KEY` — key gratis en [newsapi.org](https://newsapi.org) (amplía cobertura)
- `POLL_INTERVAL_MINUTES` — frecuencia de polling (default: 10 min)
- `MIN_IMPORTANCE_SCORE` — umbral de importancia (default: 0.2, rango 0-1)

### 4. Ejecutar

```bash
python main.py
```

## Estructura del proyecto

```
Dameko/
├── main.py                  # Punto de entrada y scheduler
├── config.py                # Configuración desde .env
├── requirements.txt
├── .env.example
├── src/
│   ├── news_fetcher.py      # RSS + NewsAPI
│   ├── polymarket.py        # Cliente API Polymarket
│   ├── telegram_notifier.py # Envío de mensajes Telegram
│   ├── matcher.py           # Extracción de keywords y scoring
│   └── storage.py           # SQLite para deduplicación
└── data/
    └── dameko.db            # Base de datos (auto-creada)
```

## Despliegue continuo

Para mantener el bot corriendo 24/7:

**Con systemd (Linux):**
```ini
# /etc/systemd/system/dameko.service
[Unit]
Description=Dameko News Bot

[Service]
WorkingDirectory=/path/to/Dameko
ExecStart=/path/to/venv/bin/python main.py
Restart=always
EnvironmentFile=/path/to/Dameko/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable dameko
sudo systemctl start dameko
```

**Con Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Licencia

Apache License 2.0
