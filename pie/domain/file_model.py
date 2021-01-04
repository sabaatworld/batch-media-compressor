import hashlib
import multiprocessing
import sys
from datetime import datetime
from enum import Enum
from typing import Set

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from pie.common import DB_BASE


class ScannedFileType(Enum):
    IMAGE = 1
    VIDEO = 2
    UNKNOWN = 3

    @staticmethod
    def get_type(image_extensions: Set[str], image_raw_extensions: Set[str], video_extensions: Set[str], video_raw_extensions: Set[str], file_extension: str):
        if file_extension in image_extensions:
            return (ScannedFileType.IMAGE, False)
        elif file_extension in image_raw_extensions:
            return (ScannedFileType.IMAGE, True)
        elif file_extension in video_extensions:
            return (ScannedFileType.VIDEO, False)
        elif file_extension in video_raw_extensions:
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
        self.dirs_to_exclude: str = '[]'
        self.output_dir: str = None
        self.unknown_output_dir: str = None
        self.output_dir_path_type: str = "Use Original Paths"
        self.unknown_output_dir_path_type: str = "Use Original Paths"
        self.skip_same_name_video: bool = True
        self.skip_same_name_raw: bool = True
        self.convert_unknown: bool = False
        self.overwrite_output_files: bool = False
        self.indexing_workers: int = Settings.get_default_worker_count()
        self.conversion_workers: int = Settings.get_default_worker_count()
        self.gpu_workers: int = 1
        self.gpu_count: int = 0
        self.image_compression_quality: int = 75
        self.image_max_dimension: int = 1920
        self.video_max_dimension: int = 1920
        self.video_crf: int = 28
        self.video_nvenc_preset: str = "fast"
        self.video_audio_bitrate: int = 128
        self.path_ffmpeg: str = "/usr/local/bin/ffmpeg" if not Settings.is_platform_win() else "ffmpeg"
        self.path_magick: str = "/usr/local/bin/magick" if not Settings.is_platform_win() else "magick"
        self.path_exiftool: str = "/usr/local/bin/exiftool" if not Settings.is_platform_win() else "exiftool"
        self.auto_update_check: bool = True
        self.auto_show_log_window: bool = True
        self.image_extensions: str = "JPEG, JPG, TIF, TIFF, PNG, BMP, HEIC"
        self.image_raw_extensions: str = "CRW, CR2, CR3, NRW, NEF, ARW, SRF, SR2, DNG"
        self.video_extensions: str = "MOV, MP4, M4V, 3G2, 3GP, AVI, MTS, MPG, MPEG"
        self.video_raw_extensions: str = ""

    @staticmethod
    def is_platform_win() -> bool:
        return sys.platform == 'win32' or sys.platform == 'cygwin'

    @staticmethod
    def get_default_worker_count() -> int:
        try:
            return multiprocessing.cpu_count()
        except:
            return 1

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
