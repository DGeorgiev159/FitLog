import sqlite3
import logging
from datetime import datetime
import json

from abc import ABC, abstractmethod


class IRepository(ABC):
    @abstractmethod
    def fetch_categories(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def add_exercise_category(self, category: str):
        raise NotImplementedError

    @abstractmethod
    def delete_exercise_category(self, category: str):
        raise NotImplementedError

    @abstractmethod
    def fetch_exercises(self, category: str):
        raise NotImplementedError

    @abstractmethod
    def add_exercise(self, category: str, exercise: str):
        raise NotImplementedError

    @abstractmethod
    def delete_exercise(self, category: str, exercise: str):
        raise NotImplementedError

    @abstractmethod
    def fetch_day_log(self, date: datetime | None = None):
        raise NotImplementedError

    @abstractmethod
    def fetch_exercise_totals_over_time(self, exercise_id: int):
        raise NotImplementedError

    @abstractmethod
    def add_exercise_log(
        self,
        exercise: str,
        reps: list[int] = [],
        units: str = "quantity",
        date: datetime | None = None,
        weight: int = 0,
    ):
        raise NotImplementedError

    @abstractmethod
    def delete_exercise_log(self, id: int):
        raise NotImplementedError

    @abstractmethod
    def set_weight(self, id: int, weight: int):
        raise NotImplementedError

    @abstractmethod
    def set_reps(self, id: int, reps: list[int]):
        raise NotImplementedError

    @abstractmethod
    def destroy(self):
        raise NotImplementedError


class SQLiteRepository(IRepository):

    def __init__(self, db_path: str = "training_data.sqlite"):
        self._logger = logging.getLogger(__name__)
        self._connect_to_database(db_path)

    def fetch_categories(self) -> list[str]:
        self._cursor.execute("""SELECT name FROM exercise_category""")

        return self._cursor.fetchall()

    def fetch_exercises(self, category: str):
        self._cursor.execute(
            """SELECT e.name
            FROM exercises e
            JOIN exercise_category ec ON e.category_id=ec.id
            WHERE ec.name=?""",
            (category,),
        )

        return self._cursor.fetchall()

    def fetch_day_log(self, date: datetime | None = None):
        training_date = self._convert_date_to_iso(date)

        self._cursor.execute(
            """
            SELECT l.*, e.name as exercise_name
            FROM exercise_log l
            JOIN exercises e ON l.exercise_id = e.id
            WHERE training_date = ?
            """,
            (training_date,),
        )
        return self._cursor.fetchall()

    def fetch_exercise_totals_over_time(self, exercise_id: int):

        self._cursor.execute(
            """
            SELECT total, training_date
            FROM exercise_log
            WHERE exercise_id = ?
            ORDER BY training_date
            """,
            (exercise_id,),
        )
        return self._cursor.fetchall()

    def add_exercise_category(self, category: str):

        self._cursor.execute(
            "INSERT OR IGNORE INTO exercise_category (name) VALUES (?);", (category,)
        )
        self._connection.commit()

    def delete_exercise_category(self, category: str):
        self._cursor.execute("DELETE FROM exercise_category WHERE name=?;", (category,))
        self._connection.commit()

    def add_exercise(self, category: str, exercise: str):
        self.add_exercise_category(category)
        self._cursor.execute(
            """
            INSERT OR IGNORE INTO exercises (name, category_id)
            VALUES (?, (SELECT id FROM exercise_category WHERE name = ?));
            """,
            (exercise, category),
        )
        self._connection.commit()

    def delete_exercise(self, category: str, exercise: str):
        self._cursor.execute(
            """
            DELETE FROM exercises WHERE name=?,
            (SELECT id FROM exercise_category WHERE name=?);""",
            (exercise, category),
        )
        self._connection.commit()

    def add_exercise_log(
        self,
        exercise: str,
        reps: list[int] = [],
        units: str = "quantity",
        date: datetime | None = None,
        weight: int = 0,
    ):
        training_date = self._convert_date_to_iso(date)
        total = sum(reps)
        sets = int(len(reps))
        json_reps = json.dumps(reps)

        self._cursor.execute(
            """
            INSERT INTO exercise_log (exercise_id, training_date, sets, reps, total, units, weight)
            VALUES (
            (SELECT id FROM exercises WHERE name = ?),
            ?, ?, ?, ?, ?, ?);""",
            (exercise, training_date, sets, json_reps, total, units, weight),
        )
        self._connection.commit()

    def delete_exercise_log(self, id: int):
        self._cursor.execute("DELETE FROM exercise_log WHERE id=?;", (id,))
        self._connection.commit()

    def set_date(self, id: int, date: datetime | None = None):
        training_date = self._convert_date_to_iso(date)
        self._cursor.execute(
            "UPDATE exercise_log SET training_date=? WHERE id=?;", (training_date, id)
        )
        self._connection.commit()

    def set_weight(self, id: int, weight: int):
        self._cursor.execute(
            "UPDATE exercise_log SET weight=? WHERE id=?;", (weight, id)
        )
        self._connection.commit()

    def set_reps(self, id: int, reps: list[int]):
        json_reps = json.dumps(reps)
        total = sum(reps)
        sets = int(len(reps))
        self._cursor.execute(
            "UPDATE exercise_log SET reps=?, total=?, sets=? WHERE id=?;",
            (json_reps, total, sets, id),
        )
        self._connection.commit()

    def set_units(self, id: int, units: str = "quantity"):
        self._cursor.execute("UPDATE exercise_log SET units=? WHERE id=?;", (units, id))
        self._connection.commit()

    def set_data(self, id: int, reps: list[int], date: datetime | None = None):
        self.set_reps(id, reps)
        self.set_date(id, date)

    def destroy(self):
        if self._connection:
            self._connection.close()

    def _convert_date_to_iso(self, date: datetime | None):
        if date is None:
            date = datetime.now()
        return date.isoformat()

    def _connect_to_database(self, db_path):
        try:
            self._connection = sqlite3.connect(db_path)
            self._cursor = self._connection.cursor()
        except sqlite3.Error as e:
            self._logger.critical(e)

        # check if database is empty
        self._cursor.execute("SELECT name FROM sqlite_master")
        if not self._cursor.fetchall():
            self._load_default_data()

    def _load_default_data(self):
        self._load_tables()
        self._load_exercises()

    def _load_tables(self):
        self._cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS exercise_category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES exercise_category(id)
            );
            
            CREATE TABLE IF NOT EXISTS exercise_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                training_date TEXT NOT NULL,
                sets INTEGER NOT NULL,
                reps TEXT,
                total INTEGER,
                units TEXT,
                weight REAL,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            );
        """
        )
        self._connection.commit()

    def _load_exercises(self):
        default_data = {
            "Push": [
                "Push-ups",
                "Declined push-ups",
                "Elevated pike push-ups",
                "One arm inclined push-ups",
            ],
            "Pull": ["Chin-ups", "Pull-ups", "One arm hold"],
            "Legs": ["Squats", "Bulgarian squats", "One leg squats"],
            "Core": ["Plank", "Dragon-flag", "Hollow body hold"],
            "Dips": ["Dips", "Single bar dips"],
            "Inversions": ["Headstand", "Headstand advanced"],
            "Handstand": [
                "Handstand",
                "Handstand push-ups",
                "Tuck handstand",
                "Straddle handstand",
                "One arm handstand",
                "Wall handstand shoulder taps",
            ],
            "Lever": [
                "Tuck front lever rises",
                "Advance tuck front lever rises",
                "Straddle lever rises",
                "Frond lever rises",
                "Tuck front lever hold",
                "Advance tuck front lever hold",
                "Straddle front lever hold",
                "Front lever hold",
            ],
        }

        for category, exercises in default_data.items():
            for exercise in exercises:
                self.add_exercise(category, exercise)
        self._connection.commit()
