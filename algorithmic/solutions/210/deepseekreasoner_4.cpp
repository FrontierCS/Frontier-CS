#include <bits/stdc++.h>
using namespace std;

const int MAX_FRAMES = 15000;
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

struct BlueBase {
    int x, y;
    int fuel_supply;
    int missile_supply;
};

struct RedBase {
    int x, y;
    int defense;         // remaining defense
    int initial_defense;
    int value;
    bool destroyed;
    bool assigned;       // reserved by a fighter
};

enum FighterState {
    IDLE,
    MOVING_TO_BLUE_BASE,
    RESUPPLYING,
    MOVING_TO_RED_BASE,
    ATTACKING
};

struct Fighter {
    int id;
    int x, y;
    int fuel;
    int missiles;
    int capacity_fuel;    // G
    int capacity_missiles; // C
    FighterState state;
    int target_base_index;   // index in blue_bases or red_bases
    vector<int> path;        // directions to follow
    int path_index;          // next move index in path

    Fighter() : state(IDLE), path_index(0) {}
};

int n, m;
vector<vector<char>> grid;
vector<vector<bool>> passable;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
int total_score = 0;

struct BFSResult {
    vector<vector<int>> dist;
    vector<vector<pair<int, int>>> parent;
    vector<vector<int>> dir;   // direction from parent to cell

    BFSResult(int n, int m) {
        dist.assign(n, vector<int>(m, -1));
        parent.assign(n, vector<pair<int, int>>(m, {-1, -1}));
        dir.assign(n, vector<int>(m, -1));
    }
};

BFSResult bfs(int sx, int sy) {
    BFSResult res(n, m);
    queue<pair<int, int>> q;
    q.push({sx, sy});
    res.dist[sx][sy] = 0;
    res.parent[sx][sy] = {sx, sy};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (nx >= 0 && nx < n && ny >= 0 && ny < m && passable[nx][ny] && res.dist[nx][ny] == -1) {
                res.dist[nx][ny] = res.dist[x][y] + 1;
                res.parent[nx][ny] = {x, y};
                res.dir[nx][ny] = d;
                q.push({nx, ny});
            }
        }
    }
    return res;
}

vector<int> reconstruct_path(const BFSResult& res, int tx, int ty) {
    vector<int> path;
    int x = tx, y = ty;
    while (res.parent[x][y] != make_pair(x, y)) {
        path.push_back(res.dir[x][y]);
        int px = res.parent[x][y].first;
        int py = res.parent[x][y].second;
        x = px; y = py;
    }
    reverse(path.begin(), path.end());
    return path;
}

