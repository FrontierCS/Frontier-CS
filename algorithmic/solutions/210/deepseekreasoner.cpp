#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
    bool operator==(const Point& other) const { return x == other.x && y == other.y; }
};

struct Cell {
    char type; // '#', '*', '.'
    int base_id; // for blue or red base
};

struct BlueBase {
    int x, y;
    int fuel_supply;
    int missile_supply;
};

struct RedBase {
    int x, y;
    int defense; // remaining missiles needed
    int value;
    bool destroyed;
};

struct Fighter {
    int id;
    int x, y;
    int fuel;
    int missiles;
    int G, C;
    enum State { IDLE, LOADING, MOVING_TO_RED, ATTACKING, MOVING_TO_BLUE } state;
    int target_red_id;
    Point target_pos;
    vector<int> path; // directions to follow
};

int n, m;
vector<vector<Cell>> grid;
vector<vector<int>> blue_base_id;
vector<vector<int>> red_base_id;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
vector<vector<int>> dist_blue; // distance to nearest blue base

// directions: 0 up, 1 down, 2 left, 3 right
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

bool in_bounds(int x, int y) {
    return 0 <= x && x < n && 0 <= y && y < m;
}

// BFS from a single source, avoiding undestroyed red bases.
// Returns distance matrix and parent matrix.
pair<vector<vector<int>>, vector<vector<Point>>> bfs(Point start) {
    vector<vector<int>> dist(n, vector<int>(m, -1));
    vector<vector<Point>> parent(n, vector<Point>(m, {-1, -1}));
    queue<Point> q;
    dist[start.x][start.y] = 0;
    q.push(start);
    while (!q.empty()) {
        Point p = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = p.x + dx[d];
            int ny = p.y + dy[d];
            if (in_bounds(nx, ny) && dist[nx][ny] == -1) {
                Cell& cell = grid[nx][ny];
                if (cell.type == '#' && !red_bases[cell.base_id].destroyed) {
                    continue;
                }
                dist[nx][ny] = dist[p.x][p.y] + 1;
                parent[nx][ny] = p;
                q.push({nx, ny});
            }
        }
    }
    return {dist, parent};
}

// Multi-source BFS from all blue bases to update dist_blue.
void update_dist_blue() {
    dist_blue.assign(n, vector<int>(m, -1));
    queue<Point> q;
    for (const BlueBase& base : blue_bases) {
        dist_blue[base.x][base.y] = 0;
        q.push({base.x, base.y});
    }
    while (!q.empty()) {
        Point p = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = p.x + dx[d];
            int ny = p.y + dy[d];
            if (in_bounds(nx, ny) && dist_blue[nx][ny] == -1) {
                Cell& cell = grid[nx][ny];
                if (cell.type == '#' && !red_bases[cell.base_id].destroyed) {
                    continue;
                }
                dist_blue[nx][ny] = dist_blue[p.x][p.y] + 1;
                q.push({nx, ny});
            }
        }
    }
}

// Reconstruct path from start to target using parent matrix.
vector<int> reconstruct_path(Point start, Point target, const vector<vector<Point>>& parent) {
    vector<int> path;
    Point cur = target;
    while (!(cur.x == start.x && cur.y == start.y)) {
        Point prev = parent[cur.x][cur.y];
        if (prev.x == -1) return {};
        // find direction from prev to cur
        for (int d = 0; d < 4; d++) {
            if (prev.x + dx[d] == cur.x && prev.y + dy[d] == cur.y) {
                path.push_back(d);
                break;
            }
        }
        cur = prev;
    }
    reverse(path.begin(), path.end());
    return path;
}

