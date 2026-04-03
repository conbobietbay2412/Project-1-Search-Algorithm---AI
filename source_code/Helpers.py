"""
Search_function.py
========================
Tổng hợp 8 thuật toán tìm kiếm đường đi trên lưới có trọng số.

Quy ước lưới:
    - 0          : tường (không thể đi qua)
    - 1..N       : ô đi được, giá trị = chi phí bước chân

Định dạng trả về thống nhất (SearchResult dict):
    {
        "found"          : bool,        # Tìm thấy đường hay không
        "path"           : list[tuple], # Danh sách ô [(r,c), ...] start→goal, [] nếu không tìm thấy
        "visited_order"  : list[tuple], # Thứ tự duyệt (dùng cho animation GUI)
        "nodes_explored" : int,         # Số nút đã duyệt
        "path_length"    : int,         # Số ô trên đường đi (kể cả start)
        "path_cost"      : int|float,   # Tổng chi phí đường đi (không tính chi phí ô start)
        "time_ms"        : float,       # Thời gian thực thi (ms)
    }
"""

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # Lên, Xuống, Trái, Phải


def get_neighbors(maze: list, row: int, col: int) -> list:
    """
    Lấy các ô hàng xóm có thể đi được từ ô (row, col).
    Returns: list[(next_row, next_col, step_cost)]
    """
    num_rows = len(maze)
    num_cols = len(maze[0])
    result   = []
    for dr, dc in DIRECTIONS:
        next_row = row + dr
        next_col = col + dc
        if 0 <= next_row < num_rows and 0 <= next_col < num_cols:
            if maze[next_row][next_col] != 0:
                step_cost = maze[next_row][next_col]
                result.append((next_row, next_col, step_cost))
    return result


def reconstruct_path(parent: dict, start: tuple, goal: tuple) -> list:
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = parent.get(node)
    path.reverse()
    if path and path[0] != start:
        return []
    return path


def heuristic(pos: tuple, goal: tuple) -> int:
    """Manhattan distance heuristic. Returns: int"""
    return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])


def calc_path_cost(path: list, grid: list) -> int:
    total = 0
    for r, c in path[1:]:
        total += grid[r][c]
    return total


# TIỆN ÍCH IN / HIỂN THỊ
# =============================================================================
def print_grid_with_path(grid: list, path: list) -> None:
    path_set = set(path)
    for r, row in enumerate(grid):
        row_str = []
        for c, val in enumerate(row):
            if (r, c) in path_set:
                row_str.append(" * ")
            elif val == 0:
                row_str.append(" # ")
            else:
                row_str.append(f"{val:2d} ")
        print("".join(row_str))


def print_comparison_table(results: dict) -> None:
    header = (f"{'Thuat toan':<18} | {'Tim thay':<8} | {'Nut duyet':<10} | "
              f"{'Do dai path':<11} | {'Chi phi':<8} | {'Thoi gian (ms)':<14}")
    sep = "=" * len(header)
    print("\n" + sep)
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        found = "v" if r["found"] else "x"
        print(f"{name:<18} | {found:<8} | {r['nodes_explored']:<10} | "
              f"{r['path_length']:<11} | {r['path_cost']:<8} | {r['time_ms']:<14.4f}")
    print(sep)