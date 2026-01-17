#include <iostream>
#include <vector>
#include <queue>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

// Data structures
struct BlueBase {
    int id;
    int x, y;
    int fuel, missiles;
};

struct RedBase {
    int id;
    int x, y;
    int hp, max_hp;
    int value;
    bool destroyed;
    int pending_damage;
};

struct Fighter {
    int id;
    int x, y;
    int fuel, missiles;
    int max_fuel, max_missiles;
    
    int state; // 0: IDLE, 1: MOVING_TO_BASE, 2: RESUPPLYING, 3: MOVING_TO_TARGET, 4: ATTACKING
    int target_bb_idx;
    int target_rb_idx;
    int target_r, target_c;
    vector<int> path;
    size_t path_idx;
};

int N, M;
vector<string> grid_map;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
int K;

int dx[] = {-1, 1, 0, 0};
int dy[] = {0, 0, -1, 1};

bool valid(int x, int y) {
    return x >= 0 && x < N && y >= 0 && y < M;
}

// BFS to find distances from a source to all points
// treating undestroyed red bases as obstacles
vector<vector<int>> get_dist_map(int sx, int sy) {
    vector<vector<int>> dist(N, vector<int>(M, -1));
    queue<pair<int,int>> q;
    
    dist[sx][sy] = 0;
    q.push({sx, sy});
    
    while(!q.empty()) {
        auto [cx, cy] = q.front(); q.pop();
        for(int i=0; i<4; ++i) {
            int nx = cx + dx[i];
            int ny = cy + dy[i];
            if(valid(nx, ny) && dist[nx][ny] == -1) {
                // Treat undestroyed red bases as obstacles
                if(grid_map[nx][ny] != '#') {
                    dist[nx][ny] = dist[cx][cy] + 1;
                    q.push({nx, ny});
                }
            }
        }
    }
    return dist;
}

// BFS to find path from (sx, sy) to (ex, ey)
vector<int> find_path(int sx, int sy, int ex, int ey) {
    vector<vector<int>> dist(N, vector<int>(M, -1));
    vector<vector<int>> parent_dir(N, vector<int>(M, -1));
    queue<pair<int,int>> q;
    
    dist[sx][sy] = 0;
    q.push({sx, sy});
    
    bool found = false;
    while(!q.empty()) {
        auto [cx, cy] = q.front(); q.pop();
        if(cx == ex && cy == ey) {
            found = true;
            break;
        }
        
        for(int i=0; i<4; ++i) {
            int nx = cx + dx[i];
            int ny = cy + dy[i];
            
            if(valid(nx, ny) && dist[nx][ny] == -1) {
                if(grid_map[nx][ny] != '#' || (nx == ex && ny == ey && grid_map[nx][ny] != '#')) {
                     dist[nx][ny] = dist[cx][cy] + 1;
                     parent_dir[nx][ny] = i;
                     q.push({nx, ny});
                }
            }
        }
    }
    
    vector<int> path;
    if(found) {
        int cur_x = ex;
        int cur_y = ey;
        while(cur_x != sx || cur_y != sy) {
            int p_dir = parent_dir[cur_x][cur_y];
            path.push_back(p_dir);
            cur_x -= dx[p_dir];
            cur_y -= dy[p_dir];
        }
        reverse(path.begin(), path.end());
    }
    return path;
}

