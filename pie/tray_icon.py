import logging
from pie.core import IndexingHelper, ExifHelper, MediaProcessor, IndexDB
from pie.util import MiscUtils, QWorker
from pie.domain import IndexingTask, Settings
from .preferences_window import PreferencesWindow
from PySide2 import QtCore, QtWidgets, QtGui
from multiprocessing import Queue, Event, Manager
from typing import Set


class TrayIcon(QtWidgets.QSystemTrayIcon):
    __logger = logging.getLogger('TrayIcon')

    def __init__(self, tray_icon_file_path: str, log_queue: Queue):
        super().__init__(QtGui.QIcon(tray_icon_file_path))
        self.log_queue = log_queue
        self.preferences_window: PreferencesWindow = None
        self.indexing_stop_event: Event = None
        self.observer = None
        self.threadpool: QtCore.QThreadPool = QtCore.QThreadPool()
        self.__logger.debug("QT multithreading with thread pool size: %s", self.threadpool.maxThreadCount())

        self.setToolTip("Personal Image Explorer")
        self.activated.connect(self.trayIcon_activated)

        tray_menu = QtWidgets.QMenu('Main Menu')
        self.startIndexAction = tray_menu.addAction('Start Indexing', self.startIndexAction_triggered)
        self.stopIndexAction = tray_menu.addAction('Stop Indexing', self.stopIndexAction_triggered)
        self.stopIndexAction.setEnabled(False)
        tray_menu.addSeparator()
        self.clearIndexAction = tray_menu.addAction('Clear Index', self.clearIndexAction_triggered)
        self.clearOutputDirsAction = tray_menu.addAction('Clear Ouput Directories', self.clearOutputDirsAction_triggered)
        tray_menu.addSeparator()
        self.editPrefAction = tray_menu.addAction('Edit Preferences', self.editPreferencesAction_triggered)
        tray_menu.addSeparator()
        tray_menu.addAction('Quit', self.quitMenuAction_triggered)
        self.setContextMenu(tray_menu)

        self.apply_process_changed_setting()

    def trayIcon_activated(self, reason):
        pass

    def startIndexAction_triggered(self):
        self.background_processing_started()
        self.indexing_stop_event = Event()
        self.deletion_worker = QWorker(self.start_indexing)
        self.deletion_worker.signals.progress.connect(self.indexing_progress)
        self.deletion_worker.signals.finished.connect(self.background_processing_finished)
        self.threadpool.start(self.deletion_worker)
        self.stopIndexAction.setEnabled(True)

    def stopIndexAction_triggered(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            None, "Confirm Action", "Are you sure you want to stop the current task?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if (QtWidgets.QMessageBox.Yes == response):
            self.stopIndexAction.setEnabled(False)
            self.stop_async_tasks()

    def clearIndexAction_triggered(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            None, "Confirm Action", "Forget indexed files and delete all output files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if (QtWidgets.QMessageBox.Yes == response):
            self.background_processing_started()
            self.deletion_worker = QWorker(self.start_deletion, True)
            self.deletion_worker.signals.finished.connect(self.background_processing_finished)
            self.threadpool.start(self.deletion_worker)

    def clearOutputDirsAction_triggered(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            None, "Confirm Action", "Delete all output files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if (QtWidgets.QMessageBox.Yes == response):
            self.background_processing_started()
            self.deletion_worker = QWorker(self.start_deletion, False)
            self.deletion_worker.signals.finished.connect(self.background_processing_finished)
            self.threadpool.start(self.deletion_worker)

    def start_deletion(self, clearIndex: bool, progress_callback):
        with IndexDB() as indexDB:
            if clearIndex:
                indexDB.clear_indexed_files()
                self.__logger.info("Index cleared")
            settings: Settings = indexDB.get_settings()
            MiscUtils.recursively_delete_children(settings.output_dir)
            MiscUtils.recursively_delete_children(settings.unknown_output_dir)
            self.__logger.info("Output directories cleared")

    def editPreferencesAction_triggered(self):
        if (self.preferences_window == None):
            self.preferences_window = PreferencesWindow(self.log_queue, self.apply_process_changed_setting)
        self.preferences_window.show()

    def quitMenuAction_triggered(self):
        QtWidgets.QApplication.quit()

    def start_indexing(self, progress_callback):
        with IndexDB() as indexDB:
            MiscUtils.debug_this_thread()
            indexing_task = IndexingTask()
            indexing_task.settings = indexDB.get_settings()
            misc_utils = MiscUtils(indexing_task)
            misc_utils.create_root_marker()
            indexing_helper = IndexingHelper(indexing_task, self.log_queue, self.indexing_stop_event)
            (scanned_files, _) = indexing_helper.scan_dirs()
            indexing_helper.remove_slate_files(indexDB, scanned_files)
            indexing_helper.lookup_already_indexed_files(indexDB, scanned_files)
            if (not self.indexing_stop_event.is_set()):
                indexing_helper.create_media_files(scanned_files)
            if (not self.indexing_stop_event.is_set()):
                media_processor = MediaProcessor(indexing_task, self.log_queue, self.indexing_stop_event)
                media_processor.save_processed_files(indexDB)
            if (not self.indexing_stop_event.is_set()):
                misc_utils.cleanEmptyOutputDirs()

    def background_processing_started(self):
        self.startIndexAction.setEnabled(False)
        self.clearIndexAction.setEnabled(False)
        self.clearOutputDirsAction.setEnabled(False)
        self.editPrefAction.setEnabled(False)
        if (self.preferences_window != None):
            self.preferences_window.hide()

    def background_processing_finished(self):
        self.startIndexAction.setEnabled(True)
        self.stopIndexAction.setEnabled(False)
        self.clearIndexAction.setEnabled(True)
        self.clearOutputDirsAction.setEnabled(True)
        self.editPrefAction.setEnabled(True)

    def indexing_progress(self, progress):
        print("%d%% done" % progress)

    def stop_async_tasks(self):
        if(self.indexing_stop_event):
            self.indexing_stop_event.set()

    def cleanup(self):
        if (not self.preferences_window == None):
            self.preferences_window.cleanup()

    def apply_process_changed_setting(self):
        with IndexDB() as indexDB:
            settings = indexDB.get_settings()
            # Not doing anything here for now
