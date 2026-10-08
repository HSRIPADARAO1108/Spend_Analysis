# Family Money Tracker: setup guide (Google Sheets version)

Folder layout on GitHub (turn on "show hidden files" to see the dot folders):
```
app.py  db.py  notifier.py  requirements.txt  requirements-notify.txt
.streamlit/config.toml
.github/workflows/notify.yml   .github/workflows/build-apk.yml
android-app/   (optional)
```

---
## Part 0: Google Sheet as the database (free, once)

**A. Make the sheet**
1. Go to sheets.google.com -> **Blank spreadsheet**. Name it `MoneyTracker`. Leave it empty.
2. Look at the address bar: `https://docs.google.com/spreadsheets/d/`**`THIS-LONG-ID`**`/edit`. Copy that long id. This is your `SHEET_ID`.

**B. Make the robot account (service account)**
1. Go to **console.cloud.google.com** and sign in. Click the project picker at the top -> **New project** -> name `MoneyTracker` -> Create.
2. Menu -> **APIs & Services -> Library** -> search **Google Sheets API** -> **Enable**.
3. Menu -> **IAM & Admin -> Service Accounts** -> **Create service account** -> name `money-bot` -> Create and continue -> Done.
4. Click the new account -> **Keys** tab -> **Add key -> Create new key -> JSON -> Create**. A `.json` file downloads. This file is like a password.
5. Open the JSON in Notepad and copy the `client_email` value (looks like `money-bot@moneytracker-123.iam.gserviceaccount.com`).

**C. Give the robot access**
1. Open your `MoneyTracker` sheet -> **Share**.
2. Paste the `client_email`, set **Editor**, untick "Notify people", click **Share**.

## Part 1: Deploy the app + PIN lock

1. Put all files in a **private** GitHub repo. Do NOT upload the downloaded `.json` key file.
2. share.streamlit.io -> New app -> your repo -> main file `app.py`.
3. App -> **Settings -> Secrets**, paste (keep the `'''` lines):
   ```
   SHEET_ID = "your-long-sheet-id"
   APP_PIN = "choose-a-strong-pin"
   GOOGLE_SERVICE_ACCOUNT_JSON = '''
   {paste the whole contents of the downloaded JSON file here}
   '''
   ```
4. Save. The app restarts. Both yellow warnings should disappear and it asks for your PIN.
5. Add a test entry, then open the Google Sheet. You will see the row appear.

## Step 1: 10 PM Gmail notification

1. **Gmail App password:** Google Account -> Security -> turn on **2-Step Verification** -> search **App passwords** -> name `Money Tracker` -> Create -> copy the 16 letters (remove spaces).
2. GitHub repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**. Add:

   | Name | Value |
   |---|---|
   | SMTP_USER | your Gmail address |
   | SMTP_PASS | the 16-letter app password |
   | EMAIL_TO | your email, brother's email (comma separated) |
   | SHEET_ID | same long sheet id |
   | GOOGLE_SERVICE_ACCOUNT_JSON | the whole JSON file contents (no `'''`) |
   | APP_URL | your Streamlit link |

3. **Test:** Actions -> *Money notifications* -> **Run workflow** -> `daily`. Check inbox (and Spam).
4. In the Gmail app, allow notifications. Optional filter: subject contains `10 PM` -> Never send to Spam.
5. It then runs every day at 10:00 PM IST (GitHub can be a few minutes late).

## Step 3: Monthly report email
Same secrets as Step 1. Test with Run workflow -> `monthly`. It runs on the 1st at 8:00 AM IST for the previous month.
GitHub pauses scheduled jobs after 60 days of no repo activity. If emails stop, open Actions and click "Enable workflow".

## Step 2: Android app
- **Easiest:** Chrome -> your link -> menu -> **Add to Home screen**.
- **Website-to-app tools (webintoapp, Kodular, MIT App Inventor):** just give them your Streamlit link. The PIN protects your data.
- **Own APK:** Actions -> **Build Android APK** -> Run workflow -> paste your link -> download the artifact (see `android-app/`).

## Good to know
- Your sheet is private. Only you and the robot email can open it. You can edit or fix rows in the sheet directly: keep the header row and the column order (id, member, type, category, amount, note, date). Dates must look like `2026-10-09`.
- The app refreshes from the sheet about every 10 seconds, so a manual edit may take a moment to show.
- Treat the JSON key like a password. If it leaks: Cloud Console -> Service Accounts -> Keys -> delete it and make a new one.
- If you see "APIError 403": the sheet is not shared with the `client_email`, or Sheets API is not enabled. "APIError 404": wrong SHEET_ID.
- If emails show all ₹0: the two secrets are missing or wrong in GitHub (the job now stops with an error instead).
