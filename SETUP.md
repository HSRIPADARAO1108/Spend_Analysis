# Family Money Tracker: setup guide (Google Sheets version)

Folder layout on GitHub (turn on "show hidden files" to see the dot folders):
```
app.py  db.py  notifier.py  requirements.txt  requirements-notify.txt
.streamlit/config.toml
.github/workflows/notify.yml   .github/workflows/build-apk.yml
android-app/   (optional)
```

---
## Part 0: Free online database with Supabase (no Google needed)

1. Go to **supabase.com** -> sign up (GitHub login is fine) -> **New project**.
2. Name it `MoneyTracker`. For **Database password** use only letters and numbers (no symbols like @ # / ?). Save it. Pick the region nearest you (Mumbai if shown). Click **Create**, wait about 2 minutes.
3. Click **Connect** at the top of the project page. Open **Connection string**, choose the **Session pooler** tab (not "Direct connection"; GitHub cannot reach that one).
4. Copy the string. It looks like:
   `postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
5. Replace `[YOUR-PASSWORD]` (with the brackets) by your real password. This whole line is your `DATABASE_URL`.
The tables are created automatically the first time the app runs.

(Neon, Aiven and CockroachDB also work: paste their Postgres connection string as `DATABASE_URL`. A Google Sheet also still works if you ever set SHEET_ID + GOOGLE_SERVICE_ACCOUNT_JSON, but DATABASE_URL wins when both exist.)

## Part 1: Deploy the app + PIN lock

1. Put all files in a **private** GitHub repo.
2. share.streamlit.io -> New app -> your repo -> main file `app.py`.
3. App -> **Settings -> Secrets**, paste:
   ```
   DATABASE_URL = "postgresql://postgres.xxxx:YOURPASSWORD@aws-0-xx.pooler.supabase.com:5432/postgres"
   APP_PIN = "choose-a-strong-pin"
   ```
4. Save. The app restarts. Both yellow warnings should disappear and it asks for your PIN.
5. Add a test entry. In Supabase -> **Table Editor -> entries** you will see it.

## Step 1: 10 PM Gmail notification

1. **Gmail App password:** Google Account -> Security -> turn on **2-Step Verification** -> search **App passwords** -> name `Money Tracker` -> Create -> copy the 16 letters (remove spaces).
2. GitHub repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**. Add:

   | Name | Value |
   |---|---|
   | SMTP_USER | your Gmail address |
   | SMTP_PASS | the 16-letter app password |
   | EMAIL_TO | your email, brother's email (comma separated) |
   | DATABASE_URL | the same Supabase connection string |
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
- Supabase free projects can pause after about a week with no activity (check their site, free plans change). If the app errors after a long break, open the Supabase dashboard and click **Restore project**.
- If the password has special characters, the connection fails. Reset it in Supabase -> Project Settings -> Database to letters and numbers only.
- "could not translate host name" or a timeout in GitHub: you used the Direct connection string. Use the **Session pooler** one.
- If emails show all ₹0 the job now stops with an error instead: check `DATABASE_URL` in GitHub secrets.
- Keep the connection string private. If it leaks, reset the database password in Supabase and update both secrets.
