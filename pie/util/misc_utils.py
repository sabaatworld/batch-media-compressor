import logging
import os
import sys
import shutil
import multiprocessing
from pie.domain import IndexingTask
from logging.handlers import TimedRotatingFileHandler, QueueHandler
from multiprocessing import Queue


class MiscUtils:
    __APP_LOG_FILE_NAME = "application.log"

    __logger = logging.getLogger('MiscUtils')

    def __init__(self, indexing_task: IndexingTask):
        self.__indexing_task = indexing_task

    @staticmethod
    def configure_logging(log_file_dir: str):
        os.makedirs(log_file_dir, exist_ok=True)
        formatter = logging.Formatter('[%(asctime)s][%(processName)s][%(threadName)s][%(name)s] %(levelname)5s: %(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        rolling_file_handler = TimedRotatingFileHandler(os.path.join(log_file_dir, MiscUtils.__APP_LOG_FILE_NAME), when="h", interval=1)
        rolling_file_handler.setLevel(logging.DEBUG)
        rolling_file_handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(rolling_file_handler)
        logging.info("Logging has been configured")

    @staticmethod
    def logger_thread_exec(log_queue: Queue):
        while True:
            record = log_queue.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)

    @staticmethod
    def configure_worker_logger(log_queue: Queue):
        queue_handler = QueueHandler(log_queue)
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        root_logger.setLevel(logging.DEBUG)

    @staticmethod
    def recursively_delete_children(dir: str):
        if (dir and os.path.exists(dir)):
            child_dirs = next(x[1] for x in os.walk(dir))
            for child_dir in child_dirs:
                shutil.rmtree(os.path.join(dir, child_dir))

    @staticmethod
    def debug_this_thread():
        try:
            # Only available during debugging session. It's important to not install this module in Python evnironment.
            import ptvsd
            ptvsd.debug_this_thread()
        except:
            pass

    @staticmethod
    def get_all_from_queue(queue: Queue):
        results = []
        while not queue.empty():
            results.append(queue.get_nowait())
        return results

    @staticmethod
    def get_default_worker_count():
        try:
            return multiprocessing.cpu_count()
        except:
            return 1

    @staticmethod
    def cleanEmptyDirs(path, removeRoot=True):
        'Function to remove empty folders recursively'
        if not os.path.isdir(path):
            return

        # remove empty subfolders
        files = os.listdir(path)
        if len(files):
            for f in files:
                fullpath = os.path.join(path, f)
                if os.path.isdir(fullpath):
                    MiscUtils.cleanEmptyDirs(fullpath)

        # if folder empty, delete it
        files = os.listdir(path)
        if len(files) == 0 and removeRoot:
            MiscUtils.__logger.info("Removing empty directory: %s", path)
            os.rmdir(path)

    def cleanEmptyOutputDirs(self):
        MiscUtils.__logger.info("BEGIN:: Deletion of empty output dirs")
        MiscUtils.cleanEmptyDirs(self.__indexing_task.settings.output_dir, False)
        MiscUtils.cleanEmptyDirs(self.__indexing_task.settings.unknown_output_dir, False)
        MiscUtils.__logger.info("END:: Deletion of empty output dirs")

    def create_root_marker(self):
        os.makedirs(self.__indexing_task.settings.output_dir, exist_ok=True)
        os.makedirs(self.__indexing_task.settings.unknown_output_dir, exist_ok=True)
        marker_file_name = ".pie_root"
        with open(os.path.join(self.__indexing_task.settings.output_dir, marker_file_name), 'w') as file:
            file.write("Just a marker file. Nothing interesting here.")
        with open(os.path.join(self.__indexing_task.settings.unknown_output_dir, marker_file_name), 'w') as file:
            file.write("Just a marker file. Nothing interesting here.")
