import sys
import logging
import multiprocessing
import threading
import datetime
import os
from pie import TrayIcon, PreferencesWindow
from pie.domain import IndexingTask, MediaFile, ScannedFileType
from pie.util import MiscUtils
from pie.core import IndexingHelper, IndexDB, MediaProcessor
from multiprocessing import Manager, Queue
from PySide2 import QtCore, QtWidgets, QtGui, QtUiTools
from typing import List
from natsort import natsorted

class ExifFixerWindow(QtCore.QObject):
    __logger = logging.getLogger('ExifFixerWindow')
    __UI_FILE = "assets/exif_fixer_window.ui"

    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue
        self.indexDB = IndexDB()
        self.mediaFiles: List[MediaFile] = []
        self.info1 = None
        self.info3 = None
        self.picked_index = -1

        ui_file = QtCore.QFile(ExifFixerWindow.__UI_FILE)
        ui_file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window: QtWidgets.QMainWindow = loader.load(ui_file)
        ui_file.close()

        self.window.setFixedSize(self.window.size())

        self.txtDirToScan: QtWidgets.QLineEdit = self.window.findChild(QtWidgets.QLineEdit, 'txtDirToScan')
        self.btnPickDirToScan: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPickDirToScan')
        self.btnStartScan: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnStartScan')

        self.lblPic1: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblPic1')
        self.lblFileName1: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblFileName1')
        self.lblInfo1: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblInfo1')
        self.btnPrev1: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPrev1')
        self.btnNext1: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnNext1')
        self.btnCopy1: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnCopy1')

        self.lblPic2: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblPic2')
        self.lblFileName2: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblFileName2')
        self.lblInfo1: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblInfo1')
        self.selectedDateTimeEdit2: QtWidgets.QDateTimeEdit = self.window.findChild(QtWidgets.QDateTimeEdit, 'selectedDateTimeEdit2')
        self.btnSave2: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnSave2')
        self.btnDelete2: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnDelete2')

        self.lblPic3: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblPic3')
        self.lblFileName3: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblFileName3')
        self.lblInfo3: QtWidgets.QLabel = self.window.findChild(QtWidgets.QLabel, 'lblInfo3')
        self.btnPrev3: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnPrev3')
        self.btnNext3: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnNext3')
        self.btnCopy3: QtWidgets.QPushButton = self.window.findChild(QtWidgets.QPushButton, 'btnCopy3')

        # TODO remove
        self.txtDirToScan.setText('/Users/sabaata/Desktop/Misc Files/PIE Data/Input/iPhone 5S Mix 1')

        self.btnStartScan.clicked.connect(self.btnStartScan_click)
        self.btnCopy1.clicked.connect(self.btnCopy1_click)
        self.btnCopy3.clicked.connect(self.btnCopy3_click)
        self.btnSave2.clicked.connect(self.btnSave2_click)
        self.btnDelete2.clicked.connect(self.btnDelete2_click)
        # self.lwDirsToExclude.itemSelectionChanged.connect(self.lwDirsToExclude_itemSelectionChanged)
        # self.btnAddDirToExclude.clicked.connect(self.btnAddDirToExclude_click)
        # self.btnDelDirToExclude.clicked.connect(self.btnDelDirToExclude_click)
        # self.btnPickOutputDir.clicked.connect(self.btnPickOutputDir_click)
        # self.btnPickUnknownOutputDir.clicked.connect(self.btnPickUnknownOutputDir_click)
        # self.cbOutputDirPathType.currentTextChanged.connect(self.cbOutputDirPathType_currentTextChanged)
        # self.cbUnknownOutputDirPathType.currentTextChanged.connect(self.cbUnknownOutputDirPathType_currentTextChanged)
        # self.chkSkipSameNameVideo.stateChanged.connect(self.chkSkipSameNameVideo_stateChanged)
        # self.chkConvertUnknown.stateChanged.connect(self.chkConvertUnknown_stateChanged)
        # self.chkOverwriteFiles.stateChanged.connect(self.chkOverwriteFiles_stateChanged)

    def show(self):
        self.window.show()

    def btnStartScan_click(self):
        self.mediaFiles = []
        for mediaFile in self.indexDB.get_by_parent_dir_sorted_lexicographically(self.txtDirToScan.text()):
            self.mediaFiles.append(mediaFile)

        # self.mediaFiles.sort(key = lambda m1: m1.file_path)
        self.mediaFiles = natsorted(self.mediaFiles, key = lambda m1: m1.file_path)
        self.pullUpNextMediaFile()

    def pullUpNextMediaFile(self):
        last_picked_index = self.picked_index
        self.picked_index = -1
        for index, mediaFile in enumerate(self.mediaFiles, start=0):
            mediaFile: MediaFile = mediaFile
            if (index > last_picked_index and mediaFile.capture_date == None):
                self.picked_index = index
                break

        if (self.picked_index > -1):
            sectionEnabled = False
            for index in reversed(range(0, self.picked_index)):
                if (not self.mediaFiles[index].capture_date == None):
                    self.mark_section_enabled([self.lblPic1, self.lblFileName1, self.lblInfo1], [self.btnPrev1, self.btnNext1, self.btnCopy1])
                    self.apply_media_file(self.mediaFiles[index], self.lblPic1, self.lblFileName1, self.lblInfo1)
                    self.info1 = self.mediaFiles[index].capture_date
                    sectionEnabled = True
                    break
            if (not sectionEnabled):
                self.mark_section_disabled([self.lblPic1, self.lblFileName1, self.lblInfo1], [self.btnPrev1, self.btnNext1, self.btnCopy1])

            self.apply_media_file(self.mediaFiles[self.picked_index], self.lblPic2, self.lblFileName2, None)

            sectionEnabled = False
            for index in range(self.picked_index + 1, len(self.mediaFiles)):
                if (not self.mediaFiles[index].capture_date == None):
                    self.mark_section_enabled([self.lblPic3, self.lblFileName3, self.lblInfo3], [self.btnPrev3, self.btnNext3, self.btnCopy3])
                    self.apply_media_file(self.mediaFiles[index], self.lblPic3, self.lblFileName3, self.lblInfo3)
                    self.info3 = self.mediaFiles[index].capture_date
                    sectionEnabled = True
                    break
            if (not sectionEnabled):
                self.mark_section_disabled([self.lblPic3, self.lblFileName3, self.lblInfo3], [self.btnPrev3, self.btnNext3, self.btnCopy3])

    def apply_media_file(self, mediaFile: MediaFile,  picLabel: QtWidgets.QLabel, fileNameLabel: QtWidgets.QLabel, infoLabel: QtWidgets.QLabel):
        pic1: QtGui.QPixmap = QtGui.QPixmap(mediaFile.file_path)
        picLabel.setPixmap(pic1.scaled(picLabel.width(), picLabel.height(), aspectMode=QtCore.Qt.KeepAspectRatio))

        fileNameLabel.setText(os.path.relpath(mediaFile.file_path, self.txtDirToScan.text()))

        if (not infoLabel == None):
            infoLabel.setText(mediaFile.capture_date.strftime("%m/%d/%Y, %H:%M:%S"))

    def mark_section_disabled(self, labels: List[QtWidgets.QLabel], buttons: List[QtWidgets.QPushButton]):
        for label in labels:
            label.setPixmap(None)
            label.setText("N/A")
        for button in buttons:
            button.setEnabled(False)

    def mark_section_enabled(self, labels: List[QtWidgets.QLabel], buttons: List[QtWidgets.QPushButton]):
        for label in labels:
            label.setText("")
        for button in buttons:
            button.setEnabled(True)

    def btnCopy1_click(self):
        self.selectedDateTimeEdit2.setDateTime(QtCore.QDateTime(self.info1))

    def btnCopy3_click(self):
        self.selectedDateTimeEdit2.setDateTime(QtCore.QDateTime(self.info3))

    def btnSave2_click(self):
        if (self.mediaFiles[self.picked_index].file_type == ScannedFileType.IMAGE.name):
            self.write_exif_to_file(self.mediaFiles[self.picked_index].file_path, 'datetimeoriginal', self.selectedDateTimeEdit2.dateTime().toPyDateTime())
        if (self.mediaFiles[self.picked_index].file_type == ScannedFileType.VIDEO.name):
            self.write_exif_to_file(self.mediaFiles[self.picked_index].file_path, 'createdate', self.selectedDateTimeEdit2.dateTime().toPyDateTime())
            self.write_exif_to_file(self.mediaFiles[self.picked_index].file_path, 'modifydate', self.selectedDateTimeEdit2.dateTime().toPyDateTime())
        self.pullUpNextMediaFile()

    def btnDelete2_click(self):
        os.remove(self.mediaFiles[self.picked_index].file_path)
        self.pullUpNextMediaFile()

    def write_exif_to_file(self, file_path: str, exif_tag_name: str, capture_date: datetime):
        tag_with_value = "-" + exif_tag_name + "=" + capture_date.strftime("%Y:%m:%d %H:%M:%S")
        args = ["exiftool", "-overwrite_original", tag_with_value, file_path]
        MediaProcessor.exec_subprocess(args, "EXIF write failed")