// Get blue base id at (x,y), or -1.
int get_blue_base_id(int x, int y) {
    return blue_base_id[x][y];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    // Read grid
    cin >> n >> m;
    grid.assign(n, vector<Cell>(m));
    blue_base_id.assign(n, vector<int>(m, -1));
    red_base_id.assign(n, vector<int>(m, -1));

    for (int i = 0; i < n; i++) {
        string line;
        cin >> line;
        for (int j = 0; j < m; j++) {
            grid[i][j].type = line[j];
            grid[i][j].base_id = -1;
        }
    }

    // Read blue bases
    int N_blue;
    cin >> N_blue;
    blue_bases.resize(N_blue);
    for (int i = 0; i < N_blue; i++) {
        int x, y;
        cin >> x >> y;
        blue_bases[i].x = x;
        blue_bases[i].y = y;
        blue_base_id[x][y] = i;
        grid[x][y].type = '*';
        grid[x][y].base_id = i;
        cin >> blue_bases[i].fuel_supply >> blue_bases[i].missile_supply;
        int d, v; // d and v for blue bases are irrelevant, but we read them.
        cin >> d >> v;
    }

    // Read red bases
    int N_red;
    cin >> N_red;
    red_bases.resize(N_red);
    for (int i = 0; i < N_red; i++) {
        int x, y;
        cin >> x >> y;
        red_bases[i].x = x;
        red_bases[i].y = y;
        red_base_id[x][y] = i;
        grid[x][y].type = '#';
        grid[x][y].base_id = i;
        int g, c, d, v;
        cin >> g >> c >> d >> v;
        red_bases[i].defense = d;
        red_bases[i].value = v;
        red_bases[i].destroyed = false;
    }

    // Read fighters
    int k;
    cin >> k;
    fighters.resize(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i].id = i;
        fighters[i].x = x;
        fighters[i].y = y;
        fighters[i].fuel = 0;
        fighters[i].missiles = 0;
        fighters[i].G = G;
        fighters[i].C = C;
        fighters[i].state = Fighter::LOADING; // start on a blue base
    }

    // Initialize distance to nearest blue base
    update_dist_blue();

    // Main simulation loop
    for (int frame = 0; frame < 15000; frame++) {
        vector<string> commands;
        bool all_idle = true;

        for (Fighter& f : fighters) {
            // If moving to red and target is destroyed, cancel.
            if (f.state == Fighter::MOVING_TO_RED && red_bases[f.target_red_id].destroyed) {
                f.state = Fighter::MOVING_TO_BLUE;
                f.path.clear();
            }

            if (f.state == Fighter::LOADING) {
                all_idle = false;
                int base_id = get_blue_base_id(f.x, f.y);
                if (base_id == -1) {
                    f.state = Fighter::MOVING_TO_BLUE;
                    continue;
                }
                BlueBase& base = blue_bases[base_id];
                if (base.fuel_supply == 0 && base.missile_supply == 0) {
                    f.state = Fighter::MOVING_TO_BLUE;
                    continue;
                }

                // Run BFS from current position to evaluate reachable red bases.
                auto [dist, parent] = bfs({f.x, f.y});
                double best_score = -1;
                int best_red_id = -1;
                Point best_adj;
                int best_d1 = 0;

                for (int r_id = 0; r_id < N_red; r_id++) {
                    RedBase& red = red_bases[r_id];
                    if (red.destroyed) continue;
                    for (int d = 0; d < 4; d++) {
                        int adj_x = red.x + dx[d];
                        int adj_y = red.y + dy[d];
                        if (!in_bounds(adj_x, adj_y)) continue;
                        // Adjacent cell must not be an undestroyed red base.
                        Cell& adj_cell = grid[adj_x][adj_y];
                        if (adj_cell.type == '#' && !red_bases[adj_cell.base_id].destroyed) {
                            continue;
                        }
                        if (dist[adj_x][adj_y] == -1) continue;
                        int d1 = dist[adj_x][adj_y];
                        int d2 = dist_blue[adj_x][adj_y];
                        if (d2 == -1) continue;
                        if (d1 + d2 > f.G) continue;
                        // Check resource availability at current blue base.
                        int fuel_needed = d1 + d2;
                        if (fuel_needed > base.fuel_supply) continue;
                        int missile_needed = min(f.C, red.defense);
                        if (missile_needed > base.missile_supply) continue;
                        // Compute number of trips (simplified heuristic).
                        int trips = (red.defense + missile_needed - 1) / missile_needed;
                        double score = (double)red.value / (trips * (d1 + d2 + 1));
                        if (score > best_score) {
                            best_score = score;
                            best_red_id = r_id;
                            best_adj = {adj_x, adj_y};
                            best_d1 = d1;
                        }
                    }
                }

                if (best_red_id != -1) {
                    RedBase& red = red_bases[best_red_id];
                    int d2 = dist_blue[best_adj.x][best_adj.y];
                    int fuel_needed = best_d1 + d2;
                    int missile_needed = min(f.C, red.defense);
                    // Load fuel.
                    int fuel_load = min(fuel_needed, base.fuel_supply);
                    if (fuel_load > 0) {
                        commands.push_back("fuel " + to_string(f.id) + " " + to_string(fuel_load));
                        f.fuel += fuel_load;
                        base.fuel_supply -= fuel_load;
                    }
                    // Load missiles.
                    int missile_load = min(missile_needed, base.missile_supply);
                    if (missile_load > 0) {
                        commands.push_back("missile " + to_string(f.id) + " " + to_string(missile_load));
                        f.missiles += missile_load;
                        base.missile_supply -= missile_load;
                    }
                    // Compute path to the adjacent cell.
                    f.path = reconstruct_path({f.x, f.y}, best_adj, parent);
                    f.target_red_id = best_red_id;
                    f.target_pos = best_adj;
                    f.state = Fighter::MOVING_TO_RED;
                } else {
                    // No feasible red base from this blue base.
                    f.state = Fighter::MOVING_TO_BLUE;
                }
            }
            else if (f.state == Fighter::MOVING_TO_RED) {
                all_idle = false;
                if (f.path.empty()) {
                    if (f.x == f.target_pos.x && f.y == f.target_pos.y) {
                        f.state = Fighter::ATTACKING;
                    } else {
                        f.state = Fighter::MOVING_TO_BLUE;
                    }
                    continue;
                }
                int dir = f.path[0];
                f.path.erase(f.path.begin());
                int nx = f.x + dx[dir];
                int ny = f.y + dy[dir];
                // Check move validity.
                if (in_bounds(nx, ny)) {
                    Cell& cell = grid[nx][ny];
                    if (!(cell.type == '#' && !red_bases[cell.base_id].destroyed)) {
                        commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.x = nx;
                        f.y = ny;
                        f.fuel--;
                        if (f.x == f.target_pos.x && f.y == f.target_pos.y) {
                            f.state = Fighter::ATTACKING;
                        }
                    } else {
                        // Blocked by undestroyed red base.
                        f.state = Fighter::MOVING_TO_BLUE;
                        f.path.clear();
                    }
                } else {
                    f.state = Fighter::MOVING_TO_BLUE;
                    f.path.clear();
                }
            }
            else if (f.state == Fighter::ATTACKING) {
                all_idle = false;
                int red_id = f.target_red_id;
                RedBase& red = red_bases[red_id];
                if (red.destroyed) {
                    f.state = Fighter::MOVING_TO_BLUE;
                    continue;
                }
                // Determine attack direction.
                int attack_dir = -1;
                for (int d = 0; d < 4; d++) {
                    int nx = f.x + dx[d];
                    int ny = f.y + dy[d];
                    if (in_bounds(nx, ny) && nx == red.x && ny == red.y) {
                        attack_dir = d;
                        break;
                    }
                }
                if (attack_dir == -1) {
                    f.state = Fighter::MOVING_TO_BLUE;
                    continue;
                }
                int missiles_to_fire = min(f.missiles, red.defense);
                if (missiles_to_fire == 0) {
                    f.state = Fighter::MOVING_TO_BLUE;
                    continue;
                }
                commands.push_back("attack " + to_string(f.id) + " " + to_string(attack_dir) + " " + to_string(missiles_to_fire));
                f.missiles -= missiles_to_fire;
                red.defense -= missiles_to_fire;
                if (red.defense == 0) {
                    red.destroyed = true;
                    update_dist_blue();
                }
                f.state = Fighter::MOVING_TO_BLUE;
            }
            else if (f.state == Fighter::MOVING_TO_BLUE) {
                all_idle = false;
                if (f.path.empty()) {
                    // Find the nearest blue base with positive supplies.
                    auto [dist, parent] = bfs({f.x, f.y});
                    int best_dist = INT_MAX;
                    Point best_blue;
                    for (const BlueBase& base : blue_bases) {
                        if (dist[base.x][base.y] != -1 && dist[base.x][base.y] < best_dist &&
                            (base.fuel_supply > 0 || base.missile_supply > 0)) {
                            best_dist = dist[base.x][base.y];
                            best_blue = {base.x, base.y};
                        }
                    }
                    // If none with supplies, just pick the nearest.
                    if (best_dist == INT_MAX) {
                        for (const BlueBase& base : blue_bases) {
                            if (dist[base.x][base.y] != -1 && dist[base.x][base.y] < best_dist) {
                                best_dist = dist[base.x][base.y];
                                best_blue = {base.x, base.y};
                            }
                        }
                    }
                    if (best_dist == INT_MAX) {
                        f.state = Fighter::IDLE;
                        continue;
                    }
                    f.path = reconstruct_path({f.x, f.y}, best_blue, parent);
                    f.target_pos = best_blue;
                }
                if (!f.path.empty()) {
                    int dir = f.path[0];
                    f.path.erase(f.path.begin());
                    int nx = f.x + dx[dir];
                    int ny = f.y + dy[dir];
                    if (in_bounds(nx, ny)) {
                        Cell& cell = grid[nx][ny];
                        if (!(cell.type == '#' && !red_bases[cell.base_id].destroyed)) {
                            commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.x = nx;
                            f.y = ny;
                            f.fuel--;
                            if (f.x == f.target_pos.x && f.y == f.target_pos.y) {
                                f.state = Fighter::LOADING;
                            }
                        } else {
                            f.path.clear();
                        }
                    } else {
                        f.path.clear();
                    }
                }
            }
            else if (f.state == Fighter::IDLE) {
                if (get_blue_base_id(f.x, f.y) != -1) {
                    f.state = Fighter::LOADING;
                    all_idle = false;
                } else {
                    f.state = Fighter::MOVING_TO_BLUE;
                    all_idle = false;
                }
            }
        }

        // Output commands for this frame.
        for (const string& cmd : commands) {
            cout << cmd << "\n";
        }
        cout << "OK\n";

        // Check termination conditions.
        bool all_red_destroyed = true;
        for (const RedBase& red : red_bases) {
            if (!red.destroyed) {
                all_red_destroyed = false;
                break;
            }
        }
        if (all_red_destroyed) break;
        if (all_idle && commands.empty()) break;
    }

    return 0;
}