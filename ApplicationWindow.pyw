import sys
import random
import logging
import multiprocessing
import threading
from pie.core import IndexingHelper, ExifHelper, MediaProcessor, MongoDB
from pie.util import MiscUtils, QWorker
from pie.domain import IndexingTask, Settings
from PySide2 import QtCore, QtWidgets, QtGui, QtUiTools
from datetime import datetime

from multiprocessing import Queue, Event


class ApplicationWindow():
    __logger = logging.getLogger('ApplicationWindow')

    def __init__(self, main_window_ui_file_path: str):
        MongoDB.connect_db()
        self.settings = MongoDB.get_settings()

        MiscUtils.configure_logging(self.settings.log_file_dir)
        self.log_queue = Queue()
        self.logger_thread = threading.Thread(target=MiscUtils.logger_thread_exec, args=(self.log_queue,))
        self.logger_thread.start()

        self.threadpool: QtCore.QThreadPool = QtCore.QThreadPool()
        ApplicationWindow.__logger.info("QT multithreading with thread pool size: %s", self.threadpool.maxThreadCount())

        ui_file = QtCore.QFile(main_window_ui_file_path)
        ui_file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window: QtWidgets.QMainWindow = loader.load(ui_file)
        ui_file.close()

        self.window.setFixedSize(self.window.size())

        self.lwDirsToScan: QtWidgets.QListWidget = self.window.findChild(QtWidgets.QListWidget, 'lwDirsToScan')
        self.btnAddDirToScan: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnAddDirToScan')
        self.btnDelDirToScan: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnDelDirToScan')
        self.lwDirsToExclude: QtWidgets.QListWidget = self.window.findChild(QtWidgets.QListWidget, 'lwDirsToExclude')
        self.btnAddDirToExclude: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnAddDirToExclude')
        self.btnDelDirToExclude: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnDelDirToExclude')
        self.txtOutputDir: QtWidgets.QLineEdit = self.window.findChild(QtWidgets.QLineEdit, 'txtOutputDir')
        self.btnPickOutputDir: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPickOutputDir')
        self.btnStartIndex: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnStartIndex')
        self.btnStop: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnStop')
        self.btnClearIndex: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnClearIndex')
        self.btnRestoreDefaults: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnRestoreDefaults')
        self.lblTaskStatus: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblTaskStatus')
        self.pbTaskProgress: QtWidgets.QProgressBar = self.window.findChild(QtWidgets.QProgressBar, 'pbTaskProgress')
        self.chkOverwriteFiles: QtWidgets.QCheckBox = self.window.findChild(QtWidgets.QCheckBox, 'chkOverwriteFiles')
        self.spinImageQuality: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinImageQuality')
        self.spinImageMaxDimension: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinImageMaxDimension')
        self.spinVideoMaxDimension: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinVideoMaxDimension')
        self.spinVideoCrf: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinVideoCrf')
        self.cbVideoNvencPreset: QtWidgets.QComboBox = self.window.findChild(QtWidgets.QComboBox, 'cbVideoNvencPreset')
        self.spinVideoAudioBitrate: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinVideoAudioBitrate')
        self.spinIndexingWorkers: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinIndexingWorkers')
        self.spinConversionWorkers: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinConversionWorkers')
        self.spinGpuWorkers: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinGpuWorkers')
        self.spinGpuCount: QtWidgets.QSpinBox = self.window.findChild(QtWidgets.QSpinBox, 'spinGpuCount')

        self.lwDirsToScan.itemSelectionChanged.connect(self.lwDirsToScan_itemSelectionChanged)
        self.btnAddDirToScan.clicked.connect(self.btnAddDirToScan_click)
        self.btnDelDirToScan.clicked.connect(self.btnDelDirToScan_click)
        self.lwDirsToExclude.itemSelectionChanged.connect(self.lwDirsToExclude_itemSelectionChanged)
        self.btnAddDirToExclude.clicked.connect(self.btnAddDirToExclude_click)
        self.btnDelDirToExclude.clicked.connect(self.btnDelDirToExclude_click)
        self.btnPickOutputDir.clicked.connect(self.btnPickOutputDir_click)
        self.chkOverwriteFiles.stateChanged.connect(self.chkOverwriteFiles_stateChanged)

        self.btnStartIndex.clicked.connect(self.btnStartIndex_click)
        self.btnStop.clicked.connect(self.btnStop_click)
        self.btnClearIndex.clicked.connect(self.btnClearIndex_click)
        self.btnRestoreDefaults.clicked.connect(self.btnRestoreDefaults_click)

        self.spinImageQuality.valueChanged.connect(self.spinImageQuality_valueChanged)
        self.spinImageMaxDimension.valueChanged.connect(self.spinImageMaxDimension_valueChanged)
        self.spinVideoMaxDimension.valueChanged.connect(self.spinVideoMaxDimension_valueChanged)
        self.spinVideoCrf.valueChanged.connect(self.spinVideoCrf_valueChanged)
        self.cbVideoNvencPreset.currentTextChanged.connect(self.cbVideoNvencPreset_currentTextChanged)
        self.spinVideoAudioBitrate.valueChanged.connect(self.spinVideoAudioBitrate_valueChanged)
        self.spinIndexingWorkers.valueChanged.connect(self.spinIndexingWorkers_valueChanged)
        self.spinConversionWorkers.valueChanged.connect(self.spinConversionWorkers_valueChanged)
        self.spinGpuWorkers.valueChanged.connect(self.spinGpuWorkers_valueChanged)
        self.spinGpuCount.valueChanged.connect(self.spinGpuCount_valueChanged)

        self.cbVideoNvencPreset: QtWidgets.QComboBox = self.window.findChild(QtWidgets.QComboBox, 'cbVideoNvencPreset')

        # Following variables are set later on
        self.indexing_task: IndexingTask = None
        self.indexing_stop_event: Event = None

        MongoDB.save_settings(self.settings)
        self.apply_settings()

    def show(self):
        self.window.show()

    def lwDirsToScan_itemSelectionChanged(self):
        selected_items = self.lwDirsToScan.selectedItems()
        self.btnDelDirToScan.setEnabled(len(selected_items) > 0)

    def btnAddDirToScan_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick a directory to include")
        if (selected_directory and not selected_directory in self.settings.dirs_to_include):
            self.settings.dirs_to_include.append(selected_directory)
            self.lwDirsToScan.addItem(selected_directory)
            MongoDB.save_settings(self.settings)

    def btnDelDirToScan_click(self):
        selected_items = self.lwDirsToScan.selectedItems()
        for selected_item in selected_items:
            selected_item: QtWidgets.QListWidgetItem = selected_item
            self.settings.dirs_to_include.remove(selected_item.text())
            self.lwDirsToScan.takeItem(self.lwDirsToScan.row(selected_item))
        MongoDB.save_settings(self.settings)

    def lwDirsToExclude_itemSelectionChanged(self):
        selected_items = self.lwDirsToExclude.selectedItems()
        self.btnDelDirToExclude.setEnabled(len(selected_items) > 0)

    def btnAddDirToExclude_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick a directory to exclude")
        if (selected_directory and not selected_directory in self.settings.dirs_to_exclude):
            self.settings.dirs_to_exclude.append(selected_directory)
            self.lwDirsToExclude.addItem(selected_directory)
            MongoDB.save_settings(self.settings)

    def btnDelDirToExclude_click(self):
        selected_items = self.lwDirsToExclude.selectedItems()
        for selected_item in selected_items:
            selected_item: QtWidgets.QListWidgetItem = selected_item
            self.settings.dirs_to_exclude.remove(selected_item.text())
            self.lwDirsToExclude.takeItem(self.lwDirsToExclude.row(selected_item))
        MongoDB.save_settings(self.settings)

    def btnPickOutputDir_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick output directory")
        if (selected_directory):
            self.settings.output_dir = selected_directory
            MongoDB.save_settings(self.settings)
            self.txtOutputDir.setText(self.settings.output_dir)

    def btnStartIndex_click(self):
        self.btnStartIndex.setEnabled(False)
        self.btnClearIndex.setEnabled(False)
        self.btnRestoreDefaults.setEnabled(False)
        self.indexing_stop_event = Event()
        self.indexing_worker = QWorker(self.start_indexing)
        self.indexing_worker.signals.progress.connect(self.indexing_progress)
        self.indexing_worker.signals.finished.connect(self.indexing_finished)
        self.threadpool.start(self.indexing_worker)
        self.btnStop.setEnabled(True)

    def btnStop_click(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self.window, "Confirm Action", "Are you sure you want to stop the current task?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if (QtWidgets.QMessageBox.Yes == response):
            self.btnStop.setEnabled(False)
            self.stop_async_tasks()

    def btnClearIndex_click(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self.window, "Confirm Action", "Clear indexed files from MongoDB and delete all output files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if (QtWidgets.QMessageBox.Yes == response):
            MongoDB.clear_indexed_files()
            MiscUtils.recursively_delete_children(self.settings.output_dir)
            self.__logger.info("Output directory cleared")

    def btnRestoreDefaults_click(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self.window, "Confirm Action", "Clear all settings and restore defaults?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if (QtWidgets.QMessageBox.Yes == response):
            MongoDB.clear_settings()
            self.settings = MongoDB.get_settings()
            self.apply_settings()

    def apply_settings(self):
        # MongoDB.save_settings(self.settings)
        self.lwDirsToScan.clear()
        self.lwDirsToScan.addItems(self.settings.dirs_to_include)
        self.lwDirsToExclude.clear()
        self.lwDirsToExclude.addItems(self.settings.dirs_to_exclude)
        self.txtOutputDir.setText(self.settings.output_dir)
        self.chkOverwriteFiles.setChecked(self.settings.overwrite_output_files)
        self.spinImageQuality.setValue(self.settings.image_compression_quality)
        self.spinImageMaxDimension.setValue(self.settings.image_max_dimension)
        self.spinVideoMaxDimension.setValue(self.settings.video_max_dimension)
        self.spinVideoCrf.setValue(self.settings.video_crf)
        self.cbVideoNvencPreset.setCurrentIndex(self.cbVideoNvencPreset.findText(self.settings.video_nvenc_preset))
        self.spinVideoAudioBitrate.setValue(self.settings.video_audio_bitrate)
        self.spinIndexingWorkers.setValue(self.settings.indexing_workers)
        self.spinConversionWorkers.setValue(self.settings.conversion_workers)
        self.spinGpuWorkers.setValue(self.settings.gpu_workers)
        self.spinGpuCount.setValue(self.settings.gpu_count)

    def stop_async_tasks(self):
        if(self.indexing_stop_event):
            self.indexing_stop_event.set()

    def cleanup(self):
        ApplicationWindow.__logger.info("Performing cleanup")
        self.stop_async_tasks()
        MongoDB.disconnect_db()
        self.log_queue.put(None)
        self.logger_thread.join()

    def start_indexing(self, progress_callback):
        MiscUtils.debug_this_thread()
        self.indexing_task = IndexingTask()
        self.indexing_task.settings = self.settings
        indexing_helper = IndexingHelper(self.indexing_task, self.log_queue, self.indexing_stop_event)
        scanned_files = indexing_helper.scan_dirs()
        indexing_helper.remove_slate_files(scanned_files)
        indexing_helper.lookup_already_indexed_files(scanned_files)
        indexing_helper.create_media_files(scanned_files)
        if (not self.indexing_stop_event.is_set()):
            media_processor = MediaProcessor(self.indexing_task, self.log_queue, self.indexing_stop_event)
            media_processor.save_processed_files()
        if (not self.indexing_stop_event.is_set()):
            misc_utils = MiscUtils(self.indexing_task)
            misc_utils.cleanEmptyOutputDirs()

    def indexing_finished(self):
        self.btnStartIndex.setEnabled(True)
        self.btnClearIndex.setEnabled(True)
        self.btnRestoreDefaults.setEnabled(True)
        self.btnStop.setEnabled(False)
        pass

    def indexing_progress(self, progress):
        print("%d%% done" % progress)

    def chkOverwriteFiles_stateChanged(self):
        self.settings.overwrite_output_files = self.chkOverwriteFiles.isChecked()
        MongoDB.save_settings(self.settings)

    def spinImageQuality_valueChanged(self, new_value: int):
        self.settings.image_compression_quality = new_value
        MongoDB.save_settings(self.settings)

    def spinImageMaxDimension_valueChanged(self, new_value: int):
        self.settings.image_max_dimension = new_value
        MongoDB.save_settings(self.settings)

    def spinVideoMaxDimension_valueChanged(self, new_value: int):
        self.settings.video_max_dimension = new_value
        MongoDB.save_settings(self.settings)

    def spinVideoCrf_valueChanged(self, new_value: int):
        self.settings.video_crf = new_value
        MongoDB.save_settings(self.settings)

    def cbVideoNvencPreset_currentTextChanged(self, new_text: str):
        self.settings.video_nvenc_preset = new_text
        MongoDB.save_settings(self.settings)

    def spinVideoAudioBitrate_valueChanged(self, new_value: int):
        self.settings.video_audio_bitrate = new_value
        MongoDB.save_settings(self.settings)

    def spinIndexingWorkers_valueChanged(self, new_value: int):
        self.settings.indexing_workers = new_value
        MongoDB.save_settings(self.settings)

    def spinConversionWorkers_valueChanged(self, new_value: int):
        self.settings.conversion_workers = new_value
        MongoDB.save_settings(self.settings)

    def spinGpuWorkers_valueChanged(self, new_value: int):
        self.settings.gpu_workers = new_value
        MongoDB.save_settings(self.settings)

    def spinGpuCount_valueChanged(self, new_value: int):
        self.settings.gpu_count = new_value
        MongoDB.save_settings(self.settings)


if __name__ == "__main__":
    MAIN_WINDOW_UI_FILE_PATH = "assets/mainwindow.ui"
    APP_ICON_FILE_PATH = "assets/pie_logo.png"

    multiprocessing.set_start_method('spawn')
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    QtGui.QGuiApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(APP_ICON_FILE_PATH))
    app.setApplicationDisplayName("PIE Indexing Service")  # TODO test + add org / ver
    application_window = ApplicationWindow(MAIN_WINDOW_UI_FILE_PATH)
    application_window.show()
    return_code = app.exec_()
    logging.info("Application is being shutdown")
    application_window.cleanup()
    sys.exit(return_code)
