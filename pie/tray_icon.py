import json
import logging
import os
import ssl
import webbrowser
from multiprocessing import Event, Queue
from urllib.request import urlopen

import certifi
from PySide2 import QtCore, QtGui, QtWidgets

from packaging import version
from pie.core import IndexDB, IndexingHelper, MediaProcessor
from pie.domain import IndexingTask, Settings
from pie.log_window import LogWindow
from pie.preferences_window import PreferencesWindow
from pie.util import MiscUtils, QWorker


class TrayIcon(QtWidgets.QSystemTrayIcon):
    __APP_VER = "1.0.1"
    __logger = logging.getLogger('TrayIcon')

    def __init__(self, log_queue: Queue):
        super().__init__(QtGui.QIcon(MiscUtils.get_app_icon_path()))
        self.log_queue = log_queue
        self.preferences_window: PreferencesWindow = None
        self.log_window: LogWindow = None
        self.indexing_stop_event: Event = None
        self.observer = None
        self.indexDB = IndexDB()
        self.threadpool: QtCore.QThreadPool = QtCore.QThreadPool()
        self.__logger.debug("QT multithreading with thread pool size: %s", self.threadpool.maxThreadCount())

        self.setToolTip("Batch Media Compressor")
        self.activated.connect(self.trayIcon_activated)

        tray_menu = QtWidgets.QMenu('Main Menu')
        self.startIndexAction = tray_menu.addAction('Start Processing', self.startIndexAction_triggered)
        self.stopIndexAction = tray_menu.addAction('Stop Processing', self.stopIndexAction_triggered)
        self.stopIndexAction.setEnabled(False)
        tray_menu.addSeparator()
        self.clearIndexAction = tray_menu.addAction('Clear Indexed Files', self.clearIndexAction_triggered)
        self.clearOutputDirsAction = tray_menu.addAction('Clear Ouput Directories', self.clearOutputDirsAction_triggered)
        tray_menu.addSeparator()
        self.editPrefAction = tray_menu.addAction('Edit Preferences', self.editPreferencesAction_triggered)
        self.viewLogsAction = tray_menu.addAction('View Logs', self.viewLogsAction_triggered)
        tray_menu.addSeparator()
        self.updateCheckAction = tray_menu.addAction('Check for Updates', self.updateCheckAction_triggered)
        self.coffeeAction = tray_menu.addAction('Buy me a Coffee', self.coffeeAction_triggered)
        tray_menu.addSeparator()
        tray_menu.addAction('Quit', self.quitMenuAction_triggered)
        self.setContextMenu(tray_menu)

        self.apply_process_changed_setting()
        if self.indexDB.get_settings().auto_update_check:
            self.update_check_worker = QWorker(self.auto_update_check)
            self.threadpool.start(self.update_check_worker)

    def trayIcon_activated(self, reason):
        pass

    def startIndexAction_triggered(self):
        if self.indexDB.get_settings().auto_show_log_window:
            self.show_view_logs_window()
        self.background_processing_started()
        self.indexing_stop_event = Event()
        self.indexing_worker = QWorker(self.start_indexing)
        self.indexing_worker.signals.finished.connect(self.background_processing_finished)
        self.threadpool.start(self.indexing_worker)
        self.stopIndexAction.setEnabled(True)

    def stopIndexAction_triggered(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            None, "Confirm Action", "Are you sure you want to stop the current task?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if QtWidgets.QMessageBox.Yes == response:
            self.stopIndexAction.setEnabled(False)
            self.stop_async_tasks()

    def clearIndexAction_triggered(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            None, "Confirm Action", "Forget indexed files and delete all output files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if QtWidgets.QMessageBox.Yes == response:
            self.background_processing_started()
            self.deletion_worker = QWorker(self.start_deletion, True)
            self.deletion_worker.signals.finished.connect(self.background_processing_finished)
            self.threadpool.start(self.deletion_worker)

    def clearOutputDirsAction_triggered(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            None, "Confirm Action", "Delete all output files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if QtWidgets.QMessageBox.Yes == response:
            self.background_processing_started()
            self.deletion_worker = QWorker(self.start_deletion, False)
            self.deletion_worker.signals.finished.connect(self.background_processing_finished)
            self.threadpool.start(self.deletion_worker)

    def start_deletion(self, clearIndex: bool):
        MiscUtils.debug_this_thread()
        with IndexDB() as indexDB:
            if clearIndex:
                indexDB.clear_indexed_files()
                self.__logger.info("Index cleared")
            settings: Settings = indexDB.get_settings()
            MiscUtils.recursively_delete_children(settings.output_dir)
            MiscUtils.recursively_delete_children(settings.unknown_output_dir)
            self.__logger.info("Output directories cleared")

    def editPreferencesAction_triggered(self):
        if self.preferences_window is None:
            self.preferences_window = PreferencesWindow(self.apply_process_changed_setting)
        self.preferences_window.show()

    def viewLogsAction_triggered(self):
        self.show_view_logs_window()

    def show_view_logs_window(self):
        if self.log_window is None:
            self.log_window = LogWindow(self.threadpool)
        self.log_window.show()

    def updateCheckAction_triggered(self):
        self.check_for_updates(True)

    def auto_update_check(self):
        MiscUtils.debug_this_thread()
        self.check_for_updates(False)

    def check_for_updates(self, display_not_found: bool):
        api_url = "https://api.github.com/repos/sabaatworld/batch-media-compressor/releases/latest"
        releases_url = "https://github.com/sabaatworld/batch-media-compressor/releases"
        update_found = False
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            response = urlopen(api_url, context=ssl_context)
            response_string = response.read().decode('utf-8')
            response_json = json.loads(response_string)
            tag_name: str = response_json["tag_name"]
            if tag_name is not None:
                release_version = version.parse(tag_name.replace("v", ""))
                current_version = version.parse(self.__APP_VER)
                self.__logger.info("Updated Check successful: Current Version: %s, Latest Release: %s", str(current_version), str(release_version))
                if current_version < release_version:
                    update_found = True
        except:
            self.__logger.exception("Failed to check for updates")

        if update_found:
            if QtWidgets.QMessageBox.information(
                None, "Update Check",
                "New version available. Do you wish to download the latest release now?\n\nCurrent Verion: {}\nNew Version: {}".format(str(current_version), str(release_version)),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            ) == QtWidgets.QMessageBox.Yes:
                webbrowser.open(releases_url)
        elif display_not_found:
            QtWidgets.QMessageBox.information(None, "Update Check", "No updates found.\n\nIf you think this is an error, please check your internet connection and try again.", QtWidgets.QMessageBox.Ok)

    def coffeeAction_triggered(self):
        webbrowser.open('https://paypal.me/sabaat')

    def quitMenuAction_triggered(self):
        QtWidgets.QApplication.quit()

    def start_indexing(self):
        MiscUtils.debug_this_thread()
        with IndexDB() as indexDB:
            indexing_task = IndexingTask()
            indexing_task.settings = indexDB.get_settings()
            if self.settings_valid(indexing_task.settings):
                misc_utils = MiscUtils(indexing_task)
                misc_utils.create_root_marker()
                indexing_helper = IndexingHelper(indexing_task, self.log_queue, self.indexing_stop_event)
                (scanned_files, _) = indexing_helper.scan_dirs()
                indexing_helper.remove_slate_files(indexDB, scanned_files)
                indexing_helper.lookup_already_indexed_files(indexDB, scanned_files)
                if not self.indexing_stop_event.is_set():
                    indexing_helper.create_media_files(scanned_files)
                if not self.indexing_stop_event.is_set():
                    media_processor = MediaProcessor(indexing_task, self.log_queue, self.indexing_stop_event)
                    media_processor.save_processed_files(indexDB)
                if not self.indexing_stop_event.is_set():
                    misc_utils.cleanEmptyOutputDirs()

    def settings_valid(self, settings: Settings) -> bool:
        error_msg: str = None
        if settings.monitored_dir is None:
            error_msg = "Directory to scan not configured"
        elif not os.path.isdir(settings.monitored_dir):
            error_msg = "Directory to scan is invalid"
        elif settings.output_dir is None:
            error_msg = "Media with Capture Date directory not configured"
        elif not os.path.isdir(settings.output_dir):
            error_msg = "Media with Capture Date directory is invalid"
        elif settings.unknown_output_dir is None:
            error_msg = "Media without Capture Date directory not configured"
        elif not os.path.isdir(settings.unknown_output_dir):
            error_msg = "Media without Capture Date directory is invalid"

        if error_msg is not None:
            self.__logger.error("Cannot start processing: %s. Please update preferences and try again.", error_msg)
            return False
        else:
            return True

    def background_processing_started(self):
        self.startIndexAction.setEnabled(False)
        self.clearIndexAction.setEnabled(False)
        self.clearOutputDirsAction.setEnabled(False)
        self.editPrefAction.setEnabled(False)
        if self.preferences_window is not None:
            self.preferences_window.hide()

    def background_processing_finished(self):
        self.startIndexAction.setEnabled(True)
        self.stopIndexAction.setEnabled(False)
        self.clearIndexAction.setEnabled(True)
        self.clearOutputDirsAction.setEnabled(True)
        self.editPrefAction.setEnabled(True)

    def stop_async_tasks(self):
        if self.indexing_stop_event:
            self.indexing_stop_event.set()

    def cleanup(self):
        if self.preferences_window is not None:
            self.preferences_window.cleanup()
        if self.log_window is not None:
            self.log_window.cleanup()
        self.indexDB.disconnect_db()

    def apply_process_changed_setting(self):
        pass
