import heapq
import sys
import time
from collections import deque
from typing import Optional
from Helpers import get_neighbors, reconstruct_path, heuristic, calc_path_cost, print_grid_with_path, print_comparison_table

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # Lên, Xuống, Trái, Phải




# =============================================================================
# 1. BFS - Breadth-First Search
# =============================================================================
def bfs(grid: list, start: tuple, goal: tuple) -> dict:
    start_time    = time.perf_counter()
    queue         = deque([start])
    came_from     = {start: None}
    visited_order = []

    while queue:
        current = queue.popleft()
        visited_order.append(current)

        if current == goal:
            path = reconstruct_path(came_from, start, goal)
            return {
                "found"         : True,
                "path"          : path,
                "visited_order" : visited_order,
                "nodes_explored": len(visited_order),
                "path_length"   : len(path),
                "path_cost"     : calc_path_cost(path, grid),
                "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
            }

        for (nr, nc, _cost) in get_neighbors(grid, *current):
            neighbor = (nr, nc)
            if neighbor not in came_from:
                came_from[neighbor] = current
                queue.append(neighbor)

    return {
        "found"         : False,
        "path"          : [],
        "visited_order" : visited_order,
        "nodes_explored": len(visited_order),
        "path_length"   : 0,
        "path_cost"     : 0,
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
    }


# =============================================================================
# 2. DFS - Depth-First Search
# =============================================================================
def dfs(maze: list, start: tuple, goal: tuple) -> dict:
    start_time = time.perf_counter()
    stack         = [start]
    visited       = set()
    parent        = {start: None}
    cost          = {start: 0}
    visited_order = []
    found         = False

    while stack:
        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)
        visited_order.append(current)

        if current == goal:
            found = True
            break

        row, col = current
        for next_row, next_col, step_cost in get_neighbors(maze, row, col):
            neighbor = (next_row, next_col)
            if neighbor not in visited:
                stack.append(neighbor)
                if neighbor not in parent:
                    parent[neighbor] = current
                    cost[neighbor]   = cost[current] + step_cost

    path = reconstruct_path(parent, start, goal) if found else []

    return {
        "found"         : found,
        "path"          : path,
        "visited_order" : visited_order,
        "nodes_explored": len(visited),
        "path_length"   : len(path),
        "path_cost"     : cost.get(goal, 0),
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
    }


# =============================================================================
# 3. UCS - Uniform Cost Search
# =============================================================================
def ucs(grid: list, start_pos: tuple, goal_pos: tuple) -> dict:
    start_time    = time.perf_counter()
    frontier      = [(0, start_pos)]
    came_from     = {start_pos: None}
    g_cost        = {start_pos: 0}
    explored      = set()
    visited_order = []

    while frontier:
        g, current = heapq.heappop(frontier)

        if current in explored:
            continue
        explored.add(current)
        visited_order.append(current)

        if current == goal_pos:
            path = reconstruct_path(came_from, start_pos, goal_pos)
            return {
                "found"         : True,
                "path"          : path,
                "visited_order" : visited_order,
                "nodes_explored": len(visited_order),
                "path_length"   : len(path),
                "path_cost"     : g_cost[goal_pos],
                "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
            }

        nx_row, nx_col = current
        for nr, nc, cost in get_neighbors(grid, nx_row, nx_col):
            neighbor = (nr, nc)
            new_g    = g + cost
            if neighbor not in explored and new_g < g_cost.get(neighbor, float("inf")):
                g_cost[neighbor]    = new_g
                came_from[neighbor] = current
                heapq.heappush(frontier, (new_g, neighbor))

    return {
        "found"         : False,
        "path"          : [],
        "visited_order" : visited_order,
        "nodes_explored": len(visited_order),
        "path_length"   : 0,
        "path_cost"     : 0,
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
    }


