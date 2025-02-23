from dataclasses import dataclass
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Any, Generator

from abc import ABC, abstractmethod


# Models

@dataclass
class Category:
    name: str
    id: Optional[int] = None


@dataclass
class Exercise:
    name: str
    id: Optional[int] = None
    category_id: Optional[int] = None
    units: str = "-"


@dataclass
class DataLog:
    reps: str
    training_date: datetime
    weight: str
    id: Optional[int] = None
    exercise_id: Optional[int] = None
    sets: Optional[int] = None
    total: Optional[int] = None
    exercise_name: Optional[str] = None


# Repository


class IRepository(ABC):
    @abstractmethod
    def fetch_categories(self) -> Generator[Category, None, None]:
        raise NotImplementedError

    @abstractmethod
    def add_exercise_category(self, category: Category) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_exercise_category(self, category: Category) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_all_exercises(self, category: Category) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def add_exercise(self, category: Category, exercise: Exercise) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_exercise(self, exercise: Exercise) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_day_log(
        self, date: Optional[datetime] = None
    ) -> Generator[DataLog, None, None]:
        raise NotImplementedError

    @abstractmethod
    def fetch_exercise_totals_over_time(self, exercise_id: int) -> Tuple[Tuple]:
        raise NotImplementedError

    @abstractmethod
    def add_exercise_log(self, data_log: DataLog) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_exercise_log(self, log_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_weight(self, log_id: int, weight: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_reps(self, log_id: int, reps: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def destroy(self) -> None:
        raise NotImplementedError


class SQLiteRepository(IRepository):

    def __init__(self, db_path: str = "training_data.sqlite"):
        self._logger = logging.getLogger(__name__)
        self._connect_to_database(db_path)

    def fetch_categories(self) -> Generator[Category, None, None]:
        self._cursor.execute("""SELECT name FROM exercise_category""")

        categories = self._cursor.fetchall()
        for c in categories:
            yield Category(name=c[0])

    def fetch_all_exercises(
        self, category: Category
    ) -> Generator[Exercise, None, None]:
        self._cursor.execute(
            """SELECT e.name
            FROM exercises e
            JOIN exercise_category ec ON e.category_id=ec.id
            WHERE ec.name=?""",
            (category.name,),
        )
        exercises = self._cursor.fetchall()
        for ex in exercises:
            yield Exercise(name=ex[0])

    def fetch_day_log(
        self, date: Optional[datetime] = None
    ) -> Generator[DataLog, None, None]:
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
        for log in self._map_to_data_log(self._cursor.fetchall()):
            yield log

    def fetch_exercise_totals_over_time(self, exercise_id: int) -> Tuple[Tuple]:
        # TODO: make docstring it returns totals, date (in this order)
        self._cursor.execute(
            """
            SELECT total, training_date
            FROM exercise_log
            WHERE exercise_id = ?
            ORDER BY training_date
            """,
            (exercise_id,),
        )

        return tuple(zip(*self._cursor.fetchall()))

    def add_exercise_category(self, category: Category) -> None:
        try:
            self._cursor.execute(
                "INSERT OR IGNORE INTO exercise_category (name) VALUES (?);",
                (category.name,),
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def delete_exercise_category(self, category: Category) -> None:
        try:
            self._cursor.execute(
                "DELETE FROM exercises WHERE category_id = (SELECT id FROM exercise_category WHERE name = ?);",
                (category.name,),
            )

            self._cursor.execute(
                "DELETE FROM exercise_category WHERE name=?;", (category.name,)
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def add_exercise(self, category: Category, exercise: Exercise) -> None:
        self.add_exercise_category(category)
        try:
            self._cursor.execute(
                """
                INSERT OR IGNORE INTO exercises (name, category_id, units)
                VALUES (?, (SELECT id FROM exercise_category WHERE name = ?), ?);
                """,
                (exercise.name, category.name, exercise.units),
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def delete_exercise(self, exercise: Exercise) -> None:
        try:
            self._cursor.execute(
                """
                DELETE FROM exercises WHERE name=?
                """,
                (exercise.name,),
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def add_exercise_log(self, data_log: DataLog) -> None:

        training_date = self._convert_date_to_iso(data_log.training_date)
        json_reps, total, sets = self._process_reps_data(data_log.reps)

        self._cursor.execute(
            "SELECT id FROM exercises WHERE name = ?", (data_log.exercise_name,)
        )
        exercise_id = self._cursor.fetchone()

        if not exercise_id:
            self._logger.error(f"Exercise '{data_log.exercise_name}' does not exist.")
            raise sqlite3.IntegrityError(
                f"Exercise '{data_log.exercise_name}' does not exist."
            )

        try:
            self._cursor.execute(
                """
                INSERT INTO exercise_log (exercise_id, training_date, sets, reps, total, weight)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    exercise_id[0],
                    training_date,
                    sets,
                    json_reps,
                    total,
                    data_log.weight,
                ),
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def delete_exercise_log(self, log_id: int) -> None:
        try:
            self._cursor.execute("DELETE FROM exercise_log WHERE id=?;", (log_id,))
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def set_weight(self, log_id: int, weight: str) -> None:
        try:
            self._cursor.execute(
                "UPDATE exercise_log SET weight=? WHERE id=?;", (weight, log_id)
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def set_reps(self, log_id: int, reps: str) -> None:
        json_reps, total, sets = self._process_reps_data(reps)
        try:
            self._cursor.execute(
                "UPDATE exercise_log SET reps=?, total=?, sets=? WHERE id=?;",
                (json_reps, total, sets, log_id),
            )
            self._connection.commit()
        except sqlite3.Error as e:
            self._logger.error(f"Database error: {e}")
            self._connection.rollback()

    def destroy(self) -> None:
        if self._connection:
            self._connection.close()

    def _process_reps_data(self, reps: str) -> Tuple[str, int, int]:
        import json
        reps_list = self._str2list(reps)
        total = sum(reps_list)
        sets = len(reps_list) if len(reps_list) else 1
        json_reps = json.dumps(reps_list)
        return (json_reps, total, sets)

    def _convert_date_to_iso(self, date: Optional[datetime]) -> str:
        if date is None:
            date = datetime.now()
        return date.isoformat()

    def _connect_to_database(self, db_path) -> None:
        try:
            self._connection = sqlite3.connect(db_path)
            self._cursor = self._connection.cursor()
        except sqlite3.Error as e:
            self._logger.critical(e)

        # check if database is empty
        self._cursor.execute("SELECT name FROM sqlite_master")
        if not self._cursor.fetchall():
            self._load_default_data()

    def _str2list(self, s: str) -> List:
        return [int(x.strip()) for x in s.strip("[]").split(",") if x.strip().isdigit()]

    def _map_to_data_log(self, logs: List[Any]) -> Generator[DataLog, None, None]:

        for row in logs:
            # Each row is expected to have eight elements:
            # (id, exercise_id, training_date, sets, reps, total, weight, exercise_name)
            id, exercise_id, training_date, sets, reps, total, weight, exercise_name = (
                row
            )

            import json

            try:
                reps_list = json.loads(reps)
            except json.JSONDecodeError:
                reps_list = [0]

            yield DataLog(
                id=id,
                exercise_id=exercise_id,
                training_date=training_date,
                sets=sets,
                reps=reps_list,
                total=total,
                weight=weight,
                exercise_name=exercise_name,
            )

    def _load_default_data(self) -> None:
        self._load_tables()
        self._load_exercises()

    def _load_tables(self) -> None:
        self._cursor.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS exercise_category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                units TEXT,
                FOREIGN KEY (category_id) REFERENCES exercise_category(id)
            );
            
            CREATE TABLE IF NOT EXISTS exercise_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                training_date TEXT NOT NULL,
                sets INTEGER NOT NULL,
                reps TEXT,
                total INTEGER,
                weight TEXT,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            );
        """
        )
        self._connection.commit()

    def _load_exercises(self) -> None:
        default_data = {
            "Push": [
                ("Push-ups", "-"),
                ("Declined push-ups", "-"),
                ("Elevated pike push-ups", "-"),
                ("One arm inclined push-ups", "-"),
            ],
            "Pull": [("Chin-ups", "-"), ("Pull-ups", "-"), ("One arm hold", "seconds")],
            "Legs": [
                ("Squats", "-"),
                ("Bulgarian squats", "-"),
                ("One leg squats", "-"),
            ],
            "Core": [
                ("Plank", "seconds"),
                ("Dragon-flag", "seconds"),
                ("Hollow body hold", "seconds"),
            ],
            "Dips": [("Dips", "-"), ("Single bar dips", "-")],
            "Inversions": [("Headstand", "seconds"), ("Headstand advanced", "seconds")],
            "Handstand": [
                ("Handstand", "seconds"),
                ("Handstand push-ups", "-"),
                ("Tuck handstand", "seconds"),
                ("Straddle handstand", "seconds"),
                ("One arm handstand", "seconds"),
                ("Wall handstand shoulder taps", "-"),
            ],
            "Lever": [
                ("Tuck front lever rises", "-"),
                ("Advance tuck front lever rises", "-"),
                ("Straddle lever rises", "-"),
                ("Frond lever rises", "-"),
                ("Tuck front lever hold", "seconds"),
                ("Advance tuck front lever hold", "seconds"),
                ("Straddle front lever hold", "seconds"),
                ("Front lever hold", "seconds"),
            ],
        }

        for cat_name, exercises in default_data.items():
            for e in exercises:
                self.add_exercise(
                    Category(name=cat_name), Exercise(name=e[0], units=e[1])
                )
        self._connection.commit()
