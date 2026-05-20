# Vector Vario Analyzer v0.02

![vector vario software logo](src/gui/icons/logo.png)

## Overview


This software was developed to fully explore the data recorded by the Vector Vario in its enriched files (IGC+ format).

It enables a high level of scientific flight analysis, as well as in-depth discussions about the data and its interpretation.

Please refer to the user manual for detailed usage instructions, or visit [Vector Vario website](https://vectorvario.com/softwares/)

---

# Requirements

Before running the application, make sure the following are installed on your system:

- Python >= 3.12.7
- pip

Python packages and dependencies are listed in:

```bash
requirements.txt
```

---

# Installation

## 1. Clone or Download the Project

Using Git:

Go the a specific location where you want the app to be cloned :

```bash
git clone https://github.com/TheGoodWeather/vector_software
cd vector_software
```

Or download the ZIP archive from GitHub and extract it.

---

# Windows Installation

## Create a Virtual Environment

In the folder vector_software where the files are extracted : 

```bash
python -m venv .venv
```

## Activate the Virtual Environment

The virtual Environment must be activated before installing dependencies :

```bash
.venv\Scripts\activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Launch the Application

You can manualy launch the app : 

```bash
python src/main.py
```

Or you can also use the provided launcher:

```bash
src/launch.bat
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
src/launch.command
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
src/launch.sh
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