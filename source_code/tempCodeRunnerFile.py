def _draw_cell_state(self, node, state):
        """Redraw a single cell with a given state: normal/visited/path/current."""
        r, c = node
        try:
            start_pos = tuple(map(int, self.start_entry.get().split(",")))
            goal_pos  = tuple(map(int, self.goal_entry.get().split(",")))
        except Exception:
            start_pos = goal_pos = None

        # Compute position
        grid_w   = self.cols * self.cell_size
        grid_h   = self.rows * self.cell_size