# =============================================================================
# 4. IDDFS - Iterative Deepening Depth-First Search
# =============================================================================
def _dls(grid: list, current: tuple, goal: tuple, depth: int,
         parent: dict, visited_in_path: set, visited_order: list) -> bool:
    
    visited_order.append(current)

    if current == goal:
        return True

    if depth <= 0:
        return False
    
    if current in _dls.reached and _dls.reached[current] >= depth:
        return False
    _dls.reached[current] = depth
    
    visited_in_path.add(current)
    r, c = current

    for nr, nc, _ in get_neighbors(grid, r, c):
        neighbor = (nr, nc)
        if neighbor not in visited_in_path:
            parent[neighbor] = current
            found = _dls(grid, neighbor, goal, depth - 1,
                         parent, visited_in_path, visited_order)
            if found:
                return True

    visited_in_path.discard(current)
    return False


def iddfs(grid: list, start_pos: tuple, goal_pos: tuple, max_depth: int = 200) -> dict:
    """
    Tìm đường bằng IDDFS — tăng dần giới hạn độ sâu từ 0 đến max_depth.
    visited_order tích lũy toàn bộ qua mọi iteration (dùng cho animation GUI).
    Returns: SearchResult dict
    """
    start_time    = time.perf_counter()
    visited_order = []

    for depth in range(max_depth + 1):
        parent          = {start_pos: None}
        
        visited_in_path = set()
        
        # visited_order.clear()
        
        _dls.reached = {}
        # ============================

        found = _dls(grid, start_pos, goal_pos, depth,
                     parent, visited_in_path, visited_order)
        if found:
            path = reconstruct_path(parent, start_pos, goal_pos)
            return {
                "found"         : True,
                "path"          : path,
                "visited_order" : visited_order,
                "nodes_explored": len(visited_order),
                "path_length"   : len(path),
                "path_cost"     : calc_path_cost(path, grid),
                "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
            }

    return {
        "found"         : False,
        "path"          : [],
        "visited_order" : visited_order,
        "nodes_explored": len(visited_order),
        "path_length"   : 0,
        "path_cost"     : 0,
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
    }


# =============================================================================
# 5. A* Search
# =============================================================================
def astar(grid: list, sx: int, sy: int, gx: int, gy: int) -> dict:
    start_time = time.perf_counter()
    n, m       = len(grid), len(grid[0])

    pq = []
    h0 = heuristic((sx, sy), (gx, gy))
    # Tuple: (f, h, g, x, y)
    # Tie-breaking: khi f bằng nhau → ưu tiên h nhỏ hơn (node gần goal hơn)
    # → A* đâm thẳng về goal thay vì mở rộng rộng ra hai bên
    heapq.heappush(pq, (h0, h0, 0, sx, sy))

    g_score         = [[float("inf")] * m for _ in range(n)]
    g_score[sx][sy] = 0

    parent        = {}
    visited_order = []
    closed        = set()

    while pq:
        f, _, g, x, y = heapq.heappop(pq)

        if (x, y) in closed:
            continue
        closed.add((x, y))
        visited_order.append((x, y))

        if (x, y) == (gx, gy):
            path = reconstruct_path(parent | {(sx, sy): None}, (sx, sy), (gx, gy))
            return {
                "found"         : True,
                "path"          : path,
                "visited_order" : visited_order,
                "nodes_explored": len(visited_order),
                "path_length"   : len(path),
                "path_cost"     : g,
                "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
            }

        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy

            if 0 <= nx < n and 0 <= ny < m and grid[nx][ny] != 0:
                new_g = g + grid[nx][ny]

                if new_g < g_score[nx][ny]:
                    g_score[nx][ny]  = new_g
                    parent[(nx, ny)] = (x, y)

                    h = heuristic((nx, ny), (gx, gy))
                    heapq.heappush(pq, (new_g + h, h, new_g, nx, ny))

    return {
        "found"         : False,
        "path"          : [],
        "visited_order" : visited_order,
        "nodes_explored": len(visited_order),
        "path_length"   : 0,
        "path_cost"     : 0,
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
    }


