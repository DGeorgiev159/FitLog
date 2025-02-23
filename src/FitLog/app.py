from datetime import datetime
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from toga.colors import GRAY, BLUE

from .db_manager import SQLiteRepository, Category, Exercise, DataLog


class TrainingApp(toga.App):

    DARK_BACKGROUND = "#121212"
    DARK_FOREGROUND = "#e0e0e0"
    ACCENT_COLOR = "#9160c9"
    BUTTON_BACKGROUND = "#1f1f1f"
    BUTTON_TEXT_COLOR = "#ffffff"

    def startup(self):
        """Main entry point: show a window with a DatePicker to choose the day."""
        self.data_manager = DataManager()  # Initialize the DB connection
        self._load_styles()

        self.main_window = toga.MainWindow(title=self.formal_name, on_close=self.destroy)
        self.main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.canvas = toga.Canvas(style=Pack(flex=1))

        self.main_box.add(toga.Label("Select Date:", style=Pack(padding_bottom=5)))
        self.date_picker = toga.DateInput(
            value=datetime.now(), style=Pack(padding_bottom=10, width=200), on_change=self.refresh_day_view
        )
        self.main_box.add(self.date_picker)

        # open the daily log view for the chosen date
        self.open_day_view()
        self.main_box.add(self.day_box)

        self.show_main_content()

    def destroy(self, w):
        self.data_manager.destroy()

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
        self.logs_box = toga.Box(style=Pack(direction=ROW, padding_top=10))
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
            exercise_id = row[1]
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

            self.logs_box.add(toga.Label(f"{exercise_name} > sets: {sets_val} |", id=f"{id}", style=Pack(padding_right=5)))
            self.logs_box.add(toga.Label("reps: ", style=Pack(padding_right=5),))
            self.logs_box.add(toga.TextInput(style=Pack(padding_right=5),
                        on_change=self.save_exercise_reps, value=str(reps_list), id=f"{id}_reps"))
            self.logs_box.add(toga.Label(f"| Units: {units_val}",style=Pack(padding_right=5)))
            self.logs_box.add(toga.Label(f"| total: {total_val:.2f} | weight ", style=Pack(padding_right=5)))
            self.logs_box.add(toga.NumberInput(style=Pack(padding_right=5, width=30),
                        min=0, max=300, on_change=self.save_exercise_weight, value=weight_val, id=f"{id}_weight"))
            self.logs_box.add(toga.Label("kg"))
            self.logs_box.add(toga.Button(" - ", on_press=self.remove_exercise_from_log, id=f"{id}_remove"))
            self.logs_box.add(toga.Button("Progress", on_press=self.show_progress, id=f"{exercise_id}_progress"))

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

        # Create input fields for reps, weight, and unit selection
        row = toga.Box(style=Pack(direction=ROW, padding_bottom=10))

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
            reps=reps_list,
            weight=weight_val,
            units=units_val,
            date=self.date_picker.value,
        )

        # Close the detail window and refresh the day view logs
        self.show_main_content()
        self.refresh_day_logs()

    # --- CANVAS (DATA DISPLAY) ---

    def show_progress(self, widget):
        """Displays the chart in a new window"""
        data = self.data_manager.fetch_exercise_totals_over_time(int(widget.id.split("_")[0]))
        totals, dates = zip(*data)
    
        self.draw_chart(list(dates), list(totals))
        # Create new box with back button
        canvas_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        canvas_box.add(self.canvas)
        back_btn = toga.Button("Go Back", on_press=self.show_main_content, style=Pack(padding=10))
        canvas_box.add(back_btn)

        self.show_content(canvas_box)

    def draw_chart(self, x_data, y_data: list[int]):
        """Draws a smooth line chart with dots"""

        context = self.canvas.context
        width, height = self.main_window.size
        c_margin_x = 40
        c_margin_y_top = 30
        c_margin_y_bottom = 130

        coords_origin = (c_margin_x, height - c_margin_y_bottom)

        graph_line_x_coords = (width - c_margin_x, height - c_margin_y_bottom)
        graph_line_y_coords = (c_margin_x, c_margin_y_top)
        grid_lines = len(x_data)

        # Margin between data points
        margin_data_x = int((width - 3*c_margin_x) / grid_lines)
        margin_lines_y = int((height - c_margin_y_top - c_margin_y_bottom)/ 5)

        initial_margin_data_x = c_margin_x + 20
        initial_margin_data_y = c_margin_y_bottom + 20

        # Get min/max values for scaling
        max_total = max(y_data) + 10
        min_total = min(y_data) - 5


        # Draw graph lines X & Y axis
        context.line_width = 2
        context.move_to(graph_line_x_coords[0], graph_line_x_coords[1])
        context.line_to(coords_origin[0], coords_origin[1])  # Y-axis
        context.line_to(graph_line_y_coords[0], graph_line_y_coords[1])  # X-axis
        context.stroke(color="black")
        
        # Draw vertical grid lines
        x_lines_pos = []
        context.line_width = 1
        for i in range(grid_lines):
            x = i*margin_data_x + initial_margin_data_x
            context.move_to(x, c_margin_y_top + 10)
            context.line_to(x, height - c_margin_y_bottom)
            context.stroke(color=GRAY)
            x_lines_pos.append(x)

        # Draw horizontal grid lines
        for j in range(5):
            y = c_margin_y_top + j * margin_lines_y + 15
            context.move_to(c_margin_x, y)
            context.line_to(width - c_margin_x - 10, y)
            context.stroke(color=GRAY)

        # Bound for data point to be in the graph
        data_margin_top = c_margin_y_top + 15
        data_margin_bottom = height - c_margin_y_bottom - 15

        # Draw points
        total_range = (max_total - min_total)
        points_coords = []
        for i in range(len(y_data)):
            y = (y_data[i] - min_total) / total_range # 0...1 range
            y = y*data_margin_bottom + data_margin_top 
            context.arc(x_lines_pos[i], y, 5, 0, 360)
            context.fill(color=BLUE)
            points_coords.append([x_lines_pos[i], y])

        # Draw lines connecting the dots
        context.move_to(points_coords[0][0], points_coords[0][1])
        for i in range(1, len(y_data)):
            context.line_to(points_coords[i][0], points_coords[i][1])
            
        context.stroke(color=BLUE)

    def _load_styles(self):
         # Define a style for the main container (Box) with a dark background.
        self.box_style_column = Pack(
            background_color=self.DARK_BACKGROUND,
            padding=10,
            alignment="center",
            direction=COLUMN
        )
        self.box_style_row = Pack(
            background_color=self.DARK_BACKGROUND,
            padding=20,
            alignment="center",
            direction=ROW
        )
        
        # Create a label with dark theme style.
        self.label_style = Pack(
            color=self.DARK_FOREGROUND,
            background_color=self.DARK_BACKGROUND,
            font_size=16,
            padding=10,
        )
        
        # Create a button with a dark background and an accent-colored border.
        self.button_style = Pack(
            background_color=self.ACCENT_COLOR,
            color=self.BUTTON_TEXT_COLOR,
            padding=10,
            font_size=14,
        )


def main():
    return TrainingApp("Training Tracker", "org.example.trainingtracker")


if __name__ == "__main__":
    main().main_loop()
