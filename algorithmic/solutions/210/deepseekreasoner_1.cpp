#include <bits/stdc++.h>
using namespace std;

const int INF = 1e9;

enum class State { IDLE_AT_BASE, MOVING_TO_TARGET, ATTACKING, RETURNING };

struct Point {
    int x, y;
    Point(int x = 0, int y = 0) : x(x), y(y) {}
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

namespace std {
    template <>
    struct hash<Point> {
        size_t operator()(const Point& p) const {
            return p.x * 1000 + p.y;
        }
    };
}

struct Base {
    int x, y;
    int fuel_supply;
    int missile_supply;
    int defense;      // for red bases only
    int value;        // for red bases only
    bool destroyed;   // for red bases only
    vector<Point> attack_positions; // for red bases only
};

struct Fighter {
    int id;
    Point pos;
    int fuel;
    int missiles;
    int capacity_fuel;
    int capacity_missiles;
    State state;
    int target_red_base; // index in red_bases
    Point target_pos;
    vector<Point> path;
    int path_index;
};

int n, m;
vector<vector<int>> cell_type;      // 0: neutral, 1: blue base, 2: red base
vector<vector<int>> blue_base_id;   // -1 if not a blue base
vector<vector<int>> red_base_id;    // -1 if not a red base
vector<Base> blue_bases;
vector<Base> red_bases;
vector<Fighter> fighters;
vector<int> attackable_reds;        // indices of red bases that can be attacked
int current_target_idx = 0;

// Directions: 0-up, 1-down, 2-left, 3-right
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

bool in_bounds(int x, int y) {
    return 0 <= x && x < n && 0 <= y && y < m;
}

bool is_undestroyed_red_base(int x, int y) {
    if (!in_bounds(x, y)) return false;
    if (cell_type[x][y] == 2) {
        int id = red_base_id[x][y];
        if (id >= 0 && !red_bases[id].destroyed)
            return true;
    }
    return false;
}

bool is_blue_base_cell(int x, int y) {
    return in_bounds(x, y) && cell_type[x][y] == 1;
}

bool is_adjacent(const Point& a, const Point& b) {
    return abs(a.x - b.x) + abs(a.y - b.y) == 1;
}

int get_direction(const Point& from, const Point& to) {
    if (to.x == from.x - 1) return 0;
    if (to.x == from.x + 1) return 1;
    if (to.y == from.y - 1) return 2;
    if (to.y == from.y + 1) return 3;
    return -1;
}

int get_direction_toward(const Point& from, const Point& to) {
    return get_direction(from, to);
}

vector<Point> BFS(const Point& start, const Point& target, bool avoid_red) {
    if (start == target) return {};
    vector<vector<Point>> parent(n, vector<Point>(m, Point(-1, -1)));
    vector<vector<bool>> visited(n, vector<bool>(m, false));
    queue<Point> q;
    q.push(start);
    visited[start.x][start.y] = true;

    while (!q.empty()) {
        Point cur = q.front(); q.pop();
        if (cur == target) {
            vector<Point> path;
            Point p = cur;
            while (!(p == start)) {
                path.push_back(p);
                p = parent[p.x][p.y];
            }
            reverse(path.begin(), path.end());
            return path;
        }
        for (int d = 0; d < 4; ++d) {
            int nx = cur.x + dx[d];
            int ny = cur.y + dy[d];
            if (!in_bounds(nx, ny)) continue;
            if (visited[nx][ny]) continue;
            if (avoid_red && is_undestroyed_red_base(nx, ny)) continue;
            visited[nx][ny] = true;
            parent[nx][ny] = cur;
            q.push(Point(nx, ny));
        }
    }
    return {};
}

vector<Point> BFS_to_nearest_blue(const Point& start) {
    if (is_blue_base_cell(start.x, start.y)) return {};
    vector<vector<Point>> parent(n, vector<Point>(m, Point(-1, -1)));
    vector<vector<bool>> visited(n, vector<bool>(m, false));
    queue<Point> q;
    q.push(start);
    visited[start.x][start.y] = true;

    while (!q.empty()) {
        Point cur = q.front(); q.pop();
        if (is_blue_base_cell(cur.x, cur.y)) {
            vector<Point> path;
            Point p = cur;
            while (!(p == start)) {
                path.push_back(p);
                p = parent[p.x][p.y];
            }
            reverse(path.begin(), path.end());
            return path;
        }
        for (int d = 0; d < 4; ++d) {
            int nx = cur.x + dx[d];
            int ny = cur.y + dy[d];
            if (!in_bounds(nx, ny)) continue;
            if (visited[nx][ny]) continue;
            if (is_undestroyed_red_base(nx, ny)) continue;
            visited[nx][ny] = true;
            parent[nx][ny] = cur;
            q.push(Point(nx, ny));
        }
    }
    return {};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read grid size
    cin >> n >> m;
    cell_type.assign(n, vector<int>(m, 0));
    blue_base_id.assign(n, vector<int>(m, -1));
    red_base_id.assign(n, vector<int>(m, -1));

    // Read grid (we ignore the characters because base positions are given separately)
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
    }

