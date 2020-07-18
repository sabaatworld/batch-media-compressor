import logging
import multiprocessing
import os
from pie.domain import MediaFile, Settings
from pie.util import MiscUtils
from mongoengine import connect, disconnect, disconnect_all, Document
from pie.common import Base
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


class IndexDB:
    __logger = logging.getLogger('IndexDB')
    __DB_NAME = "pie"

    @staticmethod
    def connect_db():
        # For in-memory, use: 'sqlite:///:memory:'
        IndexDB.__engine = create_engine('sqlite:///' + os.path.join(MiscUtils.get_app_data_dir(), "index.db"), echo=True)
        Base.metadata.create_all(IndexDB.__engine)
        IndexDB.__Session = sessionmaker(bind=IndexDB.__engine)
        IndexDB.__logger.info("Connected to IndexDB")

    @staticmethod
    def disconnect_db():
        IndexDB.__engine.dispose()
        IndexDB.__logger.info("Disconnected from IndexDB")

    @staticmethod
    def clear_indexed_files():
        session = IndexDB.__Session()
        session.query(MediaFile).delete()
        session.commit()
        session.close()
        IndexDB.__logger.info("Indexed file IndexDB collection cleared")

    @staticmethod
    def clear_settings():
        session = IndexDB.__Session()
        session.query(Settings).delete()
        session.commit()
        session.close()
        IndexDB.__logger.info("Settings cleared")

    @staticmethod
    def insert_media_file(media_file: MediaFile):
        session = inspect(media_file).session
        if (session):
            session.commit()
        else:
            session = IndexDB.__Session()
            session.add(media_file)
            session.commit()
            session.close()

    @staticmethod
    def get_by_file_path(file_path_to_query: str):
        session = IndexDB.__Session()
        return session.query(MediaFile).filter_by(file_path=file_path_to_query).first()

    @staticmethod
    def get_by_output_rel_path(output_rel_path_to_query: str):
        session = IndexDB.__Session()
        return session.query(MediaFile).filter_by(output_rel_file_path=output_rel_path_to_query).first()

    @staticmethod
    def delete_media_file(media_file: MediaFile):
        inspect(media_file).session.delete(media_file)

    @staticmethod
    def get_all_media_file_ordered():
        # Sort entries like: None -> 2003 -> 2004 -> 2019 -> ect
        session = IndexDB.__Session()
        return session.query(MediaFile).order_by(MediaFile.capture_date)

    @staticmethod
    def get_settings():
        session = IndexDB.__Session()
        save_record = False
        settings = session.query(Settings).filter_by(id='app_settings').first()
        if (not settings):
            settings = Settings(id='app_settings')
            save_record = True

        # Apply defaults if they are not already set
        if (not settings.dirs_to_exclude):
            settings.dirs_to_exclude = '[]'
            save_record = True
        if (not settings.output_dir_path_type):
            settings.output_dir_path_type = "Use Original Paths"
            save_record = True
        if (not settings.unknown_output_dir_path_type):
            settings.unknown_output_dir_path_type = "Use Original Paths"
            save_record = True
        if (settings.skip_same_name_video == None):
            settings.skip_same_name_video = True
            save_record = True
        if (settings.convert_unknown == None):
            settings.convert_unknown = False
            save_record = True
        if (settings.overwrite_output_files == None):
            settings.overwrite_output_files = False
            save_record = True
        if (not settings.indexing_workers):
            settings.indexing_workers = MiscUtils.get_default_worker_count()
            save_record = True
        if (not settings.conversion_workers):
            settings.conversion_workers = MiscUtils.get_default_worker_count()
            save_record = True
        if (not settings.gpu_workers):
            settings.gpu_workers = 1
            save_record = True
        if (not settings.gpu_count):
            settings.gpu_count = 0
            save_record = True
        if (not settings.image_compression_quality):
            settings.image_compression_quality = 75
            save_record = True
        if (not settings.image_max_dimension):
            settings.image_max_dimension = 1920
            save_record = True
        if (not settings.video_max_dimension):
            settings.video_max_dimension = 1920
            save_record = True
        if (not settings.video_crf):
            settings.video_crf = 28
            save_record = True
        if (not settings.video_nvenc_preset):
            settings.video_nvenc_preset = "fast"
            save_record = True
        if (not settings.video_audio_bitrate):
            settings.video_audio_bitrate = 128
            save_record = True

        if (save_record):
            session.add(settings)
            session.commit()

        return settings

    @staticmethod
    def save_settings(settings: Settings):
        inspect(settings).session.commit()
