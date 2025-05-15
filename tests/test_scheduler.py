from app.services.scheduler import example_task
import time

def test_example_task(capfd):
    # Capture the output of the example_task
    example_task()
    captured = capfd.readouterr()
    assert "Task executed at" in captured.out
    assert time.strftime('%Y-%m-%d %H:%M:%S') in captured.out
