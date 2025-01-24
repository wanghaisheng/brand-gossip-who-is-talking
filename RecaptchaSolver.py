import os
import urllib.request
import random
import pydub
import speech_recognition
import time
from typing import Optional, Protocol
import logging
from DrissionPage import Chromium
from DrissionPage.common import Settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Browser(Protocol):
    # def wait.ele_displayed(self, selector:str, timeout:int): ...
    def element(self, selector: str, timeout: int): ...
    def click(self): ...
    def input(self, value: str): ...
    def element_states(self): ...
    def attrs(self) -> dict: ...
    def clear_cookies(self): ...
    def get(self, url: str): ...
    def quit(self): ...

class DrissionPageBrowser(Browser):
    def __init__(self, driver: Chromium):
        self.driver = driver
    # def wait.ele_displayed(self, selector:str, timeout:int):
        # self.driver.wait.ele_displayed(selector, timeout=timeout)
    def element(self, selector: str, timeout: int):
        return self.driver.ele(selector, timeout=timeout)
    def click(self):
        self.driver.click()
    def input(self, value: str):
        self.driver.input(value)
    def element_states(self):
        return self.driver.states()
    def attrs(self) -> dict:
        return self.driver.attrs
    def clear_cookies(self):
        self.driver.clear_cookies()
    def get(self, url: str):
        self.driver.get(url)
    def quit(self):
        self.driver.quit()


class RecaptchaSolver:
    """A class to solve reCAPTCHA challenges using audio recognition."""

    # Constants
    TEMP_DIR = os.getenv("TEMP") if os.name == "nt" else "/tmp"
    TIMEOUT_STANDARD = 7
    TIMEOUT_SHORT = 1
    TIMEOUT_DETECTION = 0.05
    RETRY_COUNT = 2

    def __init__(self, driver: Browser, timeouts: dict=None) -> None:
        """Initialize the solver with a Chromium driver.

        Args:
            driver: Browser instance for browser interaction
        """
        self.driver = driver
        self.recognizer = speech_recognition.Recognizer()
        self.timeouts = timeouts or {
             "standard": self.TIMEOUT_STANDARD,
             "short": self.TIMEOUT_SHORT,
             "detection": self.TIMEOUT_DETECTION
        }

    def solveCaptcha(self) -> None:
        """Attempt to solve the reCAPTCHA challenge.

        Raises:
            Exception: If captcha solving fails or bot is detected
        """
        for attempt in range(self.RETRY_COUNT):
            try:
                self._solve_captcha_attempt()
                return  # Exit if successful
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2)  # Small backoff before retrying
        raise Exception("Captcha failed after multiple retries.")


    def _solve_captcha_attempt(self) -> None:
        # Handle main reCAPTCHA iframe
        self.driver.wait.ele_displayed(
            "@title=reCAPTCHA", timeout=self.timeouts["standard"]
        )
        time.sleep(0.1)
        iframe_inner = self.driver.ele("@title=reCAPTCHA", timeout=self.timeouts["standard"])
        logging.info('found reCAPTCHA')

        # Click the checkbox
        iframe_inner.wait.ele_displayed(
            ".rc-anchor-content", timeout=self.timeouts["standard"]
        )
        iframe_inner.ele(".rc-anchor-content", timeout=self.timeouts["short"]).click()
        logging.info('found reCAPTCHA and click checkbox')

        # Check if solved by just clicking
        if self.is_solved():
            return

        # Handle audio challenge
        iframe = self.driver.ele("xpath://iframe[contains(@title, 'recaptcha')]", timeout=self.timeouts["standard"])
        logging.info('found reCAPTCHA  recaptcha iframe')

        iframe.wait.ele_displayed(
            "#recaptcha-audio-button", timeout=self.timeouts["standard"]
        )
        iframe.ele("#recaptcha-audio-button", timeout=self.timeouts["short"]).click()
        logging.info('found reCAPTCHA  recaptcha iframe click audio button')

        time.sleep(0.3)

        if self.is_detected():
            raise Exception("Captcha detected bot behavior")

        # Download and process audio
        print('iframe',iframe.html)
        # iframe.wait.ele_displayed("#audio-source", timeout=self.timeouts["standard"])
        print('found audio source')
        src = iframe.ele("#audio-source", timeout=self.timeouts["standard"]).attrs()["src"]
        return

        logging.info('found audio source src',src)

        try:
            text_response = self._process_audio_challenge(src)
            logging.info(f'get audio text_response: {text_response}')

            iframe.ele("#audio-response", timeout=self.timeouts["standard"]).input(text_response.lower())
            iframe.ele("#recaptcha-verify-button", timeout=self.timeouts["standard"]).click()
            logging.info('click audio verify button')

            time.sleep(0.4)

            if not self.is_solved():
                raise Exception("Failed to solve the captcha")

        except Exception as e:
            raise Exception(f"Audio challenge failed: {str(e)}")

    def _process_audio_challenge(self, audio_url: str) -> str:
        """Process the audio challenge and return the recognized text.

        Args:
            audio_url: URL of the audio file to process

        Returns:
            str: Recognized text from the audio file
        """
        mp3_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.mp3")
        wav_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.wav")

        try:
            urllib.request.urlretrieve(audio_url, mp3_path)
            sound = pydub.AudioSegment.from_mp3(mp3_path)
            sound.export(wav_path, format="wav")

            with speech_recognition.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)

            return self.recognizer.recognize_google(audio)

        finally:
            for path in (mp3_path, wav_path):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def is_solved(self) -> bool:
        """Check if the captcha has been solved successfully."""
        try:
            return (
                "style"
                in self.driver.ele(
                    ".recaptcha-checkbox-checkmark", timeout=self.timeouts["short"]
                ).attrs()
            )
        except Exception:
            return False

    def is_detected(self) -> bool:
        """Check if the bot has been detected."""
        try:
            return (
                self.driver.ele("Try again later", timeout=self.timeouts["detection"])
                .ele_states()
                .is_displayed
            )
        except Exception:
            return False

    def get_token(self) -> Optional[str]:
        """Get the reCAPTCHA token if available."""
        try:
            return self.driver.ele("#recaptcha-token", timeout=self.timeouts["standard"]).attrs()["value"]
        except Exception:
            return None

def main():
    Settings.chrome_executable_path = '/usr/bin/google-chrome'  # Or other path

    # Config for DrissionPage, mimic a real browser
    user_data_dir = os.path.join(os.getenv("HOME"), ".chrome_profile")
    driver = Chromium(
        user_data_dir=user_data_dir,
        headless=False, # Use True to see a UI, keep false to make it headless
        is_system_chrome=True,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36", # or other user agent
        # proxy='socks5://127.0.0.1:1080' # Replace your socks or http proxy here if needed
    )
    browser = DrissionPageBrowser(driver)
    browser.clear_cookies()
    solver = RecaptchaSolver(browser)

    sites = ['twitter.com', 'youtube.com', 'tiktok.com', 'reddit.com']
    queries = {site: f'"rednote" site:{site}' for site in sites}

    for site, query in queries.items():
        logging.info(f"Monitoring advance url https://www.google.com/search?q={query}&tbs=None&num=100&start=0 for all, page 1")
        logging.info(f"Monitoring {site} for all, page 1")

        browser.get(f"https://www.google.com/search?q={query}&tbs=None&num=100&start=0")

        try:
            solver.solveCaptcha()
            # ... process your scrape results
        except Exception as e:
            logging.error(f"Error processing page 1 for {site}: {str(e)}")

        time.sleep(random.uniform(2, 10))  # Random sleep to avoid detection
    browser.quit()


if __name__ == "__main__":
    main()
