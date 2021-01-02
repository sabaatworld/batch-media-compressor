import json
import logging
from threading import Thread
import webbrowser
from multiprocessing import Event
from queue import Queue
from urllib.request import urlopen

from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools

from packaging import version
from pie.core import IndexDB, IndexingHelper, MediaProcessor
from pie.domain import IndexingTask, Settings
from pie.util import MiscUtils, QWorker
from typing import Optional
import time
from threading import Thread

from logging.handlers import QueueHandler
from .preferences_window import PreferencesWindow
import logging
from collections import deque


class LogWindow:
    __logger = logging.getLogger('LogWindow')
    __UI_FILE = "assets/logwindow.ui"

    def __init__(self, qt_threadpool: QtCore.QThreadPool):
        self.__qt_threadpool = qt_threadpool

        ui_file = QtCore.QFile(MiscUtils.get_abs_resource_path(LogWindow.__UI_FILE))
        ui_file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.__window: QtWidgets.QMainWindow = loader.load(ui_file)
        ui_file.close()

        self.__cleanup_started = False
        self.__window.setWindowTitle("View Logs")
        self.__window.setFixedSize(self.__window.size())
        self.__window_visible = False

        self.__log_window_queue = Queue()
        self.__log_window_queue_handler = QueueHandler(self.__log_window_queue)
        self.__log_window_queue_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self.__log_window_queue_handler)

        self.__log_lines_to_display = deque(maxlen=3)
        self.__queue_poll_thread = Thread(target=self.queue_poll_thread_target)
        self.__queue_poll_thread.start()

        self.__log_display_thread = Thread(target=self.log_display_thread_target)
        self.__log_display_thread.start()

        self.__txt_log_display: QtWidgets.QPlainTextEdit = self.__window.findChild(QtWidgets.QPlainTextEdit, 'txt_log_display')

    def show(self):
        self.__txt_log_display.clear()
        self.__window.show()
        self.__window.raise_()
        self.__window.activateWindow()
        self.__window_visible = True

    def hide(self):
        self.__window.hide()
        self.__window_visible = False

    def cleanup(self):
        self.__logger.info("Performing cleanup")
        self.__cleanup_started = True
        self.hide()
        logging.getLogger().removeHandler(self.__log_window_queue_handler)
        self.__log_window_queue.put(None)
        self.__queue_poll_thread.join()
        self.__log_display_thread.join()
        self.__logger.info("Cleanup completed")

    def queue_poll_thread_target(self):
        self.__logger.info("Queue poll thread started")
        log_formatter = MiscUtils.get_default_log_formatter()
        while not self.__cleanup_started:
            log_record = self.__log_window_queue.get()
            if log_record is None:
                break
            log_text = log_formatter.format(log_record)
            self.__log_lines_to_display.append(log_text)

    def log_display_thread_target(self):
        self.__logger.info("Log display QT thread started")
        while not self.__cleanup_started:
            if self.__window_visible:
                qt_update_worker = QWorker(self.qt_update_thread_target)
                self.__qt_threadpool.start(qt_update_worker)
            time.sleep(1)

    def qt_update_thread_target(self, progress_callback):
        log_text_to_display = str('\n'.join(self.__log_lines_to_display))
        self.__txt_log_display.setPlainText(log_text_to_display)
        self.__txt_log_display.repaint()

    def get_log_window_queue(self) -> Queue:
        return self.__log_window_queue