void solve() {
    cin >> N >> M;
    grid_map.resize(N);
    for(int i=0; i<N; ++i) cin >> grid_map[i];
    
    int num_blue;
    cin >> num_blue;
    for(int i=0; i<num_blue; ++i) {
        BlueBase b;
        b.id = i;
        int d, v; 
        cin >> b.x >> b.y >> b.fuel >> b.missiles >> d >> v;
        blue_bases.push_back(b);
    }
    
    int num_red;
    cin >> num_red;
    for(int i=0; i<num_red; ++i) {
        RedBase r;
        r.id = i;
        int dummy_g, dummy_c;
        cin >> r.x >> r.y >> dummy_g >> dummy_c >> r.hp >> r.value;
        r.max_hp = r.hp;
        r.destroyed = false;
        r.pending_damage = 0;
        red_bases.push_back(r);
    }
    
    cin >> K;
    for(int i=0; i<K; ++i) {
        Fighter f;
        f.id = i;
        cin >> f.x >> f.y >> f.max_fuel >> f.max_missiles;
        f.fuel = 0;
        f.missiles = 0;
        f.state = 0;
        fighters.push_back(f);
    }
    
    for(int frame = 1; frame <= 15000; ++frame) {
        vector<string> output_cmds;
        
        for(auto& f : fighters) {
            // State 0: IDLE - Plan a mission
            if(f.state == 0) {
                double best_score = -1.0;
                int best_bb = -1;
                int best_rb = -1;
                int best_tx = -1, best_ty = -1;
                
                vector<vector<int>> dist_f = get_dist_map(f.x, f.y);
                
                for(int b=0; b < blue_bases.size(); ++b) {
                    if(dist_f[blue_bases[b].x][blue_bases[b].y] == -1) continue;
                    
                    if(blue_bases[b].fuel <= 0 && blue_bases[b].missiles <= 0) continue; 
                    
                    vector<vector<int>> dist_b = get_dist_map(blue_bases[b].x, blue_bases[b].y);
                    
                    for(int r=0; r < red_bases.size(); ++r) {
                        RedBase& rb = red_bases[r];
                        if(rb.destroyed || (rb.hp - rb.pending_damage <= 0)) continue;
                        
                        // Find best adjacent spot to attack from
                        int rx = rb.x, ry = rb.y;
                        int local_best_dist = 1e9;
                        int tx = -1, ty = -1;
                        
                        for(int k=0; k<4; ++k) {
                            int nx = rx + dx[k];
                            int ny = ry + dy[k];
                            if(valid(nx, ny) && grid_map[nx][ny] != '#') {
                                int d = dist_b[nx][ny];
                                if(d != -1 && d < local_best_dist) {
                                    local_best_dist = d;
                                    tx = nx; ty = ny;
                                }
                            }
                        }
                        
                        if(tx == -1) continue;
                        
                        int dist_to_base = dist_f[blue_bases[b].x][blue_bases[b].y];
                        int total_time = dist_to_base + local_best_dist;
                        
                        // Fuel check
                        int trip_fuel = local_best_dist * 2 + 10;
                        if(trip_fuel > f.max_fuel) continue;
                        
                        // Missile check
                        int m_needed = min(f.max_missiles, rb.hp - rb.pending_damage);
                        int m_avail = min(m_needed, blue_bases[b].missiles);
                        if(m_avail <= 0) continue;
                        
                        double score = (double)rb.value * m_avail / (double)rb.max_hp / (total_time + 1.0);
                        
                        if(score > best_score) {
                            best_score = score;
                            best_bb = b;
                            best_rb = r;
                            best_tx = tx;
                            best_ty = ty;
                        }
                    }
                }
                
                if(best_bb != -1) {
                    f.state = 1; // MOVING_TO_BASE
                    f.target_bb_idx = best_bb;
                    f.target_rb_idx = best_rb;
                    f.target_r = best_tx;
                    f.target_c = best_ty;
                    
                    f.path = find_path(f.x, f.y, blue_bases[best_bb].x, blue_bases[best_bb].y);
                    f.path_idx = 0;
                    
                    int m_needed = min(f.max_missiles, red_bases[best_rb].hp - red_bases[best_rb].pending_damage);
                    int m_take = min(m_needed, blue_bases[best_bb].missiles);
                    red_bases[best_rb].pending_damage += m_take;
                }
            }
            
            // State 1: MOVING_TO_BASE
            if(f.state == 1) {
                if(f.path_idx < f.path.size()) {
                    int d = f.path[f.path_idx];
                    if(f.fuel > 0 || (f.path.empty())) {
                         output_cmds.push_back("move " + to_string(f.id) + " " + to_string(d));
                         f.x += dx[d];
                         f.y += dy[d];
                         f.fuel--;
                         f.path_idx++;
                    } else if (f.fuel <= 0) {
                        // Should not happen if fuel planning is correct, unless initial state at base
                        // At base we have fuel=0, but we are at the base, so path_idx=0 and path.size()=0 usually.
                        // If we are moving TO a base and run out of fuel, we are stuck.
                        f.state = 0;
                    }
                }
                if(f.path_idx >= f.path.size()) {
                    f.state = 2; // RESUPPLYING
                }
            }
            // State 2: RESUPPLYING
            else if(f.state == 2) {
                BlueBase& bb = blue_bases[f.target_bb_idx];
                
                vector<int> p = find_path(f.x, f.y, f.target_r, f.target_c);
                if(p.empty() && !(f.x == f.target_r && f.y == f.target_c)) {
                    f.state = 0;
                } else {
                    int dist = p.size();
                    int need = dist * 2 + 10;
                    if(need > f.max_fuel) need = f.max_fuel;
                    
                    int load_f = need - f.fuel;
                    if(load_f > 0 && bb.fuel > 0) {
                        int actual = min(load_f, bb.fuel);
                        output_cmds.push_back("fuel " + to_string(f.id) + " " + to_string(actual));
                        f.fuel += actual;
                        bb.fuel -= actual;
                    }
                    
                    int space = f.max_missiles - f.missiles;
                    if(space > 0 && bb.missiles > 0) {
                        int actual = min(space, bb.missiles);
                        output_cmds.push_back("missile " + to_string(f.id) + " " + to_string(actual));
                        f.missiles += actual;
                        bb.missiles -= actual;
                    }
                    
                    f.path = p;
                    f.path_idx = 0;
                    f.state = 3; // MOVING_TO_TARGET
                }
            }
            // State 3: MOVING_TO_TARGET
            else if(f.state == 3) {
                RedBase& rb = red_bases[f.target_rb_idx];
                if(rb.destroyed) {
                    f.state = 0;
                } else {
                    if(f.path_idx < f.path.size()) {
                        int d = f.path[f.path_idx];
                        if(f.fuel > 0) {
                            output_cmds.push_back("move " + to_string(f.id) + " " + to_string(d));
                            f.x += dx[d];
                            f.y += dy[d];
                            f.fuel--;
                            f.path_idx++;
                        } else {
                            f.state = 0;
                        }
                    }
                    if(f.path_idx >= f.path.size()) {
                        f.state = 4; // ATTACKING
                    }
                }
            }
            // State 4: ATTACKING
            else if(f.state == 4) {
                RedBase& rb = red_bases[f.target_rb_idx];
                if(rb.destroyed) {
                    f.state = 0;
                } else {
                    int dir = -1;
                    for(int k=0; k<4; ++k) {
                        if(f.x + dx[k] == rb.x && f.y + dy[k] == rb.y) {
                            dir = k; break;
                        }
                    }
                    if(dir != -1) {
                        int amt = min(f.missiles, rb.hp);
                        if(amt > 0) {
                            output_cmds.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(amt));
                            f.missiles -= amt;
                            rb.hp -= amt;
                            rb.pending_damage -= amt;
                            if(rb.pending_damage < 0) rb.pending_damage = 0;
                            
                            if(rb.hp <= 0) {
                                rb.destroyed = true;
                                grid_map[rb.x][rb.y] = '.';
                            }
                        }
                        if(f.missiles == 0 || rb.destroyed) f.state = 0;
                    } else {
                        f.state = 0;
                    }
                }
            }
        }
        
        for(const string& s : output_cmds) cout << s << "\n";
        cout << "OK" << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}