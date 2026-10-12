# 🚀 How to Deploy TypeBridge on InfinityFree (Step-by-Step)

This guide walks you through deploying your TypeBridge website to **InfinityFree** free hosting.

---

## 📦 What Was Prepared for InfinityFree

We created a ready-to-upload ZIP file:
📁 **[`website/infinityfree_htdocs.zip`](file:///c:/Users/lokes/Music/typeanywhere/website/infinityfree_htdocs.zip)** (**8.44 MB**)

Inside this archive is everything needed:
- `index.html` (Upgraded landing page with Java Precision Engine, 3 modes, download buttons, and dynamic QR scanner)
- `styles.css` (Obsidian cyber-glassmorphism dark styling)
- `config.js` (Download link configuration)
- `.htaccess` (Configures Apache for `.apk` and `.exe` MIME types, forced downloads, and GZIP compression)
- `assets/logo.png` (App logo)
- `downloads/TypeBridge-Android-v1.0.0.apk` (**9.3 MB** — fits within InfinityFree's 10MB limit!)

---

## ⚠️ Important Note: InfinityFree 10 MB File Limit

InfinityFree free hosting accounts enforce a **strict 10 MB per-file limit**:
- ✅ **Android APK (9.3 MB)**: Under 10 MB. It is already included and hosted directly on InfinityFree!
- ⚠️ **Windows Setup (.exe) (34.9 MB)**: Exceeds 10 MB. If you upload a file >10MB to InfinityFree, their system will automatically delete it.
  
**Easy Solution**:
1. Upload [`TypeBridgeSetup-v1.0.0.exe`](file:///c:/Users/lokes/Music/typeanywhere/Release_Packages/TypeBridgeSetup-v1.0.0.exe) to **Google Drive**, **GitHub Releases**, or **MediaFire**.
2. Copy the share link.
3. Open `config.js` and paste your link in `windowsInstallerUrl`:
   ```javascript
   windowsInstallerUrl: "https://drive.google.com/uc?export=download&id=YOUR_FILE_ID",
   ```

---

## 🛠️ Step-by-Step Deployment Instructions

### Step 1: Create an Account on InfinityFree
1. Go to [https://www.infinityfree.com](https://www.infinityfree.com) and click **Sign Up Now** (free).
2. Confirm your email address and log in to the dashboard.

### Step 2: Create a Free Website Account
1. In the InfinityFree Client Area, click **Create Account**.
2. Choose a free subdomain (e.g. `typebridge.infinityfreeapp.com` or `typebridge.free.nf`).
3. Click **Create Account**. Your account will be ready in a few seconds.

### Step 3: Open the Online File Manager
1. In your InfinityFree dashboard, click **Manage** next to your new account.
2. Click **File Manager** (this opens Monsta FTP in your browser).
3. In the file list, double-click to enter the **`htdocs`** folder.
   *(Delete any default files like `index2.html` or `DO NOT UPLOAD FILES HERE` inside `htdocs`)*.

### Step 4: Upload and Extract `infinityfree_htdocs.zip`
1. Click the **Upload** button at the bottom of the File Manager and choose **Upload Zip**.
2. Select [`c:\Users\lokes\Music\typeanywhere\website\infinityfree_htdocs.zip`](file:///c:/Users/lokes/Music/typeanywhere/website/infinityfree_htdocs.zip).
3. When prompted, choose **Extract to current directory** (`htdocs`).
4. Monsta File Manager will automatically unpack `index.html`, `styles.css`, `config.js`, `.htaccess`, `assets/`, and `downloads/` into `htdocs/`.

### Step 5: (Optional) Set Your Windows Installer Link
1. In the File Manager inside `htdocs`, right-click **`config.js`** and select **Edit**.
2. Paste your Google Drive or GitHub download link for `windowsInstallerUrl`.
3. Click **Save & Close**.

### Step 6: View Your Live Website! 🎉
Open your domain in your browser:
`http://your-subdomain.infinityfreeapp.com`

- The website is live with the Obsidian cyber-glassmorphism theme.
- The dynamic QR code will automatically encode your live InfinityFree URL for one-tap Android installation!
- Visitors can download both the Android APK and Windows installer directly from your site.
