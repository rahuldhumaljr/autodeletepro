# AutoDelete Pro — Right-Click File Expiry Scheduler for Windows

<img width="1917" height="986" alt="image" src="https://github.com/user-attachments/assets/be329383-6447-4bdb-afd3-137df63ecc15" />


**A Windows desktop utility for scheduling file and folder expiry.**

AutoDelete Pro helps users schedule files or folders for removal after a selected duration. It provides a desktop interface for managing scheduled items and includes optional Windows Explorer context-menu and startup integration.

> **Data safety:** AutoDelete Pro performs file operations that can result in data loss. Test with disposable files in a temporary directory before using it with real data, and maintain backups of important files. When Recycle Bin mode is disabled, expiry may permanently remove data.

## Features

- Schedule files and folders for expiry
- Optional Recycle Bin handling
- Clear a folder's contents while retaining the folder itself
- View active scheduled items and operation history
- Dark and light interface themes
- Basic usage statistics
- Optional Windows startup and Explorer context-menu integration

## Technology

- **Language:** Python
- **Desktop UI:** Tkinter
- **Platform integration:** Windows Registry and Windows Shell APIs
- **Persistence:** Local configuration, history, and statistics files

AutoDelete Pro is designed for Windows and is not a cross-platform application.

## Getting started

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or later recommended
- Tkinter, normally included with the standard Windows Python installer

### Run from source

1. Install Python from [python.org](https://www.python.org/downloads/windows/). Ensure the Python launcher is available.
2. Download or clone this repository.
3. Open Command Prompt or PowerShell in the project directory.
4. Run:

   ```powershell
   py autodeletepro.py
   ```

The current source does not require additional third-party Python packages.

## Reliability and safety

File-management utilities need predictable failure behavior. This project includes work to avoid silently converting a failed Recycle Bin operation into permanent deletion and to keep expiry failures visible for retry rather than treating them as successful operations. Expiry checks are scheduled through Tkinter's event loop to reduce shared-state and concurrent-write risks.

These safeguards should be validated on the target Windows environment before the application is relied on for important files. In particular, test normal expiry, folder handling, locked or missing files, Recycle Bin failures, application restarts, startup behavior, and Explorer context-menu launches using disposable data.

## Project status

AutoDelete Pro is an actively developed portfolio project. The source has been syntax-checked, but full runtime validation across Windows versions and packaged executable builds remains outstanding. The project should not yet be treated as production-ready for important data.

## Development approach

AI-assisted development was used to accelerate implementation. The project is being refined through code review, safety-focused changes, documentation, and testing. Feedback, reproducible bug reports, and code review are welcome.

## Roadmap

- Add automated tests for expiry and failure-handling logic
- Improve diagnostic logging and error reporting
- Validate startup and Explorer integration on supported Windows configurations
- Document and test a repeatable Windows packaging and release process

## License

AutoDelete Pro is licensed under the **MIT License**. You may use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software, provided that the copyright and permission notice are included in all copies or substantial portions of the software.

The software is provided "as is", without warranty of any kind. See the [`LICENSE`](LICENSE) file for the full license text.

Copyright (c) 2026 Rahul Dhumal
