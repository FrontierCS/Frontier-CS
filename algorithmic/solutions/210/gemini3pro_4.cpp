#include <iostream>
#include <vector>
#include <queue>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

// Constants and Globals
const int MAX_FRAMES = 15000;
int N_ROWS, M_COLS;
vector<string> grid;

struct BlueBase {
    int id;
    int x, y;
    int fuel, missiles;
    int defense, value; 
};

struct RedBase {
    int id;
    int x, y;
    int fuel, missiles; 
    int defense, value;
    int current_hp;
    bool destroyed;
    int incoming_damage; 
};

struct Fighter {
    int id;
    int x, y;
    int G, C; 
    int fuel, missiles; 
    
    int target_red_base_id; 
    vector<pair<int, int>> path; 
    int state; // 0: IDLE/RESUPPLYING, 1: MOVING_TO_TARGET, 2: ATTACKING
    int target_base_x, target_base_y; 
};

vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
int K;

bool isValid(int r, int c) {
    return r >= 0 && r < N_ROWS && c >= 0 && c < M_COLS;
}

bool isPassable(int r, int c) {
    if (!isValid(r, c)) return false;
    if (grid[r][c] == '#') return false; 
    return true;
}

// 0: up, 1: down, 2: left, 3: right
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

// Finds path from (sx, sy) to a cell adjacent to (tx, ty).
vector<pair<int, int>> findPath(int sx, int sy, int tx, int ty) {
    queue<pair<int, int>> q;
    q.push({sx, sy});
    
    vector<vector<int>> dist(N_ROWS, vector<int>(M_COLS, -1));
    vector<vector<pair<int, int>>> parent(N_ROWS, vector<pair<int, int>>(M_COLS, {-1, -1}));
    
    dist[sx][sy] = 0;
    
    int final_x = -1, final_y = -1;
    
    // If already adjacent
    if (abs(sx - tx) + abs(sy - ty) == 1) {
        return {};
    }

    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        int r = curr.first;
        int c = curr.second;
        
        if (abs(r - tx) + abs(c - ty) == 1) {
            final_x = r;
            final_y = c;
            break;
        }
        
        for (int i = 0; i < 4; i++) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            
            if (isValid(nr, nc) && isPassable(nr, nc) && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                parent[nr][nc] = {r, c};
                q.push({nr, nc});
            }
        }
    }
    
    vector<pair<int, int>> path;
    if (final_x != -1) {
        int cur_x = final_x;
        int cur_y = final_y;
        while (cur_x != sx || cur_y != sy) {
            path.push_back({cur_x, cur_y});
            pair<int, int> p = parent[cur_x][cur_y];
            cur_x = p.first;
            cur_y = p.second;
        }
        reverse(path.begin(), path.end());
    }
    return path;
}

pair<int, vector<pair<int, int>>> findNearestBlueBase(int sx, int sy) {
    queue<pair<int, int>> q;
    q.push({sx, sy});
    
    vector<vector<int>> dist(N_ROWS, vector<int>(M_COLS, -1));
    vector<vector<pair<int, int>>> parent(N_ROWS, vector<pair<int, int>>(M_COLS, {-1, -1}));
    
    dist[sx][sy] = 0;
    
    int target_idx = -1;
    int fx = -1, fy = -1;

    for(int i=0; i<(int)blue_bases.size(); ++i) {
        if (blue_bases[i].x == sx && blue_bases[i].y == sy) {
             return {i, {}};
        }
    }
    
    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        int r = curr.first;
        int c = curr.second;
        
        if (grid[r][c] == '*') {
            for(int i=0; i<(int)blue_bases.size(); ++i) {
                if (blue_bases[i].x == r && blue_bases[i].y == c) {
                    target_idx = i;
                    fx = r;
                    fy = c;
                    goto found;
                }
            }
        }
        
        for (int i = 0; i < 4; i++) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (isValid(nr, nc) && isPassable(nr, nc) && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                parent[nr][nc] = {r, c};
                q.push({nr, nc});
            }
        }
    }
    
    found:;
    vector<pair<int, int>> path;
    if (target_idx != -1) {
        int cur_x = fx;
        int cur_y = fy;
        while (cur_x != sx || cur_y != sy) {
            path.push_back({cur_x, cur_y});
            pair<int, int> p = parent[cur_x][cur_y];
            cur_x = p.first;
            cur_y = p.second;
        }
        reverse(path.begin(), path.end());
    }
    return {target_idx, path};
}

