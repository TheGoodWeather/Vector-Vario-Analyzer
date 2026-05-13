# Flight Data Analyzer v0.02

## Overview

Flight Data Analyzer is a Python application for flight data analysis and visualization.

Please refer to the user manual for detailed usage instructions.

---

# Requirements

Before running the application, make sure the following are installed on your system:

- Python 3.12.7
- pip

Python packages and dependencies are listed in:

```bash
requirements.txt
```

---

# Installation

## 1. Clone or Download the Project

Using Git:

```bash
git clone <YOUR_GITHUB_URL>
cd FlightDataAnalyzer
```

Or download the ZIP archive from GitHub and extract it.

---

# Windows Installation

## Create a Virtual Environment

Create a Virtual Environment in the extracted folder :

```bash
python -m venv .venv
```

## Activate the Virtual Environment

Before installing dependancies, you should activate the venv : 

```bash
source .venv\Scripts\activate
```

## Install Dependencies

Now run this command in order to download the required dependencies :

```bash
pip install -r requirements.txt
```

## Launch the Application

To manually launch the app, run the following command : 

```bash
python src/main.py
```

Or you can also use the provided launcher:

```bash
launch.bat
```

---

# macOS Installation

## Create a Virtual Environment

```bash
python3 -m venv .venv
```

## Activate the Virtual Environment

```bash
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Launch the Application

```bash
python src/main.py
```

Or use the launcher:

```bash
./launch.command
```

If needed, make the launcher executable:

```bash
chmod +x launch.command
```

---

# Linux Installation

## Create a Virtual Environment

```bash
python3 -m venv .venv
```

## Activate the Virtual Environment

```bash
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Launch the Application

```bash
python src/main.py
```

Or use:

```bash
./launch.sh
```

If needed, make the launcher executable:

```bash
chmod +x launch.sh
```

---

# Standalone Build (Optional)

Standalone builds can be created using PyInstaller.

PyInstaller is installed automatically through the `requirements.txt` file.

## Important

Always activate the virtual environment before building the executable, otherwise dependencies may not be included correctly.

---

## Windows

Activate the virtual environment:

```bash
.venv\Scripts\activate
```

Build the executable:

```bash
pyinstaller VVA.spec --clean
```

---

## macOS / Linux

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Build the executable:

```bash
pyinstaller VVA.spec --clean
```

---

# Notes

- The application has been tested with Python 3.12.7.
- Using another Python version may lead to compatibility issues.
- It is recommended to always use a virtual environment.