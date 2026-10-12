# TypeBridge Official Website & Download Portal

A modern, Cyber-Glassmorphism landing page for distributing the **TypeBridge Windows Desktop Assistant** and **Android Mobile App**.

---

## 📁 Directory Structure

```
website/
├── index.html                  # Landing page with hero, downloads, setup guide & FAQ
├── styles.css                  # Obsidian glassmorphic responsive stylesheet
├── serve_website.py            # Local Wi-Fi server (preview & test downloads)
├── assets/
│   └── logo.png                # Official TypeBridge high-resolution icon
└── downloads/
    ├── TypeBridgeSetup-v1.0.0.exe    # Windows Installer (34.9 MB)
    └── TypeBridge-Android-v1.0.0.apk  # Android Release APK (9.3 MB)
```

---

## 🚀 How to Host & Upload

### Option 1: GitHub Pages + GitHub Releases (Recommended & 100% Free)
1. **Create a GitHub Repository**:
   - Go to [github.com/new](https://github.com/new) and create a repository named `typebridge`.
2. **Upload Website Code**:
   - Push `index.html`, `styles.css`, and `assets/logo.png`.
3. **Upload the Large Binaries (.exe & .apk)**:
   - In your repo, click **Releases** > **Draft a new release**.
   - Set tag: `v1.0.0`.
   - Drag and drop `TypeBridgeSetup-v1.0.0.exe` and `TypeBridge-Android-v1.0.0.apk` from the `downloads/` folder.
   - Click **Publish release**.
   - Copy the direct download links of both assets and update the `<a href="...">` links in `index.html`.
4. **Enable GitHub Pages**:
   - Go to repo **Settings** > **Pages**.
   - Under **Build and deployment > Branch**, select `main` (or `master`) and `/root`.
   - Click **Save**.
   - Your website is instantly live at: `https://<your-username>.github.io/typebridge/`

---

### Option 2: Netlify (Instant Drag-and-Drop)
1. Open [app.netlify.com/drop](https://app.netlify.com/drop) in your browser.
2. Drag and drop this entire `website/` folder into the upload box.
3. Netlify immediately publishes your website and assigns a free live URL (e.g., `https://typebridge.netlify.app`).

---

### Option 3: Local Wi-Fi Sharing (Right Now)
To share and download directly between your PC and phone without uploading to the cloud:
```powershell
python serve_website.py
```
Open the printed URL on your phone's browser (e.g., `http://172.20.60.148:8080`).
