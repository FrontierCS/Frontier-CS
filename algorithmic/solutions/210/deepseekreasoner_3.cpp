#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstring>
#include <string>
#include <cmath>
using namespace std;

const int MAXN = 200;
const int MAXM = 200;
const int INF = 1e9;

int n, m;
char grid[MAXN][MAXM];
int blue_base_id[MAXN][MAXM];
int red_base_id[MAXN][MAXM];
vector<pair<int, int>> blue_bases;
vector<int> blue_fuel, blue_missiles;
vector<pair<int, int>> red_bases;
vector<int> red_defense, red_value, red_remaining;
vector<bool> red_destroyed;

int minDistToBlue[MAXN][MAXM];

struct Fighter {
    int id;
    int x, y;
    int fuel, missiles;
    int G, C;
    int target_type; // 0: none, 1: blue, 2: red
    int target_id;   // index in base list
    int target_x, target_y;
    vector<int> path;
};

vector<Fighter> fighters;

int dx[4] = {-1, 1, 0, 0};
int dy[4] = {0, 0, -1, 1};

// BFS structures
int vis[MAXN][MAXM], dist[MAXN][MAXM], prev_dir[MAXN][MAXM];
int cur_vis_id = 0;
int bfs_start_x, bfs_start_y;

bool is_passable(int x, int y) {
    if (x < 0 || x >= n || y < 0 || y >= m) return false;
    int rb_id = red_base_id[x][y];
    if (rb_id != -1 && !red_destroyed[rb_id]) return false;
    return true;
}

void bfs(int sx, int sy) {
    cur_vis_id++;
    bfs_start_x = sx;
    bfs_start_y = sy;
    queue<pair<int, int>> q;
    dist[sx][sy] = 0;
    vis[sx][sy] = cur_vis_id;
    q.push({sx, sy});
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (!is_passable(nx, ny)) continue;
            if (vis[nx][ny] != cur_vis_id) {
                vis[nx][ny] = cur_vis_id;
                dist[nx][ny] = dist[x][y] + 1;
                prev_dir[nx][ny] = d;
                q.push({nx, ny});
            }
        }
    }
}

vector<int> reconstruct_path(int tx, int ty) {
    if (vis[tx][ty] != cur_vis_id) return {};
    vector<int> path;
    int x = tx, y = ty;
    while (!(x == bfs_start_x && y == bfs_start_y)) {
        int d = prev_dir[x][y];
        path.insert(path.begin(), d);
        // move to parent
        int opp = (d == 0 ? 1 : (d == 1 ? 0 : (d == 2 ? 3 : 2)));
        x += dx[opp];
        y += dy[opp];
    }
    return path;
}

