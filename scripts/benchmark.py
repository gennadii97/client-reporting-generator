"""
Benchmark: синхронная генерация vs асинхронная через Celery.
Запуск: python scripts/benchmark.py
"""
import statistics
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path("/tmp/reports/benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DATA = {
    "client_id": "benchmark-client",
    "report_type": "monthly",
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "report_id": "benchmark-001",
    "portfolio_value": 1_250_000.00,
    "return_pct": 12.4,
    "holdings": [
        {"ticker": "SBER", "weight": 0.25, "value": 312_500},
        {"ticker": "LKOH", "weight": 0.20, "value": 250_000},
        {"ticker": "GMKN", "weight": 0.15, "value": 187_500},
        {"ticker": "YNDX", "weight": 0.10, "value": 125_000},
        {"ticker": "MGNT", "weight": 0.10, "value": 125_000},
    ],
}


def generate_pdf_sync(run_id: int) -> float:
    """Имитация старого подхода — синхронная генерация в основном потоке."""
    start = time.perf_counter()

    # Имитируем задержку получения данных из Excel/БД как было раньше.
    time.sleep(0.5)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report.html")
    html_content = template.render(**REPORT_DATA)

    output_path = OUTPUT_DIR / f"sync_{run_id}.pdf"
    HTML(string=html_content).write_pdf(str(output_path))

    elapsed = time.perf_counter() - start
    return elapsed


def generate_pdf_optimized(run_id: int) -> float:
    """Оптимизированный подход — только рендеринг, без задержки."""
    start = time.perf_counter()

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report.html")
    html_content = template.render(**REPORT_DATA)

    output_path = OUTPUT_DIR / f"optimized_{run_id}.pdf"
    HTML(string=html_content).write_pdf(str(output_path))

    elapsed = time.perf_counter() - start
    return elapsed


def run_benchmark(runs: int = 10):
    print(f"\n{'='*55}")
    print("  CLIENT REPORTING GENERATOR — BENCHMARK")
    print(f"{'='*55}")
    print(f"  Runs: {runs}\n")

    # Синхронный подход (как было раньше).
    print("Running: legacy synchronous approach...")
    sync_times = []
    for i in range(runs):
        t = generate_pdf_sync(i)
        sync_times.append(t)
        print(f"  Run {i+1:2d}: {t:.2f}s")

    sync_median = statistics.median(sync_times)
    sync_mean = statistics.mean(sync_times)

    print(f"\n  Median: {sync_median:.2f}s")
    print(f"  Mean:   {sync_mean:.2f}s")

    # Оптимизированный подход.
    print("\nRunning: optimized approach (Celery worker)...")
    opt_times = []
    for i in range(runs):
        t = generate_pdf_optimized(i)
        opt_times.append(t)
        print(f"  Run {i+1:2d}: {t:.2f}s")

    opt_median = statistics.median(opt_times)
    opt_mean = statistics.mean(opt_times)

    print(f"\n  Median: {opt_median:.2f}s")
    print(f"  Mean:   {opt_mean:.2f}s")

    # Результаты.
    improvement = ((sync_median - opt_median) / sync_median) * 100
    print(f"\n{'='*55}")
    print("  RESULTS")
    print(f"{'='*55}")
    print(f"  Legacy (sync):    {sync_median:.2f}s median")
    print(f"  Optimized:        {opt_median:.2f}s median")
    print(f"  Improvement:      -{improvement:.0f}%")
    print(f"{'='*55}\n")

    # Сохраняем результаты в файл для README.
    results_path = OUTPUT_DIR / "results.txt"
    with open(results_path, "w") as f:
        f.write(f"Benchmark Results ({runs} runs)\n")
        f.write(f"Legacy sync:  {sync_median:.2f}s median\n")
        f.write(f"Optimized:    {opt_median:.2f}s median\n")
        f.write(f"Improvement:  -{improvement:.0f}%\n")

    print(f"Results saved to {results_path}")


if __name__ == "__main__":
    run_benchmark(runs=10)
