import unittest
import json
from datetime import datetime

from src.FitLog.db_manager import DataManager  # Adjust the import path if needed


class TestDataManager(unittest.TestCase):

    def setUp(self):
        # Create a DataManager instance with an in-memory database.
        self.dm = DataManager(":memory:")

    def tearDown(self):
        self.dm.destroy()

    def test_default_categories_loaded(self):
        """Test that default categories were loaded by _load_exercises."""
        categories = [c[0] for c in self.dm.fetch_categories()]
        # Check that some expected default categories exist.
        self.assertIn("Push", categories)
        self.assertIn("Pull", categories)
        self.assertIn("Legs", categories)

    def test_add_exercise_category(self):
        """Test adding a new exercise category."""
        new_cat = "TestCategory"
        self.dm.add_exercise_category(new_cat)
        categories = [c[0] for c in self.dm.fetch_categories()]
        self.assertIn(new_cat, categories)

        # Adding the same category again should not duplicate it.
        self.dm.add_exercise_category(new_cat)
        categories_after = [c[0] for c in self.dm.fetch_categories()]
        self.assertEqual(categories_after.count(new_cat), 1)

    def test_add_exercise_and_fetch(self):
        """Test adding an exercise under a new category and fetching it."""
        category = "TestCategory2"
        exercise_name = "TestExercise"
        self.dm.add_exercise(category, exercise_name)
        exercises = [e[0] for e in self.dm.fetch_exercises(category)]
        self.assertIn(exercise_name, exercises)

    def test_add_exercise_log_and_fetch_day_log(self):
        """Test adding an exercise log and then fetching it by date."""
        category = "TestCategory3"
        exercise_name = "TestExerciseLog"
        self.dm.add_exercise(category, exercise_name)

        test_date = datetime(2025, 2, 18, 12, 0, 0)
        sets_val = 3
        reps_list = [10, 10, 8]
        units = "quantity"
        self.dm.add_exercise_log(
            exercise=exercise_name,
            sets=sets_val,
            reps=reps_list,
            units=units,
            date=test_date,
        )
        logs = self.dm.fetch_day_log(test_date)
        self.assertTrue(len(logs) >= 1)

        # Verify the contents of the first returned log.
        log = logs[0]
        # Expected row format: (id, exercise_id, training_date, sets, reps, total, units, weight, exercise_name)
        self.assertEqual(log[3], sets_val)
        self.assertEqual(log[5], sum(reps_list))
        self.assertEqual(log[6], units)
        self.assertEqual(log[8], exercise_name)

    def test_update_log_fields(self):
        """Test updating log fields (sets, reps, weight, units) using the set_* methods."""
        category = "TestCategory4"
        exercise_name = "TestExerciseSet"
        self.dm.add_exercise(category, exercise_name)

        test_date = datetime(2025, 2, 18, 12, 0, 0)
        # Insert an initial log.
        self.dm.add_exercise_log(
            exercise=exercise_name,
            sets=2,
            reps=[5, 5],
            units="quantity",
            date=test_date,
        )
        logs = self.dm.fetch_day_log(test_date)
        self.assertTrue(len(logs) >= 1)
        log = logs[0]
        log_id = log[0]

        # Update fields.
        self.dm.set_sets(log_id, 4)
        self.dm.set_reps(log_id, [8, 8, 8, 8])
        self.dm.set_weight(log_id, 50)
        self.dm.set_units(log_id, "quantity")

        # Fetch updated log.
        logs_updated = self.dm.fetch_day_log(test_date)
        updated_log = None
        for row in logs_updated:
            if row[0] == log_id:
                updated_log = row
                break
        self.assertIsNotNone(updated_log)
        self.assertEqual(updated_log[3], 4)
        new_reps = json.loads(updated_log[4])
        self.assertEqual(new_reps, [8, 8, 8, 8])
        self.assertEqual(updated_log[5], sum(new_reps))
        self.assertEqual(updated_log[7], 50)
        self.assertEqual(updated_log[6], "quantity")


if __name__ == "__main__":
    unittest.main()
