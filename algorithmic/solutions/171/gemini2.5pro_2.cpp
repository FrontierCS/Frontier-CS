#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

const int INF = 1e9;

struct Pos {
    int r, c;

    bool operator==(const Pos& other) const {
        return r == other.r && c == other.c;
    }
     bool operator!=(const Pos& other) const {
        return !(*this == other);
    }
};

int N, M;
vector<vector<bool>> grid;
Pos current_pos;
vector<pair<char, char>> solution;

// Directions: Up, Down, Left, Right
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char d_chars[] = {'U', 'D', 'L', 'R'};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

struct PathNode {
    Pos prev_pos;
    char action_type;
    char direction_char;
};

// Forward BFS from start_pos. Returns distances and predecessors map.
pair<vector<vector<int>>, vector<vector<PathNode>>> bfs(const Pos& start_pos, const vector<vector<bool>>& current_grid) {
    vector<vector<int>> dist(N, vector<int>(N, INF));
    vector<vector<PathNode>> parent(N, vector<PathNode>(N));
    queue<Pos> q;

    dist[start_pos.r][start_pos.c] = 0;
    q.push(start_pos);

    while (!q.empty()) {
        Pos curr = q.front();
        q.pop();

        // Moves
        for (int i = 0; i < 4; ++i) {
            Pos next = {curr.r + dr[i], curr.c + dc[i]};
            if (is_valid(next.r, next.c) && !current_grid[next.r][next.c] && dist[next.r][next.c] == INF) {
                dist[next.r][next.c] = dist[curr.r][curr.c] + 1;
                parent[next.r][next.c] = {curr, 'M', d_chars[i]};
                q.push(next);
            }
        }

        // Slides
        for (int i = 0; i < 4; ++i) {
            Pos runner = curr;
            while (true) {
                Pos next_runner = {runner.r + dr[i], runner.c + dc[i]};
                if (!is_valid(next_runner.r, next_runner.c) || current_grid[next_runner.r][next_runner.c]) {
                    break;
                }
                runner = next_runner;
            }
            if (runner != curr) {
                if (dist[runner.r][runner.c] == INF) {
                    dist[runner.r][runner.c] = dist[curr.r][curr.c] + 1;
                    parent[runner.r][runner.c] = {curr, 'S', d_chars[i]};
                    q.push(runner);
                }
            }
        }
    }
    return {dist, parent};
}

// Backward BFS from end_pos. Returns distances and successors map.
pair<vector<vector<int>>, vector<vector<PathNode>>> bbfs(const Pos& end_pos, const vector<vector<bool>>& current_grid) {
    vector<vector<int>> dist(N, vector<int>(N, INF));
    vector<vector<PathNode>> parent(N, vector<PathNode>(N));
    queue<Pos> q;

    dist[end_pos.r][end_pos.c] = 0;
    q.push(end_pos);

    while (!q.empty()) {
        Pos curr = q.front();
        q.pop();

        // Moves (reversed)
        for (int i = 0; i < 4; ++i) {
            Pos prev = {curr.r - dr[i], curr.c - dc[i]};
            if (is_valid(prev.r, prev.c) && !current_grid[prev.r][prev.c] && dist[prev.r][prev.c] == INF) {
                dist[prev.r][prev.c] = dist[curr.r][curr.c] + 1;
                parent[prev.r][prev.c] = {curr, 'M', d_chars[i]};
                q.push(prev);
            }
        }

        // Slides (reversed)
        for (int i = 0; i < 4; ++i) {
            Pos stopper = {curr.r + dr[i], curr.c + dc[i]};
            if (!is_valid(stopper.r, stopper.c) || current_grid[stopper.r][stopper.c]) {
                Pos runner = {curr.r - dr[i], curr.c - dc[i]};
                while (is_valid(runner.r, runner.c) && !current_grid[runner.r][runner.c]) {
                    if (dist[runner.r][runner.c] == INF) {
                        dist[runner.r][runner.c] = dist[curr.r][curr.c] + 1;
                        parent[runner.r][runner.c] = {curr, 'S', d_chars[i]};
                        q.push(runner);
                    }
                    runner = {runner.r - dr[i], runner.c - dc[i]};
                }
            }
        }
    }
    return {dist, parent};
}

