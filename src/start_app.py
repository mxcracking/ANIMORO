import os
import time
import subprocess
from threading import active_count
from time import sleep

from src.constants import (APP_VERSION, ddos_protection_calc, ddos_wait_timer,
                           language, name, output_path, season_override,
                           site_url, type_of_media, url, dlMode, cliProvider, output_root, output_name,
                           thread_download_wait_timer, max_download_threads, disable_thread_timer,
                           episode_override)
from src.custom_logging import setup_logger
from src.logic.collect_all_seasons_and_episodes import get_episodes, get_season, get_movies
from src.logic.downloader import already_downloaded, create_new_download_thread
from src.logic.language import LanguageError
from src.logic.search_for_links import (find_cache_url, get_redirect_link_by_provider, get_year)
from src.failures import write_fails
from src.successes import write_success

logger = setup_logger(__name__)

def is_ffmpeg_installed():
    # Attempt to execute ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "ffmpeg version" in result.stdout.decode()
    
    except FileNotFoundError:
        return False

# ------------------------------------------------------- #
#                       main
# ------------------------------------------------------- #

def main(args=None):
    if args is None:
        args = {}
    
    # Überschreibe die Konstanten mit den GUI-Argumenten
    global type_of_media, name, language, dlMode, season_override, cliProvider, url, output_name, episode_override
    type_of_media = args.get("TYPE", type_of_media)
    name = args.get("NAME", name)
    output_name = name
    language = args.get("LANG", language)
    dlMode = args.get("MODE", dlMode)
    season_override = args.get("SEASON", season_override)
    episode_override = args.get("EPISODE", episode_override)
    cliProvider = args.get("PROVIDER", cliProvider)
    url = "{}/{}/stream/{}/".format(site_url[type_of_media], type_of_media, name)

    logger.info("-----------------------------------------------------------")
    logger.info(f"            AnimeSerienScraper {APP_VERSION} started")
    logger.info("-----------------------------------------------------------")

    ddos_start_value = 0

    read_check = os.access('DO_NOT_DELETE.txt', os.R_OK)
    if read_check:
        logger.debug("We have Read Permission")
    else:
        logger.error("No Read Permission. Please check if you own the Folder and/or have "
                     "permissions to read.")
        exit()
    write_check = os.access('DO_NOT_DELETE.txt', os.W_OK)
    if write_check:
        logger.debug("We have Write Permission")
    else:
        logger.error("No Write Permission. Please check if you own the Folder and/or have "
                     "permissions to write.")
        exit()

    if not os.path.exists(output_root):
        logger.info("Output folder does not exist. Creating it now.")
        os.makedirs(output_root, exist_ok=True)

    if name == "Name-Goes-Here":
        logger.error("Name is Default. Please read readme before starting.")
        exit()

    # Check if FFMPEG is installed before even trying to download episodes
    if not is_ffmpeg_installed():
        logger.error("FFMPEG is not installed or could not be run. You can download it at https://ffmpeg.org/")
        exit()

    # if user wants to download all seasons starting from X it would be X+ so 2+ would be 2,3,4...
    str_season_override = str(season_override)
    if "+" in str_season_override:
        starting_season = int(season_override.replace("+", "")) - 1
        logger.info(f"Starting Season is: {starting_season + 1}")
        seasons = get_season(url)
    else:
        starting_season = 0
        if season_override == 0:
            logger.info("No Season override detected.")
            if dlMode.lower() == 'movies':
                seasons = 1
            else:
                seasons = get_season(url)
            logger.info("We have this many seasons: {}".format(seasons))
        else:
            logger.info("Season Override detected. Override set to: {}".format(season_override))
            seasons = 1

    year = get_year(url)
    output_path = f"{output_root}/{type_of_media}/{output_name}_({year})"
    os.makedirs(output_path, exist_ok=True)

    threadpool = []

    for season in range(int(seasons)):
        if season < starting_season:
            continue
        if not starting_season:
            season = season + 1 if season_override == 0 else season_override
        else:
            season = season + 1
        season = int(season)
        if dlMode.lower() == 'movies':
            season_path_movies = f"{output_path}/Movies"
            os.makedirs(season_path_movies, exist_ok=True)
        elif dlMode.lower() == 'series':
            season_path_series = f"{output_path}/Season {season:02}"
            os.makedirs(season_path_series, exist_ok=True)
        else:
            season_path_movies = f"{output_path}/Movies"
            season_path_series = f"{output_path}/Season {season:02}"
            os.makedirs(season_path_movies, exist_ok=True)
            os.makedirs(season_path_series, exist_ok=True)

        if dlMode.lower() == 'movies':
            episode_count_movies = get_movies(url)
            logger.info("Show has {} Movie(s)/Special(s).".format(episode_count_movies))
        elif dlMode.lower() == 'series':
            episode_count_series = get_episodes(url, season)
            logger.info("Season {} has {} Episodes.".format(season, episode_count_series))
        else:
            episode_count_movies = get_movies(url)
            episode_count_series = get_episodes(url, season)
            logger.info("Show has {} Movies/Specials.".format(episode_count_movies))
            logger.info("Season {} has {} Episodes.".format(season, episode_count_series))

        if dlMode.lower() == 'movies':
            for episode in range(int(episode_count_movies)):
                episode = episode + 1
                file_name = "{}/{}-{}.mp4".format(season_path_movies, name, episode)
                logger.info("File name will be: " + file_name)
                if not already_downloaded(file_name):
                    link = url + "filme/film-{}".format(episode)
                    try:
                        redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, cliProvider)
                    except LanguageError:
                        continue
                    if ddos_start_value < ddos_protection_calc:
                        logger.debug("Entered DDOS var check and starting new downloader.")
                        ddos_start_value += 1
                    else:
                        logger.info("Started {} Downloads. Waiting for {} Seconds to not trigger DDOS"
                                    "Protection.".format(ddos_protection_calc, ddos_wait_timer))
                        time.sleep(ddos_wait_timer)
                        ddos_start_value = 1
                    cache_url = find_cache_url(redirect_link, provider)
                    if cache_url == 0:
                        logger.error(f"Could not find cache url for {provider} on {season}, {episode}.")
                        continue
                    logger.debug("{} Cache URL is: ".format(provider) + cache_url)
                    threadpool.append(create_new_download_thread(cache_url, file_name, provider))
        elif dlMode.lower() == 'series':
            if episode_override:
                episode = int(episode_override)
                file_name = "{}/{} - s{:02}e{:02} - {}.mp4".format(season_path_series, name, season, episode, language)
                logger.info("File name will be: " + file_name)
                if not already_downloaded(file_name):
                    link = url + "staffel-{}/episode-{}".format(season, episode)
                    try:
                        redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, cliProvider)
                    except LanguageError:
                        return
                    if ddos_start_value < ddos_protection_calc:
                        logger.debug("Entered DDOS var check and starting new downloader.")
                        ddos_start_value += 1
                    else:
                        logger.info("Started {} Downloads. Waiting for {} Seconds to not trigger DDOS"
                                    "Protection.".format(ddos_protection_calc, ddos_wait_timer))
                        time.sleep(ddos_wait_timer)
                        ddos_start_value = 1
                    cache_url = find_cache_url(redirect_link, provider)
                    if cache_url == 0:
                        logger.error(f"Could not find cache url for {provider} on {season}, {episode}.")
                        return
                    logger.debug("{} Cache URL is: ".format(provider) + cache_url)
                    threadpool.append(create_new_download_thread(cache_url, file_name, provider))
            else:
                for episode in range(int(episode_count_series)):
                    episode = episode + 1
                    file_name = "{}/{} - s{:02}e{:02} - {}.mp4".format(season_path_series, name, season, episode, language)
                    logger.info("File name will be: " + file_name)
                    if not already_downloaded(file_name):
                        link = url + "staffel-{}/episode-{}".format(season, episode)
                        try:
                            redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, cliProvider)
                        except LanguageError:
                            continue
                        if ddos_start_value < ddos_protection_calc:
                            logger.debug("Entered DDOS var check and starting new downloader.")
                            ddos_start_value += 1
                        else:
                            logger.info("Started {} Downloads. Waiting for {} Seconds to not trigger DDOS"
                                        "Protection.".format(ddos_protection_calc, ddos_wait_timer))
                            time.sleep(ddos_wait_timer)
                            ddos_start_value = 1
                        cache_url = find_cache_url(redirect_link, provider)
                        if cache_url == 0:
                            logger.error(f"Could not find cache url for {provider} on {season}, {episode}.")
                            continue
                        logger.debug("{} Cache URL is: ".format(provider) + cache_url)
                        threadpool.append(create_new_download_thread(cache_url, file_name, provider))
        else:
            for episode in range(int(episode_count_movies)):
                episode = episode + 1
                file_name = "{}/{}-{}.mp4".format(season_path_movies, name, episode)
                logger.info("File name will be: " + file_name)
                if not already_downloaded(file_name):
                    link = url + "filme/film-{}".format(episode)
                    try:
                        redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, cliProvider)
                    except LanguageError:
                        continue
                    if ddos_start_value < ddos_protection_calc:
                        logger.debug("Entered DDOS var check and starting new downloader.")
                        ddos_start_value += 1
                    else:
                        logger.info("Started {} Downloads. Waiting for {} Seconds to not trigger DDOS"
                                    "Protection.".format(ddos_protection_calc, ddos_wait_timer))
                        time.sleep(ddos_wait_timer)
                        ddos_start_value = 1
                    cache_url = find_cache_url(redirect_link, provider)
                    if cache_url == 0:
                        logger.error(f"Could not find cache url for {provider} on {season}, {episode}.")
                        continue
                    logger.debug("{} Cache URL is: ".format(provider) + cache_url)
                    threadpool.append(create_new_download_thread(cache_url, file_name, provider))
            for episode in range(int(episode_count_series)):
                episode = episode + 1
                file_name = "{}/{} - s{:02}e{:02} - {}.mp4".format(season_path_series, name, season, episode, language)
                logger.info("File name will be: " + file_name)
                if not already_downloaded(file_name):
                    link = url + "staffel-{}/episode-{}".format(season, episode)
                    try:
                        redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, cliProvider)
                    except LanguageError:
                        continue
                    active_threads = active_count()
                    logger.debug(f"Active Threads START: {active_threads}")
                    if ddos_start_value < ddos_protection_calc:
                        logger.debug("Entered DDOS var check and starting new downloader.")
                        ddos_start_value += 1
                    else:
                        logger.info("Started {} Downloads. Waiting for {} Seconds to not trigger DDOS"
                                    "Protection.".format(ddos_protection_calc, ddos_wait_timer))
                        time.sleep(ddos_wait_timer)
                        active_threads = active_count()
                        if not disable_thread_timer:
                            while active_threads > max_download_threads:
                                logger.info(f"Active Threads: {active_threads}. Waiting {thread_download_wait_timer}s "
                                            f"before checking again if we are under {max_download_threads} threads.")
                                time.sleep(thread_download_wait_timer)
                                active_threads = active_count()
                        logger.debug(f"Resetting DDOS Counter to 1.")
                        ddos_start_value = 1
                    cache_url = find_cache_url(redirect_link, provider)
                    if cache_url == 0:
                        logger.error(f"Could not find cache url for {provider} on {season}, {episode}.")
                        continue
                    logger.debug("{} Cache URL is: ".format(provider) + cache_url)
                    threadpool.append(create_new_download_thread(cache_url, file_name, provider))
                    active_threads = active_count()
                    logger.debug(f"Active Threads STARTED: {active_threads}")

        for thread in threadpool:
            thread.join()

        write_success()
        write_fails()
