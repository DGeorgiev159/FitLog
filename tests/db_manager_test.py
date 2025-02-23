import unittest
import sqlite3
import json
from datetime import datetime
from src.FitLog.db_manager import SQLiteRepository, Category, Exercise, DataLog


class TestSQLiteRepository(unittest.TestCase):
    """Test suite for SQLiteRepository"""

    def setUp(self):
        """Set up an in-memory database before each test"""
        self.repo = SQLiteRepository(":memory:")  # Use in-memory DB
        self.repo._load_tables()  # Create tables
        self.preloaded_tables = True

    def tearDown(self):
        """Close the database connection after each test"""
        self.repo.destroy()

    # UNIT TESTS FOR HELPER METHODS

    def test_process_reps_data(self):
        """Test converting reps string into JSON, total reps, and sets"""
        json_reps, total, sets = self.repo._process_reps_data("10,20,30")
        self.assertEqual(json_reps, "[10, 20, 30]")
        self.assertEqual(total, 60)
        self.assertEqual(sets, 3)

    def test_str2list(self):
        """Test conversion of string to list of integers"""
        self.assertEqual(self.repo._str2list("10, 20, 30"), [10, 20, 30])
        self.assertEqual(self.repo._str2list("[5, 15, 25]"), [5, 15, 25])
        self.assertEqual(self.repo._str2list(""), [])

    def test_convert_date_to_iso(self):
        """Test date conversion to ISO format"""
        date = datetime(2024, 2, 23)
        self.assertEqual(self.repo._convert_date_to_iso(date), "2024-02-23T00:00:00")

    # INTEGRATION TESTS

    def test_add_fetch_category(self):
        """Test adding and fetching a category"""
        category = Category(name="Legs")
        self.repo.add_exercise_category(category)

        categories = list(self.repo.fetch_categories())
        self.assertEqual(len(categories), 8 if self.preloaded_tables == True else 1)
        self.assertEqual(categories[2].name, "Legs")

    def test_delete_category(self):
        """Test deleting a category"""
        category = Category(name="Push")
        self.repo.add_exercise_category(category)
        self.repo.delete_exercise_category(category)

        categories = list(self.repo.fetch_categories())
        self.assertEqual(len(categories), 7 if self.preloaded_tables == True else 0)

    def test_add_fetch_exercise(self):
        """Test adding and fetching exercises"""
        category = Category(name="Pull")
        exercise = Exercise(name="Pull-ups")

        self.repo.add_exercise(category, exercise)
        exercises = list(self.repo.fetch_all_exercises(category))

        self.assertEqual(len(exercises), 4 if self.preloaded_tables == True else 1)
        self.assertEqual(exercises[1].name, "Pull-ups")

    def test_delete_exercise(self):
        """Test deleting an exercise"""
        category = Category(name="Core")
        exercise = Exercise(name="Plank", units="seconds")

        self.repo.add_exercise(category, exercise)
        self.repo.delete_exercise(exercise)

        exercises = list(self.repo.fetch_all_exercises(category))
        self.assertEqual(len(exercises), 2 if self.preloaded_tables == True else 0)

    def test_add_fetch_log(self):
        """Test adding and fetching an exercise log"""
        category = Category(name="Push")
        exercise = Exercise(name="Push-ups")

        self.repo.add_exercise(category, exercise)

        log = DataLog(
            exercise_name="Push-ups",
            training_date=datetime.now(),
            reps="10,10,10",
            weight="Bodyweight",
        )
        self.repo.add_exercise_log(log)

        logs = list(self.repo.fetch_day_log(datetime.now()))
        # self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].exercise_name, "Push-ups")

    def test_delete_log(self):
        """Test deleting an exercise log"""
        category = Category(name="Pull")
        exercise = Exercise(name="Chin-ups")

        self.repo.add_exercise(category, exercise)

        log = DataLog(
            exercise_name="Chin-ups",
            training_date=datetime.now(),
            reps="5,5,5",
            weight="Bodyweight",
        )
        self.repo.add_exercise_log(log)

        logs = list(self.repo.fetch_day_log(datetime.now()))
        self.assertEqual(len(logs), 1)

        self.repo.delete_exercise_log(logs[0].id)
        logs = list(self.repo.fetch_day_log(datetime.now()))
        self.assertEqual(len(logs), 0)

    def test_set_weight(self):
        """Test updating weight in exercise log"""
        category = Category(name="Dips")
        exercise = Exercise(name="Dips")

        self.repo.add_exercise(category, exercise)

        log = DataLog(
            exercise_name="Dips",
            training_date=datetime.now(),
            reps="8,8,8",
            weight="Bodyweight",
        )
        self.repo.add_exercise_log(log)

        logs = list(self.repo.fetch_day_log(datetime.now()))
        log_id = logs[0].id

        self.repo.set_weight(log_id, "10kg")

        updated_logs = list(self.repo.fetch_day_log(datetime.now()))
        self.assertEqual(updated_logs[0].weight, "10kg")

    def test_set_reps(self):
        """Test updating reps in exercise log"""
        category = Category(name="Handstand")
        exercise = Exercise(name="Handstand push-ups")

        self.repo.add_exercise(category, exercise)

        log = DataLog(
            exercise_name="Handstand push-ups",
            training_date=datetime.now(),
            reps="3,3,3",
            weight="Bodyweight",
        )
        self.repo.add_exercise_log(log)

        logs = list(self.repo.fetch_day_log(datetime.now()))
        log_id = logs[0].id

        self.repo.set_reps(log_id, "4,4,4")

        updated_logs = list(self.repo.fetch_day_log(datetime.now()))
        self.assertEqual(updated_logs[0].reps, [4, 4, 4])
        self.assertEqual(updated_logs[0].total, 12)
        self.assertEqual(updated_logs[0].sets, 3)

    # Additional Edge Cases & Error Handling Tests

    def test_add_fetch_exercise_with_same_name_different_categories(self):
        """Ensure exercises with the same name in different categories are allowed"""
        category1 = Category(name="Push")
        category2 = Category(name="Pull")
        exercise = Exercise(name="Rows")

        self.repo.add_exercise(category1, exercise)
        self.repo.add_exercise(category2, exercise)

        exercises1 = list(self.repo.fetch_all_exercises(category1))
        exercises2 = list(self.repo.fetch_all_exercises(category2))

        self.assertEqual(len(exercises1), 5 if self.preloaded_tables == True else 1)
        self.assertEqual(len(exercises2), 4 if self.preloaded_tables == True else 1)
        self.assertEqual(exercises1[4].name, "Rows")
        self.assertEqual(exercises2[3].name, "Rows")

    def test_delete_nonexistent_category(self):
        """Ensure deleting a non-existent category does nothing"""
        category = Category(name="Nonexistent")
        self.repo.delete_exercise_category(category)  # Should not fail
        categories = list(self.repo.fetch_categories())
        self.assertEqual(len(categories), 8 if self.preloaded_tables == True else 0)

    def test_add_exercise_log_invalid_exercise(self):
        """Ensure adding a log for a non-existent exercise raises an error"""
        log = DataLog(
            exercise_name="Nonexistent",
            training_date=datetime.now(),
            reps="10,10,10",
            weight="Bodyweight",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.add_exercise_log(log)

    def test_fetch_logs_on_empty_day(self):
        """Ensure fetching logs for a day with no entries returns empty list"""
        logs = list(self.repo.fetch_day_log(datetime.now()))
        self.assertEqual(len(logs), 0)

    def test_set_invalid_weight(self):
        """Ensure setting weight on a non-existent log fails silently"""
        self.repo.set_weight(log_id=999, weight="20kg")  # Should not throw error

    def test_set_invalid_reps(self):
        """Ensure setting reps on a non-existent log fails silently"""
        self.repo.set_reps(log_id=999, reps="10,10,10")  # Should not throw error


if __name__ == "__main__":
    unittest.main()
