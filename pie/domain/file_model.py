from enum import Enum
from datetime import datetime
from typing import List
from pie.common import Base
from sqlalchemy import Column, Integer, String, Boolean, ARRAY, DateTime, Float


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

    def __init__(self, parent_dir_path, file_path, extension, file_type, is_raw, creation_time, last_modification_time,
                 already_indexed=False, index_id=None, needs_reindex=False):
        self.parent_dir_path = parent_dir_path
        self.file_path = file_path
        self.extension = extension
        self.file_type = file_type
        self.is_raw = is_raw
        self.creation_time = creation_time
        self.last_modification_time = last_modification_time
        self.already_indexed = already_indexed
        self.needs_reindex = needs_reindex


class MediaFile(Base):
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


class Settings(Base):
    __tablename__ = 'settings'
    id: str = Column(String, primary_key=True)
    monitored_dir: str = Column(String)
    dirs_to_exclude: str = Column(String)
    output_dir: str = Column(String)
    unknown_output_dir: str = Column(String)
    output_dir_path_type: str = Column(String)
    unknown_output_dir_path_type: str = Column(String)
    app_data_dir: str = Column(String)
    skip_same_name_video: bool = Column(Boolean)
    skip_same_name_raw: bool = Column(Boolean)
    convert_unknown: bool = Column(Boolean)
    overwrite_output_files: bool = Column(Boolean)
    indexing_workers: int = Column(Integer)
    conversion_workers: int = Column(Integer)
    gpu_workers: int = Column(Integer)
    gpu_count: int = Column(Integer)
    image_compression_quality: int = Column(Integer)
    image_max_dimension: int = Column(Integer)
    video_max_dimension: int = Column(Integer)
    video_crf: int = Column(Integer)
    video_nvenc_preset: str = Column(String)
    video_audio_bitrate: int = Column(Integer)


class IndexingTask:
    indexing_time: datetime
    settings: Settings

    def __init__(self):
        self.indexing_time = datetime.now()
