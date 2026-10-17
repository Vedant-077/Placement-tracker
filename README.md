# Placement Tracker - Cloud Computing Mini Project

Flask web app (login, add company applications, upload resume to AWS S3),
packaged with Docker, deployed on AWS EC2, auto-deployed with GitHub Actions (CI/CD),
with optional Terraform (Infrastructure as Code).

Run locally:  pip install -r requirements.txt && python app.py   -> http://localhost:5000
Run tests:    python -m pytest -q
Run in Docker: cp .env.example .env && docker compose up --build  -> http://localhost
