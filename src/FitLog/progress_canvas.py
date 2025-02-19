import toga
from toga.colors import GRAY, BLUE


class ProgressCanvas(toga.Canvas):

    def __init__(self, x_data, y_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_data = x_data
        self.y_data = y_data
        self.on_draw = self.draw_chart

    def draw_chart(self, canvas, context):
        """Draws a smooth line chart with dots"""

        width, height = canvas.size
        margin = 50  # Space around the graph

        graph_width = width - 2 * margin
        graph_height = height - 2 * margin

        # Get min/max values for scaling
        max_total = max(self.x_data) if self.x_data else 1
        min_total = min(self.x_data) if self.x_data else 0
        total_range = max_total - min_total or 1

        # X-axis scaling
        def scale_x(i):
            return margin + (i / (len(self.y_data) - 1)) * graph_width

        # Y-axis scaling (invert because 0 is at the top)
        def scale_y(value):
            return height - margin - ((value - min_total) / total_range) * graph_height

        # Draw vertical grid lines
        context.stroke_color = GRAY
        context.line_width = 1
        for i in range(len(self.y_data)):
            x = scale_x(i)
            context.move_to(x, margin)
            context.line_to(x, height - margin)
            context.stroke_path()

        # Draw horizontal grid lines
        for j in range(5):
            y = margin + j * (graph_height / 5)
            context.move_to(margin, y)
            context.line_to(width - margin, y)
            context.stroke_path()

        # Draw X & Y axis
        context.stroke_color = "black"
        context.line_width = 2
        context.move_to(margin, margin)
        context.line_to(margin, height - margin)  # Y-axis
        context.line_to(width - margin, height - margin)  # X-axis
        context.stroke_path()

        # Draw the line chart
        context.stroke_color = BLUE
        context.line_width = 3
        context.move_to(scale_x(0), scale_y(self.x_data[0]))

        for i in range(1, len(self.x_data)):
            context.line_to(scale_x(i), scale_y(self.x_data[i]))

        context.stroke_path()

        # Draw points
        for i in range(len(self.x_data)):
            x, y = scale_x(i), scale_y(self.x_data[i])
            context.arc(x, y, 5, 0, 360)
            context.fill_color = BLUE
            context.fill_path()