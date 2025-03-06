import os
import platform
import subprocess
import time
from os import path
from threading import Thread
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from src.custom_logging import setup_logger
from src.failures import append_failure, remove_file
from src.successes import append_success

logger = setup_logger(__name__)

def create_session_with_retries():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504, 520, 521, 522, 524]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def already_downloaded(file_name):
    if os.path.exists(file_name):
        if os.path.getsize(file_name) > 0:
            logger.info("Episode {} already downloaded.".format(file_name))
            return True
        else:
            logger.debug("File exists but is empty. Removing and re-downloading: {}".format(file_name))
            os.remove(file_name)
    logger.debug("File not downloaded. Downloading: {}".format(file_name))
    return False

def download(link, file_name):
    MAX_RETRIES = 3
    CHUNK_SIZE = 8192
    retry_count = 0
    session = create_session_with_retries()

    while retry_count < MAX_RETRIES:
        try:
            logger.debug(f"Attempt {retry_count + 1}/{MAX_RETRIES} - Link: {link}, File: {file_name}")
            
            # Überprüfe zuerst den Link
            head_response = session.head(link, timeout=10)
            if head_response.status_code != 200:
                raise requests.RequestException(f"Invalid status code: {head_response.status_code}")
            
            # Starte den Download
            with session.get(link, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                with open(file_name, 'wb') as f:
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                logger.debug(f"Download progress: {percent:.1f}%")
                
                if path.getsize(file_name) > 0:
                    logger.success("Finished download of {}.".format(file_name))
                    append_success(file_name)
                    return True
                else:
                    raise Exception("Downloaded file is empty")
                
        except (requests.RequestException, Exception) as e:
            retry_count += 1
            logger.warning(f"Download attempt {retry_count} failed: {str(e)}")
            
            if retry_count < MAX_RETRIES:
                wait_time = 20 * retry_count
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to download {file_name} after {MAX_RETRIES} attempts: {str(e)}")
                append_failure(file_name)
                remove_file(file_name)
                return False

def download_and_convert_hls_stream(hls_url, file_name):
    MAX_RETRIES = 3
    retry_count = 0
    
    # Finde den FFmpeg-Pfad
    if path.exists("ffmpeg.exe"):
        ffmpeg_path = "ffmpeg.exe"
    elif path.exists("src/ffmpeg.exe"):
        ffmpeg_path = "src/ffmpeg.exe"
    else:
        ffmpeg_path = "ffmpeg"

    while retry_count < MAX_RETRIES:
        try:
            # Überprüfe zuerst die HLS-URL
            session = create_session_with_retries()
            response = session.head(hls_url, timeout=10)
            if response.status_code != 200:
                raise requests.RequestException(f"Invalid HLS URL status: {response.status_code}")

            # FFmpeg-Befehl mit zusätzlichen Optionen für bessere Stabilität
            ffmpeg_cmd = [
                ffmpeg_path,
                '-y',  # Überschreibe existierende Dateien
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '30',
                '-i', hls_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                file_name
            ]

            if platform.system() == "Windows":
                process = subprocess.run(
                    ffmpeg_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
            else:
                process = subprocess.run(
                    ffmpeg_cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            # Überprüfe die Ausgabedatei
            if path.exists(file_name) and path.getsize(file_name) > 0:
                logger.success("Finished download of {}.".format(file_name))
                append_success(file_name)
                return True
            else:
                raise Exception("Output file is empty or missing")

        except (subprocess.CalledProcessError, requests.RequestException, Exception) as e:
            retry_count += 1
            logger.warning(f"HLS download attempt {retry_count} failed: {str(e)}")
            
            if retry_count < MAX_RETRIES:
                wait_time = 20 * retry_count
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to download {file_name} after {MAX_RETRIES} attempts: {str(e)}")
                append_failure(file_name)
                remove_file(file_name)
                return False

def create_new_download_thread(url, file_name, provider) -> Thread:
    logger.debug("Creating new download thread.")
    
    # Stelle sicher, dass der Ausgabeordner existiert
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    
    if provider in ["Vidoza", "Streamtape"]:
        t = Thread(target=download, args=(url, file_name))
    elif provider == "VOE":
        t = Thread(target=download_and_convert_hls_stream, args=(url, file_name))
    else:
        logger.error(f"Unknown provider: {provider}")
        return None
        
    t.daemon = True  # Beende Thread, wenn Hauptprogramm beendet wird
    t.start()
    logger.loading("Provider {} - File {} added to queue.".format(provider, file_name))
    return t