int getDir(int r1, int c1, int r2, int c2) {
    if (r2 == r1 - 1) return 0;
    if (r2 == r1 + 1) return 1;
    if (c2 == c1 - 1) return 2;
    if (c2 == c1 + 1) return 3;
    return -1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N_ROWS >> M_COLS)) return 0;
    grid.resize(N_ROWS);
    for (int i = 0; i < N_ROWS; i++) cin >> grid[i];

    int num_blue;
    cin >> num_blue;
    for (int i = 0; i < num_blue; i++) {
        BlueBase b; b.id = i;
        cin >> b.x >> b.y >> b.fuel >> b.missiles >> b.defense >> b.value;
        blue_bases.push_back(b);
    }

    int num_red;
    cin >> num_red;
    for (int i = 0; i < num_red; i++) {
        RedBase b; b.id = i;
        cin >> b.x >> b.y >> b.fuel >> b.missiles >> b.defense >> b.value;
        b.current_hp = 0; b.destroyed = false; b.incoming_damage = 0;
        red_bases.push_back(b);
    }

    cin >> K;
    for (int i = 0; i < K; i++) {
        Fighter f; f.id = i;
        cin >> f.x >> f.y >> f.G >> f.C;
        f.fuel = 0; f.missiles = 0;
        f.target_red_base_id = -1; f.state = 0;
        fighters.push_back(f);
    }

    for (int frame = 0; frame < MAX_FRAMES; frame++) {
        vector<string> commands;

        bool all_destroyed = true;
        for(auto &rb : red_bases) if (!rb.destroyed) { all_destroyed = false; break; }
        if (all_destroyed) { cout << "OK" << endl; continue; }

        for (int i = 0; i < K; i++) {
            Fighter &f = fighters[i];
            
            if (f.state == 0) {
                bool on_base = false;
                int base_idx = -1;
                for(int b=0; b<num_blue; ++b) {
                    if (blue_bases[b].x == f.x && blue_bases[b].y == f.y) {
                        on_base = true; base_idx = b; break;
                    }
                }

                if (on_base) {
                    int needed_fuel = f.G - f.fuel;
                    if (needed_fuel > 0 && blue_bases[base_idx].fuel > 0) {
                        int take = min(needed_fuel, blue_bases[base_idx].fuel);
                        f.fuel += take;
                        blue_bases[base_idx].fuel -= take;
                        commands.push_back("fuel " + to_string(f.id) + " " + to_string(take));
                    }
                    
                    int best_target = -1;
                    double best_score = -1.0;
                    vector<pair<int, int>> best_path;

                    for(int r=0; r<num_red; ++r) {
                        if (red_bases[r].destroyed) continue;
                        if (red_bases[r].incoming_damage >= red_bases[r].defense) continue;

                        vector<pair<int, int>> p = findPath(f.x, f.y, red_bases[r].x, red_bases[r].y);
                        if (p.empty() && !(abs(f.x - red_bases[r].x) + abs(f.y - red_bases[r].y) == 1)) continue;
                        
                        int dist = p.size();
                        if (dist > f.fuel) continue; 
                        
                        double score = (double)red_bases[r].value / (dist + 1.0);
                        if (score > best_score) {
                            best_score = score; best_target = r; best_path = p;
                        }
                    }

                    if (best_target != -1) {
                        f.target_red_base_id = best_target;
                        f.path = best_path;
                        f.target_base_x = red_bases[best_target].x;
                        f.target_base_y = red_bases[best_target].y;

                        int hp_remaining = red_bases[best_target].defense - red_bases[best_target].incoming_damage;
                        int capacity_room = f.C - f.missiles;
                        int supply = blue_bases[base_idx].missiles;
                        
                        int take_missiles = min({capacity_room, supply, hp_remaining});
                        
                        if (f.missiles + take_missiles == 0) {
                             f.target_red_base_id = -1;
                        } else {
                            if (take_missiles > 0) {
                                f.missiles += take_missiles;
                                blue_bases[base_idx].missiles -= take_missiles;
                                commands.push_back("missile " + to_string(f.id) + " " + to_string(take_missiles));
                            }
                            red_bases[best_target].incoming_damage += f.missiles;
                            
                            if (abs(f.x - f.target_base_x) + abs(f.y - f.target_base_y) == 1) f.state = 2;
                            else f.state = 1;
                        }
                    } 
                    
                    if (f.target_red_base_id == -1) {
                         // Idle
                    }
                } else {
                    pair<int, vector<pair<int, int>>> res = findNearestBlueBase(f.x, f.y);
                    if (res.first != -1 && !res.second.empty()) {
                        f.path = res.second;
                        f.state = 1; 
                        f.target_red_base_id = -1;
                    }
                }
            }

            if (f.state == 1) {
                if (f.target_red_base_id != -1 && red_bases[f.target_red_base_id].destroyed) {
                    f.state = 0; f.target_red_base_id = -1; f.path.clear();
                } else {
                    if (f.path.empty()) {
                         if (f.target_red_base_id != -1) {
                             if (abs(f.x - f.target_base_x) + abs(f.y - f.target_base_y) == 1) {
                                 f.state = 2;
                             } else {
                                 f.path = findPath(f.x, f.y, f.target_base_x, f.target_base_y);
                                 if (f.path.empty()) {
                                     f.state = 0;
                                     red_bases[f.target_red_base_id].incoming_damage -= f.missiles;
                                     if(red_bases[f.target_red_base_id].incoming_damage < 0) red_bases[f.target_red_base_id].incoming_damage = 0;
                                     f.target_red_base_id = -1;
                                 }
                             }
                         } else {
                             f.state = 0;
                         }
                    }
                    
                    if (f.state == 1 && !f.path.empty()) {
                        pair<int, int> next_pos = f.path.front();
                        int dir = getDir(f.x, f.y, next_pos.first, next_pos.second);
                        
                        bool move_ok = true;
                        if (f.fuel < 1) move_ok = false;
                        if (!isPassable(next_pos.first, next_pos.second)) {
                             move_ok = false; f.path.clear();
                        }

                        if (move_ok) {
                            f.path.erase(f.path.begin());
                            f.fuel--;
                            f.x = next_pos.first;
                            f.y = next_pos.second;
                            commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            
                            if (f.target_red_base_id != -1 && abs(f.x - f.target_base_x) + abs(f.y - f.target_base_y) == 1) {
                                f.state = 2;
                            }
                        } else {
                            if (f.fuel == 0) f.state = 0; 
                            else {
                                if (f.target_red_base_id != -1) {
                                    f.path = findPath(f.x, f.y, f.target_base_x, f.target_base_y);
                                    if (f.path.empty()) {
                                         f.state = 0;
                                         red_bases[f.target_red_base_id].incoming_damage -= f.missiles;
                                         if(red_bases[f.target_red_base_id].incoming_damage < 0) red_bases[f.target_red_base_id].incoming_damage = 0;
                                         f.target_red_base_id = -1;
                                    }
                                } else {
                                    pair<int, vector<pair<int, int>>> res = findNearestBlueBase(f.x, f.y);
                                    if (!res.second.empty()) f.path = res.second;
                                    else f.state = 0;
                                }
                            }
                        }
                    }
                }
            }

            if (f.state == 2) {
                 if (f.target_red_base_id == -1 || red_bases[f.target_red_base_id].destroyed) {
                     f.state = 0; f.target_red_base_id = -1;
                 } else {
                     int tid = f.target_red_base_id;
                     RedBase &rb = red_bases[tid];
                     
                     if (abs(f.x - rb.x) + abs(f.y - rb.y) != 1) {
                         f.state = 1; 
                         f.path = findPath(f.x, f.y, rb.x, rb.y);
                     } else {
                         int actual_needed = rb.defense - rb.current_hp;
                         if (actual_needed <= 0) {
                             rb.destroyed = true;
                             grid[rb.x][rb.y] = '.';
                             f.state = 0; f.target_red_base_id = -1;
                         } else {
                             int count = min(f.missiles, actual_needed);
                             if (count > 0) {
                                 commands.push_back("attack " + to_string(f.id) + " " + to_string(getDir(f.x, f.y, rb.x, rb.y)) + " " + to_string(count));
                                 f.missiles -= count;
                                 rb.current_hp += count;
                                 rb.incoming_damage -= count;
                                 if(rb.incoming_damage < 0) rb.incoming_damage = 0;
                                 
                                 if (rb.current_hp >= rb.defense) {
                                     rb.destroyed = true;
                                     grid[rb.x][rb.y] = '.'; 
                                     f.state = 0; f.target_red_base_id = -1;
                                 }
                                 if (f.missiles == 0) {
                                     f.state = 0; f.target_red_base_id = -1;
                                 }
                             } else {
                                 f.state = 0; f.target_red_base_id = -1;
                             }
                         }
                     }
                 }
            }
        }
        
        for(const string &cmd : commands) cout << cmd << endl;
        cout << "OK" << endl;
    }

    return 0;
}