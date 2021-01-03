import hashlib
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
from logging.handlers import QueueHandler, TimedRotatingFileHandler
from multiprocessing import Queue
from typing import List

from appdirs import user_data_dir

from pie.domain import IndexingTask


class MiscUtils:
    __APP_LOG_FILE_NAME = "application.log"

    __logger = logging.getLogger('MiscUtils')

    def __init__(self, indexing_task: IndexingTask):
        self.__indexing_task = indexing_task

    @staticmethod
    def get_app_data_dir():
        app_data_dir = user_data_dir("Batch Media Compressor", "Two Hand Apps") if (MiscUtils.running_in_pyinstaller_bundle()) else MiscUtils.get_abs_resource_path("app_data")
        os.makedirs(app_data_dir, exist_ok=True)
        return app_data_dir

    @staticmethod
    def get_lock_file_path():
        return os.path.join(MiscUtils.get_app_data_dir(), "run.lock")

    @staticmethod
    def get_log_dir_path():
        return os.path.join(MiscUtils.get_app_data_dir(), "logs")

    @staticmethod
    def configure_logging():
        log_file_dir = MiscUtils.get_log_dir_path()
        os.makedirs(log_file_dir, exist_ok=True)
        formatter = MiscUtils.get_default_log_formatter()
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
    def get_default_log_formatter() -> logging.Formatter:
        return logging.Formatter('[%(asctime)s][%(processName)s][%(threadName)s][%(name)s] %(levelname)5s: %(message)s')

    @staticmethod
    def logger_thread_exec(log_queue: Queue):
        while True:
            record = log_queue.get()
            if record is None:
                break
            try:
                logger = logging.getLogger(record.name)
                logger.handle(record)
            except:
                MiscUtils.__logger.exception('Exception in logging thread')

    @staticmethod
    def configure_worker_logger(log_queue: Queue):
        queue_handler = QueueHandler(log_queue)
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        root_logger.setLevel(logging.DEBUG)

    @staticmethod
    def recursively_delete_children(dir: str):
        if (dir and os.path.exists(dir)):
            for file in next(x[2] for x in os.walk(dir)):
                os.remove(os.path.join(dir, file))
            for child_dir in next(x[1] for x in os.walk(dir)):
                shutil.rmtree(os.path.join(dir, child_dir))

    @staticmethod
    def debug_this_thread():
        try:
            # Only available during debugging session. It's important to not install this module in Python evnironment.
            import debugpy
            debugpy.debug_this_thread()
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
        if files is not None:
            for file in files:
                fullpath = os.path.join(path, file)
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

    @staticmethod
    def generate_hash(file_path: str) -> str:
        with open(file_path, "rb") as file:
            file_hash = hashlib.sha1()
            while chunk := file.read(1048576): # 1MB in bytes
                file_hash.update(chunk)
        return file_hash.hexdigest()

    @staticmethod
    def get_abs_resource_path(rel_path: str) -> str:
        base_dir = getattr(sys, '_MEIPASS', os.getcwd())
        return os.path.join(base_dir, rel_path)

    @staticmethod
    def get_app_icon_path() -> str:
        file_name = "pie_logo.ico" if MiscUtils.is_platform_win() else "pie_logo.png"
        file_path = MiscUtils.get_abs_resource_path(os.path.join('assets', file_name))
        return file_path

    @staticmethod
    def is_platform_win() -> bool:
        return sys.platform == 'win32' or sys.platform == 'cygwin'

    @staticmethod
    def running_in_pyinstaller_bundle() -> bool:
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    # Adapted from https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
    @staticmethod
    def subprocess_args(include_stdout=True):
        # The following is true only on Windows.
        if hasattr(subprocess, 'STARTUPINFO'):
            # On Windows, subprocess calls will pop up a command window by default
            # when run from Pyinstaller with the ``--noconsole`` option. Avoid this
            # distraction.
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # Windows doesn't search the path by default. Pass it an environment so
            # it will.
            env = os.environ
        else:
            si = None
            env = None

        # ``subprocess.check_output`` doesn't allow specifying ``stdout``::
        #
        #   Traceback (most recent call last):
        #     File "test_subprocess.py", line 58, in <module>
        #       **subprocess_args(stdout=None))
        #     File "C:\Python27\lib\subprocess.py", line 567, in check_output
        #       raise ValueError('stdout argument not allowed, it will be overridden.')
        #   ValueError: stdout argument not allowed, it will be overridden.
        #
        # So, add it only if it's needed.
        if include_stdout:
            ret = {'stdout': subprocess.PIPE}
        else:
            ret = {}

        # On Windows, running this from the binary produced by Pyinstaller
        # with the ``--noconsole`` option requires redirecting everything
        # (stdin, stdout, stderr) to avoid an OSError exception
        # "[Error 6] the handle is invalid."
        ret.update({
            'stdin': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'startupinfo': si,
            'env': env,
            'close_fds': True,
        })
        return ret

    @staticmethod
    def exec_subprocess(popenargs: List[str], errorMsg: str):
        results = subprocess.run(popenargs, **MiscUtils.subprocess_args())
        if results.returncode != 0:
            raise RuntimeError("{}: CommandLine: {}, Output: {}".format(errorMsg, subprocess.list2cmdline(popenargs), str(results.stderr)))
