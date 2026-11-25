# Local data and public release

English · [繁體中文](PRIVACY.zh-TW.md) · [日本語](PRIVACY.ja.md) · [한국어](PRIVACY.ko.md)

For the current Windows installer, settings, calibration and local logs are stored under %LOCALAPPDATA%\tt-tool\data. The uninstaller keeps them by default and offers an option to remove them.

Image recognition is processed locally. The app connects to GitHub when you manually check for updates or download an update. Diagnostic data is not uploaded automatically. No registration, account password or API key is required to run the program.

Normal fishing does not automatically save screenshots, tracks, running logs or diagnostic ZIPs. Pause, F9 and shutdown will not export test data. Historical diagnostic tools and regression code are for development purposes only and are not launched from the normal runtime path of this release.

When a Ruins Adventure boss decision is made or the activity waits for a long time, `logs/ruins_decisions.jsonl` records the observed win chance, red-treasure recognition, decision and input result to help diagnose stalls. It excludes screenshots, accounts and device identifiers. The log rotates at approximately 256 KB and retains at most the current and previous files. It is not uploaded automatically.

| Location | Content | Open Source Packages |
|---|---|---|
| `config.example.json` | Default setting, box selection is empty | Contains |
| `assets/templates/` | Necessary local control diagram | Contains |
| `docs/images/` | Desensitization operation example | Contains |
| `tests/assets/` | Partial regression material containing only judgment bar, weight icon and accept button | Contains |
| `config.json` | Local settings, simulator type, window title and box selection | Exclusion |
| `speed_profile.json` | Clarify the proportions and statistics after calibration | Exclusion |
| `snapshots/`, `recordings/` | Screenshots/recorded files taken by users, which may contain nicknames or chats | Exclusion |
| `logs/`, `support/`, `replay_output/` | Startup abnormality, ruin leader decision-making or manual development tool output | Exclusion |
| `trial_records/`, `trial_exports/` | Data directory built by historical tests | Exclusion |

The source code version saves local files in the project directory by default, and the portable startup entry uses `data/`. The launcher only saves local error information when there is an exception, which may include the installation path; do not disclose it as it is. Fixed speed runs do not save raw position samples; explicit calibration only writes the qualified scale, number of samples, and dispersion to the speed file.

`.gitignore` Unable to delete Git history that has been committed. Public updates should run `python build_release.py`, which uses an explicit file list and does not scan additional local data. Do not directly compress the entire used project directory, and do not submit the historical diagnosis ZIP to the warehouse.

`make_support_bundle.py` is a manual development tool that only contains open source code by default. Attaching screenshots, videos or logs requires explicit parameters; it may contain personal information, so check each item before sharing. Problem feedback will give priority to providing version, status prompts and reproduction steps. Account passwords, chat records, private directories or complete local configuration will not be disclosed.
