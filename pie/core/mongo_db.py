import logging
import multiprocessing
from pie.domain import MediaFile, Settings
from pie.util import MiscUtils
from mongoengine import connect, disconnect, disconnect_all, Document


class MongoDB:
    __logger = logging.getLogger('MongoDB')
    __DB_NAME = "pie2"

    @staticmethod
    def connect_db():
        connect(MongoDB.__DB_NAME)
        MongoDB.__logger.info("Connected to MongoDB")

    @staticmethod
    def disconnect_db():
        disconnect()
        MongoDB.__logger.info("Disconnected from MongoDB")

    @staticmethod
    def disconnect_db_all():
        disconnect_all()
        MongoDB.__logger.info("Disconnected all from MongoDB")

    @staticmethod
    def clear_indexed_files():
        MediaFile.drop_collection()
        MongoDB.__logger.info("Indexed file MongoDB collection cleared")

    @staticmethod
    def clear_settings():
        Settings.drop_collection()
        MongoDB.__logger.info("Settings cleared")

    @staticmethod
    def insert_media_file(media_file: MediaFile):
        media_file.save()

    @staticmethod
    def get_by_file_path(file_path_to_query: str):
        results = MediaFile.objects(file_path=file_path_to_query)
        if results and len(results) > 0:
            return results[0]
        return None

    @staticmethod
    def get_by_output_rel_path(output_rel_path_to_query: str):
        results = MediaFile.objects(output_rel_file_path = output_rel_path_to_query)
        if results and len(results) > 0:
            return results[0]
        return None
    
    @staticmethod
    def delete_document(document: Document):
        document.delete()

    @staticmethod
    def get_all_media_file_ordered():
        # Sort entries like: None -> 2003 -> 2004 -> 2019 -> ect
        return MediaFile.objects().order_by(MediaFile.capture_date.name)

    @staticmethod
    def get_settings():
        save_record = False
        results = Settings.objects()
        if (results and len(results) > 0):
            settings = results[0]
        else:
            settings = Settings()

        # Apply defaults if they are not already set
        if (not settings.dirs_to_exclude):
            settings.dirs_to_exclude = []
            save_record = True
        if (not settings.log_file_dir):
            settings.log_file_dir = "logs"
            save_record = True
        if (not settings.convert_unknown):
            settings.convert_unknown = False
            save_record = True
        if (not settings.output_dir_path_type):
            settings.output_dir_path_type = "Use Original Paths"
            save_record = True
        if (not settings.unknown_output_dir_path_type):
            settings.unknown_output_dir_path_type = "Use Original Paths"
            save_record = True
        if (not settings.overwrite_output_files):
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
            MongoDB.save_settings(settings)
        return settings

    @staticmethod
    def save_settings(settings: Settings):
        settings.save()
