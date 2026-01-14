#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>
#include <cstring>

using namespace std;

const int INF = 1e9;
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

enum State { LOADING, MOVING, ATTACKING, RETURNING };

struct BlueBase {
    int x, y;
    int fuel_supply, missile_supply;
};

struct RedBase {
    int x, y;
    int defense, value;
    bool destroyed;
};

struct Fighter {
    int x, y;
    int fuel, missiles;
    int max_fuel, max_missiles;
    State state;
    int target;                // index of red base
    int adj_x, adj_y;          // adjacent cell we are heading to
    vector<int> path;          // directions to follow
};

int n, m;
vector<string> grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
vector<vector<bool>> passable;
vector<vector<int>> dist_to_blue;
vector<vector<int>> blue_base_index; // -1 if not a blue base

void recompute_dist_to_blue() {
    dist_to_blue.assign(n, vector<int>(m, INF));
    queue<pair<int, int>> q;
    for (const auto& base : blue_bases) {
        dist_to_blue[base.x][base.y] = 0;
        q.push({base.x, base.y});
    }
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 0 || nx >= n || ny < 0 || ny >= m || !passable[nx][ny]) continue;
            if (dist_to_blue[nx][ny] > dist_to_blue[x][y] + 1) {
                dist_to_blue[nx][ny] = dist_to_blue[x][y] + 1;
                q.push({nx, ny});
            }
        }
    }
}

