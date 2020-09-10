import logging
import os
import concurrent.futures
import time
from pie.domain import ScannedFile, ScannedFileType, IndexingTask, MediaFile
from pie.util import MiscUtils, PyProcess, PyProcessPool
from .index_db import IndexDB
from .exif_helper import ExifHelper
from typing import List, Dict, Callable
from datetime import datetime
from multiprocessing import Process, Value, Queue, JoinableQueue, Event, Manager, Lock
from logging import Logger
from pathlib import Path


class IndexingHelper:
    __logger: Logger = logging.getLogger('IndexingHelper')

    def __init__(self, indexing_task: IndexingTask, log_queue: Queue, indexing_stop_event: Event):
        self.__indexing_task = indexing_task
        self.__log_queue = log_queue
        self.__indexing_stop_event = indexing_stop_event

    def lookup_already_indexed_files(self, indexDB: IndexDB, scanned_files: List[ScannedFile]):
        IndexingHelper.__logger.info("BEGIN:: IndexDB lookup for indexed files")
        total_scanned_files = len(scanned_files)
        media_files_by_path = indexDB.get_all_media_files_by_path()
        for scanned_file_num, scanned_file in enumerate(scanned_files, start=1):
            if (self.__indexing_stop_event.is_set()):
                break
            if (scanned_file.file_path in media_files_by_path):
                media_file = media_files_by_path[scanned_file.file_path]
                scanned_file.already_indexed = True
                if (scanned_file.creation_time != media_file.creation_time or scanned_file.last_modification_time != media_file.last_modification_time):
                    scanned_file.needs_reindex = True
            IndexingHelper.__logger.info("Searched Index %s/%s: %s (AlreadyIndexed = %s, NeedsReindex= %s)", scanned_file_num, total_scanned_files,
                                         scanned_file.file_path, scanned_file.already_indexed, scanned_file.needs_reindex)
        IndexingHelper.__logger.info("END:: IndexDB lookup for indexed files")

    def remove_slate_files(self, indexDB: IndexDB, scanned_files: List[ScannedFile]):
        IndexingHelper.__logger.info("BEGIN:: Deletion of slate files")
        media_files: List[MediaFile] = indexDB.get_all_media_file_ordered()
        scanned_files_by_path = self.get_scanned_files_by_path(scanned_files)
        if (not media_files or media_files.count() == 0):
            IndexingHelper.__logger.info("No media files found in IndexDB")
        else:
            for media_file in media_files:
                if (self.__indexing_stop_event.is_set()):
                    break
                if (not media_file.file_path in scanned_files_by_path):
                    output_file = None
                    if (media_file.output_rel_file_path):
                        out_dir = self.__indexing_task.settings.output_dir if media_file.capture_date else self.__indexing_task.settings.unknown_output_dir
                        output_file = os.path.join(out_dir, media_file.output_rel_file_path)
                    IndexingHelper.__logger.info("Deleting slate entry %s and its output file %s", media_file.file_path, output_file)
                    if (not output_file == None and os.path.exists(output_file)):
                        os.remove(output_file)
                    indexDB.delete_media_file(media_file)
        IndexingHelper.__logger.info("END:: Deletion of slate files")

    def get_scanned_files_by_path(self, scanned_files: List[ScannedFile]) -> Dict[str, ScannedFile]:
        scanned_files_by_path: Dict[str, ScannedFile] = {}
        for scanned_file in scanned_files:
            scanned_files_by_path[scanned_file.file_path] = scanned_file
        return scanned_files_by_path

    def scan_dirs(self):
        IndexingHelper.__logger.info("BEGIN:: Dir scan")
        scanned_files = self.__scan_dir(self.__indexing_task.settings.monitored_dir)
        IndexingHelper.__logger.info("END:: Dir scan")
        return scanned_files

    def __scan_dir(self, dir):
        IndexingHelper.__logger.info("BEGIN:: Scanning DIR: %s", dir)
        scanned_files = []
        for dir_path, _, file_names in os.walk(dir):
            if (self.__indexing_stop_event.is_set()):
                break
            if (self.exclude_dir_from_scan(dir_path)):
                IndexingHelper.__logger.info("Skipping Directory Scan: %s", dir_path)
            else:
                scanned_files_by_name = {}
                for file_name in file_names:
                    file_name_tuple = os.path.splitext(file_name)
                    file_name_without_extension = file_name_tuple[0]
                    extension = file_name_tuple[1].replace(".", "").upper()
                    scanned_file_type = ScannedFileType.get_type(extension)
                    file_path = os.path.join(dir_path, file_name)
                    if (ScannedFileType.UNKNOWN != scanned_file_type):
                        creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        last_modification_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        scanned_file = ScannedFile(dir_path, file_path, extension, scanned_file_type, creation_time, last_modification_time)
                        if file_name_without_extension not in scanned_files_by_name:
                            scanned_files_by_name[file_name_without_extension] = []
                        scanned_files_by_name[file_name_without_extension].append(scanned_file)
                    else:
                        IndexingHelper.__logger.info("File Skipped (UNKNOWN_TYPE): %s", file_path)
                # Filter videos if there are images with the same name
                for _, files in scanned_files_by_name.items():
                    for file in files:
                        if (self.__indexing_task.settings.skip_same_name_video and len(files) > 1 and ScannedFileType.IMAGE != file.file_type):
                            IndexingHelper.__logger.info("File Skipped (SAME_NAME_AS_IMAGE): %s", file.file_path)
                        else:
                            IndexingHelper.__logger.info("File Scanned: %s", file.file_path)
                            scanned_files.append(file)
        IndexingHelper.__logger.info("END:: Scanning DIR: %s", dir)
        return scanned_files

    def create_media_files(self, scanned_files: List[ScannedFile]):
        IndexingHelper.__logger.info("BEGIN:: Media file creation and indexing")
        pool = PyProcessPool(pool_name="IndexingWorker", process_count=self.__indexing_task.settings.indexing_workers, log_queue=self.__log_queue,
                             target=IndexingHelper.indexing_process_exec, initializer=IndexDB.create_instance, terminator=IndexDB.destroy_instance, stop_event=self.__indexing_stop_event)
        db_write_lock: Lock = Manager().Lock()
        tasks = list(map(lambda scanned_file: (self.__indexing_task.indexing_time, self.__indexing_task.settings.output_dir,
                                               self.__indexing_task.settings.unknown_output_dir, scanned_file, db_write_lock), scanned_files))
        pool.submit_and_wait(tasks)
        IndexingHelper.__logger.info("END:: Media file creation and indexing")

    @staticmethod
    def indexing_process_exec(indexing_time: datetime, output_dir: str, unknown_output_dir: str, scanned_file: ScannedFile, db_write_lock: Lock, indexDB: IndexDB, task_id: str):
        if (not scanned_file.already_indexed or scanned_file.needs_reindex):
            try:
                existing_media_file = None
                if (scanned_file.needs_reindex):
                    existing_media_file: MediaFile = indexDB.get_by_file_path(scanned_file.file_path)
                    if (existing_media_file and existing_media_file.output_rel_file_path):
                        out_dir = output_dir if existing_media_file.capture_date else unknown_output_dir
                        existing_output_file = os.path.join(out_dir, existing_media_file.output_rel_file_path)
                        if (os.path.exists(existing_output_file)):
                            logging.info("Deleting old output file %s for %s", existing_output_file, existing_media_file.file_path)
                            os.remove(existing_output_file)
                media_file = ExifHelper.create_media_file(indexing_time, scanned_file, existing_media_file)
                if (media_file):
                    with db_write_lock:
                        indexDB.insert_media_file(media_file)
                logging.info("Indexed Successfully %s: %s", task_id, scanned_file.file_path)
                return media_file  # PyProcessPool will take care of filtering None values
            except:
                logging.exception("Indexing Failed %s: %s", task_id, scanned_file.file_path)
        else:
            logging.info("Indexing Skipped %s: %s", task_id, scanned_file.file_path)

    def exclude_dir_from_scan(self, dir_path: str):
        for dir_to_exclude in self.__indexing_task.settings.dirs_to_exclude:
            path_to_exclude = Path(dir_to_exclude)
            path_to_check = Path(dir_path)
            return path_to_exclude == path_to_check or path_to_exclude in path_to_check.parents
