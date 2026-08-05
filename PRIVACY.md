# Privacy Policy

**BabelGG** — Last updated: 2026-04-19

---

## What BabelGG Collects

BabelGG stores all data **locally on your machine**. Nothing is sent to any server unless you explicitly opt in to cloud features (not yet available).

### Translation Cache (`data/vault.json`)
- Records of source text, target language, and translated text
- Stored in `%LOCALAPPDATA%\BabelGG\data\vault.json`
- Used to speed up repeated translations
- You can delete this at any time — it will be recreated automatically

### Usage Telemetry (`data/telemetry.json`)
- Counts of translations, card interactions, and reply opens
- **No personal information** — session IDs are anonymized hashes
- **No text content** — only language codes, timing (ms), and interaction flags
- Stored in `%LOCALAPPDATA%\BabelGG\data\telemetry.json`
- Capped at 500 events; older events are discarded automatically

### License Data (`data/license.json`)
- Stores your license key and activation status locally
- Communicates with Lemon Squeezy's license API only when you activate or validate a license
- No payment information is ever stored on your machine by BabelGG

---

## What BabelGG Does NOT Collect

- Your clipboard contents (processed in memory only, never persisted)
- Keystrokes or hotkey presses
- Any data from other applications
- Your IP address, device identifier, or any personally identifiable information
- Translation content in any cloud service

---

## How to Delete Your Data

BabelGG provides an in-app option to clear all local data:

1. Open BabelGG Settings
2. Navigate to **Privacy** section
3. Click **Clear All Data**

This will delete `vault.json`, `telemetry.json`, and `license.json`. Your config settings will be preserved.

You can also manually delete the folder:
```
%LOCALAPPDATA%\BabelGG\
```

---

## Cloud Features (Future)

If cloud telemetry or translation upload features are added in a future version:
- They will be **opt-in only**
- You will be shown a clear explanation of what is sent and to where
- You can opt out at any time

---

## License API

BabelGG's license activation communicates with:
- **Host:** `api.lemonsqueezy.com`
- **Purpose:** License key activation and validation only
- **Data sent:** License key, instance name
- **No personal data** is sent to this API beyond what is required for license management

---

## Questions?

Open an issue at: https://github.com/aldoud1799/babelGG_v2/issues
