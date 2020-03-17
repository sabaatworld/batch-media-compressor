import time
import logging
from multiprocessing import Process, Queue, Event, JoinableQueue
from typing import Callable, List
from pie.util import MiscUtils
from logging import Logger


class PyProcessPool():
    __logger: Logger = logging.getLogger('PyProcessPool')

    def __init__(self, pool_name: str, process_count: int, log_queue: Queue, target: Callable, initializer: Callable = None, initializer_args: List = (),
                 terminator: Callable = None, terminator_args: List = (), stop_event: Event = None):
        self.__task_queue = JoinableQueue()
        self.__result_queue = Queue()
        self.__logger.debug("Initializing worker processes")
        self.__processes = []
        for process_num in range(1, process_count + 1):
            process = PyProcess("{} {}".format(pool_name, process_num), log_queue, target, self.__task_queue, initializer, initializer_args,
                                terminator, terminator_args, stop_event, self.__result_queue)
            process.start()
            self.__processes.append(process)
        self.__logger.info("PyProcessPool initialized")

    def submit_and_wait(self, tasks: List):
        self.submit(tasks)
        return self.wait_and_get_results()

    def submit(self, tasks: List):
        total_tasks = len(tasks)
        for task_num, args in enumerate(tasks, start=1):
            task = (args, "{}/{}".format(task_num, total_tasks))
            self.__task_queue.put(task)
        for _ in range(len(self.__processes)):  # Each process will pick up only one poison pill
            self.__task_queue.put(None)

    def wait_and_get_results(self):
        self.__task_queue.join()
        for process in self.__processes:
            process.terminate()
        self.__logger.info("PyProcessPool tasks completed")
        return MiscUtils.get_all_from_queue(self.__result_queue)


class PyProcess(Process):
    __logger: Logger = logging.getLogger("PyProcess")

    def __init__(self, process_name: str, log_queue: Queue, target: Callable, task_queue: JoinableQueue,
                 initializer: Callable = None, initializer_args: List = (), terminator: Callable = None, terminator_args: List = (),
                 stop_event: Event = None, result_queue: Queue = None):
        Process.__init__(self, name=process_name)
        self.__process_name = process_name
        self.__log_queue = log_queue
        self.__target = target
        self.__task_queue = task_queue
        self.__initializer = initializer
        self.__initializer_args = initializer_args
        self.__terminator = terminator
        self.__terminator_args = terminator_args
        self.__stop_event = stop_event
        self.__result_queue = result_queue

    def run(self):
        MiscUtils.configure_worker_logger(self.__log_queue)
        if (self.__initializer):
            self.__initializer(*self.__initializer_args)

        self.__logger.debug("Starting task execution loop")
        while True:
            next_task = self.__task_queue.get()
            if next_task is None:
                self.__logger.debug("Poison pill received")
                self.__task_queue.task_done()
                break
            if (self.__stop_event == None or not self.__stop_event.is_set()):
                try:
                    args = next_task[0]
                    id = next_task[1]
                    result = self.__target(*args, task_id=id)
                    if (result and self.__result_queue != None):
                        self.__result_queue.put(result)
                except:
                    self.__logger.exception("Uncaught exception while executing target")
            self.__task_queue.task_done()
        self.__logger.debug("Exited task execution loop")

        if (self.__terminator):
            self.__terminator(*self.__terminator_args)
