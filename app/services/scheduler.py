from apscheduler.schedulers.background import BackgroundScheduler
import time

def example_task():
    print(f"Task executed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(example_task, 'interval', seconds=10)
    scheduler.start()
