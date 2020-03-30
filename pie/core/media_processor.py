import logging
import subprocess
import time
import math
import os
from pie.domain import ScannedFileType, MediaFile, IndexingTask, Settings
from pie.util import PyProcessPool
from .mongo_db import MongoDB
from typing import List
from datetime import datetime
from multiprocessing import Queue, Event, Lock, Manager


class MediaProcessor:
    __logger = logging.getLogger('MediaProcessor')

    def __init__(self, indexing_task: IndexingTask, log_queue: Queue,  indexing_stop_event: Event):
        self.__indexing_task = indexing_task
        self.__log_queue = log_queue
        self.__indexing_stop_event = indexing_stop_event

    def save_processed_files(self):
        MediaProcessor.__logger.info("BEGIN:: Media file conversion")
        media_files = MongoDB.get_all_media_file_ordered()
        if (not media_files or len(media_files) == 0):
            MediaProcessor.__logger.info("No media files found in MongoDB")
        else:
            manager = Manager()
            save_file_path_computation_lock = manager.Lock()

            if (self.__indexing_task.settings.gpu_count == 0):
                self.start_cpu_pool(save_file_path_computation_lock, media_files).wait_and_get_results()
            else:
                image_media_files = []
                video_media_files = []
                for media_file in media_files:
                    media_file: MediaFile = media_file
                    if (media_file.file_type == ScannedFileType.IMAGE.name):
                        image_media_files.append(media_file)
                    if (media_file.file_type == ScannedFileType.VIDEO.name):
                        video_media_files.append(media_file)
                cpu_pool = self.start_cpu_pool(save_file_path_computation_lock, image_media_files)
                gpu_pool = self.start_gpu_pool(save_file_path_computation_lock, video_media_files)
                cpu_pool.wait_and_get_results()
                gpu_pool.wait_and_get_results()
        MediaProcessor.__logger.info("END:: Media file conversion")

    def start_gpu_pool(self, save_file_path_computation_lock: Lock, media_files: List[MediaFile]):
        process_count = self.__indexing_task.settings.gpu_count * self.__indexing_task.settings.gpu_workers
        pool = PyProcessPool(pool_name="GPUConversionWorker", process_count=process_count, log_queue=self.__log_queue, target=MediaProcessor.conversion_process_exec,
                             initializer=MongoDB.connect_db, terminator=MongoDB.disconnect_db, stop_event=self.__indexing_stop_event)
        tasks = []
        for media_file_index, media_file in enumerate(media_files, start=0):
            target_gpu = media_file_index % self.__indexing_task.settings.gpu_count
            tasks.append([self.__indexing_task, media_file, target_gpu, save_file_path_computation_lock])
        pool.submit(tasks)
        return pool

    def start_cpu_pool(self, save_file_path_computation_lock: Lock, media_files: List[MediaFile]):
        pool = PyProcessPool(pool_name="CPUConversionWorker", process_count=self.__indexing_task.settings.conversion_workers, log_queue=self.__log_queue,
                             target=MediaProcessor.conversion_process_exec, initializer=MongoDB.connect_db, terminator=MongoDB.disconnect_db, stop_event=self.__indexing_stop_event)
        tasks = list(map(lambda media_file: (self.__indexing_task, media_file, -1, save_file_path_computation_lock), media_files))
        pool.submit(tasks)
        return pool

    @staticmethod
    def conversion_process_exec(indexing_task: IndexingTask, media_file: MediaFile, target_gpu: int, save_file_path_computation_lock: Lock, task_id: str):
        processing_start_time = time.time()
        original_file_path = media_file.file_path
        save_file_path_copy = "UNKNOWN"  # Creating a copy so that it can be used with exception logging below
        try:
            with save_file_path_computation_lock:
                save_file_path = MediaProcessor.get_save_file_path(media_file, indexing_task.settings)
                save_file_path_copy = save_file_path

            skip_conversion: bool = False
            if (not media_file.capture_date and not indexing_task.settings.convert_unknown):  # No captureDate and conversion not requested for unknown
                if os.path.exists(save_file_path):
                    os.remove(save_file_path)
                    logging.info("Deleted Converted File %s: %s -> %s", task_id, original_file_path, save_file_path)
                skip_conversion = True
            else:
                os.makedirs(os.path.dirname(save_file_path), exist_ok=True)
                open(save_file_path, 'a').close()  # Append mode ensures that existing file is not emptied TODO move to lock block above
                if (not indexing_task.settings.overwrite_output_files and os.path.exists(save_file_path) and os.path.getsize(save_file_path) > 0):
                    skip_conversion = True

            if not skip_conversion:
                if ScannedFileType.IMAGE.name == media_file.file_type:
                    MediaProcessor.convert_image_file(indexing_task.settings, media_file, original_file_path, save_file_path)
                if ScannedFileType.VIDEO.name == media_file.file_type:
                    MediaProcessor.convert_video_file(indexing_task.settings, media_file, original_file_path, save_file_path, target_gpu)
                MediaProcessor.copy_exif_to_file(original_file_path, save_file_path, media_file.video_rotation)
                logging.info("Converted %s: %s -> %s (%s%%) (%ss)", task_id, original_file_path, save_file_path,
                             round(os.path.getsize(save_file_path) / media_file.original_size * 100, 2), round(time.time() - processing_start_time, 2))
            else:
                logging.info("Skipped Conversion %s: %s -> %s", task_id, original_file_path, save_file_path)
        except:
            logging.exception("Failed Processing %s: %s -> %s (%ss)", task_id, original_file_path, save_file_path_copy, round(time.time() - processing_start_time, 2))

    @staticmethod
    def convert_image_file(settings: Settings, media_file: MediaFile, original_file_path: str, save_file_path: str):
        # Sample: magick convert -resize 320x480 -quality 75 inputFile.cr2 outputfile.jpg
        args = ["magick", "convert", "-quality", str(settings.image_compression_quality), original_file_path, save_file_path]

        new_dimentions = MediaProcessor.get_new_dimentions(media_file.height, media_file.width, settings.image_max_dimension)
        if (new_dimentions):
            args.insert(2, "-resize")
            args.insert(3, "{}x{}".format(new_dimentions['height'], new_dimentions['width']))
        MediaProcessor.exec_subprocess(args, "Image conversion failed")

    @staticmethod
    def convert_video_file(settings: Settings, media_file: MediaFile, original_file_path: str, new_file_path: str, target_gpu: int):
        new_dimentions = MediaProcessor.get_new_dimentions(media_file.height, media_file.width, settings.video_max_dimension)
        audio_bitrate_arg = str(settings.video_audio_bitrate) + "k"

        if (target_gpu < 0):
            # CPU Sample: ffmpeg -noautorotate -i input -c:v libx265 -crf 28 -c:a aac -vf scale=320:240 -b:a 128k -y output.mp4
            args = ["ffmpeg", "-noautorotate",  "-i", original_file_path, "-c:v", "libx265",  "-crf", str(settings.video_crf),
                    "-c:a",  "aac", "-b:a", audio_bitrate_arg, "-y", new_file_path]
            if (new_dimentions):
                args.insert(10, "-vf")
                args.insert(11, "scale={}:{}".format(new_dimentions['width'], new_dimentions['height']))
        else:
            # GPU Sample: ffmpeg -noautorotate -hwaccel nvdec -hwaccel_device 0 -i input -c:v hevc_nvenc -preset fast -gpu 0 -c:a aac -b:a 128k -vf "hwupload_cuda,scale_npp=w=1920:h=1080:format=yuv420p" -y output.mp4
            args = ["ffmpeg", "-noautorotate",  "-hwaccel", "nvdec", "-hwaccel_device", str(target_gpu), "-i",  original_file_path,
                    "-c:v", "hevc_nvenc",  "-preset", settings.video_nvenc_preset, "-gpu", str(target_gpu),
                    "-c:a",  "aac", "-b:a", audio_bitrate_arg, "-y", new_file_path]
            if (new_dimentions):
                args.insert(18, "-vf")
                args.insert(19, "hwupload_cuda,scale_npp=w={}:h={}:format=yuv420p".format(new_dimentions['width'], new_dimentions['height']))
        MediaProcessor.exec_subprocess(args, "Video conversion failed")

    @staticmethod
    def copy_exif_to_file(original_file_path: str, new_file_path: str, rotation: str):
        args = ["exiftool", "-overwrite_original", "-tagsFromFile", original_file_path, new_file_path]
        if (rotation):
            args.insert(4, "-rotation={}".format(rotation))
        MediaProcessor.exec_subprocess(args, "EXIF copy failed")

    @staticmethod
    def exec_subprocess(popenargs: List[str], errorMsg: str):
        results = subprocess.run(popenargs, capture_output=True)
        if (results.returncode != 0):
            raise RuntimeError("{}: CommandLine: {}, Output: {}".format(errorMsg, subprocess.list2cmdline(popenargs), str(results.stderr)))

    @staticmethod
    def get_new_dimentions(original_height: int, original_width: int, max_dimention: int):
        if (max(original_height, original_width) <= max_dimention):
            return None
        if (original_height > original_width):
            new_height = max_dimention
            new_width = (new_height * original_width) / original_height
        else:
            new_width = max_dimention
            new_height = (original_height * new_width) / original_width
        return {'height': math.floor(new_height), 'width': math.floor(new_width)}

    @staticmethod
    def get_save_file_path(media_file: MediaFile, settings: Settings):
        capture_date: datetime = media_file.capture_date
        out_dir = settings.output_dir if capture_date else settings.unknown_output_dir
        if (media_file.output_rel_file_path):
            return os.path.join(out_dir, media_file.output_rel_file_path)

        save_dir_path = MediaProcessor.get_save_dir_path(media_file, settings)
        file_extension = MediaProcessor.get_save_file_extension(media_file)
        if (capture_date):
            save_file_path = MediaProcessor.get_regular_save_file_path(media_file, save_dir_path, file_extension)
        else:
            save_file_path = MediaProcessor.get_unknown_save_file_path(media_file, save_dir_path, file_extension)
        media_file.output_rel_file_path = os.path.relpath(save_file_path, out_dir)
        MongoDB.insert_media_file(media_file)
        return save_file_path

    @staticmethod
    def get_save_dir_path(media_file: MediaFile, settings: Settings):
        if media_file.capture_date:
            date_path = os.path.join(str(media_file.capture_date.year), str(media_file.capture_date.month), str(media_file.capture_date.day))
            save_dir_path = os.path.join(settings.output_dir, date_path)
        else:
            parent_dir_rel_path = os.path.relpath(media_file.parent_dir_path, settings.monitored_dir)
            save_dir_path = os.path.join(settings.unknown_output_dir, parent_dir_rel_path)
        return save_dir_path

    @staticmethod
    def get_save_file_extension(media_file: MediaFile):
        if ScannedFileType.IMAGE.name == media_file.file_type:
            file_extension = ".JPG"
        elif ScannedFileType.VIDEO.name == media_file.file_type:
            file_extension = ".MP4"
        else:
            raise RuntimeError("Media file type '{}' is not supported", media_file.file_type)
        return file_extension

    @staticmethod
    def get_unknown_save_file_path(media_file: MediaFile, save_dir_path: str, file_extension: str):
        original_file_name = os.path.basename(media_file.file_path)
        file_name_tuple = os.path.splitext(original_file_name)
        file_name_without_extension = file_name_tuple[0]
        return MediaProcessor.find_save_file_path(save_dir_path, file_name_without_extension, file_extension)

    @staticmethod
    def get_regular_save_file_path(media_file: MediaFile, save_dir_path: str, file_extension: str):
        time_prefix = media_file.capture_date.strftime("%H%M%S")
        return MediaProcessor.find_save_file_path(save_dir_path, time_prefix, file_extension)

    @staticmethod
    def find_save_file_path(save_dir_path: str, file_name: str, file_extension: str):
        ideal_save_path = os.path.join(save_dir_path, file_name + file_extension)
        if (not os.path.isfile(ideal_save_path)):
            save_file_path = ideal_save_path
        else:
            files = sorted(filter(lambda k: k.startswith(file_name) and k.endswith(file_extension), os.listdir(save_dir_path)), reverse=True)
            # We know that there is atleast 1 file; but we would have applied the counter only if there were 2 or more
            if (len(files) > 1):
                # TODO this will not work when path contains symbols like '.' , '_'. May also fail due to parallel processing. Best to use DB and find out a good filename.
                next = int(files[0].rsplit(".")[0].rsplit("_")[1]) + 1
            else:
                next = 1
            save_file_path = os.path.join(save_dir_path, file_name + "_" + format(next, '05d') + file_extension)
        return save_file_path
