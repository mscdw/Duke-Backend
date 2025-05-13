from apscheduler.schedulers.background import BackgroundScheduler

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Example job: scheduler.add_job(func, 'interval', seconds=10)
    scheduler.start()
