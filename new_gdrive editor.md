# 📘 The Complete Dummy-Proof Guide to Fixing Google Drive API (403 Quota Error)

---

## 🧐 1. What Actually Went Wrong?

You ran into this annoying error:

```text
❌ Google 403: "Service Accounts do not have storage quota. Leverage shared drives or use OAuth delegation instead."

```

### 🧠 The Simple Explanation:

- You were using a **Google Cloud Service Account** (a bot account ending in `@...iam.gserviceaccount.com`).
- Google gives service account bots **exactly 0 bytes (0 KB)** of Google Drive storage space.
- Even though you created a folder on your personal Google Drive and shared it with the bot, whenever the bot uploads a file, Google marks the bot as the **owner** of that file.
- Because the bot has **0 bytes** of storage allowed, Google immediately blocks the upload with `storageQuotaExceeded (403)`.

### 💡 The Solution:

Instead of pretending to be a bot with 0 storage, we switch your script to **OAuth 2.0 (User Credentials)**.

- This tells Google: _"Hey, this script is uploading on behalf of my personal Google account."_
- Your personal Google Drive has 15 GB+ of space, so files upload smoothly without quota issues! 🚀

---

## 🛠️ 2. Step-by-Step Setup Guide (From Scratch)

Follow these steps once, and it will work forever.

---

### 📍 Phase 1: Configure the Google Cloud Consent Screen

1. Open your browser and go to [Google Cloud Console](https://console.cloud.google.com/).
2. In the top bar, ensure your project (e.g., `Paper-Harvester-Drive`) is selected.
3. Open the left sidebar menu (three lines `☰` in the top left) and go to:
   👉 **APIs & Services** > **OAuth consent screen** (or **Google Auth Platform**).
4. **Select Audience / User Type:**

- Choose **External** (this allows you to test with your own Gmail address).
- Click **Next** / **Create**.

5. **Fill in App Information:**

- **App name:** `Paper getter`
- **User support email:** Select your own Gmail from the dropdown.
- **Developer contact email:** Type your own Gmail address.
- Click **Save and Continue**.

6. **Scopes (Permissions):**

- Click **Add or Remove Scopes**.
- In the filter box, type `drive.file`.
- Check the box for:
  `.../auth/drive.file` (_See, edit, create, and delete only the specific Google Drive files you use with this app_).
- Click **Update**, then **Save and Continue**.

7. **Test Users (⚠️ CRITICAL STEP — DO NOT SKIP):**

- Since your app is in "Testing" mode, Google blocks everyone by default.
- Click **+ Add Users**.
- Type your exact personal Google email address (the one whose Drive you want to upload to).
- Click **Add**, then **Save and Continue**.
- Click **Back to Dashboard**.

---

### 📍 Phase 2: Create and Download `credentials.json`

1. Go to the left sidebar menu and click **Clients** (or **Credentials**).
2. Click the blue **`+ Create client`** (or **`+ Create Credentials` > `OAuth client ID**`) button at the top.
3. In the setup form:

- **Application type:** Select **Desktop app**.
- **Name:** `Paper getter`
- Click **Create**.

4. Once created, click on `Paper getter` to open its details.
5. In the **Client secrets** section at the bottom right:

- Next to the client secret asterisks, click the **Download icon** (the arrow pointing down into a tray).

6. **Rename and place the file:**

- Find the downloaded JSON file on your computer.
- Rename it to exactly:

```text
credentials.json

```

- Move `credentials.json` directly into your project's root folder (`The_Paper_Getter`).

---

### 📍 Phase 3: Install the Required Python Packages

Open your terminal (PowerShell or Bash) in your project directory and run:

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

```

---

### 📍 Phase 4: The Python Upload Script

Create or replace your Google Drive upload module (e.g., `services/drive_client.py`) with this clean, robust code:

```python
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# We only ask for permission to manage files created by this app
SCOPES = ['https://www.googleapis.com/auth/drive.file']

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def get_drive_service():
    """Authenticates the user and returns an authorized Google Drive v3 service client."""
    creds = None

    # token.json stores the access and refresh tokens created after first login
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If there are no valid saved credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 [Drive Auth] Refreshing expired session token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"❌ Missing '{CREDENTIALS_FILE}'! Place the downloaded OAuth client JSON in the project root."
                )
            print("🌐 [Drive Auth] Opening browser for one-time Google Account login...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the tokens for future runs so you never have to log in again manually
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
            print("✅ [Drive Auth] Successfully generated and stored 'token.json'!")

    return build('drive', 'v3', credentials=creds)


def upload_csv_to_drive(file_path: str, target_folder_id: str = None) -> dict:
    """
    Uploads a CSV file to Google Drive using the authenticated user's account.
    Consumes user storage space, eliminating the 403 quota exceeded error.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    service = get_drive_service()
    filename = os.path.basename(file_path)

    file_metadata = {'name': filename}

    # If a specific target folder was given, assign it as parent
    if target_folder_id:
        file_metadata['parents'] = [target_folder_id]

    # Stream the file payload
    media = MediaFileUpload(file_path, mimetype='text/csv', resumable=True)

    print(f"🚀 [Drive Sync] Uploading '{filename}' to Google Drive...")
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink, size'
    ).execute()

    print(f"🎉 [Drive Sync] Upload Complete!")
    print(f"   📁 File Name : {uploaded_file.get('name')}")
    print(f"   🆔 File ID   : {uploaded_file.get('id')}")
    print(f"   🔗 Drive URL : {uploaded_file.get('webViewLink')}")

    return uploaded_file

```

---

## 🚀 3. What Happens on Your First Run?

When you execute your pipeline the first time:

1. **A browser tab will automatically pop open** asking you to choose your Google Account.
2. **Select the Gmail address** you added as a **Test User** in Phase 1.
3. **Google Security Warning Screen:**

- You will see: _"Google hasn't verified this app"_.
- **Do not panic!** This is normal because it is your own personal private developer project.
- Click **Advanced** (small link in the lower left).
- Click **Go to Paper getter (unsafe)**.

4. Click **Continue** to grant the app permission to upload files to your Drive.
5. The browser will say: _"The authentication flow has completed. You may close this window."_
6. Your script will immediately create a file called **`token.json`** in your project folder.

---

## 🔒 4. Important Git Security Rule

Now that you have credentials and tokens on your machine, protect them:

Open your **`.gitignore`** file and make sure these lines are inside:

```gitignore
credentials.json
token.json
.env

```

This ensures you never accidentally leak your authentication secrets or credentials to GitHub!

---
