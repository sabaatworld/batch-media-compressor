import logging
import multiprocessing
import sys
import threading
from multiprocessing import Manager, freeze_support

from PySide2 import QtCore, QtGui, QtWidgets
from zc.lockfile import LockError, LockFile

from pie import TrayIcon
from pie.util import MiscUtils

if __name__ == "__main__":
    if MiscUtils.running_in_pyinstaller_bundle():
        freeze_support()

    multiprocessing.set_start_method('spawn')
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    QtGui.QGuiApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    MiscUtils.configure_logging()
    log_queue = Manager().Queue()
    logger_thread = threading.Thread(target=MiscUtils.logger_thread_exec, args=(log_queue,))
    logger_thread.start()

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(MiscUtils.get_app_icon_path()))
    app.setApplicationDisplayName("Batch Media Compressor")
    app.setQuitOnLastWindowClosed(False)

    try:
        lock = LockFile(MiscUtils.get_lock_file_path())
        tray_icon = TrayIcon(log_queue)
        tray_icon.show()
        return_code = app.exec_()
        tray_icon.cleanup()
        lock.close()
    except LockError:
        error_msg = "Cannot acquire lock on file {}.\n\nAnother instance of the application is probably running.".format(MiscUtils.get_lock_file_path())
        logging.fatal(error_msg)
        QtWidgets.QMessageBox.critical(None, "Batch Media Compressor - Error", error_msg, QtWidgets.QMessageBox.Ok)
        return_code = -1
    
    logging.info("Application is being shutdown")
    log_queue.put(None)
    logging.debug("Waiting for logging thread to terminate")
    logger_thread.join()
    logging.debug("Exit Code: %s", return_code)
    sys.exit(return_code)
