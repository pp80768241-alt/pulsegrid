# PulseGrid — Distributed Real-Time Backend

A horizontally-scalable, real-time chat + async notification system built to
demonstrate distributed backend patterns: WebSocket fan-out across multiple
stateless replicas, load balancing, pub/sub coordination, and a decoupled
producer/consumer job queue.

```
                        ┌────────────┐
   client (WebSocket) ─▶│   Nginx    │  (ip_hash load balancer)
                        └─────┬──────┘
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌───────────┐       ┌───────────┐
              │ backend_1 │       │ backend_2 │   (stateless API replicas)
              └─────┬─────┘       └─────┬─────┘
                    │      Redis pub/sub │
                    └─────────┬──────────┘
                               ▼
                         ┌──────────┐
                         │  Redis   │  (fan-out channels + job queue)
                         └────┬─────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌───────────┐       ┌────────────┐
              │ PostgreSQL│       │   Worker   │  (async notification delivery)
              └───────────┘       └────────────┘
```

## Why this design

A WebSocket connection lives in the memory of exactly one server process. The
moment you run more than one replica behind a load balancer, a naive
implementation breaks: a message sent by a client on `backend_1` never
reaches a client connected to `backend_2`.

PulseGrid solves this the way production real-time systems do — **Redis
pub/sub as the coordination layer**. Every replica subscribes to the same
channels; whichever replica receives a message publishes it once, and every
replica (including itself) re-broadcasts it to its own locally-connected
clients. No replica ever talks to another directly, so you can add or remove
replicas freely.

Notifications follow a classic **producer/consumer** split: the API enqueues
a job in Redis and returns immediately (sub-millisecond), while a separate,
independently-scalable **worker** process pulls jobs off the queue and
handles delivery. This keeps the request path fast regardless of how slow
the actual delivery integration (email/SMS/push) is.

## Stack

| Layer          | Tech                                                    |
|-----------------|----------------------------------------------------------|
| API             | FastAPI, WebSockets, SQLAlchemy                           |
| Coordination    | Redis (pub/sub for fan-out, list for the job queue)        |
| Persistence     | PostgreSQL                                                 |
| Load balancing  | Nginx (`ip_hash`, WebSocket upgrade support)                |
| Frontend        | React (Vite)                                               |
| Infra           | Docker, docker-compose (2 API replicas + worker + Redis + Postgres + Nginx) |

## Project structure

```
pulsegrid/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, wires Redis subscriber → connection manager
│   │   ├── worker.py             # standalone async notification worker (run as its own container)
│   │   ├── connection_manager.py # tracks WebSocket clients local to THIS process
│   │   ├── redis_bus.py          # pub/sub + queue helper shared by API and worker
│   │   ├── config.py / database.py / models.py / schemas.py
│   │   └── routes/
│   │       ├── chat.py           # WebSocket endpoint + REST history
│   │       └── notifications.py  # enqueue + status endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # chat UI + notification trigger panel
│   │   └── components/           # ReplicaBadge (shows which replica served a message), NotificationPanel
│   └── Dockerfile
├── nginx/
│   └── nginx.conf                # load balancer across backend_1 / backend_2
├── docker-compose.yml
└── README.md
```

## Run it

```bash
git clone <your-repo-url>
cd pulsegrid
docker-compose up --build
```

- App: http://localhost:5173
- Load-balanced API/WebSocket entrypoint: http://localhost:8080
- API docs (hits whichever replica the load balancer picks): http://localhost:8080/docs
- Postgres: localhost:5432 · Redis: localhost:6379

Open the app in **two browser tabs** and send messages — watch the small
badge next to each message (`R1` / `R2`) to see it's genuinely being served
by different backend replicas, yet every tab stays in sync instantly.

## API reference

| Method | Endpoint                          | Description                                      |
|--------|-------------------------------------|----------------------------------------------------|
| WS     | `/ws/{room}?sender=name`            | Join a room, send/receive chat messages in real time |
| GET    | `/api/rooms/{room}/history`         | Last N persisted messages for a room                |
| POST   | `/api/notifications`                | Enqueue a notification (returns immediately)         |
| GET    | `/api/notifications/{id}`           | Check delivery status of one notification             |
| GET    | `/api/notifications?recipient=...`  | List notifications, optionally filtered               |
| GET    | `/health`                           | Per-replica health + active local connection count     |

## Scaling further

- **More replicas**: add `backend_3`, `backend_4`, etc. to `docker-compose.yml` and `nginx/nginx.conf`'s upstream block — no application code changes needed.
- **Durable, replayable events**: swap the Redis list-based queue in `worker.py` for Kafka or RabbitMQ once you need message replay, consumer groups, or guaranteed-once delivery semantics.
- **Sticky sessions at scale**: `ip_hash` works for a demo; a real deployment behind multiple load balancer nodes would use Redis-backed session affinity or a dedicated WebSocket gateway (e.g. Centrifugo, Socket.IO with a Redis adapter).
- **Observability**: the `/health` endpoint already reports per-replica connection counts — wire it into Prometheus/Grafana to visualize load distribution across replicas live.

## Push this project to your own GitHub

```bash
cd pulsegrid
git init
git add .
git commit -m "Initial commit: distributed real-time backend (PulseGrid)"
git branch -M main
git remote add origin https://github.com/<your-username>/pulsegrid.git
git push -u origin main
```

## License

MIT — use freely for your portfolio.
