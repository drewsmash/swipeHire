# SwipeHire

Swipe right on jobs. Match when the employer swipes right on you.
Group 15 project – Flask + MySQL, runs in Docker.

```bash
cp .env.example .env     # change the passwords
docker compose up --build -d
```

Open http://localhost:8300 and log in with `seeker@swipehire.test` or
`google@swipehire.test` (password = `DEMO_PASSWORD` in `.env`, default `swipehire`),
or click a guest button. Admin dashboard: `admin@swipehire.test`.

Full details – file map, data model, conventions, TODO list – are in [AGENTS.md](AGENTS.md).
