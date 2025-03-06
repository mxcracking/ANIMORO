from bs4 import BeautifulSoup

from src.custom_logging import setup_logger

logger = setup_logger(__name__)


class ProviderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class LanguageError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def restructure_dict(given_dict):
    new_dict = {}
    already_seen = set()
    for key, value in given_dict.items():
        new_dict[value] = set([element.strip() for element in key.split(',')])
    return_dict = {}
    for key, values in new_dict.items():
        for value in values:
            if value in already_seen and value in return_dict:
                del return_dict[value]
                continue
            if value not in already_seen and value not in return_dict:
                return_dict[value] = key
                already_seen.add(value)
    return return_dict


def extract_lang_key_mapping(soup):
    lang_key_mapping = {}
    
    # Versuche zuerst die changeLanguageBox
    change_language_div = soup.find("div", class_="changeLanguageBox")
    if change_language_div:
        lang_elements = change_language_div.find_all("img")
        for lang_element in lang_elements:
            language = lang_element.get("alt", "") + "," + lang_element.get("title", "")
            data_lang_key = lang_element.get("data-lang-key", "")
            if language and data_lang_key:
                lang_key_mapping[language] = data_lang_key
    
    # Wenn keine changeLanguageBox gefunden wurde, suche nach anderen Sprachhinweisen
    if not lang_key_mapping:
        # Suche nach Sprach-Links
        lang_links = soup.find_all("a", {"class": ["language-link", "lang-select"]})
        for link in lang_links:
            language = link.get_text().strip()
            data_lang_key = link.get("data-lang", link.get("data-language", link.get("id", "")))
            if language and data_lang_key:
                lang_key_mapping[language] = data_lang_key
        
        # Suche nach Sprach-Buttons
        lang_buttons = soup.find_all("button", {"class": ["language-button", "lang-btn"]})
        for button in lang_buttons:
            language = button.get_text().strip()
            data_lang_key = button.get("data-lang", button.get("data-language", button.get("id", "")))
            if language and data_lang_key:
                lang_key_mapping[language] = data_lang_key

    # Wenn immer noch keine Sprachen gefunden wurden, versuche es mit Standard-Mapping
    if not lang_key_mapping:
        default_mapping = {
            "Deutsch": "german",
            "Ger-Sub": "german-sub",
            "English": "english",
            "Eng-Sub": "english-sub"
        }
        # Suche nach Text-Hinweisen für verfügbare Sprachen
        content = soup.get_text().lower()
        for lang, key in default_mapping.items():
            if lang.lower() in content or key in content:
                lang_key_mapping[lang] = key

    ret = restructure_dict(lang_key_mapping)
    logger.debug(f"Restructured language mapping: {ret}")
    return ret


def get_href_by_language(html_content, language, provider):
    soup = BeautifulSoup(html_content, "html.parser")
    lang_key_mapping = extract_lang_key_mapping(soup)

    if not lang_key_mapping:
        # Versuche es mit dem Standard-Provider-Link
        provider_elements = soup.find_all(["a", "div", "li"], string=lambda text: provider.lower() in str(text).lower())
        if provider_elements:
            for element in provider_elements:
                href = element.get("data-link-target") or element.get("href")
                if href:
                    logger.warning(f"No language mapping found, using first available {provider} link")
                    return href
        raise LanguageError(logger.error("No language mapping or provider links found."))

    # Debug logs
    logger.debug(f"Language mapping: {lang_key_mapping}")
    logger.debug(f"Given language: {language}")

    # Find the data-lang-key value based on the input language
    lang_key = lang_key_mapping.get(language)
    if lang_key is None:
        available_langs = list(lang_key_mapping.keys())
        if available_langs:
            logger.warning(f"Language '{language}' not found. Available languages: {available_langs}")
            logger.warning(f"Using first available language: {available_langs[0]}")
            lang_key = lang_key_mapping[available_langs[0]]
        else:
            raise LanguageError(logger.error("No languages available"))

    # Find all <li> elements with the given data-lang-key value and h4=provider
    matching_li_elements = soup.find_all("li", {"data-lang-key": lang_key})
    matching_li_element = next((li_element for li_element in matching_li_elements
                                if li_element.find("h4") and li_element.find("h4").get_text().lower() == provider.lower()), None)

    # Wenn kein passendes Element gefunden wurde, suche nach alternativen Elementen
    if not matching_li_element:
        # Suche nach Links mit dem Provider-Namen
        provider_elements = soup.find_all(["a", "div", "li"], string=lambda text: provider.lower() in str(text).lower())
        for element in provider_elements:
            href = element.get("data-link-target") or element.get("href")
            if href:
                logger.warning(f"Using alternative {provider} link")
                return href

    # Wenn ein passendes Element gefunden wurde, gib den Link zurück
    if matching_li_element:
        href = matching_li_element.get("data-link-target", "")
        return href

    raise ProviderError(logger.error(f"No matching download found for language '{language}' and provider '{provider}'"))
