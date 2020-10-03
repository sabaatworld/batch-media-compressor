import sys
import logging
import multiprocessing
import threading
from pie import TrayIcon, PreferencesWindow
from pie.util import MiscUtils
from multiprocessing import Manager
from PySide2 import QtCore, QtWidgets, QtGui

if __name__ == "__main__":
    APP_ICON_FILE_PATH = "assets/pie_logo.png"

    multiprocessing.set_start_method('spawn')
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    QtGui.QGuiApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    MiscUtils.configure_logging()
    log_queue = Manager().Queue()
    logger_thread = threading.Thread(target=MiscUtils.logger_thread_exec, args=(log_queue,))
    logger_thread.start()

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(APP_ICON_FILE_PATH))
    app.setApplicationDisplayName("Personal Image Explorer")  # TODO test + add org / ver
    app.setQuitOnLastWindowClosed(False)

    tray_icon = TrayIcon(APP_ICON_FILE_PATH, log_queue)
    tray_icon.show()
    tray_icon.start_watching()
    return_code = app.exec_()
    tray_icon.stop_watching()

    # tray_icon.cleanup()
    logging.info("Application is being shutdown")
    log_queue.put(None)
    logging.debug("Waiting for logging thread to terminate")
    logger_thread.join()
    sys.exit(return_code)
