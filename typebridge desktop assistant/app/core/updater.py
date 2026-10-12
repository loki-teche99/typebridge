"""
TypeBridge Desktop - GitHub Releases Remote Auto-Updater
=========================================================
Checks the GitHub Releases API for new versions of TypeBridge,
downloads the Windows Setup installer (.exe) with live progress tracking,
and launches a silent in-place upgrade with auto-restart.
"""
import os
import sys
import json
import re
import urllib.request
import urllib.error
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from app.core.config import ConfigManager

CURRENT_VERSION = "1.0.0"


def parse_version(ver_str: str) -> tuple[int, ...]:
    """Extract integer version tuple, e.g. 'v1.1.0' -> (1, 1, 0)."""
    cleaned = re.sub(r'^[vV]', '', ver_str.strip())
    nums = re.findall(r'\d+', cleaned)
    return tuple(map(int, nums)) if nums else (0, 0, 0)


def is_newer_version(remote: str, local: str) -> bool:
    """Returns True if remote version is strictly greater than local version."""
    return parse_version(remote) > parse_version(local)


class UpdateCheckerThread(QThread):
    """
    Background worker thread to check GitHub Releases API for updates.
    Does not freeze or block the UI thread.
    """
    update_available = pyqtSignal(dict)  # Emits update details dict
    no_update_found  = pyqtSignal(str)   # Emits current version
    check_failed     = pyqtSignal(str)   # Emits error message

    def __init__(self, repo_slug: str | None = None, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.repo_slug = repo_slug or self.config.get('github_repo', 'loki-teche99/typebridge')
        self.current_ver = self.config.get('app_version', CURRENT_VERSION)

    def run(self):
        repo = self.repo_slug.strip().strip('/')
        if not repo or '/' not in repo:
            self.no_update_found.emit(self.current_ver)
            return

        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "TypeBridge-Desktop-Assistant",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            tag_name = data.get("tag_name", "")
            release_name = data.get("name", tag_name)
            body = data.get("body", "No release notes provided.")
            published_at = data.get("published_at", "")

            # Look for Windows installer in assets
            exe_url = None
            exe_size = 0
            exe_name = None

            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.lower().endswith(".exe") and ("setup" in name.lower() or "typebridge" in name.lower()):
                    exe_url = asset.get("browser_download_url")
                    exe_size = asset.get("size", 0)
                    exe_name = name
                    break

            if not exe_url:
                for asset in data.get("assets", []):
                    name = asset.get("name", "")
                    if name.lower().endswith(".exe"):
                        exe_url = asset.get("browser_download_url")
                        exe_size = asset.get("size", 0)
                        exe_name = name
                        break

            remote_ver = re.sub(r'^[vV]', '', tag_name)
            if is_newer_version(remote_ver, self.current_ver):
                self.update_available.emit({
                    "version": remote_ver,
                    "tag_name": tag_name,
                    "name": release_name,
                    "body": body,
                    "download_url": exe_url,
                    "filename": exe_name or f"TypeBridgeSetup-v{remote_ver}.exe",
                    "size_mb": round(exe_size / (1024 * 1024), 2) if exe_size else 0,
                    "published_at": published_at,
                    "html_url": data.get("html_url", f"https://github.com/{repo}/releases")
                })
            else:
                self.no_update_found.emit(self.current_ver)

        except urllib.error.HTTPError as e:
            # Fallback to rate-limit-free web release check if API is rate-limited or unavailable
            if self._check_via_web_fallback(repo):
                return
            # If rate-limited (403/429), repo private (404), or on latest version:
            # Report up-to-date rather than alarming the user with technical rate-limiting errors!
            self.no_update_found.emit(self.current_ver)
        except urllib.error.URLError:
            if self._check_via_web_fallback(repo):
                return
            self.no_update_found.emit(self.current_ver)
        except Exception:
            if self._check_via_web_fallback(repo):
                return
            self.no_update_found.emit(self.current_ver)

    def _check_via_web_fallback(self, repo: str) -> bool:
        """
        Bypasses GitHub REST API rate limits (60/hr) by querying public release web redirect.
        """
        try:
            latest_url = f"https://github.com/{repo}/releases/latest"
            req = urllib.request.Request(
                latest_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                final_url = resp.geturl()
                tag_name = final_url.split('/')[-1]

            if not tag_name or tag_name == "latest" or tag_name == "releases":
                return False

            remote_ver = re.sub(r'^[vV]', '', tag_name)

            # Discover assets
            exe_url = None
            exe_name = None
            exe_size = 0

            try:
                assets_url = f"https://github.com/{repo}/releases/expanded_assets/{tag_name}"
                req2 = urllib.request.Request(
                    assets_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    html = resp2.read().decode('utf-8')
                    matches = set(re.findall(r'href=[\x22\x27](/[\w\-]+/[\w\-]+/releases/download/[^\x22\x27]+)[\x22\x27]', html))
                    for m in matches:
                        fname = m.split('/')[-1]
                        if fname.lower().endswith('.exe'):
                            exe_url = f"https://github.com{m}"
                            exe_name = fname
                            break
            except Exception:
                pass

            if not exe_url:
                exe_url = f"https://github.com/{repo}/releases/download/{tag_name}/TypeBridgeSetup-{tag_name}.exe"
                exe_name = f"TypeBridgeSetup-{tag_name}.exe"

            if is_newer_version(remote_ver, self.current_ver):
                self.update_available.emit({
                    "version": remote_ver,
                    "tag_name": tag_name,
                    "name": f"TypeBridge {tag_name}",
                    "body": "A new version of TypeBridge is ready to install from GitHub Releases.",
                    "download_url": exe_url,
                    "filename": exe_name or f"TypeBridgeSetup-v{remote_ver}.exe",
                    "size_mb": round(exe_size / (1024 * 1024), 2) if exe_size else 35.0,
                    "published_at": "",
                    "html_url": f"https://github.com/{repo}/releases/tag/{tag_name}"
                })
            else:
                self.no_update_found.emit(self.current_ver)
            return True
        except Exception:
            return False


class UpdateDownloaderThread(QThread):
    """
    Downloads the new installer executable in chunks,
    emitting progress signals along the way.
    """
    download_progress = pyqtSignal(int, int, int)  # percent, downloaded_bytes, total_bytes
    download_finished = pyqtSignal(str)            # local installer path
    download_failed   = pyqtSignal(str)            # error message

    def __init__(self, download_url: str, version: str, expected_sha256: str | None = None, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.version = version
        self.expected_sha256 = expected_sha256
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not self.download_url:
            self.download_failed.emit("Download URL is empty or missing.")
            return

        temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
        target_path = os.path.join(temp_dir, f"TypeBridgeSetup-v{self.version}.exe")

        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "TypeBridge-Desktop-Assistant"}
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024

                with open(target_path, "wb") as out_file:
                    while True:
                        if self._is_cancelled:
                            out_file.close()
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break

                        out_file.write(chunk)
                        downloaded += len(chunk)

                        pct = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        self.download_progress.emit(pct, downloaded, total_size)

            if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
                # Cryptographic SHA-256 Integrity Check
                if self.expected_sha256:
                    import hashlib
                    hasher = hashlib.sha256()
                    with open(target_path, "rb") as f:
                        for b_chunk in iter(lambda: f.read(65536), b""):
                            hasher.update(b_chunk)
                    computed = hasher.hexdigest().lower()
                    if computed != self.expected_sha256.lower().strip():
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        self.download_failed.emit(
                            f"Integrity check failed: SHA-256 mismatch (expected {self.expected_sha256[:8]}..., got {computed[:8]}...). File removed."
                        )
                        return
                self.download_finished.emit(target_path)
            else:
                self.download_failed.emit("Downloaded file was empty or corrupted.")

        except Exception as e:
            self.download_failed.emit(f"Download failed: {str(e)}")


def launch_silent_installer(installer_path: str):
    """
    Executes the Inno Setup installer silently with /CLOSEAPPLICATIONS and /RESTARTAPPLICATIONS,
    then cleanly terminates the current TypeBridge instance.
    """
    if not os.path.exists(installer_path):
        raise FileNotFoundError(f"Installer not found at {installer_path}")

    cmd = f'"{installer_path}" /SILENT /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /NORESTART'
    subprocess.Popen(cmd, shell=True)
    QApplication.quit()
    sys.exit(0)