void read_input() {
    cin >> n >> m;
    grid.resize(n, vector<char>(m));
    passable.resize(n, vector<bool>(m, false));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            cin >> grid[i][j];
            if (grid[i][j] != '#') {
                passable[i][j] = true;
            }
        }
    }

    int N;
    // blue bases
    cin >> N;
    blue_bases.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> blue_bases[i].x >> blue_bases[i].y;
        int g, c, d, v;
        cin >> g >> c >> d >> v;
        blue_bases[i].fuel_supply = g;
        blue_bases[i].missile_supply = c;
        // d and v are irrelevant for blue bases in this problem
    }

    // red bases
    cin >> N;
    red_bases.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> red_bases[i].x >> red_bases[i].y;
        int g, c, d, v;
        cin >> g >> c >> d >> v;
        red_bases[i].defense = d;
        red_bases[i].initial_defense = d;
        red_bases[i].value = v;
        red_bases[i].destroyed = false;
        red_bases[i].assigned = false;
        passable[red_bases[i].x][red_bases[i].y] = false;
    }

    int k;
    cin >> k;
    fighters.resize(k);
    for (int i = 0; i < k; ++i) {
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].capacity_fuel >> fighters[i].capacity_missiles;
        fighters[i].id = i;
        fighters[i].fuel = 0;
        fighters[i].missiles = 0;
        fighters[i].state = IDLE;
        fighters[i].path_index = 0;

        // find the blue base they are on and set to resupply
        for (int j = 0; j < (int)blue_bases.size(); ++j) {
            if (blue_bases[j].x == fighters[i].x && blue_bases[j].y == fighters[i].y) {
                fighters[i].state = RESUPPLYING;
                fighters[i].target_base_index = j;
                break;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    read_input();

    for (int frame = 0; frame < MAX_FRAMES; ++frame) {
        bool all_destroyed = true;
        for (auto& rb : red_bases) {
            if (!rb.destroyed) {
                all_destroyed = false;
                break;
            }
        }
        if (all_destroyed) {
            cout << "OK" << endl;
            break;
        }

        vector<string> commands;

        for (auto& f : fighters) {
            if (f.state == MOVING_TO_BLUE_BASE || f.state == MOVING_TO_RED_BASE) {
                // check if target red base is already destroyed
                if (f.state == MOVING_TO_RED_BASE) {
                    RedBase& rb = red_bases[f.target_base_index];
                    if (rb.destroyed) {
                        f.state = IDLE;
                        rb.assigned = false;
                        continue;
                    }
                }

                if (f.path_index < (int)f.path.size()) {
                    int dir = f.path[f.path_index];
                    int nx = f.x + dx[dir];
                    int ny = f.y + dy[dir];
                    if (nx >= 0 && nx < n && ny >= 0 && ny < m && passable[nx][ny]) {
                        commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.x = nx;
                        f.y = ny;
                        f.fuel--;
                        f.path_index++;
                        if (f.path_index == (int)f.path.size()) {
                            if (f.state == MOVING_TO_BLUE_BASE) {
                                f.state = RESUPPLYING;
                            } else {
                                f.state = ATTACKING;
                            }
                        }
                    } else {
                        // move invalid, replan
                        f.state = IDLE;
                        if (f.state == MOVING_TO_RED_BASE) {
                            red_bases[f.target_base_index].assigned = false;
                        }
                    }
                } else {
                    f.state = IDLE;
                }
            } else if (f.state == RESUPPLYING) {
                int bb_idx = -1;
                for (int i = 0; i < (int)blue_bases.size(); ++i) {
                    if (blue_bases[i].x == f.x && blue_bases[i].y == f.y) {
                        bb_idx = i;
                        break;
                    }
                }
                if (bb_idx == -1) {
                    f.state = IDLE;
                    continue;
                }
                BlueBase& bb = blue_bases[bb_idx];
                bool did_something = false;
                if (f.fuel < f.capacity_fuel && bb.fuel_supply > 0) {
                    int take = min(f.capacity_fuel - f.fuel, bb.fuel_supply);
                    commands.push_back("fuel " + to_string(f.id) + " " + to_string(take));
                    f.fuel += take;
                    bb.fuel_supply -= take;
                    did_something = true;
                }
                if (f.missiles < f.capacity_missiles && bb.missile_supply > 0) {
                    int take = min(f.capacity_missiles - f.missiles, bb.missile_supply);
                    commands.push_back("missile " + to_string(f.id) + " " + to_string(take));
                    f.missiles += take;
                    bb.missile_supply -= take;
                    did_something = true;
                }
                if (!did_something) {
                    f.state = IDLE;
                }
            } else if (f.state == ATTACKING) {
                RedBase& rb = red_bases[f.target_base_index];
                if (rb.destroyed) {
                    f.state = IDLE;
                    continue;
                }
                int dx_val = rb.x - f.x;
                int dy_val = rb.y - f.y;
                if (abs(dx_val) + abs(dy_val) != 1) {
                    f.state = IDLE;
                    rb.assigned = false;
                    continue;
                }
                int dir;
                if (dx_val == -1) dir = 0;
                else if (dx_val == 1) dir = 1;
                else if (dy_val == -1) dir = 2;
                else dir = 3;
                int count = min(f.missiles, rb.defense);
                if (count > 0) {
                    commands.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(count));
                    f.missiles -= count;
                    rb.defense -= count;
                    if (rb.defense == 0) {
                        rb.destroyed = true;
                        total_score += rb.value;
                        passable[rb.x][rb.y] = true;
                        rb.assigned = false;
                    }
                }
                if (f.missiles == 0 || rb.destroyed) {
                    f.state = IDLE;
                    if (!rb.destroyed) {
                        rb.assigned = false;
                    }
                }
            } else if (f.state == IDLE) {
                // check if at a blue base and need supplies
                bool at_blue_base = false;
                int blue_base_idx = -1;
                for (int i = 0; i < (int)blue_bases.size(); ++i) {
                    if (blue_bases[i].x == f.x && blue_bases[i].y == f.y) {
                        at_blue_base = true;
                        blue_base_idx = i;
                        break;
                    }
                }
                if (at_blue_base) {
                    BlueBase& bb = blue_bases[blue_base_idx];
                    if ((f.fuel < f.capacity_fuel || f.missiles < f.capacity_missiles) &&
                        (bb.fuel_supply > 0 || bb.missile_supply > 0)) {
                        f.state = RESUPPLYING;
                        f.target_base_index = blue_base_idx;
                        continue;
                    }
                }

                if (f.missiles > 0) {
                    BFSResult bfs_res = bfs(f.x, f.y);
                    int best_rb = -1;
                    double best_score = -1e9;
                    int best_nx = -1, best_ny = -1;
                    for (int i = 0; i < (int)red_bases.size(); ++i) {
                        RedBase& rb = red_bases[i];
                        if (rb.destroyed || rb.assigned) continue;
                        int min_dist = INT_MAX;
                        int best_neighbor_x, best_neighbor_y;
                        for (int d = 0; d < 4; ++d) {
                            int nx = rb.x + dx[d];
                            int ny = rb.y + dy[d];
                            if (nx >= 0 && nx < n && ny >= 0 && ny < m && passable[nx][ny]) {
                                int dist = bfs_res.dist[nx][ny];
                                if (dist != -1 && dist < min_dist) {
                                    min_dist = dist;
                                    best_neighbor_x = nx;
                                    best_neighbor_y = ny;
                                }
                            }
                        }
                        if (min_dist != INT_MAX && min_dist <= f.fuel) {
                            double score = (double)rb.value / rb.initial_defense / (min_dist + 1);
                            if (score > best_score) {
                                best_score = score;
                                best_rb = i;
                                best_nx = best_neighbor_x;
                                best_ny = best_neighbor_y;
                            }
                        }
                    }
                    if (best_rb != -1) {
                        red_bases[best_rb].assigned = true;
                        f.state = MOVING_TO_RED_BASE;
                        f.target_base_index = best_rb;
                        vector<int> path = reconstruct_path(bfs_res, best_nx, best_ny);
                        f.path = path;
                        f.path_index = 0;
                        continue;
                    }
                }

                // go to nearest blue base (that is reachable with current fuel)
                BFSResult bfs_res = bfs(f.x, f.y);
                int best_bb = -1;
                int min_dist = INT_MAX;
                for (int i = 0; i < (int)blue_bases.size(); ++i) {
                    int dist = bfs_res.dist[blue_bases[i].x][blue_bases[i].y];
                    if (dist != -1 && dist <= f.fuel && dist < min_dist) {
                        min_dist = dist;
                        best_bb = i;
                    }
                }
                if (best_bb != -1) {
                    f.state = MOVING_TO_BLUE_BASE;
                    f.target_base_index = best_bb;
                    vector<int> path = reconstruct_path(bfs_res, blue_bases[best_bb].x, blue_bases[best_bb].y);
                    f.path = path;
                    f.path_index = 0;
                    continue;
                }
                // otherwise stay idle
            }
        }

        for (const string& cmd : commands) {
            cout << cmd << endl;
        }
        cout << "OK" << endl;
    }

    return 0;
}