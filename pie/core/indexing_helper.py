import logging
import os
import concurrent.futures
import multiprocessing
import time
from pie.domain import ScannedFile, ScannedFileType, IndexingTask, MediaFile
from .mongo_db import MongoDB
from .exif_helper import ExifHelper
from typing import List, Dict, Callable
from datetime import datetime
from pie.util import MiscUtils, PyProcess, PyProcessPool
from multiprocessing import Process, Value, Queue, JoinableQueue, Event
from logging import Logger


class IndexingHelper:
    __logger: Logger = logging.getLogger('IndexingHelper')

    def __init__(self, indexing_task: IndexingTask, log_queue: Queue, indexing_stop_event: Event):
        self.__indexing_task = indexing_task
        self.__log_queue = log_queue
        self.__indexing_stop_event = indexing_stop_event

    def lookup_already_indexed_files(self, scanned_files: List[ScannedFile]):
        IndexingHelper.__logger.info("BEGIN:: MongoDB lookup for indexed files")
        total_scanned_files = len(scanned_files)
        for scanned_file_num, scanned_file in enumerate(scanned_files, start=1):
            media_file = MongoDB.get_by_file_path(scanned_file.file_path)
            if (media_file):
                scanned_file.already_indexed = True
                if (scanned_file.creation_time > media_file.index_time or scanned_file.last_modification_time > media_file.index_time):
                    scanned_file.needs_reindex = True
            IndexingHelper.__logger.info("Searched Index %s/%s: %s (AlreadyIndexed = %s, NeedsReindex= %s)", scanned_file_num, total_scanned_files,
                                         scanned_file.file_path, scanned_file.already_indexed, scanned_file.needs_reindex)
        IndexingHelper.__logger.info("END:: MongoDB lookup for indexed files")

    def remove_slate_files(self, scanned_files: List[ScannedFile]):
        IndexingHelper.__logger.info("BEGIN:: Deletion of slate files")
        media_files: List[MediaFile] = MongoDB.get_all_media_file_ordered()
        if (not media_files or len(media_files) == 0):
            IndexingHelper.__logger.info("No media files found in MongoDB")
        else:
            for media_file in media_files:
                if (not any(scanned_file.file_path == media_file.file_path for scanned_file in scanned_files)):
                    IndexingHelper.__logger.info("Deleting slate entry %s and its output file %s", media_file.file_path, media_file.output_rel_file_path)
                    if (media_file.output_rel_file_path):
                        out_dir = self.__indexing_task.settings.output_dir if media_file.capture_date else self.__indexing_task.settings.unknown_output_dir
                        output_file = os.path.join(out_dir, media_file.output_rel_file_path)
                        if (os.path.exists(output_file)):
                            os.remove(output_file)
                    MongoDB.delete_document(media_file)
        IndexingHelper.__logger.info("END:: Deletion of slate files")

    def scan_dirs(self):
        IndexingHelper.__logger.info("BEGIN:: Dir scan")
        scanned_files = self.__scan_dir(self.__indexing_task.settings.monitored_dir)
        IndexingHelper.__logger.info("END:: Dir scan")
        return scanned_files

    def __scan_dir(self, dir):
        IndexingHelper.__logger.info("BEGIN:: Scanning DIR: %s", dir)
        scanned_files = []
        for dir_path, _, file_names in os.walk(dir):
            if (self.exclude_dir_from_scan(dir_path)):
                IndexingHelper.__logger.info("Skipping Directory Scan: %s", dir_path)
            else:
                for file_name in file_names:
                    file_name_tuple = os.path.splitext(file_name)
                    extension = file_name_tuple[1].replace(".", "").upper()
                    scanned_file_type = ScannedFileType.get_type(extension)
                    file_path = os.path.join(dir_path, file_name)
                    if (ScannedFileType.UNKNOWN != scanned_file_type):
                        creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        last_modification_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        scanned_file = ScannedFile(dir_path, file_path, extension, scanned_file_type, creation_time, last_modification_time)
                        scanned_files.append(scanned_file)
                        IndexingHelper.__logger.info("Found File: %s", file_path)
                    else:
                        IndexingHelper.__logger.info("Skipped File: %s", file_path)
        IndexingHelper.__logger.info("END:: Scanning DIR: %s", dir)
        return scanned_files

    def create_media_files(self, scanned_files: List[ScannedFile]):
        IndexingHelper.__logger.info("BEGIN:: Media file creation and indexing")
        pool = PyProcessPool(pool_name="IndexingWorker", process_count=self.__indexing_task.settings.indexing_workers, log_queue=self.__log_queue,
                             target=IndexingHelper.indexing_process_exec, initializer=MongoDB.connect_db, terminator=MongoDB.disconnect_db, stop_event=self.__indexing_stop_event)
        tasks = list(map(lambda scanned_file: (self.__indexing_task, scanned_file), scanned_files))
        media_files = pool.submit_and_wait(tasks)
        IndexingHelper.__logger.info("END:: Media file creation and indexing")
        return media_files

    @staticmethod
    def indexing_process_exec(indexing_task: IndexingTask, scanned_file: ScannedFile, task_id: str):
        if (not scanned_file.already_indexed or scanned_file.needs_reindex):
            try:
                existing_media_file = None
                if (scanned_file.needs_reindex):
                    existing_media_file: MediaFile = MongoDB.get_by_file_path(scanned_file.file_path)
                    if (existing_media_file and existing_media_file.output_rel_file_path):
                        out_dir = indexing_task.settings.output_dir if existing_media_file.capture_date else indexing_task.settings.unknown_output_dir
                        existing_output_file = os.path.join(out_dir, existing_media_file.output_rel_file_path)
                        if (os.path.exists(existing_output_file)):
                            logging.info("Deleting old output file %s for %s", existing_output_file, existing_media_file.file_path)
                            os.remove(existing_output_file)
                media_file = ExifHelper.create_media_file(indexing_task.indexing_time, scanned_file, existing_media_file)
                if (media_file):
                    MongoDB.insert_media_file(media_file)
                logging.info("Indexed Successfully %s: %s", task_id, scanned_file.file_path)
                return media_file  # PyProcessPool will take care of filtering None values
            except:
                logging.exception("Indexing Failed %s: %s", task_id, scanned_file.file_path)
        else:
            logging.info("Indexing Skipped %s: %s", task_id, scanned_file.file_path)

    def exclude_dir_from_scan(self, dir_path: str):
        for dir_to_exclude in self.__indexing_task.settings.dirs_to_exclude:
            return dir_path.startswith(dir_to_exclude)
