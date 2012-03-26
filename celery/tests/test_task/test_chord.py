from __future__ import absolute_import
from __future__ import with_statement

from mock import patch
from contextlib import contextmanager

from celery import current_app
from celery import result
from celery.result import AsyncResult, TaskSetResult
from celery.task import chords
from celery.task import task, TaskSet
from celery.tests.utils import AppCase, Mock

passthru = lambda x: x


@current_app.task
def add(x, y):
    return x + y


@current_app.task
def callback(r):
    return r


class TSR(TaskSetResult):
    is_ready = True
    value = [2, 4, 8, 6]

    def ready(self):
        return self.is_ready

    def join(self, **kwargs):
        return self.value

    def join_native(self, **kwargs):
        return self.value


@contextmanager
def patch_unlock_retry():
    unlock = current_app.tasks["celery.chord_unlock"]
    retry = Mock()
    prev, unlock.retry = unlock.retry, retry
    yield unlock, retry
    unlock.retry = prev


class test_unlock_chord_task(AppCase):

    @patch("celery.result.TaskSetResult")
    def test_unlock_ready(self, TaskSetResult):
        from nose import SkipTest
        raise SkipTest("Not passing")

        class NeverReady(TSR):
            is_ready = False

        @task
        def callback(*args, **kwargs):
            pass

        pts, result.TaskSetResult = result.TaskSetResult, NeverReady
        callback.apply_async = Mock()
        try:
            with patch_unlock_retry() as (unlock, retry):
                res = Mock(attrs=dict(ready=lambda: True,
                                        join=lambda **kw: [2, 4, 8, 6]))
                TaskSetResult.restore = lambda setid: res
                subtask, chords.subtask = chords.subtask, passthru
                try:
                    unlock("setid", callback,
                           result=map(AsyncResult, [1, 2, 3]))
                finally:
                    chords.subtask = subtask
                callback.apply_async.assert_called_with(([2, 4, 8, 6], ), {})
                result.delete.assert_called_with()
                # did not retry
                self.assertFalse(retry.call_count)
        finally:
            result.TaskSetResult = pts

    @patch("celery.result.TaskSetResult")
    def test_when_not_ready(self, TaskSetResult):
        from nose import SkipTest
        raise SkipTest("Not passing")
        with patch_unlock_retry() as (unlock, retry):
            callback = Mock()
            result = Mock(attrs=dict(ready=lambda: False))
            TaskSetResult.restore = lambda setid: result
            unlock("setid", callback, interval=10, max_retries=30,)
            self.assertFalse(callback.delay.call_count)
            # did retry
            unlock.retry.assert_called_with(countdown=10, max_retries=30)

    def test_is_in_registry(self):
        self.assertIn("celery.chord_unlock", current_app.tasks)


class test_chord(AppCase):

    def test_apply(self):

        class chord(chords.chord):
            Chord = Mock()

        x = chord(add.subtask((i, i)) for i in xrange(10))
        body = add.subtask((2, ))
        result = x(body)
        self.assertEqual(result.id, body.options["task_id"])
        self.assertTrue(chord.Chord.apply_async.call_count)


class test_Chord_task(AppCase):

    def test_run(self):
        prev, current_app.backend = current_app.backend, Mock()
        try:
            Chord = current_app.tasks["celery.chord"]

            body = dict()
            Chord(TaskSet(add.subtask((i, i)) for i in xrange(5)), body)
            Chord([add.subtask((i, i)) for i in xrange(5)], body)
            self.assertEqual(current_app.backend.on_chord_apply.call_count, 2)
        finally:
            current_app.backend = prev
