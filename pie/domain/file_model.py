from enum import Enum
from datetime import datetime
from typing import List
from multiprocessing import Queue
from mongoengine import Document, EmbeddedDocument, StringField, ListField, ReferenceField, EmbeddedDocumentField, DateTimeField, ComplexDateTimeField, FloatField, EmbeddedDocumentListField, PointField, IntField, LongField, BooleanField


class ScannedFileType(Enum):
    __IMAGE_EXTENSIONS__ = ["JPEG", "JPG", "TIFF", "PNG", "BMP", "CR2", "DNG"]
    __VIDEO_EXTENSIONS__ = ["MOV", "MP4", "M4V", "3G2", "3GP", "AVI"]

    IMAGE = 1
    VIDEO = 2
    UNKNOWN = 3

    @staticmethod
    def get_type(extension):
        if extension in ScannedFileType.__IMAGE_EXTENSIONS__:
            return ScannedFileType.IMAGE
        elif extension in ScannedFileType.__VIDEO_EXTENSIONS__:
            return ScannedFileType.VIDEO
        else:
            return ScannedFileType.UNKNOWN


class ScannedFile:

    def __init__(self, parent_dir_path, file_path, extension, file_type, creation_time, last_modification_time,
                 already_indexed=False, index_id=None, needs_reindex=False):
        self.parent_dir_path = parent_dir_path
        self.file_path = file_path
        self.extension = extension
        self.file_type = file_type
        self.creation_time = creation_time
        self.last_modification_time = last_modification_time
        self.already_indexed = already_indexed
        self.needs_reindex = needs_reindex


class GPSAddressDecodeStatus(Enum):
    NOT_ATTEMPTED = 1
    DECODED = 2
    NO_MATCH = 3


class GPSInfo(EmbeddedDocument):
    point = PointField()
    altitude = FloatField()
    country = StringField()
    city = StringField()
    zip_code = StringField()
    street_address = StringField()
    address_decode_status = StringField()


class MediaFile(Document):
    uuid = StringField()
    parent_dir_path = StringField()
    file_path = StringField()
    extension = StringField()
    file_type = StringField()
    mime = StringField()
    original_size = LongField()
    creation_time = DateTimeField()
    last_modification_time = DateTimeField()
    index_time = DateTimeField()
    height = IntField()
    width = IntField()
    capture_date = DateTimeField()
    camera_make = StringField()
    camera_model = StringField()
    lens_model = StringField()
    gps_info = EmbeddedDocumentField(GPSInfo)
    view_rotation = StringField()
    image_orientation = StringField()
    video_duration = IntField()
    video_rotation = StringField()
    output_rel_file_path = StringField()
    meta = {
        'indexes': [
            {
                'fields': ['file_path'],
                'unique': True
            },
            {
                'fields': ['uuid'],
                'unique': True
            },
            {
                'fields': ['output_rel_file_path']  # Can't be unique since its also saved as None
            }
        ]
    }


class Settings(Document):
    dirs_to_include: list = ListField()
    dirs_to_exclude: list = ListField()
    output_dir: str = StringField()
    log_file_dir: str = StringField()
    overwrite_output_files: bool = BooleanField()
    indexing_workers: int = LongField()
    conversion_workers: int = LongField()
    gpu_workers: int = LongField()
    gpu_count: int = LongField()
    image_compression_quality: int = LongField()
    image_max_dimension: int = LongField()
    video_max_dimension: int = LongField()
    video_crf: int = LongField()
    video_nvenc_preset: str = StringField()
    video_audio_bitrate: int = LongField()


class IndexingTask:
    indexing_time: datetime
    settings: Settings

    def __init__(self):
        self.indexing_time = datetime.now()