void choose_new_target(Fighter &f) {
    // If low on fuel or missiles, target nearest blue base that can provide resources
    bool need_missiles = (f.missiles == 0);
    bool need_fuel = (f.fuel < 10);
    if (need_missiles || need_fuel) {
        bfs(f.x, f.y);
        int best_dist = INF;
        int best_bb = -1;
        // First, try bases that have the required resources
        for (int i = 0; i < (int)blue_bases.size(); i++) {
            int bx = blue_bases[i].first, by = blue_bases[i].second;
            if (dist[bx][by] == INF) continue;
            bool ok = true;
            if (need_missiles && blue_missiles[i] == 0) ok = false;
            if (need_fuel && blue_fuel[i] == 0) ok = false;
            if (!ok) continue;
            if (dist[bx][by] < best_dist) {
                best_dist = dist[bx][by];
                best_bb = i;
            }
        }
        if (best_bb == -1) {
            // If none, take any reachable blue base
            for (int i = 0; i < (int)blue_bases.size(); i++) {
                int bx = blue_bases[i].first, by = blue_bases[i].second;
                if (dist[bx][by] < best_dist) {
                    best_dist = dist[bx][by];
                    best_bb = i;
                }
            }
        }
        if (best_bb != -1) {
            f.target_type = 1;
            f.target_id = best_bb;
            f.target_x = blue_bases[best_bb].first;
            f.target_y = blue_bases[best_bb].second;
            f.path = reconstruct_path(f.target_x, f.target_y);
            return;
        }
    }

    // Otherwise, try to target a red base
    bfs(f.x, f.y);
    double best_score = -1;
    int best_red = -1;
    int best_nx = -1, best_ny = -1;
    for (int i = 0; i < (int)red_bases.size(); i++) {
        if (red_destroyed[i]) continue;
        int rx = red_bases[i].first, ry = red_bases[i].second;
        for (int d = 0; d < 4; d++) {
            int nx = rx + dx[d], ny = ry + dy[d];
            if (!is_passable(nx, ny)) continue;
            if (dist[nx][ny] == INF) continue;
            // Fuel safety check using precomputed minDistToBlue (conservative)
            int required = dist[nx][ny] + minDistToBlue[nx][ny];
            if (f.fuel < required) continue;
            double score = (double)red_value[i] / (dist[nx][ny] + red_remaining[i] + 1);
            if (score > best_score) {
                best_score = score;
                best_red = i;
                best_nx = nx;
                best_ny = ny;
            }
        }
    }
    if (best_red != -1) {
        f.target_type = 2;
        f.target_id = best_red;
        f.target_x = best_nx;
        f.target_y = best_ny;
        f.path = reconstruct_path(best_nx, best_ny);
        return;
    }

    // No red base reachable/safe, target nearest blue base
    bfs(f.x, f.y);
    int best_dist = INF;
    int best_bb = -1;
    for (int i = 0; i < (int)blue_bases.size(); i++) {
        int bx = blue_bases[i].first, by = blue_bases[i].second;
        if (dist[bx][by] < best_dist) {
            best_dist = dist[bx][by];
            best_bb = i;
        }
    }
    if (best_bb != -1) {
        f.target_type = 1;
        f.target_id = best_bb;
        f.target_x = blue_bases[best_bb].first;
        f.target_y = blue_bases[best_bb].second;
        f.path = reconstruct_path(f.target_x, f.target_y);
    } else {
        f.target_type = 0;
        f.path.clear();
    }
}