void execute_path_from_pred(const Pos& start, const Pos& end, const vector<vector<PathNode>>& parent) {
    if (start == end) return;
    vector<pair<char, char>> path;
    Pos curr = end;
    while (curr != start) {
        PathNode p = parent[curr.r][curr.c];
        path.push_back({p.action_type, p.direction_char});
        curr = p.prev_pos;
    }
    reverse(path.begin(), path.end());
    for (const auto& p : path) {
        solution.push_back(p);
    }
}

void execute_path_from_succ(const Pos& start, const Pos& end, const vector<vector<PathNode>>& parent) {
    if (start == end) return;
    Pos curr = start;
    while(curr != end) {
        PathNode p = parent[curr.r][curr.c];
        solution.push_back({p.action_type, p.direction_char});
        curr = p.next_pos;
    }
}

void execute_alter(const Pos& from, const Pos& block_pos) {
    char dir = ' ';
    if (block_pos.r == from.r - 1) dir = 'U';
    else if (block_pos.r == from.r + 1) dir = 'D';
    else if (block_pos.c == from.c - 1) dir = 'L';
    else if (block_pos.c == from.c + 1) dir = 'R';
    solution.push_back({'A', dir});
    grid[block_pos.r][block_pos.c] = !grid[block_pos.r][block_pos.c];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;
    vector<Pos> all_points(M);
    for (int i = 0; i < M; ++i) {
        cin >> all_points[i].r >> all_points[i].c;
    }

    grid.assign(N, vector<bool>(N, false));
    current_pos = all_points[0];

    for (int k = 0; k < M - 1; ++k) {
        Pos start_node = current_pos;
        Pos target_node = all_points[k+1];

        auto [dist_from_start, parent_from_start] = bfs(start_node, grid);
        int best_cost = dist_from_start[target_node.r][target_node.c];
        
        char best_plan_type = 'N';
        Pos best_block_pos = {-1, -1}, best_neighbor_pos = {-1, -1};
        vector<vector<PathNode>> best_path2_parent;

        auto find_best_alter = [&](bool place_mode) {
            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (grid[r][c] == place_mode) continue;

                    Pos block_pos = {r, c};
                    
                    for (int i = 0; i < 4; ++i) {
                        Pos neighbor = {r + dr[i], c + dc[i]};
                        if (is_valid(neighbor.r, neighbor.c) && dist_from_start[neighbor.r][neighbor.c] != INF) {
                            vector<vector<bool>> temp_grid = grid;
                            temp_grid[r][c] = place_mode;
                            auto [dist_to_end, parent_to_end] = bbfs(target_node, temp_grid);
                            
                            if (dist_to_end[neighbor.r][neighbor.c] == INF) continue;
                            
                            int current_cost = dist_from_start[neighbor.r][neighbor.c] + 1 + dist_to_end[neighbor.r][neighbor.c];
                            if (current_cost < best_cost) {
                                best_cost = current_cost;
                                best_plan_type = place_mode ? 'P' : 'R';
                                best_block_pos = block_pos;
                                best_neighbor_pos = neighbor;
                                best_path2_parent = parent_to_end;
                            }
                        }
                    }
                }
            }
        };

        find_best_alter(true); // Place
        find_best_alter(false); // Remove

        if (best_plan_type == 'N') {
            execute_path_from_pred(start_node, target_node, parent_from_start);
            current_pos = target_node;
        } else {
            execute_path_from_pred(start_node, best_neighbor_pos, parent_from_start);
            current_pos = best_neighbor_pos;
            execute_alter(best_neighbor_pos, best_block_pos);
            execute_path_from_succ(best_neighbor_pos, target_node, best_path2_parent);
            current_pos = target_node;
        }
    }

    for (const auto& p : solution) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}