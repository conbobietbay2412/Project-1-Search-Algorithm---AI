import random
from collections import deque
from Constants import WATER_COST


def bfs_path_exists(grid, start, goal, rows, cols):
    visited = {start}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            return True
        r, c = cur
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] != 0 and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    q.append((nr, nc))
    return False


def carve_path(grid, start, goal, rows, cols):
    parent = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        r, c = cur
        neighbors = [(-1,0),(1,0),(0,-1),(0,1)]
        random.shuffle(neighbors)
        for dr, dc in neighbors:
            nr, nc = r+dr, c+dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr,nc) not in parent:
                parent[(nr,nc)] = cur
                q.append((nr,nc))
    node = goal
    while node is not None:
        r, c = node
        if grid[r][c] == 0:
            grid[r][c] = random.randint(1, 9)
        node = parent.get(node)


def generate_random_map(rows, cols, sp, gp):
    # 1. Base terrain
    grid = [
        [0 if random.random() < 0.25 else random.randint(1, 9)
         for _ in range(cols)]
        for _ in range(rows)
    ]

    # 2. Carve water river — a vertical column roughly midway between start & goal
    #    The river spans a contiguous vertical column; 1–2 random rows are left
    #    as ground (gaps) to keep a path possible.
    col_start = sp[1]
    col_goal  = gp[1]
    if col_start > col_goal:
        col_start, col_goal = col_goal, col_start

    # Pick river column somewhere between the two halves
    if col_goal - col_start >= 4:
        river_col = random.randint(col_start + 2, col_goal - 2)
    else:
        # cols too close — put river in the middle of the whole grid
        river_col = cols // 2

    # Decide gaps (1 or 2 ground rows) — keep them away from the very top/bottom
    num_gaps = random.randint(1, 2)
    possible_gap_rows = list(range(1, rows - 1))
    gap_rows = set(random.sample(possible_gap_rows, min(num_gaps, len(possible_gap_rows))))

    for r in range(rows):
        if r in gap_rows:
            # leave as ground
            grid[r][river_col] = random.randint(1, 9)
        else:
            grid[r][river_col] = WATER_COST

    # 3. Ensure start & goal are open (ground)
    grid[sp[0]][sp[1]] = 1
    grid[gp[0]][gp[1]] = 1

    # 4. Guarantee path exists (water cells ARE passable, just expensive)
    if not bfs_path_exists(grid, sp, gp, rows, cols):
        carve_path(grid, sp, gp, rows, cols)

    return grid


def validate_positions(grid, sp, gp, rows, cols):
    if sp is None or gp is None:
        return "⚠  Start / Goal không hợp lệ — định dạng phải là  hàng,cột"
    if sp == gp:
        return "⚠  Start và Goal không được trùng nhau"
    r0, c0 = sp; r1, c1 = gp
    msgs = []
    if grid[r0][c0] == 0:
        msgs.append(f"START ({r0},{c0}) đang nằm trên tường!")
    if grid[r1][c1] == 0:
        msgs.append(f"GOAL  ({r1},{c1}) đang nằm trên tường!")
    if msgs:
        return "⚠  " + "   |   ".join(msgs) + "\n   → Hãy đổi vị trí hoặc nhấn RANDOM MAP."
    if not bfs_path_exists(grid, sp, gp, rows, cols):
        return (f"⚠  Không tồn tại đường đi từ ({r0},{c0}) → ({r1},{c1}).\n"
                f"   → Nhấn RANDOM MAP để tạo bản đồ mới.")
    return ""


def get_run_grid(grid, weight_mode):
    if weight_mode == "weighted":
        return grid
    # Unweighted: đất liền = 1, tường = 0, nước vẫn giữ cost cao (1) để UCS tránh
    return [
        [0 if cell == 0 else (1 if cell == WATER_COST else 1)
         for cell in row]
        for row in grid
    ]