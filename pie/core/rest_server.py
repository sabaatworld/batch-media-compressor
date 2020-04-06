import logging
import os
from pie.domain import ScannedFileType, MediaFile, IndexingTask, Settings
from pie.util import PyProcess, MiscUtils
from .mongo_db import MongoDB
from multiprocessing import Queue, Event, JoinableQueue, Process
from flask import Flask, escape, request
from send2trash import send2trash


class RestServer:
    __logger = logging.getLogger('RestServer')

    def __init__(self, settings: Settings, log_queue: Queue):
        self.__settings = settings
        self.__log_queue = log_queue

    @staticmethod
    def execStartServer(settings: Settings, log_queue: Queue):
        MiscUtils.configure_worker_logger(log_queue)
        MongoDB.connect_db()
        app = Flask('PIE_REST_API')

        @app.route('/')
        def welcome():
            name = request.args.get("name", "World")
            return f'Hello, {escape(name)}!'

        @app.route('/delete-originals', methods=['POST'])
        def handleDeleteOriginal():
            output_rel_path = request.form['output_rel_path']
            logging.info("Received request to delete original for: %s", output_rel_path)
            if output_rel_path:
                media_file: MediaFile = MongoDB.get_by_output_rel_path(output_rel_path)
                if (media_file):
                    if (os.path.exists(media_file.file_path)):
                        logging.info("Moving original to trash: %s", media_file.file_path)
                        send2trash(media_file.file_path)
                        return 'true'
            return 'false'

        # app.run(host='0.0.0.0', port=9898) Uncomment to run

    def startServer(self):
        self.__process = Process(target=RestServer.execStartServer, args=[self.__settings, self.__log_queue], name="Flask")
        self.__process.start()

    def stopServer(self):
        self.__process.terminate()
        self.__process.join()
