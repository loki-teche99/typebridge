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
import time
import urllib.request
import urllib.error
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from app.core.config import ConfigManager

CURRENT_VERSION = "1.0.1"
AUTO_CHECK_INTERVAL_SECONDS = 168 * 3600  # Exactly 7 days (168 hours)


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

    def __init__(self, repo_slug: str | None = None, is_manual: bool = False, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.repo_slug = repo_slug or self.config.get('github_repo', 'loki-teche99/typebridge')
        self.current_ver = self.config.get('app_version', CURRENT_VERSION)
        self.is_manual = is_manual

    def run(self):
        repo = self.repo_slug.strip().strip('/')
        if not repo or '/' not in repo:
            self.no_update_found.emit(self.current_ver)
            return

        now = time.time()
        # 1. 7-Day (168 Hours) Interval Enforcement for Automatic Checks
        if not self.is_manual:
            last_ts = self.config.get('last_update_check_ts', 0)
            if (now - last_ts) < AUTO_CHECK_INTERVAL_SECONDS:
                # Under 168 hours have elapsed since last check.
                # Skip network request to avoid unnecessary requests and respect rate limits.
                self.no_update_found.emit(self.current_ver)
                return

        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        headers = {
            "User-Agent": "TypeBridge-Desktop-Assistant",
            "Accept": "application/vnd.github.v3+json"
        }
        # 2. ETag Caching to Avoid Wasting GitHub API Rate Limits
        cached_etag = self.config.get('update_etag', '')
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        req = urllib.request.Request(api_url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                # Store new ETag and timestamp on 200 OK
                new_etag = resp.headers.get("ETag")
                if new_etag:
                    self.config.set('update_etag', new_etag)
                self.config.set('last_update_check_ts', int(time.time()))

                data = json.loads(resp.read().decode('utf-8'))

            tag_name = data.get("tag_name", "")
            release_name = data.get("name", tag_name)
            body = data.get("body", "No release notes provided.")
            published_at = data.get("published_at", "")

            # Look for Windows installer, manifest, and checksums in assets
            exe_url = None
            exe_size = 0
            exe_name = None
            expected_sha256 = None
            manifest_url = None
            sha256sums_url = None

            for asset in data.get("assets", []):
                aname = asset.get("name", "")
                aname_lower = aname.lower()
                if aname_lower.endswith(".exe") and ("setup" in aname_lower or "typebridge" in aname_lower):
                    if not exe_url:
                        exe_url = asset.get("browser_download_url")
                        exe_size = asset.get("size", 0)
                        exe_name = aname
                elif aname_lower.endswith(".exe") and not exe_url:
                    exe_url = asset.get("browser_download_url")
                    exe_size = asset.get("size", 0)
                    exe_name = aname
                elif aname_lower == "release-manifest.json":
                    manifest_url = asset.get("browser_download_url")
                elif aname_lower == "sha256sums.txt":
                    sha256sums_url = asset.get("browser_download_url")

            # Try to fetch manifest to get authoritative SHA-256 and size
            if manifest_url:
                try:
                    mreq = urllib.request.Request(manifest_url, headers={"User-Agent": "TypeBridge-Desktop-Assistant"})
                    with urllib.request.urlopen(mreq, timeout=5) as mresp:
                        mdata = json.loads(mresp.read().decode('utf-8'))
                        win_assets = mdata.get("windows", {}).get("assets", [])
                        if win_assets:
                            expected_sha256 = win_assets[0].get("sha256")
                            msize = win_assets[0].get("size", 0)
                            if msize > 0:
                                exe_size = msize
                except Exception:
                    pass

            # Fallback to sha256sums.txt
            if not expected_sha256 and sha256sums_url:
                try:
                    sreq = urllib.request.Request(sha256sums_url, headers={"User-Agent": "TypeBridge-Desktop-Assistant"})
                    with urllib.request.urlopen(sreq, timeout=5) as sresp:
                        slines = sresp.read().decode('utf-8').splitlines()
                        for sline in slines:
                            if ".exe" in sline.lower():
                                sparts = sline.strip().split()
                                if sparts and len(sparts[0]) == 64:
                                    expected_sha256 = sparts[0]
                                    break
                except Exception:
                    pass

            remote_ver = re.sub(r'^[vV]', '', tag_name)
            if is_newer_version(remote_ver, self.current_ver):
                # Fail closed: reject untrusted releases lacking verified SHA-256 digest
                if not expected_sha256 or len(expected_sha256.strip()) != 64:
                    self.check_failed.emit(
                        f"Untrusted release (v{remote_ver}): release-manifest.json or sha256sums.txt is missing valid SHA-256 digest."
                    )
                    return

                self.update_available.emit({
                    "version": remote_ver,
                    "tag_name": tag_name,
                    "name": release_name,
                    "body": body,
                    "download_url": exe_url,
                    "filename": exe_name or f"TypeBridgeSetup-v{remote_ver}.exe",
                    "size_mb": round(exe_size / (1024 * 1024), 2) if exe_size else 0,
                    "published_at": published_at,
                    "html_url": data.get("html_url", f"https://github.com/{repo}/releases"),
                    "sha256": expected_sha256.strip()
                })
            else:
                self.no_update_found.emit(self.current_ver)

        except urllib.error.HTTPError as e:
            self.config.set('last_update_check_ts', int(time.time()))
            # 3. Handle ETag 304 Not Modified
            if e.code == 304:
                self.no_update_found.emit(self.current_ver)
                return

            # 4. Handle HTTP 404 (No release published yet on repository)
            if e.code == 404:
                self.no_update_found.emit(self.current_ver)
                return

            # 5. Handle Rate Limiting (403, 429)
            if e.code in (403, 429):
                reset_header = e.headers.get("X-RateLimit-Reset")
                try:
                    reset_epoch = int(reset_header) if reset_header else int(time.time() + 3600)
                    reset_time_str = time.strftime("%H:%M", time.localtime(reset_epoch))
                except Exception:
                    reset_time_str = "an hour"

                if not self.is_manual:
                    self.no_update_found.emit(self.current_ver)
                    return
                self.check_failed.emit(f"GitHub API rate limit exceeded. Resets at {reset_time_str}. Please try again later.")
                return

            if not self.is_manual:
                self.no_update_found.emit(self.current_ver)
            else:
                self.check_failed.emit(f"GitHub API returned HTTP {e.code}")

        except urllib.error.URLError as e:
            self.config.set('last_update_check_ts', int(time.time()))
            if not self.is_manual:
                self.no_update_found.emit(self.current_ver)
            else:
                self.check_failed.emit(f"Network error: {str(e.reason)}")
        except Exception as e:
            self.config.set('last_update_check_ts', int(time.time()))
            if not self.is_manual:
                self.no_update_found.emit(self.current_ver)
            else:
                self.check_failed.emit(f"Update check failed: {str(e)}")


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

        if not self.expected_sha256 or len(self.expected_sha256.strip()) != 64:
            self.download_failed.emit("Security check failed: Trusted 64-character SHA-256 digest is missing. Update rejected.")
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
                # Mandatory Cryptographic SHA-256 Integrity Verification
                if not self.expected_sha256 or len(self.expected_sha256.strip()) != 64:
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    self.download_failed.emit(
                        "Security check failed: Trusted 64-character SHA-256 digest is missing. Update rejected."
                    )
                    return

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
