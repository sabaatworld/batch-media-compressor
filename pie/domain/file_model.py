import hashlib
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from pie.common import DB_BASE


class ScannedFileType(Enum):
    __IMAGE_EXTENSIONS__ = ["JPEG", "JPG", "TIF", "TIFF", "PNG", "BMP", "HEIC"]
    __RAW_IMAGE_EXTENSIONS__ = ["CR2", "DNG"]
    __VIDEO_EXTENSIONS__ = ["MOV", "MP4", "M4V", "3G2", "3GP", "AVI", "MTS", "MPG", "MPEG"]
    __RAW_VIDEO_EXTENSIONS__ = []

    IMAGE = 1
    VIDEO = 2
    UNKNOWN = 3

    @staticmethod
    def get_type(extension):
        if extension in ScannedFileType.__IMAGE_EXTENSIONS__:
            return (ScannedFileType.IMAGE, False)
        elif extension in ScannedFileType.__RAW_IMAGE_EXTENSIONS__:
            return (ScannedFileType.IMAGE, True)
        elif extension in ScannedFileType.__VIDEO_EXTENSIONS__:
            return (ScannedFileType.VIDEO, False)
        elif extension in ScannedFileType.__RAW_VIDEO_EXTENSIONS__:
            return (ScannedFileType.VIDEO, True)
        else:
            return (ScannedFileType.UNKNOWN, False)


class ScannedFile:

    def __init__(self, parent_dir_path, file_path, extension, file_type, is_raw, creation_time, last_modification_time, hash,
                 already_indexed=False, needs_reindex=False):
        self.parent_dir_path = parent_dir_path
        self.file_path = file_path
        self.extension = extension
        self.file_type = file_type
        self.is_raw = is_raw
        self.creation_time = creation_time
        self.last_modification_time = last_modification_time
        self.hash = hash
        self.already_indexed = already_indexed
        self.needs_reindex = needs_reindex


class MediaFile(DB_BASE):
    __tablename__ = 'media_files'
    parent_dir_path = Column(String)
    file_path = Column(String, primary_key=True)
    extension = Column(String)
    file_type = Column(String)
    is_raw = Column(Boolean)
    mime = Column(String)
    original_size = Column(Integer)
    creation_time = Column(DateTime)
    last_modification_time = Column(DateTime)
    original_file_hash = Column(String)
    converted_file_hash = Column(String)
    conversion_settings_hash = Column(String)
    index_time = Column(DateTime)
    height = Column(Integer)
    width = Column(Integer)
    capture_date = Column(DateTime)
    camera_make = Column(String)
    camera_model = Column(String)
    lens_model = Column(String)
    gps_long = Column(Float)
    gps_lat = Column(Float)
    gps_alt = Column(Float)
    view_rotation = Column(String)
    image_orientation = Column(String)
    video_duration = Column(Integer)
    video_rotation = Column(String)
    output_rel_file_path = Column(String)


class Settings:

    def __init__(self) -> None:
        self.monitored_dir: str = None
        self.dirs_to_exclude: str = None
        self.output_dir: str = None
        self.unknown_output_dir: str = None
        self.output_dir_path_type: str = None
        self.unknown_output_dir_path_type: str = None
        self.skip_same_name_video: bool = None
        self.skip_same_name_raw: bool = None
        self.convert_unknown: bool = None
        self.overwrite_output_files: bool = None
        self.indexing_workers: int = None
        self.conversion_workers: int = None
        self.gpu_workers: int = None
        self.gpu_count: int = None
        self.image_compression_quality: int = None
        self.image_max_dimension: int = None
        self.video_max_dimension: int = None
        self.video_crf: int = None
        self.video_nvenc_preset: str = None
        self.video_audio_bitrate: int = None
        self.path_ffmpeg: str = None
        self.path_magick: str = None
        self.path_exiftool: str = None
        self.auto_update_check: bool = None

    def generate_image_settings_hash(self):
        settings_hash = hashlib.sha1()
        settings_hash.update(self.image_compression_quality.to_bytes(64, byteorder='big'))
        settings_hash.update(self.image_max_dimension.to_bytes(64, byteorder='big'))
        return settings_hash.hexdigest()

    def generate_video_settings_hash(self):
        settings_hash = hashlib.sha1()
        settings_hash.update(self.video_max_dimension.to_bytes(64, byteorder='big'))
        settings_hash.update(self.video_crf.to_bytes(64, byteorder='big'))
        settings_hash.update(str.encode(self.video_nvenc_preset))
        settings_hash.update(self.video_audio_bitrate.to_bytes(64, byteorder='big'))
        return settings_hash.hexdigest()


class IndexingTask:
    indexing_time: datetime
    settings: Settings

    def __init__(self):
        self.indexing_time = datetime.now()
