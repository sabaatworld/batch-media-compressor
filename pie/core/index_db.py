import logging
import os
from logging import Logger
from typing import Dict, List

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pie.common import Base
from pie.domain import MediaFile, Settings
from pie.util import MiscUtils


class IndexDB:
    __logger: Logger = logging.getLogger('IndexDB')

    def __init__(self):
        # For in-memory, use: 'sqlite:///:memory:'
        db_file = 'sqlite:///' + os.path.join(MiscUtils.get_app_data_dir(), "index.db")
        self.__engine = create_engine(db_file, echo=False)
        Base.metadata.create_all(self.__engine)
        self.__session: Session = sessionmaker(bind=self.__engine)()
        IndexDB.__logger.info("Connected to IndexDB")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect_db()

    def disconnect_db(self):
        self.__session.close()
        self.__engine.dispose()
        IndexDB.__logger.info("Disconnected from IndexDB")

    def clear_indexed_files(self):
        session = self.__session
        session.query(MediaFile).delete()
        session.commit()
        IndexDB.__logger.info("Indexed file IndexDB collection cleared")

    def insert_media_file(self, media_file: MediaFile):
        session = self.__session
        session.add(media_file)
        session.commit()

    def get_by_file_path(self, file_path_to_query: str):
        return self.__session.query(MediaFile).filter_by(file_path=file_path_to_query).first()

    def get_by_output_rel_path(self, output_rel_path_to_query: str):
        return self.__session.query(MediaFile).filter_by(output_rel_file_path=output_rel_path_to_query).first()

    def delete_media_file(self, media_file: MediaFile):
        session = self.__session
        session.delete(media_file)
        session.commit()

    def get_all_media_file_ordered(self) -> List[MediaFile]:
        # Sort entries like: None -> 2003 -> 2004 -> 2019 -> ect
        return self.__session.query(MediaFile).order_by(MediaFile.capture_date)

    def get_all_media_files_by_path(self) -> Dict[str, MediaFile]:
        media_files_by_path: Dict[str, MediaFile] = {}
        for media_file in self.get_all_media_file_ordered():
            media_files_by_path[media_file.file_path] = media_file
        return media_files_by_path

    def get_settings(self):
        session = self.__session
        save_record = False
        settings = session.query(Settings).filter_by(id='app_settings').first()
        if not settings:
            settings = Settings(id='app_settings')
            save_record = True

        # Apply defaults if they are not already set
        if settings.dirs_to_exclude is None:
            settings.dirs_to_exclude = '[]'
            save_record = True
        if settings.output_dir_path_type is None:
            settings.output_dir_path_type = "Use Original Paths"
            save_record = True
        if settings.unknown_output_dir_path_type is None:
            settings.unknown_output_dir_path_type = "Use Original Paths"
            save_record = True
        if settings.skip_same_name_video is None:
            settings.skip_same_name_video = True
            save_record = True
        if settings.skip_same_name_raw is None:
            settings.skip_same_name_raw = True
            save_record = True
        if settings.convert_unknown is None:
            settings.convert_unknown = False
            save_record = True
        if settings.overwrite_output_files is None:
            settings.overwrite_output_files = False
            save_record = True
        if settings.indexing_workers is None:
            settings.indexing_workers = MiscUtils.get_default_worker_count()
            save_record = True
        if settings.conversion_workers is None:
            settings.conversion_workers = MiscUtils.get_default_worker_count()
            save_record = True
        if settings.gpu_workers is None:
            settings.gpu_workers = 1
            save_record = True
        if settings.gpu_count is None:
            settings.gpu_count = 0
            save_record = True
        if settings.image_compression_quality is None:
            settings.image_compression_quality = 75
            save_record = True
        if settings.image_max_dimension is None:
            settings.image_max_dimension = 1920
            save_record = True
        if settings.video_max_dimension is None:
            settings.video_max_dimension = 1920
            save_record = True
        if settings.video_crf is None:
            settings.video_crf = 28
            save_record = True
        if settings.video_nvenc_preset is None:
            settings.video_nvenc_preset = "fast"
            save_record = True
        if settings.video_audio_bitrate is None:
            settings.video_audio_bitrate = 128
            save_record = True

        if save_record:
            session.add(settings)
            session.commit()

        return settings

    def save_settings(self, settings: Settings):
        session = self.__session
        session.add(settings)
        session.commit()

    def clear_settings(self):
        session = self.__session
        session.query(Settings).delete()
        session.commit()
        IndexDB.__logger.info("Settings cleared")

    @staticmethod
    def create_instance():
        return IndexDB()

    @staticmethod
    def destroy_instance(instance):
        instance.disconnect_db()
