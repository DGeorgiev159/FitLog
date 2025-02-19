import json
from datetime import datetime
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER, JUSTIFY

from .db_manager import DataManager


class TrainingApp(toga.App):
    def startup(self):
        """Main entry point: show a window with a DatePicker to choose the day."""
        self.data_manager = DataManager()  # Initialize the DB connection

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.main_box.add(toga.Label("Select Date:", style=Pack(padding_bottom=5)))
        self.date_picker = toga.DateInput(
            value=datetime.now(), style=Pack(padding_bottom=10, width=200), on_change=self.refresh_day_view
        )
        self.main_box.add(self.date_picker)

        # open the daily log view for the chosen date
        self.open_day_view()
        self.main_box.add(self.day_box)

        self.show_main_content()

    def show_content(self, box):
        self.main_window.content = box
        self.main_window.show()

    def show_main_content(self, w=None):
        self.show_content(self.main_box)

    def open_day_view(self):
        """Shows today's log and a button to add an exercise."""
        self.day_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Title label for the day view
        self.day_box.add(
            toga.Label(
                f"Daily Log for {self.date_picker.value.strftime('%Y-%m-%d')}",
                style=Pack(font_size=18, padding_bottom=10),
                id="header"
            )
        )

        # Button to add a new exercise entry; this will open the category selection window
        add_exercise_btn = toga.Button(
            "Add Exercise", on_press=self.open_category_selection, style=Pack(padding=5)
        )
        self.day_box.add(add_exercise_btn)

        # Box to list log entries for the day
        self.logs_box = toga.Box(style=Pack(direction=ROW, padding_top=10, alignment=CENTER))
        self.day_box.add(toga.Label("Today's Logs:", style=Pack(padding_top=10)))
        self.day_box.add(self.logs_box)

        self.refresh_day_logs()

    def refresh_day_logs(self):
        """Fetch log entries for the current day and display them."""
        # Clear existing log entries
        for child in list(self.logs_box.children):
            self.logs_box.remove(child)

        logs = self.data_manager.fetch_day_log(self.date_picker.value)
        for row in logs:
            # Expected row format: (id, exercise_id, training_date, sets, reps, total, units, weight, exercise_name)
            id = row[0]
            sets_val = row[3]
            reps_json = row[4]
            total_val = row[5]
            units_val = row[6]
            weight_val = row[7]
            exercise_name = row[8]
            try:
                reps_list = json.loads(reps_json)
            except json.JSONDecodeError:
                reps_list = [0]

            if units_val == 'seconds':
                total_val /= 60

            self.logs_box.add(toga.Label(f"{exercise_name}: sets ", id=f"{id}", style=Pack(padding_right=5)))
            self.logs_box.add(toga.NumberInput(style=Pack(padding_right=5, width=30),
                        min=0, max=20, on_change=self.save_exercise_sets, value=sets_val, id=f"{id}_sets"))
            self.logs_box.add(toga.Label("reps ", style=Pack(padding_right=5),))
            self.logs_box.add(toga.TextInput(style=Pack(padding_right=5),
                        on_change=self.save_exercise_reps, value=str(reps_list), id=f"{id}_reps"))
            self.logs_box.add(toga.Label(f"Units: {units_val}",style=Pack(padding_right=5)))
            self.logs_box.add(toga.Label(f"total: {total_val:.2f} | weight ", style=Pack(padding_right=5)))
            self.logs_box.add(toga.NumberInput(style=Pack(padding_right=5, width=30),
                        min=0, max=300, on_change=self.save_exercise_weight, value=weight_val, id=f"{id}_weight"))
            self.logs_box.add(toga.Label("kg"))
            self.logs_box.add(toga.Button("Remove", on_press=self.remove_exercise_from_log, id=f"{id}_remove"))

    def refresh_day_view(self, widget):
        for child in list(self.day_box.children):
            if child.id == "header":
                child.text = f"Daily Log for {self.date_picker.value.strftime('%Y-%m-%d')}"
        
        self.refresh_day_logs()

    # --- CATEGORY SELECTION FLOW ---

    def open_category_selection(self, widget):
        """Opens a window with buttons for each exercise category."""
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
        back_btn = toga.Button(
            "Go Back", on_press=self.show_main_content, style=Pack(padding=5)
        )
        cat_box.add(add_cat_btn)
        cat_box.add(back_btn)

        self.main_window.content = cat_box
        self.main_window.show()

    def open_add_category(self, widget):
        """Opens a window to input a new category name."""
        #self.add_category_window = toga.Window(title="Add New Category")
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        box.add(toga.Label("New Category Name:", style=Pack(padding_bottom=5)))
        self.new_category_input = toga.TextInput(placeholder="Category name")
        box.add(self.new_category_input)
        save_btn = toga.Button(
            "Save Category", on_press=self.save_new_category, style=Pack(padding=5)
        )
        back_btn = toga.Button(
            "Go Back", on_press=self.open_category_selection, style=Pack(padding=5)
        )
        box.add(save_btn)
        box.add(back_btn)
        
        self.show_content(box)

    def save_new_category(self, widget):
        """Saves the new category to the database and refreshes the category list."""
        new_cat = self.new_category_input.value.strip()
        if new_cat:
            self.data_manager.add_exercise_category(new_cat)
            self.open_category_selection(None)

    # --- EXERCISE SELECTION FLOW ---

    def open_exercise_selection(self, category):
        """Closes the category window and opens a window listing exercises for the selected category."""
        self.selected_category = category
        #self.exercise_window = toga.Window(title=f"Select Exercise ({category})")
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
        back_btn = toga.Button(
            "Go Back", on_press=self.open_category_selection, style=Pack(padding=5)
        )
        ex_box.add(add_ex_btn)
        ex_box.add(back_btn)

        self.show_content(ex_box)
    
    def open_exercise_selection_handle(self, w):
        self.open_exercise_selection(self.selected_category)

    def open_add_exercise(self, widget):
        """Opens a window to add a new exercise to the selected category."""
        #self.add_exercise_window = toga.Window(title="Add New Exercise")
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        box.add(toga.Label("New Exercise Name:", style=Pack(padding_bottom=5)))
        self.new_exercise_input = toga.TextInput(placeholder="Exercise name")
        box.add(self.new_exercise_input)
        save_btn = toga.Button(
            "Save Exercise", on_press=self.save_new_exercise, style=Pack(padding=5)
        )
        back_btn = toga.Button(
            "Go Back", on_press=self.open_exercise_selection_handle, style=Pack(padding=5)
        )
        box.add(save_btn)
        box.add(back_btn)

        self.show_content(box)

    def remove_exercise_from_log(self, widget):
        id = widget.id.split("_")[0]
        self.data_manager.delete_exercise_log(int(id))

    def save_new_exercise(self, widget):
        """Saves the new exercise to the database and refreshes the exercise list."""
        new_ex = self.new_exercise_input.value.strip()
        if new_ex:
            self.data_manager.add_exercise(self.selected_category, new_ex)
            self.open_exercise_selection(self.selected_category)

    # --- EXERCISE DETAIL (LOG ENTRY) ---

    def open_exercise_detail(self, exercise):
        """Closes the exercise selection window and opens a detail window for logging."""
        self.selected_exercise = exercise
        #self.detail_window = toga.Window(title=f"Log Details: {exercise}")
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
            items=["quantity", "seconds"], style=Pack(width=100)
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
        back_btn = toga.Button(
            "Go Back", on_press=self.open_exercise_selection_handle, style=Pack(padding=5)
        )
        home_btn = toga.Button(
            "Home", on_press=self.show_main_content, style=Pack(padding=5)
        )
        box.add(save_btn)
        box.add(back_btn)
        box.add(home_btn)

        self.show_content(box)

    def save_exercise_sets(self, widget):
        id = widget.id.split("_")[0]
        if widget.value:
            self.data_manager.set_sets(id, int(widget.value))

    def save_exercise_reps(self, widget):
        id = widget.id.split("_")[0]
        reps_list = [int(num.strip()) for num in widget.value.strip("[]").split(",") if num.strip().isdigit()]
        if reps_list:
            self.data_manager.set_reps(id, reps_list)

    def save_exercise_weight(self, widget):
        id = widget.id.split("_")[0]
        if widget.value:
            self.data_manager.set_weight(id, float(widget.value))

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
            date=self.date_picker.value,
        )

        # Close the detail window and refresh the day view logs
        self.show_main_content()
        self.refresh_day_logs()


def main():
    return TrainingApp("Training Tracker", "org.example.trainingtracker")


if __name__ == "__main__":
    main().main_loop()