    // Read blue bases
    int num_blue;
    cin >> num_blue;
    blue_bases.resize(num_blue);
    for (int i = 0; i < num_blue; ++i) {
        int x, y;
        cin >> x >> y;
        int g, c, d, v;
        cin >> g >> c >> d >> v;
        blue_bases[i] = {x, y, g, c, 0, 0, false, {}};
        cell_type[x][y] = 1;
        blue_base_id[x][y] = i;
    }

    // Read red bases
    int num_red;
    cin >> num_red;
    red_bases.resize(num_red);
    for (int i = 0; i < num_red; ++i) {
        int x, y;
        cin >> x >> y;
        int g, c, d, v;
        cin >> g >> c >> d >> v;
        red_bases[i] = {x, y, 0, 0, d, v, false, {}};
        cell_type[x][y] = 2;
        red_base_id[x][y] = i;
    }

    // Compute attack positions for each red base
    for (int i = 0; i < num_red; ++i) {
        Base& rb = red_bases[i];
        for (int d = 0; d < 4; ++d) {
            int nx = rb.x + dx[d];
            int ny = rb.y + dy[d];
            if (in_bounds(nx, ny) && cell_type[nx][ny] != 2) {
                rb.attack_positions.emplace_back(nx, ny);
            }
        }
        if (!rb.attack_positions.empty()) {
            attackable_reds.push_back(i);
        }
    }

    // Sort attackable red bases by value/defense ratio (descending)
    sort(attackable_reds.begin(), attackable_reds.end(), [&](int a, int b) {
        double r1 = (double)red_bases[a].value / red_bases[a].defense;
        double r2 = (double)red_bases[b].value / red_bases[b].defense;
        if (abs(r1 - r2) > 1e-9) return r1 > r2;
        return red_bases[a].value > red_bases[b].value;
    });

