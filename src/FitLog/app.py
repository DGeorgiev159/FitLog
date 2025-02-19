import json
from datetime import datetime
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from .db_manager import DataManager


class TrainingApp(toga.App):
    def startup(self):
        """Main entry point: show a window with a DatePicker to choose the day."""
        self.data_manager = DataManager()  # Initialize the DB connection

        self.main_window = toga.MainWindow(title=self.formal_name)
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        main_box.add(toga.Label("Select Date:", style=Pack(padding_bottom=5)))
        self.date_picker = toga.DatePicker(
            value=datetime.now(), style=Pack(padding_bottom=10, width=200)
        )
        main_box.add(self.date_picker)

        # Button to open the daily log view for the chosen date
        open_day_view_btn = toga.Button(
            "Open Day View", on_press=self.open_day_view, style=Pack(padding=5)
        )
        main_box.add(open_day_view_btn)

        self.main_window.content = main_box
        self.main_window.show()

    def open_day_view(self, widget):
        """Opens a window that shows today's log and a button to add an exercise."""
        self.current_day_date = self.date_picker.value
        self.day_window = toga.Window(title=self.current_day_date.strftime("%Y-%m-%d"))
        self.day_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Title label for the day view
        self.day_box.add(
            toga.Label(
                f"Daily Log for {self.current_day_date.strftime('%Y-%m-%d')}",
                style=Pack(font_size=18, padding_bottom=10),
            )
        )

        # Button to add a new exercise entry; this will open the category selection window
        add_exercise_btn = toga.Button(
            "Add Exercise", on_press=self.open_category_selection, style=Pack(padding=5)
        )
        self.day_box.add(add_exercise_btn)

        # Box to list log entries for the day
        self.logs_box = toga.Box(style=Pack(direction=COLUMN, padding_top=10))
        self.day_box.add(toga.Label("Today's Logs:", style=Pack(padding_top=10)))
        self.day_box.add(self.logs_box)

        self.refresh_day_logs()

        self.day_window.content = self.day_box
        self.windows.add(self.day_window)
        self.day_window.show()

    def refresh_day_logs(self):
        """Fetch log entries for the current day and display them."""
        # Clear existing log entries
        for child in list(self.logs_box.children):
            self.logs_box.remove(child)

        logs = self.data_manager.fetch_day_log(self.current_day_date)
        for row in logs:
            # Expected row format: (id, exercise_id, training_date, sets, reps, total, units, weight, exercise_name)
            log_id = row[0]
            sets_val = row[3]
            reps_json = row[4]
            total_val = row[5]
            units_val = row[6]
            weight_val = row[7]
            exercise_name = row[8]
            try:
                reps_list = json.loads(reps_json)
            except json.JSONDecodeError:
                reps_list = []
            log_text = (
                f"ID:{log_id} | {exercise_name} | Sets: {sets_val}, "
                f"Reps: {reps_list}, Total: {total_val}, Weight: {weight_val}, Units: {units_val}"
            )
            self.logs_box.add(toga.Label(log_text))

    # --- CATEGORY SELECTION FLOW ---

    def open_category_selection(self, widget):
        """Opens a window with buttons for each exercise category."""
        self.category_window = toga.Window(title="Select Category")
        cat_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        categories = [c[0] for c in self.data_manager.fetch_categories()]
        for category in categories:
            btn = toga.Button(
                category,
                on_press=lambda w, cat=category: self.open_exercise_selection(cat),
                style=Pack(padding=5),
            )
            cat_box.add(btn)

        # Button to add a new category
        add_cat_btn = toga.Button(
            "Add Category", on_press=self.open_add_category, style=Pack(padding=5)
        )
        cat_box.add(add_cat_btn)

        self.category_window.content = cat_box
        self.windows.add(self.category_window)
        self.category_window.show()

    def open_add_category(self, widget):
        """Opens a window to input a new category name."""
        self.add_category_window = toga.Window(title="Add New Category")
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        box.add(toga.Label("New Category Name:", style=Pack(padding_bottom=5)))
        self.new_category_input = toga.TextInput(placeholder="Category name")
        box.add(self.new_category_input)
        save_btn = toga.Button(
            "Save Category", on_press=self.save_new_category, style=Pack(padding=5)
        )
        box.add(save_btn)
        self.add_category_window.content = box
        self.windows.add(self.add_category_window)
        self.add_category_window.show()

    def save_new_category(self, widget):
        """Saves the new category to the database and refreshes the category list."""
        new_cat = self.new_category_input.value.strip()
        if new_cat:
            self.data_manager.add_exercise_category(new_cat)
            self.add_category_window.close()
            # Reopen the category selection to reflect the new category
            if hasattr(self, "category_window"):
                self.category_window.close()
            self.open_category_selection(None)

    # --- EXERCISE SELECTION FLOW ---

    def open_exercise_selection(self, category):
        """Closes the category window and opens a window listing exercises for the selected category."""
        if hasattr(self, "category_window"):
            self.category_window.close()
        self.selected_category = category
        self.exercise_window = toga.Window(title=f"Select Exercise ({category})")
        ex_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        exercises = [e[0] for e in self.data_manager.fetch_exercises(category)]
        for exercise in exercises:
            btn = toga.Button(
                exercise,
                on_press=lambda w, ex=exercise: self.open_exercise_detail(ex),
                style=Pack(padding=5),
            )
            ex_box.add(btn)

        # Button to add a new exercise for the current category
        add_ex_btn = toga.Button(
            "Add Exercise", on_press=self.open_add_exercise, style=Pack(padding=5)
        )
        ex_box.add(add_ex_btn)

        self.exercise_window.content = ex_box
        self.windows.add(self.exercise_window)
        self.exercise_window.show()

    def open_add_exercise(self, widget):
        """Opens a window to add a new exercise to the selected category."""
        self.add_exercise_window = toga.Window(title="Add New Exercise")
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        box.add(toga.Label("New Exercise Name:", style=Pack(padding_bottom=5)))
        self.new_exercise_input = toga.TextInput(placeholder="Exercise name")
        box.add(self.new_exercise_input)
        save_btn = toga.Button(
            "Save Exercise", on_press=self.save_new_exercise, style=Pack(padding=5)
        )
        box.add(save_btn)
        self.add_exercise_window.content = box
        self.windows.add(self.add_exercise_window)
        self.add_exercise_window.show()

    def save_new_exercise(self, widget):
        """Saves the new exercise to the database and refreshes the exercise list."""
        new_ex = self.new_exercise_input.value.strip()
        if new_ex:
            self.data_manager.add_exercise(self.selected_category, new_ex)
            self.add_exercise_window.close()
            if hasattr(self, "exercise_window"):
                self.exercise_window.close()
            self.open_exercise_selection(self.selected_category)

    # --- EXERCISE DETAIL (LOG ENTRY) ---

    def open_exercise_detail(self, exercise):
        """Closes the exercise selection window and opens a detail window for logging."""
        if hasattr(self, "exercise_window"):
            self.exercise_window.close()
        self.selected_exercise = exercise
        self.detail_window = toga.Window(title=f"Log Details: {exercise}")
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Display the selected exercise name
        box.add(toga.Label(f"Exercise: {exercise}", style=Pack(padding_bottom=10)))

        # Create input fields for sets, reps, weight, and unit selection
        row = toga.Box(style=Pack(direction=ROW, padding_bottom=10))
        row.add(toga.Label("Sets:", style=Pack(padding_right=5)))
        self.detail_sets_input = toga.TextInput(
            placeholder="Sets", style=Pack(width=60, padding_right=10)
        )
        row.add(self.detail_sets_input)

        row.add(toga.Label("Reps (comma separated):", style=Pack(padding_right=5)))
        self.detail_reps_input = toga.TextInput(
            placeholder="e.g. 10,10,8", style=Pack(width=140, padding_right=10)
        )
        row.add(self.detail_reps_input)

        row.add(toga.Label("Weight:", style=Pack(padding_right=5)))
        self.detail_weight_input = toga.TextInput(
            placeholder="Weight", style=Pack(width=60, padding_right=10)
        )
        row.add(self.detail_weight_input)

        row.add(toga.Label("Units:", style=Pack(padding_right=5)))
        self.detail_units_selection = toga.Selection(
            items=["quantity", "kg", "lbs", "seconds"], style=Pack(width=100)
        )
        row.add(self.detail_units_selection)
        box.add(row)

        # Label to display the total (calculated from reps)
        self.detail_total_label = toga.Label("Total: 0", style=Pack(padding_bottom=10))
        box.add(self.detail_total_label)

        # Button to save the log entry
        save_btn = toga.Button(
            "Save Log", on_press=self.save_exercise_log_detail, style=Pack(padding=5)
        )
        box.add(save_btn)

        self.detail_window.content = box
        self.windows.add(self.detail_window)
        self.detail_window.show()

    def save_exercise_log_detail(self, widget):
        """Reads the input from the detail window, adds the log entry to the database, and refreshes the day view."""
        try:
            sets_val = int(self.detail_sets_input.value)
        except ValueError:
            sets_val = 0

        reps_str = self.detail_reps_input.value.strip()
        reps_list = (
            [int(x.strip()) for x in reps_str.split(",") if x.strip().isdigit()]
            if reps_str
            else []
        )
        total_val = sum(reps_list)
        try:
            weight_val = float(self.detail_weight_input.value)
        except ValueError:
            weight_val = 0.0
        units_val = self.detail_units_selection.value or "quantity"

        self.detail_total_label.text = f"Total: {total_val}"

        # Save the exercise log using DataManager
        self.data_manager.add_exercise_log(
            exercise=self.selected_exercise,
            sets=sets_val,
            reps=reps_list,
            weight=weight_val,
            units=units_val,
            date=self.current_day_date,
        )

        # Close the detail window and refresh the day view logs
        self.detail_window.close()
        self.refresh_day_logs()


def main():
    return TrainingApp("Training Tracker", "org.example.trainingtracker")


if __name__ == "__main__":
    main().main_loop()
