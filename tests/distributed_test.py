from src.distributed import DistributedWorkerPool
from src.executor import Executor


def execute_target(target):
    executor = Executor(target)

    try:
        result = executor.run(b"AAAA")
        return result.status.value

    finally:
        executor.close()


def test_worker_pool_runs_tasks():
    pool = DistributedWorkerPool(
        len,
        workers=2,
    )

    try:
        results = pool.map(
            [
                b"A",
                b"BB",
                b"CCC",
                b"DDDD",
            ],
            timeout=5,
        )

        assert [
            result.result
            for result in results
        ] == [
            1,
            2,
            3,
            4,
        ]

        assert all(
            result.error is None
            for result in results
        )

        assert pool.alive_workers == 2

    finally:
        pool.close()


def test_worker_pool_closes_workers():
    pool = DistributedWorkerPool(
        len,
        workers=2,
    )

    assert pool.alive_workers == 2

    pool.close()

    assert pool.alive_workers == 0


def test_worker_count_validation():
    try:
        DistributedWorkerPool(
            len,
            workers=0,
        )

        assert False

    except ValueError:
        assert True


def test_workers_can_create_their_own_executor():
    pool = DistributedWorkerPool(
        execute_target,
        workers=2,
    )

    try:
        results = pool.map(
            [
                "src/target.py",
                "src/target.py",
            ],
            timeout=10,
        )

        assert [
            result.result
            for result in results
        ] == [
            "normal",
            "normal",
        ]

        assert all(
            result.error is None
            for result in results
        )

    finally:
        pool.close()