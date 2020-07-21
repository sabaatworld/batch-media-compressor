import logging
import json
from pie.core import IndexDB, RestServer
from pie.domain import Settings
from PySide2 import QtCore, QtWidgets, QtUiTools
from multiprocessing import Queue


class PreferencesWindow:
    __logger = logging.getLogger('PreferencesWindow')
    __UI_FILE = "assets/mainwindow.ui"

    def __init__(self, log_queue: Queue):
        self.log_queue = log_queue
        self.__indexDB = IndexDB()
        self.settings = self.__indexDB.get_settings()

        ui_file = QtCore.QFile(PreferencesWindow.__UI_FILE)
        ui_file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window: QtWidgets.QMainWindow = loader.load(ui_file)
        ui_file.close()

        self.window.setWindowTitle("Edit Preferences")
        self.window.setFixedSize(self.window.size())

        self.txtMonitoredDir: QtWidgets.QLineEdit = self.window.findChild(QtWidgets.QLineEdit, 'txtMonitoredDir')
        self.btnPickMonitoredDir: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPickMonitoredDir')
        self.lwDirsToExclude: QtWidgets.QListWidget = self.window.findChild(QtWidgets.QListWidget, 'lwDirsToExclude')
        self.btnAddDirToExclude: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnAddDirToExclude')
        self.btnDelDirToExclude: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnDelDirToExclude')

        self.txtOutputDir: QtWidgets.QLineEdit = self.window.findChild(QtWidgets.QLineEdit, 'txtOutputDir')
        self.btnPickOutputDir: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPickOutputDir')
        self.txtUnknownOutputDir: QtWidgets.QLineEdit = self.window.findChild(QtWidgets.QLineEdit, 'txtUnknownOutputDir')
        self.btnPickUnknownOutputDir: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPickUnknownOutputDir')
        self.cbOutputDirPathType: QtWidgets.QComboBox = self.window.findChild(QtWidgets.QComboBox, 'cbOutputDirPathType')
        self.cbUnknownOutputDirPathType: QtWidgets.QComboBox = self.window.findChild(QtWidgets.QComboBox, 'cbUnknownOutputDirPathType')

        self.btnRestoreDefaults: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnRestoreDefaults')
        self.lblTaskStatus: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblTaskStatus')
        self.pbTaskProgress: QtWidgets.QProgressBar = self.window.findChild(QtWidgets.QProgressBar, 'pbTaskProgress')
        self.chkSkipSameNameVideo: QtWidgets.QCheckBox = self.window.findChild(QtWidgets.QCheckBox, 'chkSkipSameNameVideo')
        self.chkConvertUnknown: QtWidgets.QCheckBox = self.window.findChild(QtWidgets.QCheckBox, 'chkConvertUnknown')
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

        self.btnPickMonitoredDir.clicked.connect(self.btnPickMonitoredDir_click)
        self.lwDirsToExclude.itemSelectionChanged.connect(self.lwDirsToExclude_itemSelectionChanged)
        self.btnAddDirToExclude.clicked.connect(self.btnAddDirToExclude_click)
        self.btnDelDirToExclude.clicked.connect(self.btnDelDirToExclude_click)
        self.btnPickOutputDir.clicked.connect(self.btnPickOutputDir_click)
        self.btnPickUnknownOutputDir.clicked.connect(self.btnPickUnknownOutputDir_click)
        self.cbOutputDirPathType.currentTextChanged.connect(self.cbOutputDirPathType_currentTextChanged)
        self.cbUnknownOutputDirPathType.currentTextChanged.connect(self.cbUnknownOutputDirPathType_currentTextChanged)
        self.chkSkipSameNameVideo.stateChanged.connect(self.chkSkipSameNameVideo_stateChanged)
        self.chkConvertUnknown.stateChanged.connect(self.chkConvertUnknown_stateChanged)
        self.chkOverwriteFiles.stateChanged.connect(self.chkOverwriteFiles_stateChanged)

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

        self.__indexDB.save_settings(self.settings)
        self.apply_settings()

        # self.restServer = RestServer(self.settings, self.log_queue)  # TODO move this somewhere else so that it picks up the latest settings
        # self.restServer.startServer()

    def show(self):
        self.window.show()

    def btnPickMonitoredDir_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick directory to monitor")
        if (selected_directory):
            self.settings.monitored_dir = selected_directory
            self.__indexDB.save_settings(self.settings)
            self.txtMonitoredDir.setText(self.settings.monitored_dir)

    def lwDirsToExclude_itemSelectionChanged(self):
        selected_items = self.lwDirsToExclude.selectedItems()
        self.btnDelDirToExclude.setEnabled(len(selected_items) > 0)

    def btnAddDirToExclude_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick a directory to exclude")
        current_dirs_to_exclude = json.loads(self.settings.dirs_to_exclude)
        if (selected_directory and not selected_directory in current_dirs_to_exclude):
            current_dirs_to_exclude.append(selected_directory)
            self.settings.dirs_to_exclude = json.dumps(current_dirs_to_exclude)
            self.lwDirsToExclude.addItem(selected_directory)
            self.__indexDB.save_settings(self.settings)

    def btnDelDirToExclude_click(self):
        selected_items = self.lwDirsToExclude.selectedItems()
        for selected_item in selected_items:
            selected_item: QtWidgets.QListWidgetItem = selected_item
            current_dirs_to_exclude = json.loads(self.settings.dirs_to_exclude)
            current_dirs_to_exclude.remove(selected_item.text())
            self.settings.dirs_to_exclude = json.dumps(current_dirs_to_exclude)
            self.lwDirsToExclude.takeItem(self.lwDirsToExclude.row(selected_item))
        self.__indexDB.save_settings(self.settings)

    def btnPickOutputDir_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick output directory")
        if (selected_directory):
            self.settings.output_dir = selected_directory
            self.__indexDB.save_settings(self.settings)
            self.txtOutputDir.setText(self.settings.output_dir)

    def btnPickUnknownOutputDir_click(self):
        selected_directory = QtWidgets.QFileDialog.getExistingDirectory(self.window, "Pick output directory")
        if (selected_directory):
            self.settings.unknown_output_dir = selected_directory
            self.__indexDB.save_settings(self.settings)
            self.txtUnknownOutputDir.setText(self.settings.unknown_output_dir)

    def btnRestoreDefaults_click(self):
        response: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self.window, "Confirm Action", "Clear all settings and restore defaults?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if (QtWidgets.QMessageBox.Yes == response):
            self.__indexDB.clear_settings()
            self.settings = self.__indexDB.get_settings()
            self.apply_settings()

    def apply_settings(self):
        self.txtMonitoredDir.setText(self.settings.monitored_dir)
        self.lwDirsToExclude.clear()
        self.lwDirsToExclude.addItems(json.loads(self.settings.dirs_to_exclude))
        self.txtUnknownOutputDir.setText(self.settings.unknown_output_dir)
        self.txtOutputDir.setText(self.settings.output_dir)
        self.cbOutputDirPathType.setCurrentIndex(self.cbOutputDirPathType.findText(self.settings.output_dir_path_type))
        self.cbUnknownOutputDirPathType.setCurrentIndex(self.cbUnknownOutputDirPathType.findText(self.settings.unknown_output_dir_path_type))
        self.chkSkipSameNameVideo.setChecked(self.settings.skip_same_name_video)
        self.chkConvertUnknown.setChecked(self.settings.convert_unknown)
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

    def cleanup(self):
        self.__logger.info("Performing cleanup")
        self.window.hide()
        # self.restServer.stopServer()
        self.__indexDB.disconnect_db()
        self.__logger.info("Cleanup completed")

    def cbOutputDirPathType_currentTextChanged(self, new_text: str):
        self.settings.output_dir_path_type = new_text
        self.__indexDB.save_settings(self.settings)

    def cbUnknownOutputDirPathType_currentTextChanged(self, new_text: str):
        self.settings.unknown_output_dir_path_type = new_text
        self.__indexDB.save_settings(self.settings)

    def chkSkipSameNameVideo_stateChanged(self):
        self.settings.skip_same_name_video = self.chkSkipSameNameVideo.isChecked()
        self.__indexDB.save_settings(self.settings)

    def chkConvertUnknown_stateChanged(self):
        self.settings.convert_unknown = self.chkConvertUnknown.isChecked()
        self.__indexDB.save_settings(self.settings)

    def chkOverwriteFiles_stateChanged(self):
        self.settings.overwrite_output_files = self.chkOverwriteFiles.isChecked()
        self.__indexDB.save_settings(self.settings)

    def spinImageQuality_valueChanged(self, new_value: int):
        self.settings.image_compression_quality = new_value
        self.__indexDB.save_settings(self.settings)

    def spinImageMaxDimension_valueChanged(self, new_value: int):
        self.settings.image_max_dimension = new_value
        self.__indexDB.save_settings(self.settings)

    def spinVideoMaxDimension_valueChanged(self, new_value: int):
        self.settings.video_max_dimension = new_value
        self.__indexDB.save_settings(self.settings)

    def spinVideoCrf_valueChanged(self, new_value: int):
        self.settings.video_crf = new_value
        self.__indexDB.save_settings(self.settings)

    def cbVideoNvencPreset_currentTextChanged(self, new_text: str):
        self.settings.video_nvenc_preset = new_text
        self.__indexDB.save_settings(self.settings)

    def spinVideoAudioBitrate_valueChanged(self, new_value: int):
        self.settings.video_audio_bitrate = new_value
        self.__indexDB.save_settings(self.settings)

    def spinIndexingWorkers_valueChanged(self, new_value: int):
        self.settings.indexing_workers = new_value
        self.__indexDB.save_settings(self.settings)

    def spinConversionWorkers_valueChanged(self, new_value: int):
        self.settings.conversion_workers = new_value
        self.__indexDB.save_settings(self.settings)

    def spinGpuWorkers_valueChanged(self, new_value: int):
        self.settings.gpu_workers = new_value
        self.__indexDB.save_settings(self.settings)

    def spinGpuCount_valueChanged(self, new_value: int):
        self.settings.gpu_count = new_value
        self.__indexDB.save_settings(self.settings)