void bfs_with_parent(int sx, int sy, vector<vector<int>>& dist, vector<vector<pair<int, int>>>& parent) {
    dist.assign(n, vector<int>(m, INF));
    parent.assign(n, vector<pair<int, int>>(m, {-1, -1}));
    queue<pair<int, int>> q;
    dist[sx][sy] = 0;
    q.push({sx, sy});
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 0 || nx >= n || ny < 0 || ny >= m || !passable[nx][ny]) continue;
            if (dist[nx][ny] > dist[x][y] + 1) {
                dist[nx][ny] = dist[x][y] + 1;
                parent[nx][ny] = {x, y};
                q.push({nx, ny});
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read grid
    cin >> n >> m;
    grid.resize(n);
    for (int i = 0; i < n; i++) {
        cin >> grid[i];
    }

    // Read blue bases
    int num_blue;
    cin >> num_blue;
    blue_bases.resize(num_blue);
    for (int i = 0; i < num_blue; i++) {
        int x, y, g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v; // d and v are ignored for blue bases
        blue_bases[i] = {x, y, g, c};
    }

    // Read red bases
    int num_red;
    cin >> num_red;
    red_bases.resize(num_red);
    for (int i = 0; i < num_red; i++) {
        int x, y, g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v; // g and c are ignored for red bases
        red_bases[i] = {x, y, d, v, false};
    }

    // Read fighters
    int k;
    cin >> k;
    fighters.resize(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {x, y, 0, 0, G, C, LOADING, -1, -1, -1, {}};
    }

    // Initialize passable: true for cells that are not red bases (even destroyed? initially all red bases are not destroyed)
    passable.assign(n, vector<bool>(m, true));
    for (const auto& rb : red_bases) {
        passable[rb.x][rb.y] = false;
    }

    // Map each cell to blue base index
    blue_base_index.assign(n, vector<int>(m, -1));
    for (int i = 0; i < num_blue; i++) {
        int x = blue_bases[i].x, y = blue_bases[i].y;
        blue_base_index[x][y] = i;
    }

    // Precompute distance to nearest blue base
    recompute_dist_to_blue();

    // Simulation
    for (int frame = 0; frame < 15000; frame++) {
        bool all_destroyed = true;
        for (const auto& rb : red_bases) {
            if (!rb.destroyed) {
                all_destroyed = false;
                break;
            }
        }
        if (all_destroyed) break;

        for (int fid = 0; fid < k; fid++) {
            auto& f = fighters[fid];

            // If target is destroyed, cancel
            if (f.target != -1 && red_bases[f.target].destroyed) {
                f.target = -1;
                f.state = RETURNING;
                f.path.clear();
            }

            switch (f.state) {
                case LOADING: {
                    // Refuel and reload if on a blue base
                    int base_id = blue_base_index[f.x][f.y];
                    if (base_id != -1) {
                        BlueBase& base = blue_bases[base_id];
                        int fuel_add = min(f.max_fuel - f.fuel, base.fuel_supply);
                        if (fuel_add > 0) {
                            cout << "fuel " << fid << " " << fuel_add << "\n";
                            f.fuel += fuel_add;
                            base.fuel_supply -= fuel_add;
                        }
                        int missile_add = min(f.max_missiles - f.missiles, base.missile_supply);
                        if (missile_add > 0) {
                            cout << "missile " << fid << " " << missile_add << "\n";
                            f.missiles += missile_add;
                            base.missile_supply -= missile_add;
                        }
                    }

                    // Choose a target red base
                    vector<vector<int>> dist;
                    vector<vector<pair<int, int>>> parent;
                    bfs_with_parent(f.x, f.y, dist, parent);

                    double best_score = -1;
                    int best_red = -1;
                    int best_adj_x = -1, best_adj_y = -1;

                    for (int rid = 0; rid < num_red; rid++) {
                        const auto& rb = red_bases[rid];
                        if (rb.destroyed) continue;

                        int min_dist = INF;
                        int adj_x = -1, adj_y = -1;
                        for (int d = 0; d < 4; d++) {
                            int ax = rb.x + dx[d], ay = rb.y + dy[d];
                            if (ax < 0 || ax >= n || ay < 0 || ay >= m) continue;
                            if (passable[ax][ay] && dist[ax][ay] < min_dist) {
                                min_dist = dist[ax][ay];
                                adj_x = ax;
                                adj_y = ay;
                            }
                        }
                        if (min_dist == INF) continue;

                        int fuel_needed = min_dist + dist_to_blue[adj_x][adj_y];
                        if (f.fuel < fuel_needed) continue;

                        double time_est = min_dist + 1 + dist_to_blue[adj_x][adj_y];
                        double score = rb.value / time_est;
                        if (score > best_score) {
                            best_score = score;
                            best_red = rid;
                            best_adj_x = adj_x;
                            best_adj_y = adj_y;
                        }
                    }

                    if (best_red != -1) {
                        f.target = best_red;
                        f.adj_x = best_adj_x;
                        f.adj_y = best_adj_y;
                        // Reconstruct path
                        vector<int> path;
                        int cx = best_adj_x, cy = best_adj_y;
                        while (cx != f.x || cy != f.y) {
                            auto p = parent[cx][cy];
                            // Determine direction from p to (cx,cy)
                            if (cx == p.first - 1) path.push_back(0); // up
                            else if (cx == p.first + 1) path.push_back(1); // down
                            else if (cy == p.second - 1) path.push_back(2); // left
                            else if (cy == p.second + 1) path.push_back(3); // right
                            cx = p.first;
                            cy = p.second;
                        }
                        reverse(path.begin(), path.end());
                        f.path = path;
                        f.state = MOVING;
                    }
                    break;
                }

                case MOVING: {
                    if (f.path.empty()) {
                        // Should be at adjacent cell
                        if (f.x == f.adj_x && f.y == f.adj_y) {
                            f.state = ATTACKING;
                        } else {
                            f.state = RETURNING;
                        }
                        break;
                    }
                    if (f.fuel == 0) {
                        f.state = RETURNING;
                        break;
                    }
                    int dir = f.path[0];
                    f.path.erase(f.path.begin());
                    int nx = f.x + dx[dir], ny = f.y + dy[dir];
                    if (nx < 0 || nx >= n || ny < 0 || ny >= m || !passable[nx][ny]) {
                        f.state = RETURNING;
                        break;
                    }
                    cout << "move " << fid << " " << dir << "\n";
                    f.x = nx;
                    f.y = ny;
                    f.fuel--;

                    // Check if now adjacent to target
                    if (f.target != -1) {
                        const auto& rb = red_bases[f.target];
                        if (abs(f.x - rb.x) + abs(f.y - rb.y) == 1) {
                            f.state = ATTACKING;
                            f.path.clear();
                        }
                    }
                    break;
                }

                case ATTACKING: {
                    if (f.target == -1) {
                        f.state = RETURNING;
                        break;
                    }
                    auto& rb = red_bases[f.target];
                    if (rb.destroyed) {
                        f.state = RETURNING;
                        break;
                    }
                    // Check adjacency
                    if (abs(f.x - rb.x) + abs(f.y - rb.y) != 1) {
                        f.state = RETURNING;
                        break;
                    }
                    // Determine attack direction
                    int dir_attack;
                    if (f.x == rb.x) {
                        if (f.y < rb.y) dir_attack = 3; // right
                        else dir_attack = 2; // left
                    } else {
                        if (f.x < rb.x) dir_attack = 1; // down
                        else dir_attack = 0; // up
                    }
                    int missiles_to_fire = min(f.missiles, rb.defense);
                    if (missiles_to_fire > 0) {
                        cout << "attack " << fid << " " << dir_attack << " " << missiles_to_fire << "\n";
                        f.missiles -= missiles_to_fire;
                        rb.defense -= missiles_to_fire;
                        if (rb.defense == 0) {
                            rb.destroyed = true;
                            passable[rb.x][rb.y] = true;
                            recompute_dist_to_blue();
                        }
                    }
                    if (rb.destroyed || f.missiles == 0) {
                        f.state = RETURNING;
                    }
                    break;
                }

                case RETURNING: {
                    if (blue_base_index[f.x][f.y] != -1) {
                        f.state = LOADING;
                        break;
                    }
                    // Move towards nearest blue base using gradient
                    int best_dir = -1;
                    int cur_dist = dist_to_blue[f.x][f.y];
                    for (int d = 0; d < 4; d++) {
                        int nx = f.x + dx[d], ny = f.y + dy[d];
                        if (nx < 0 || nx >= n || ny < 0 || ny >= m || !passable[nx][ny]) continue;
                        if (dist_to_blue[nx][ny] < cur_dist) {
                            best_dir = d;
                            break;
                        }
                    }
                    if (best_dir == -1 || f.fuel == 0) {
                        // No improving direction or no fuel
                        break;
                    }
                    cout << "move " << fid << " " << best_dir << "\n";
                    f.x += dx[best_dir];
                    f.y += dy[best_dir];
                    f.fuel--;
                    break;
                }
            }
        }
        cout << "OK\n";
    }

    return 0;
}