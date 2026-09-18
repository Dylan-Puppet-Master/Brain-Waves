from PySide6.QtCore import Qt

from brainwaves.app.sync import JobQueue


def run(queue: JobQueue) -> None:
    """Start the thread and wait for every submitted job, since stop() queues behind them."""
    queue.start()
    queue.stop()


def test_jobs_run_in_the_order_they_were_asked_for():
    order = []
    queue = JobQueue()
    for index in range(5):
        queue.submit("job", lambda n=index: order.append(n))
    run(queue)
    assert order == [0, 1, 2, 3, 4]


def test_a_failing_job_does_not_stop_the_ones_after_it():
    order = []
    queue = JobQueue()
    queue.submit("bad", lambda: 1 / 0)
    queue.submit("good", lambda: order.append("ran"))
    run(queue)
    assert order == ["ran"]


def test_a_result_is_reported_with_the_name_it_was_submitted_under():
    reported = []
    queue = JobQueue()
    queue.done.connect(lambda name, result: reported.append((name, result)), Qt.DirectConnection)
    queue.submit("reload", lambda: True)
    run(queue)
    assert reported == [("reload", True)]


def test_a_failure_is_reported_with_its_message():
    reported = []
    queue = JobQueue()
    queue.failed.connect(lambda name, text: reported.append((name, text)), Qt.DirectConnection)
    queue.submit("open", lambda: _raise("no tab 'Board'"))
    run(queue)
    assert reported == [("open", "no tab 'Board'")]


def test_waiting_counts_the_jobs_not_yet_started():
    queue = JobQueue()
    queue.submit("one", lambda: None)
    queue.submit("two", lambda: None)
    assert queue.waiting == 2
    run(queue)
    assert queue.waiting == 0


def _raise(message: str):
    raise RuntimeError(message)