# =============================================================================
# 6. IDA* Search
#
# FIX: Bỏ biến visited (2D array) dùng set visited_in_path thay thế để tránh
#      conflict giữa các nhánh đệ quy. visited_order chỉ append bên trong
#      _dfs_idastar (không append start trước vòng while) để tránh thiếu/trùng.
#      Mỗi lần tăng threshold, start được append lại đúng 1 lần qua đệ quy.
# =============================================================================
def _dfs_idastar(grid: list, x: int, y: int, gx: int, gy: int,
                 g: int, threshold: int,
                 visited_in_path: set, path: list,
                 visited_order: list,
                 best_g: dict,
                 min_cost: int) -> tuple:
    """
    DFS có giới hạn f = g + h dùng cho IDA*.
    Returns: (min_exceeded_f, path_or_None)
    """
    visited_order.append((x, y))

    # heuristic scale theo min_cost
    h = heuristic((x, y), (gx, gy)) * min_cost
    f = g + h

    # vượt threshold
    if f > threshold:
        return f, None

    # tới goal
    if (x, y) == (gx, gy):
        return None, path.copy()

    # 🔥 PRUNING: đã tới node này với cost tốt hơn
    if (x, y) in best_g and best_g[(x, y)] <= g:
        return float("inf"), None
    best_g[(x, y)] = g

    min_next = float("inf")

    # 🔥 sort neighbor theo heuristic
    neighbors = []
    for dx, dy in DIRECTIONS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
            if grid[nx][ny] != 0 and (nx, ny) not in visited_in_path:
                h_val = heuristic((nx, ny), (gx, gy))
                neighbors.append((h_val, nx, ny))

    neighbors.sort()

    for _, nx, ny in neighbors:
        visited_in_path.add((nx, ny))
        path.append((nx, ny))

        t, res_path = _dfs_idastar(
            grid, nx, ny, gx, gy,
            g + grid[nx][ny], threshold,
            visited_in_path, path, visited_order,
            best_g, min_cost
        )

        if res_path is not None:
            return None, res_path

        if t < min_next:
            min_next = t

        path.pop()
        visited_in_path.discard((nx, ny))

    return min_next, None


def idastar(grid: list, sx: int, sy: int, gx: int, gy: int) -> dict:
    """
    Tìm đường tối ưu bằng IDA* (tiết kiệm bộ nhớ hơn A*).
    visited_order tích lũy toàn bộ qua mọi threshold (dùng cho animation GUI).
    """
    sys.setrecursionlimit(100000)

    start_time = time.perf_counter()

    # 🔥 tìm cost nhỏ nhất để scale heuristic
    min_cost = min(cell for row in grid for cell in row if cell > 0)

    threshold = heuristic((sx, sy), (gx, gy)) * min_cost
    visited_order = []

    while True:
        visited_in_path = {(sx, sy)}
        path = [(sx, sy)]
        best_g = {}   # 🔥 quan trọng

        t, res_path = _dfs_idastar(
            grid, sx, sy, gx, gy,
            0, threshold,
            visited_in_path, path, visited_order,
            best_g, min_cost
        )

        # tìm thấy
        if res_path is not None:
            cost = sum(grid[x][y] for x, y in res_path[1:])
            return {
                "found"         : True,
                "path"          : res_path,
                "visited_order" : visited_order,
                "nodes_explored": len(visited_order),
                "path_length"   : len(res_path),
                "path_cost"     : cost,
                "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
            }

        # không có đường
        if t == float("inf"):
            return {
                "found"         : False,
                "path"          : [],
                "visited_order" : visited_order,
                "nodes_explored": len(visited_order),
                "path_length"   : 0,
                "path_cost"     : 0,
                "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
            }

        # tăng threshold
        threshold = t

# =============================================================================
# 7. Bidirectional Search
# =============================================================================
def bidirectional(maze: list, start: tuple, goal: tuple) -> dict:
    start_time    = time.perf_counter()
    visited_order = []

    if start == goal:
        return {
            "found"         : True,
            "path"          : [start],
            "visited_order" : [start],
            "nodes_explored": 1,
            "path_length"   : 1,
            "path_cost"     : 0,
            "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
        }

    forward_queue   = deque([start])
    forward_parent  = {start: None}
    backward_queue  = deque([goal])
    backward_parent = {goal: None}
    meeting_node    = None
    found           = False

    while forward_queue and backward_queue:
        meeting_node = _expand_one_step(
            queue         = forward_queue,
            my_parent     = forward_parent,
            other_parent  = backward_parent,
            maze          = maze,
            visited_order = visited_order,
        )
        if meeting_node is not None:
            found = True
            break

        meeting_node = _expand_one_step(
            queue         = backward_queue,
            my_parent     = backward_parent,
            other_parent  = forward_parent,
            maze          = maze,
            visited_order = visited_order,
        )
        if meeting_node is not None:
            found = True
            break

    if found:
        path       = _merge_paths(forward_parent, backward_parent, meeting_node)
        total_cost = calc_path_cost(path, maze)
    else:
        path       = []
        total_cost = 0

    return {
        "found"         : found,
        "path"          : path,
        "visited_order" : visited_order,
        "nodes_explored": len(forward_parent) + len(backward_parent),
        "path_length"   : len(path),
        "path_cost"     : total_cost,
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
    }


