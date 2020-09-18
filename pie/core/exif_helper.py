import logging
import os
import pyexifinfo
import mimetypes
import re
from pie.domain import MediaFile, ScannedFile, ScannedFileType
from pie.util import MiscUtils
from datetime import datetime
from dateutil.parser import parse
from dateutil.tz import UTC


class ExifHelper:
    __logger = logging.getLogger('ExifHelper')

    @staticmethod
    def create_media_file(index_time: datetime, scanned_file: ScannedFile, existing_media_file: MediaFile) -> MediaFile:
        file_path = scanned_file.file_path
        exif = ExifHelper.__get_exif_dict(file_path)
        error_str = ExifHelper.__get_exif(exif, "Error")
        exif_file_type_str = ExifHelper.__get_exif(exif, "FileType")
        if (error_str):
            ExifHelper.__logger.error("Error processing file. EXIF: %s", exif)
            if ('File is empty' == error_str or 'File format error' == error_str or 'file is binary' in error_str):
                return None
        if ("TXT" == exif_file_type_str):
            ExifHelper.__logger.error("Possibly corrupt file. EXIF: %s", exif)
            return None
        media_file = existing_media_file if existing_media_file else MediaFile()
        media_file.parent_dir_path = scanned_file.parent_dir_path
        media_file.file_path = file_path
        media_file.extension = scanned_file.extension
        media_file.file_type = scanned_file.file_type.name
        media_file.is_raw = scanned_file.is_raw
        media_file.mime = ExifHelper.__get_mime(file_path, exif)
        media_file.original_size = os.path.getsize(file_path)
        media_file.creation_time = scanned_file.creation_time
        media_file.last_modification_time = scanned_file.last_modification_time
        media_file.original_file_hash = scanned_file.hash if (scanned_file.hash != None) else MiscUtils.generate_hash(file_path)
        media_file.converted_file_hash = None
        media_file.conversion_settings_hash = None
        media_file.index_time = index_time
        ExifHelper.__append_dimentions(media_file, exif)
        media_file.capture_date = ExifHelper.__get_capture_date(scanned_file, exif)
        media_file.camera_make = ExifHelper.__get_exif(exif, "Make")
        media_file.camera_model = ExifHelper.__get_exif(exif, "CameraModelName", "Model")
        media_file.lens_model = ExifHelper.__get_exif(exif, "LensModel", "LensType", "LensInfo")
        gps_info = ExifHelper.__get_gps_info(exif)
        media_file.gps_alt = gps_info.get('altitude')
        media_file.gps_lat = gps_info.get('latitude')
        media_file.gps_long = gps_info.get('longitude')
        exif_orientation = ExifHelper.__get_exif(exif, "Orientation", "CameraOrientation")
        media_file.view_rotation = ExifHelper.__get_view_rotation(exif_orientation)
        media_file.image_orientation = exif_orientation
        media_file.video_duration = ExifHelper.__get_video_duration(exif)
        ExifHelper.__append_video_rotation(media_file, exif)
        return media_file

    @staticmethod
    def __get_exif_dict(file_path: str):
        json = pyexifinfo.get_json(file_path)[0]
        exif = {}
        for key, value in json.items():
            key_parts = key.split(":")
            modified_key = key_parts[1] if len(key_parts) > 1 else key_parts[0]
            exif[modified_key] = value
        return exif

    @staticmethod
    def __get_mime(file_path: str, exif: dict):
        exif_mime = ExifHelper.__get_exif(exif, "MIMEType")
        if (exif_mime):
            return exif_mime
        else:
            mime_type = mimetypes.guess_type(file_path, False)
            return mime_type[0]

    @staticmethod
    def __get_capture_date(scanned_file: ScannedFile, exif: dict):
        # Candidates: "GPSDateTime", "DateTimeOriginal", "DateTimeDigitized", "CreateDate", "CreationDate"
        date_str = None
        if (scanned_file.file_type == ScannedFileType.IMAGE):
            date_str = ExifHelper.__get_exif(exif, "DateTimeOriginal")
        if (scanned_file.file_type == ScannedFileType.VIDEO):
            date_str = ExifHelper.__get_exif(exif, "MediaCreateDate", "TrackCreateDate")
        if (date_str and not re.search(": +:|0000:00:00 00:00:00", date_str)):
            # Possible formats are yyyy:MM:dd HH:mm / yyyy.MM.dd HH:mm:ss / iPhoneImage: yyyy.MM.dd HH:mm:ss.FFF / iPhone 5: yyyy.MM.dd HH:mm:ss.XXZ
            # iPhoneVideo: yyyy.MM.dd HH:mm:sszzz, etc. To work with the automatic parser, we modify the date part a bit.
            date_str_parts = date_str.split(" ")
            if (len(date_str_parts) > 1):
                date_str_parts[0] = date_str_parts[0].replace(':', ".")
                if (re.match(r"^.+\.\d{1,2}Z$", date_str_parts[1])):  # Removing XX from yyyy.MM.dd HH:mm:ss.XXZ
                    time_str_parts = re.split(r"\.", date_str_parts[1])
                    date_str_parts[1] = time_str_parts[0] + "Z"
            date_str = " ".join(date_str_parts)
            capture_datetime = parse(date_str)
            return capture_datetime.astimezone(UTC) # TODO date gets messed up when timeZone is not specified. Sometimes it is local, sometimes UTC.

    @staticmethod
    def __append_dimentions(media_file: MediaFile, exif: dict):
        default_crop_size_str = ExifHelper.__get_exif(exif, "DefaultCropSize")
        if (default_crop_size_str):
            default_crop_size_str_parts = default_crop_size_str.split(" ")
            width = default_crop_size_str_parts[0]
            height = default_crop_size_str_parts[1]
        else:
            width = ExifHelper.__get_exif(exif, "ImageWidth", "ExifImageWidth")
            height = ExifHelper.__get_exif(exif, "ImageHeight", "ExifImageHeight")
        media_file.width = int(width)
        media_file.height = int(height)

    @staticmethod
    def __get_gps_info(exif: dict):
        gps_info = {}
        altitude_str = ExifHelper.__get_exif(exif, "GPSAltitude")
        if (altitude_str):
            altitude = float(altitude_str.split(" ")[0])
            altitude_ref_str = ExifHelper.__get_exif(exif, "GPSAltitudeRef")
            below_sea_level = "Below Sea Level"  # "Above Sea Level" is not used for anything yet
            if (below_sea_level in altitude_str or (altitude_ref_str and below_sea_level in altitude_ref_str)):
                altitude = altitude * -1.0
            gps_info['altitude'] = altitude
        longitude = ExifHelper.__gps_coordinate_str_to_float(ExifHelper.__get_exif(exif, "GPSLongitude"))
        latitude = ExifHelper.__gps_coordinate_str_to_float(ExifHelper.__get_exif(exif, "GPSLatitude"))
        if (longitude and latitude):
            gps_info['longitude'] = longitude
            gps_info['latitude'] = latitude
        return gps_info

    @staticmethod
    def __gps_coordinate_str_to_float(coordinate_str: str):
        if (coordinate_str):
            # Expects string to be in a format like 77 33 25.070000 or 77 33 25.070000 N or 47 deg 36' 27.90" N
            coordinate_str_parts = re.sub("deg |'|\"", "", coordinate_str).split(" ")
            degrees = float(coordinate_str_parts[0])
            minutes = float(coordinate_str_parts[1])
            seconds = float(coordinate_str_parts[2])
            float_value = (degrees + (minutes / 60) + (seconds / 3600))
            if (len(coordinate_str_parts) == 4):
                # This means direction is also present. Exceptions are possible due to software issues.
                if ("S" == coordinate_str_parts[3] or "W" == coordinate_str_parts[3]):
                    float_value = float_value * -1
            return float_value
        return None

    @staticmethod
    def __get_view_rotation(exif_orientation: str):
        rotations = {
            "Horizontal (normal)": "0",
            "Mirror horizontal": "!0",
            "Rotate 180": "180",
            "Mirror vertical": "!180",
            "Mirror horizontal and rotate 270 CW": "!270",
            "Rotate 90 CW": "90",
            "Mirror horizontal and rotate 90 CW": "!90",
            "Rotate 270 CW": "270"
        }
        if (exif_orientation and exif_orientation in rotations):
            return rotations[exif_orientation]
        else:
            # viewRoation for movies is 0 since their thumbnails don't need rotation
            return "0"

    @staticmethod
    def __get_video_duration(exif: dict):
        video_duration_str = ExifHelper.__get_exif(exif, "Duration", "MediaDuration", "TrackDuration")

        if (video_duration_str):
            if (re.match(r"^\d{1,2}:\d{2}:\d{2}$", video_duration_str)):  # 0:00:46
                duration_parts = video_duration_str.split(":")
                return ((int(duration_parts[0]) * 60 * 60) + (int(duration_parts[1]) * 60) + int(duration_parts[2])) * 1000
            elif (re.match(r"^\d{1,2}\.\d{1,3} s$", video_duration_str)):  # 14.44 s
                duration_parts = re.split(r"\.| ", video_duration_str)
                return (int(duration_parts[0]) * 1000) + int(duration_parts[1])
            else:
                raise RuntimeError('Unknown video duration format: ' + video_duration_str)
        return None

    @staticmethod
    def __append_video_rotation(media_file: MediaFile, exif: dict):
        video_rotation_str = str(ExifHelper.__get_exif(exif, "Rotation"))
        media_file.video_rotation = video_rotation_str
        # TODO Following logic messes with ffmpeg. Need to explore.
        # if ("90" == video_rotation_str or "270" == video_rotation_str):
        #     # If rotation is 90 or 270 flip recorded hight/width
        #     temp = media_file.width
        #     media_file.width = media_file.height
        #     media_file.height = temp

    @staticmethod
    def __get_exif(exif: dict, *keys):
        if len(keys) < 1:
            raise ValueError('get_exif() takes at least 1 key for looking up exif')
        for key in keys:
            if key in exif:
                return exif[key]
        return None
