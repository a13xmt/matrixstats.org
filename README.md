# Matrix Stats

First public catalog for matrix rooms. There you can find a lot of rooms grouped by ratings or categories. Feel free to explore new things.

Website: https://matrixstats.org

Matrix room: [#matrixstats:matrix.org](https://riot.im/app/#/room/#matrixstats:matrix.org)

Screenshots:

![Matrixstats screenshot 1](https://s3.amazonaws.com/matrixstats/matrixstats-01.png)
![Matrixstats screenshot 2](https://s3.amazonaws.com/matrixstats/matrixstats-02.png)

## Installation (dev version)

### Requirements

* python 3.6+
* postgresql 10.0+

### 1. Clone the repository

Clone the repository:

```https://github.com/a13xmt/matrixstats.org.git```

### 2. Install the requirements

Install all the project requirements via pip:

```pip install -r source/requirements.pip```

(optional) use virtualenv and python-virtualenvwrapper for installation

### 3. Create a database

Open the postgres shell via ```psql``` and run the following:

```
CREATE DATABASE matrixstats;
CREATE USER matrixstats WITH PASSWORD 'matrixstats';
GRANT ALL PRIVILEGES ON DATABASE matrixstats TO matrixstats;
```

### 4. Set environment variables

Fill environment template with your own settings:

```vi source/matrix_stats/settings/env_template```

Activate the environment file:
```
set -a
source source/matrix_stats/settings/env_template
set +a
```

(optional) add this code to virualenv postactivation hooks ```/home/<user_name>/.virtualenvs/<env_name>/bin/postactivate```

### 5. Apply database migrations

Apply database migrations:

```cd source
python manage.py migrate
```

### 6. Run dev server

Run development server, listening on http://127.0.0.1:8000

```python manage.py runserver```

(optional) Add admin account via ```python manage.py createsuperuser``` with admin page on http://127.0.0.1:8000/admin/


### Additional info

Some ratings (7/30/90 days based) may work weird on development server due to lacking statistical data. It's OK if there are some empty widgets on the main page.