void precompute_min_dist_to_blue() {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            minDistToBlue[i][j] = INF;
    queue<pair<int, int>> q;
    for (int i = 0; i < (int)blue_bases.size(); i++) {
        int bx = blue_bases[i].first, by = blue_bases[i].second;
        minDistToBlue[bx][by] = 0;
        q.push({bx, by});
    }
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
            // Initially, all red bases are blocked
            if (red_base_id[nx][ny] != -1) continue;
            if (minDistToBlue[nx][ny] == INF) {
                minDistToBlue[nx][ny] = minDistToBlue[x][y] + 1;
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
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            cin >> grid[i][j];

    // Initialize base id maps
    memset(blue_base_id, -1, sizeof blue_base_id);
    memset(red_base_id, -1, sizeof red_base_id);

    // Read blue bases
    int N_blue;
    cin >> N_blue;
    blue_bases.resize(N_blue);
    blue_fuel.resize(N_blue);
    blue_missiles.resize(N_blue);
    for (int i = 0; i < N_blue; i++) {
        int x, y, g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        blue_bases[i] = {x, y};
        blue_fuel[i] = g;
        blue_missiles[i] = c;
        blue_base_id[x][y] = i;
    }

    // Read red bases
    int N_red;
    cin >> N_red;
    red_bases.resize(N_red);
    red_defense.resize(N_red);
    red_value.resize(N_red);
    red_remaining.resize(N_red);
    red_destroyed.assign(N_red, false);
    for (int i = 0; i < N_red; i++) {
        int x, y, g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        red_bases[i] = {x, y};
        red_defense[i] = d;
        red_value[i] = v;
        red_remaining[i] = d;
        red_base_id[x][y] = i;
    }

    // Read fighters
    int k;
    cin >> k;
    fighters.resize(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {i, x, y, 0, 0, G, C, 0, -1, -1, -1, {}};
    }

    // Precompute conservative distances to nearest blue base (with red bases blocked)
    precompute_min_dist_to_blue();

    // Main simulation loop
    for (int frame = 0; frame < 15000; frame++) {
        vector<string> commands;

        // Check if all red bases destroyed
        bool all_destroyed = true;
        for (bool d : red_destroyed)
            if (!d) { all_destroyed = false; break; }
        if (all_destroyed && commands.empty()) {
            // No commands left, we can stop early
            break;
        }

        for (auto &f : fighters) {
            // Refuel/reload if on a blue base
            int bb_id = blue_base_id[f.x][f.y];
            if (bb_id != -1) {
                if (f.fuel < f.G && blue_fuel[bb_id] > 0) {
                    int take = min(f.G - f.fuel, blue_fuel[bb_id]);
                    commands.push_back("fuel " + to_string(f.id) + " " + to_string(take));
                    f.fuel += take;
                    blue_fuel[bb_id] -= take;
                }
                if (f.missiles < f.C && blue_missiles[bb_id] > 0) {
                    int take = min(f.C - f.missiles, blue_missiles[bb_id]);
                    commands.push_back("missile " + to_string(f.id) + " " + to_string(take));
                    f.missiles += take;
                    blue_missiles[bb_id] -= take;
                }
            }

            // Attack adjacent red bases
            vector<pair<int, int>> adj_reds; // (dir, red_id)
            for (int d = 0; d < 4; d++) {
                int nx = f.x + dx[d], ny = f.y + dy[d];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                int rb_id = red_base_id[nx][ny];
                if (rb_id != -1 && !red_destroyed[rb_id])
                    adj_reds.push_back({d, rb_id});
            }
            // Sort by remaining defense (weakest first)
            sort(adj_reds.begin(), adj_reds.end(),
                 [&](const pair<int,int> &a, const pair<int,int> &b) {
                     return red_remaining[a.second] < red_remaining[b.second];
                 });
            bool attacked = false;
            for (auto &p : adj_reds) {
                int dir = p.first;
                int rb_id = p.second;
                if (f.missiles == 0) break;
                if (red_remaining[rb_id] == 0) continue;
                int count = min(f.missiles, red_remaining[rb_id]);
                commands.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(count));
                f.missiles -= count;
                red_remaining[rb_id] -= count;
                if (red_remaining[rb_id] == 0) {
                    red_destroyed[rb_id] = true;
                }
                attacked = true;
            }
            if (attacked) continue;

            // Move along path if we have one
            if (f.target_type != 0 && !f.path.empty()) {
                // Check target validity
                if (f.target_type == 2) {
                    if (red_destroyed[f.target_id]) {
                        f.target_type = 0;
                        f.path.clear();
                        continue;
                    }
                }
                if (f.fuel > 0) {
                    int dir = f.path[0];
                    int nx = f.x + dx[dir], ny = f.y + dy[dir];
                    if (is_passable(nx, ny)) {
                        commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.x = nx; f.y = ny;
                        f.fuel--;
                        f.path.erase(f.path.begin());
                    } else {
                        // Cell became blocked? Should not happen, but if so, replan.
                        f.path.clear();
                        f.target_type = 0;
                    }
                } else {
                    // Out of fuel, cancel target to choose a blue base next
                    f.target_type = 0;
                    f.path.clear();
                }
            } else if (f.target_type != 0 && f.path.empty()) {
                // Reached target cell
                if (f.target_type == 1) {
                    // Already at blue base, refuel/reload handled above
                    f.target_type = 0;
                } else if (f.target_type == 2) {
                    // Adjacent to red base, will attack next frame
                    f.target_type = 0;
                }
            }

            // If no target, choose a new one
            if (f.target_type == 0) {
                choose_new_target(f);
            }
        }

        // Output commands for this frame
        for (const string &cmd : commands) {
            cout << cmd << "\n";
        }
        cout << "OK\n";
    }

    return 0;
}