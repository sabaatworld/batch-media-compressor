import logging
import os
import webbrowser
from logging.handlers import QueueHandler
from queue import Queue

from PySide2 import QtCore, QtUiTools, QtWidgets

from pie.util import MiscUtils, QWorker


class LogWindow:
    __logger = logging.getLogger('LogWindow')
    __UI_FILE = "assets/logwindow.ui"
    __LINES_TO_DISPLAY = 5000

    def __init__(self, qt_threadpool: QtCore.QThreadPool):
        self.__qt_threadpool = qt_threadpool

        ui_file = QtCore.QFile(MiscUtils.get_abs_resource_path(LogWindow.__UI_FILE))
        ui_file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.__window: QtWidgets.QMainWindow = loader.load(ui_file)
        ui_file.close()

        self.__cleanup_started = False
        self.__window.setWindowTitle("View Logs")

        self.__log_window_queue = Queue()
        self.__log_window_queue_handler = QueueHandler(self.__log_window_queue)
        self.__log_window_queue_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self.__log_window_queue_handler)

        self.qt_worker = QWorker(self.__queue_poll_thread_target)
        self.qt_worker.signals.progress.connect(self.__queue_poll_thread_progress)
        self.__qt_threadpool.start(self.qt_worker)

        self.__txt_log_display: QtWidgets.QPlainTextEdit = self.__window.findChild(QtWidgets.QPlainTextEdit, 'txt_log_display')
        self.__btn_clear: QtWidgets.QPushButton = self.__window.findChild(QtWidgets.QPushButton, 'btn_clear')
        self.__btn_log_dir: QtWidgets.QPushButton = self.__window.findChild(QtWidgets.QPushButton, 'btn_log_dir')

        self.__txt_log_display.setMaximumBlockCount(self.__LINES_TO_DISPLAY)
        self.__btn_clear.clicked.connect(self.__btn_clear_clicked)
        self.__btn_log_dir.clicked.connect(self.__btn_log_dir_clicked)

    def show(self):
        if not self.__window.isVisible():
            self.__txt_log_display.clear()
        self.__window.show()
        self.__window.raise_()
        self.__window.activateWindow()

    def hide(self):
        self.__window.hide()

    def cleanup(self):
        self.__logger.info("Performing cleanup")
        self.__cleanup_started = True
        self.hide()
        logging.getLogger().removeHandler(self.__log_window_queue_handler)
        self.__log_window_queue.put(None)
        self.__logger.info("Cleanup completed")

    def __btn_clear_clicked(self):
        self.__txt_log_display.clear()

    def __btn_log_dir_clicked(self):
        path = os.path.realpath(MiscUtils.get_log_dir_path())
        webbrowser.open("file:///" + path)

    def __queue_poll_thread_target(self, progress_signal):
        MiscUtils.debug_this_thread()
        self.__logger.info("Queue poll thread started")
        log_formatter = MiscUtils.get_default_log_formatter()
        while not self.__cleanup_started:
            log_record = self.__log_window_queue.get()
            if log_record is None:
                break
            if self.__window.isVisible():
                log_text = log_formatter.format(log_record)
                progress_signal.emit(log_text)

    def __queue_poll_thread_progress(self, progress):
        self.__txt_log_display.appendPlainText(progress)
