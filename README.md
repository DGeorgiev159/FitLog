# FitLog

**Training Tracker** is a cross-platform workout logging application built using [BeeWare Toga](https://beeware.org/project/projects/libraries/toga/). This app allows users to track their exercises, log sets and reps, and visualize progress over time.

### Prerequisites

- Python **3.12+**
- [pipenv](https://pipenv.pypa.io/en/latest/)
- [BeeWare Briefcase](https://beeware.org/project/projects/tools/briefcase/) installed

## Installation
1. Clone

```sh
    git clone git@github.com:DGeorgiev159/FitLog.git
    cd FitLog
```

2. Install dependencies and activate venv

```sh
    pipenv install
    pipenv shell
```

3. Run the app in development mode:

```sh
   briefcase dev
```

This will launch the app in a local environment for testing and development.

Alternatively, you can build and run the app as a standalone executable:

```sh
   briefcase build
   briefcase run
```

## Features

- 📆 **Daily Log View** – Select a date and log exercises for that day.
- 🏋️ **Exercise Tracking** – Record sets, reps, and weight for each exercise.
- 📊 **Progress Visualization** – View exercise performance trends using built-in charts.
- 📂 **Database-Backed Storage** – Logs are stored using SQLite for persistent tracking.
- 🌓 **Native UI** – A native, simplistic interface for easy readability and usage.
