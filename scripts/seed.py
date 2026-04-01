"""
Генерация тестовых данных.
Запуск: python scripts/seed.py --clients 100 --reports 500
"""
import argparse
import asyncio
import random

from faker import Faker

from app.core.database import AsyncSessionLocal
from app.models import Client, Report

fake = Faker("ru_RU")

REPORT_TYPES = ["monthly", "quarterly", "annual"]
REPORT_STATUSES = ["queued", "success", "failed"]
PERIODS = [
    ("2024-01-01", "2024-01-31"),
    ("2024-02-01", "2024-02-29"),
    ("2024-03-01", "2024-03-31"),
    ("2024-04-01", "2024-04-30"),
    ("2024-Q1-01", "2024-03-31"),
    ("2023-01-01", "2023-12-31"),
]


async def seed(num_clients: int, num_reports: int):
    async with AsyncSessionLocal() as session:

        print(f"Creating {num_clients} clients...")
        clients = []
        for i in range(num_clients):
            client = Client(
                name=fake.company(),
                email=fake.unique.email(),
                client_type=random.choice(["corporate", "individual"]),
            )
            clients.append(client)
            session.add(client)

        await session.flush()
        # flush() чтобы получить ID клиентов до commit —
        # они нужны для создания отчётов.

        print(f"Creating {num_reports} reports...")
        for i in range(num_reports):
            client = random.choice(clients)
            period = random.choice(PERIODS)
            report = Report(
                client_id=client.id,
                report_type=random.choice(REPORT_TYPES),
                period_start=period[0],
                period_end=period[1],
                status=random.choice(REPORT_STATUSES),
                file_path=f"/tmp/reports/{fake.uuid4()}.pdf",
                celery_task_id=str(fake.uuid4()),
            )
            session.add(report)

        await session.commit()
        print(f"Done! Created {num_clients} clients and {num_reports} reports.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=100)
    parser.add_argument("--reports", type=int, default=500)
    args = parser.parse_args()

    asyncio.run(seed(args.clients, args.reports))