def _expand_one_step(queue: deque, my_parent: dict, other_parent: dict,
                     maze: list, visited_order: list) -> Optional[tuple]:
    if not queue:
        return None
    current = queue.popleft()
    visited_order.append(current)
    row, col = current
    for next_row, next_col, _ in get_neighbors(maze, row, col):
        neighbor = (next_row, next_col)
        if neighbor not in my_parent:
            my_parent[neighbor] = current
            queue.append(neighbor)
            if neighbor in other_parent:
                return neighbor
    return None


def _merge_paths(forward_parent: dict, backward_parent: dict,
                 meeting_node: tuple) -> list:
    first_half = []
    node = meeting_node
    while node is not None:
        first_half.append(node)
        node = forward_parent[node]
    first_half.reverse()

    second_half = []
    node = backward_parent.get(meeting_node)
    while node is not None:
        second_half.append(node)
        node = backward_parent[node]

    return first_half + second_half


# =============================================================================
# 8. Beam Search
# =============================================================================
def beam_search(grid: list, start: tuple, goal: tuple, beam_width: int = 3) -> dict:
    start_time     = time.perf_counter()
    visited_order  = [start]
    came_from = {start: None}
    
    # Dùng dict để theo dõi chi phí g(n) nhỏ nhất từ start đến mỗi node
    g_score = {start: 0}
    
    # Beam bây giờ lưu trữ (node, current_g_cost)
    beam = [(start, 0)]

    while beam:
        next_candidates = []

        # Duyệt qua các node đang có trong beam hiện tại
        for current, current_g in beam:
            if current == goal:
                path = reconstruct_path(came_from, start, goal)
                return {
                    "found"         : True,
                    "path"          : path,
                    "visited_order" : visited_order,
                    "nodes_explored": len(visited_order),
                    "path_length"   : len(path),
                    "path_cost"     : current_g, # Chi phí thực tế g(n) để đến đích
                    "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
                    "beam_width"    : beam_width,
                }

            for (nr, nc, step_cost) in get_neighbors(grid, *current):
                neighbor = (nr, nc)
                
                # BỔ SUNG 2: Tính g(n) mới = g(n) hiện tại + chi phí bước đi
                new_g = current_g + step_cost 

                # Nếu neighbor chưa được khám phá HOẶC tìm được đường đi mới rẻ hơn
                if neighbor not in g_score or new_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = new_g
                    
                    # Tính h(n) và f(n)
                    h = heuristic(neighbor, goal)
                    f = new_g + h  # Tính f(n) = g(n) + h(n)
                    
                    # Thêm vào danh sách ứng viên (lưu f(n) để sắp xếp)
                    next_candidates.append((f, neighbor, new_g))

        if not next_candidates:
            break

        next_candidates.sort(key=lambda x: x[0])
        next_candidates = next_candidates[:beam_width]

        # Cập nhật beam cho bước lặp tiếp theo
        beam = []
        for _, node, node_g in next_candidates:
            # Ghi nhận thứ tự duyệt (chỉ ghi nhận khi node lọt vào top K)
            if node not in visited_order:
                visited_order.append(node)
            beam.append((node, node_g))

    return {
        "found"         : False,
        "path"          : [],
        "visited_order" : visited_order,
        "nodes_explored": len(visited_order),
        "path_length"   : 0,
        "path_cost"     : 0,
        "time_ms"       : round((time.perf_counter() - start_time) * 1000, 4),
        "beam_width"    : beam_width,
    }