    // Read fighters
    int k;
    cin >> k;
    fighters.resize(k);
    for (int i = 0; i < k; ++i) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {i, Point(x, y), 0, 0, G, C, State::IDLE_AT_BASE, -1, Point(), {}, 0};
    }

    // Simulation loop
    const int MAX_FRAMES = 15000;
    for (int frame = 0; frame < MAX_FRAMES; ++frame) {
        vector<string> commands;

        // Phase 1: Process non-idle fighters
        for (Fighter& f : fighters) {
            if (f.state == State::IDLE_AT_BASE) {
                continue;
            }

            if (f.state == State::MOVING_TO_TARGET) {
                if (f.target_red_base >= 0 && red_bases[f.target_red_base].destroyed) {
                    f.state = State::RETURNING;
                    f.path = BFS_to_nearest_blue(f.pos);
                    f.path_index = 0;
                    continue;
                }
                if (f.pos == f.target_pos) {
                    f.state = State::ATTACKING;
                    continue;
                }
                if (f.path_index < f.path.size()) {
                    Point next = f.path[f.path_index];
                    if (f.fuel > 0 && !is_undestroyed_red_base(next.x, next.y)) {
                        int dir = get_direction(f.pos, next);
                        commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.pos = next;
                        f.fuel--;
                        f.path_index++;
                    } else {
                        f.state = State::RETURNING;
                        f.path = BFS_to_nearest_blue(f.pos);
                        f.path_index = 0;
                    }
                } else {
                    f.state = State::RETURNING;
                    f.path = BFS_to_nearest_blue(f.pos);
                    f.path_index = 0;
                }
            }

            else if (f.state == State::ATTACKING) {
                if (f.target_red_base < 0 || red_bases[f.target_red_base].destroyed) {
                    f.state = State::RETURNING;
                    f.path = BFS_to_nearest_blue(f.pos);
                    f.path_index = 0;
                    continue;
                }
                Base& rb = red_bases[f.target_red_base];
                if (!is_adjacent(f.pos, Point(rb.x, rb.y))) {
                    f.state = State::RETURNING;
                    f.path = BFS_to_nearest_blue(f.pos);
                    f.path_index = 0;
                    continue;
                }
                if (f.missiles > 0 && rb.defense > 0) {
                    int fire_count = min(f.missiles, rb.defense);
                    int dir = get_direction_toward(f.pos, Point(rb.x, rb.y));
                    commands.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(fire_count));
                    f.missiles -= fire_count;
                    rb.defense -= fire_count;
                    if (rb.defense <= 0) {
                        rb.destroyed = true;
                    }
                } else {
                    f.state = State::RETURNING;
                    f.path = BFS_to_nearest_blue(f.pos);
                    f.path_index = 0;
                }
            }

            else if (f.state == State::RETURNING) {
                if (is_blue_base_cell(f.pos.x, f.pos.y)) {
                    f.state = State::IDLE_AT_BASE;
                    continue;
                }
                if (f.path_index < f.path.size()) {
                    Point next = f.path[f.path_index];
                    if (f.fuel > 0 && !is_undestroyed_red_base(next.x, next.y)) {
                        int dir = get_direction(f.pos, next);
                        commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.pos = next;
                        f.fuel--;
                        f.path_index++;
                    } else {
                        f.path = BFS_to_nearest_blue(f.pos);
                        f.path_index = 0;
                    }
                } else {
                    f.path = BFS_to_nearest_blue(f.pos);
                    f.path_index = 0;
                    if (f.path.empty()) {
                        f.state = State::IDLE_AT_BASE;
                    }
                }
            }
        }

        // Phase 2: Assign idle fighters to current target
        while (current_target_idx < attackable_reds.size() &&
               red_bases[attackable_reds[current_target_idx]].destroyed) {
            current_target_idx++;
        }

        if (current_target_idx < attackable_reds.size()) {
            int target_rb_idx = attackable_reds[current_target_idx];
            Base& target_rb = red_bases[target_rb_idx];

            for (Fighter& f : fighters) {
                if (f.state != State::IDLE_AT_BASE) continue;
                // Must be on a blue base
                int base_id = blue_base_id[f.pos.x][f.pos.y];
                if (base_id < 0) continue;

                // Find nearest reachable attack position
                Point best_pos;
                int best_dist = INF;
                vector<Point> best_path;
                for (const Point& ap : target_rb.attack_positions) {
                    vector<Point> path = BFS(f.pos, ap, true);
                    if (!path.empty() && (int)path.size() < best_dist) {
                        best_dist = path.size();
                        best_pos = ap;
                        best_path = path;
                    }
                }
                if (best_dist == INF) continue;

                // Compute return path to nearest blue base
                vector<Point> return_path = BFS_to_nearest_blue(best_pos);
                if (return_path.empty()) continue;

                int total_fuel_needed = best_dist + return_path.size();
                if (total_fuel_needed > f.capacity_fuel) continue;

                int missiles_needed = min(f.capacity_missiles, target_rb.defense);
                Base& base = blue_bases[base_id];

                // Load fuel
                int fuel_to_load = min(total_fuel_needed, f.capacity_fuel) - f.fuel;
                if (fuel_to_load > 0) {
                    int take_fuel = min(fuel_to_load, base.fuel_supply);
                    if (take_fuel > 0) {
                        commands.push_back("fuel " + to_string(f.id) + " " + to_string(take_fuel));
                        f.fuel += take_fuel;
                        base.fuel_supply -= take_fuel;
                    }
                }
                // Load missiles
                int missiles_to_load = missiles_needed - f.missiles;
                if (missiles_to_load > 0) {
                    int take_missiles = min(missiles_to_load, base.missile_supply);
                    if (take_missiles > 0) {
                        commands.push_back("missile " + to_string(f.id) + " " + to_string(take_missiles));
                        f.missiles += take_missiles;
                        base.missile_supply -= take_missiles;
                    }
                }

                if (f.fuel > 0) {
                    f.state = State::MOVING_TO_TARGET;
                    f.target_red_base = target_rb_idx;
                    f.target_pos = best_pos;
                    f.path = best_path;
                    f.path_index = 0;

                    // Move first step now if possible
                    if (!best_path.empty()) {
                        Point next = best_path[0];
                        if (f.fuel > 0 && !is_undestroyed_red_base(next.x, next.y)) {
                            int dir = get_direction(f.pos, next);
                            commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.pos = next;
                            f.fuel--;
                            f.path_index = 1;
                        }
                    }
                }
            }
        }

        // Output commands for this frame
        for (const string& cmd : commands) {
            cout << cmd << "\n";
        }
        cout << "OK" << endl;

        // Check if all attackable red bases are destroyed
        bool all_destroyed = true;
        for (int idx : attackable_reds) {
            if (!red_bases[idx].destroyed) {
                all_destroyed = false;
                break;
            }
        }
        if (all_destroyed) {
            break;
        }
    }

    return 0;
}