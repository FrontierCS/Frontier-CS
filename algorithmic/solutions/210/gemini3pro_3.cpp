#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <cmath>

using namespace std;

// Constants
const int MAX_FRAMES = 15000;
const int DR[] = {-1, 1, 0, 0}; // 0: up, 1: down, 2: left, 3: right
const int DC[] = {0, 0, -1, 1};

struct Pos {
    int r, c;
    bool operator==(const Pos& other) const { return r == other.r && c == other.c; }
    bool operator!=(const Pos& other) const { return !(*this == other); }
    int dist(const Pos& other) const { return abs(r - other.r) + abs(c - other.c); }
};

struct BlueBase {
    int id;
    Pos p;
    int fuel, missiles;
};

struct RedBase {
    int id;
    Pos p;
    int defense; 
    int hp;      
    int value;
    bool destroyed;
    int pending_damage; 
};

struct Fighter {
    int id;
    Pos p;
    int max_fuel, max_missiles;
    int fuel, missiles;
    
    // AI State
    int state; // 0: IDLE, 1: MOVING_TO_BASE, 2: RESUPPLY, 3: MOVING_TO_TARGET, 4: ATTACK
    int target_base_id; // For MOVING_TO_TARGET and ATTACK
    int target_blue_id; // For MOVING_TO_BASE
    int expected_damage; // Damage committed to current target
    
    vector<int> path_moves; // sequence of directions
    int path_idx;
};

// Global Data
int N, M;
vector<string> grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
int K;

// Helper to check bounds and obstacles
bool is_passable(int r, int c) {
    if (r < 0 || r >= N || c < 0 || c >= M) return false;
    // '#' is obstacle (undestroyed red base), '.' and '*' are passable. 
    // We update grid to '.' when a red base is destroyed.
    return grid[r][c] != '#';
}

// BFS to find path from start to goal
vector<int> find_path(Pos start, Pos goal, bool adjacent_goal) {
    if (!adjacent_goal && start == goal) return {};
    if (adjacent_goal && start.dist(goal) == 1) return {};

    static int dist[205][205];
    static int from_dir[205][205];
    // Reset dist
    for(int i=0;i<N;++i) for(int j=0;j<M;++j) dist[i][j] = -1;
    
    queue<Pos> q;
    q.push(start);
    dist[start.r][start.c] = 0;
    
    Pos final_node = {-1, -1};
    
    while(!q.empty()){
        Pos u = q.front(); q.pop();
        
        // Check termination
        if (adjacent_goal) {
            if (u.dist(goal) == 1) {
                final_node = u;
                break;
            }
        } else {
            if (u == goal) {
                final_node = u;
                break;
            }
        }
        
        for(int d=0; d<4; ++d){
            int nr = u.r + DR[d];
            int nc = u.c + DC[d];
            if(is_passable(nr, nc) && dist[nr][nc] == -1){
                dist[nr][nc] = dist[u.r][u.c] + 1;
                from_dir[nr][nc] = d;
                q.push({nr, nc});
            }
        }
    }
    
    vector<int> moves;
    if (final_node.r != -1) {
        Pos curr = final_node;
        while(curr != start){
            int d = from_dir[curr.r][curr.c];
            moves.push_back(d);
            // Reverse move
            if (d == 0) curr.r++;
            else if (d == 1) curr.r--;
            else if (d == 2) curr.c++;
            else if (d == 3) curr.c--;
        }
        reverse(moves.begin(), moves.end());
    }
    return moves;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    grid.resize(N);
    for(int i=0; i<N; ++i) cin >> grid[i];
    
    int num_blue; cin >> num_blue;
    for(int i=0; i<num_blue; ++i){
        int x, y, g, c, d, v;
        cin >> x >> y >> g >> c >> d >> v;
        blue_bases.push_back({i, {x, y}, g, c});
    }
    
    int num_red; cin >> num_red;
    for(int i=0; i<num_red; ++i){
        int x, y, g, c, d, v;
        cin >> x >> y >> g >> c >> d >> v;
        red_bases.push_back({i, {x, y}, d, d, v, false, 0});
    }
    
    cin >> K;
    for(int i=0; i<K; ++i){
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters.push_back({i, {x, y}, G, C, 0, 0, 0, -1, -1, 0, {}, 0});
    }
    
    for (int frame = 0; frame < MAX_FRAMES; ++frame) {
        vector<string> cmds;
        
        // Logic per fighter
        for(auto& f : fighters) {
            
            // State 0: IDLE - Plan
            if (f.state == 0) {
                // Heuristic target selection
                double best_score = -1.0;
                int best_rb_idx = -1;
                int best_bb_idx = -1;
                
                for (int r_idx = 0; r_idx < red_bases.size(); ++r_idx) {
                    RedBase& rb = red_bases[r_idx];
                    if (rb.destroyed || rb.hp - rb.pending_damage <= 0) continue;
                    
                    int best_dist_local = 1e9;
                    int local_bb = -1;
                    
                    for (int b_idx = 0; b_idx < blue_bases.size(); ++b_idx) {
                        BlueBase& bb = blue_bases[b_idx];
                        if (bb.fuel <= 0 && bb.missiles <= 0) continue; 
                        
                        int d1 = f.p.dist(bb.p);
                        int d2 = bb.p.dist(rb.p);
                        int total_dist = d1 + d2;
                        
                        if (total_dist < best_dist_local) {
                            best_dist_local = total_dist;
                            local_bb = b_idx;
                        }
                    }
                    
                    if (local_bb != -1) {
                        double score = (double)rb.value / (double)(best_dist_local + 10);
                        if (score > best_score) {
                            best_score = score;
                            best_rb_idx = r_idx;
                            best_bb_idx = local_bb;
                        }
                    }
                }
                
                if (best_rb_idx != -1) {
                    f.target_red_base_index = best_rb_idx;
                    f.target_blue_id = best_bb_idx;
                    
                    int capacity = f.max_missiles;
                    int supply = blue_bases[best_bb_idx].missiles;
                    int ammo = min(capacity, supply);
                    int needed = red_bases[best_rb_idx].hp - red_bases[best_rb_idx].pending_damage;
                    f.expected_damage = min(ammo, max(0, needed));
                    
                    red_bases[best_rb_idx].pending_damage += f.expected_damage;
                    
                    f.state = 1; // Moving to base
                    f.path_moves = find_path(f.p, blue_bases[best_bb_idx].p, false);
                    f.path_idx = 0;
                }
            }
            
            // State 1: MOVING_TO_BASE
            if (f.state == 1) {
                if (f.p == blue_bases[f.target_blue_id].p) {
                    f.state = 2; // Resupply
                } else {
                    if (f.fuel > 0) {
                         if (f.path_idx < f.path_moves.size()) {
                            int dir = f.path_moves[f.path_idx];
                            int nr = f.p.r + DR[dir];
                            int nc = f.p.c + DC[dir];
                            if (is_passable(nr, nc)) {
                                cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                                f.fuel--;
                                f.p = {nr, nc};
                                f.path_idx++;
                            } else {
                                f.path_moves = find_path(f.p, blue_bases[f.target_blue_id].p, false);
                                f.path_idx = 0;
                            }
                        } else {
                             f.path_moves = find_path(f.p, blue_bases[f.target_blue_id].p, false);
                             f.path_idx = 0;
                        }
                    } else {
                        // Attempt emergency refuel if on any base
                        int on_base = -1;
                        for(int b=0; b<blue_bases.size(); ++b) if(blue_bases[b].p == f.p) on_base = b;
                        if (on_base != -1) {
                            int need = f.max_fuel - f.fuel;
                            int take = min(need, blue_bases[on_base].fuel);
                            if (take > 0) {
                                blue_bases[on_base].fuel -= take;
                                f.fuel += take;
                                cmds.push_back("fuel " + to_string(f.id) + " " + to_string(take));
                            } else {
                                // Reset
                                if(f.target_red_base_index != -1) red_bases[f.target_red_base_index].pending_damage -= f.expected_damage;
                                f.expected_damage = 0;
                                f.target_red_base_index = -1;
                                f.state = 0;
                            }
                        } else {
                            // Stranded
                             if(f.target_red_base_index != -1) red_bases[f.target_red_base_index].pending_damage -= f.expected_damage;
                             f.expected_damage = 0;
                             f.target_red_base_index = -1;
                            f.state = 0; 
                        }
                    }
                }
            }
            
            // State 2: RESUPPLY
            if (f.state == 2) {
                BlueBase& bb = blue_bases[f.target_blue_id];
                
                int fuel_need = f.max_fuel - f.fuel;
                int fuel_take = min(fuel_need, bb.fuel);
                if (fuel_take > 0) {
                    bb.fuel -= fuel_take;
                    f.fuel += fuel_take;
                    cmds.push_back("fuel " + to_string(f.id) + " " + to_string(fuel_take));
                }
                
                int ammo_need = f.max_missiles - f.missiles;
                int ammo_take = min(ammo_need, bb.missiles);
                if (ammo_take > 0) {
                    bb.missiles -= ammo_take;
                    f.missiles += ammo_take;
                    cmds.push_back("missile " + to_string(f.id) + " " + to_string(ammo_take));
                }
                
                if (f.fuel > 0 && f.missiles > 0) {
                    f.state = 3;
                    f.path_moves = find_path(f.p, red_bases[f.target_red_base_index].p, true);
                    f.path_idx = 0;
                } else {
                    if (bb.fuel == 0 && bb.missiles == 0) {
                        if(f.target_red_base_index != -1) red_bases[f.target_red_base_index].pending_damage -= f.expected_damage;
                        f.expected_damage = 0;
                        f.target_red_base_index = -1;
                        f.state = 0;
                    }
                }
            } else if (f.state == 3) {
                // MOVING_TO_TARGET
                RedBase& rb = red_bases[f.target_red_base_index];
                
                if (rb.destroyed) {
                    if(f.target_red_base_index != -1) red_bases[f.target_red_base_index].pending_damage -= f.expected_damage;
                    f.expected_damage = 0;
                    f.target_red_base_index = -1;
                    f.state = 0;
                } else {
                    if (f.p.dist(rb.p) == 1) {
                        f.state = 4; // Attack
                    } else {
                        if (f.fuel > 0) {
                            if (f.path_idx < f.path_moves.size()) {
                                int dir = f.path_moves[f.path_idx];
                                int nr = f.p.r + DR[dir];
                                int nc = f.p.c + DC[dir];
                                if (is_passable(nr, nc)) {
                                    cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                                    f.fuel--;
                                    f.p = {nr, nc};
                                    f.path_idx++;
                                    if (f.p.dist(rb.p) == 1) f.state = 4;
                                } else {
                                    f.path_moves = find_path(f.p, rb.p, true);
                                    f.path_idx = 0;
                                }
                            } else {
                                f.path_moves = find_path(f.p, rb.p, true);
                                f.path_idx = 0;
                            }
                        } else {
                             if(f.target_red_base_index != -1) red_bases[f.target_red_base_index].pending_damage -= f.expected_damage;
                             f.expected_damage = 0;
                             f.target_red_base_index = -1;
                            f.state = 0;
                        }
                    }
                }
            }
            
            if (f.state == 4) {
                // ATTACK
                RedBase& rb = red_bases[f.target_red_base_index];
                if (rb.destroyed) {
                     if(f.target_red_base_index != -1) red_bases[f.target_red_base_index].pending_damage -= f.expected_damage;
                     f.expected_damage = 0;
                     f.target_red_base_index = -1;
                    f.state = 0;
                } else {
                    if (f.missiles > 0) {
                        int dir = -1;
                        for(int k=0; k<4; ++k){
                            if (f.p.r + DR[k] == rb.p.r && f.p.c + DC[k] == rb.p.c) {
                                dir = k;
                                break;
                            }
                        }
                        
                        if (dir != -1) {
                            int amount = min(f.missiles, rb.hp);
                            cmds.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(amount));
                            f.missiles -= amount;
                            rb.hp -= amount;
                            rb.pending_damage -= amount; 
                            f.expected_damage -= amount;
                            if (rb.pending_damage < 0) rb.pending_damage = 0;
                            if (f.expected_damage < 0) f.expected_damage = 0;

                            if (rb.hp <= 0) {
                                rb.destroyed = true;
                                rb.hp = 0;
                                grid[rb.p.r][rb.p.c] = '.';
                                
                                if(f.target_red_base_index != -1) rb.pending_damage -= f.expected_damage;
                                f.expected_damage = 0;
                                f.target_red_base_index = -1;
                                f.state = 0;
                            }
                        } else {
                            f.state = 3; 
                        }
                    } else {
                        if(f.target_red_base_index != -1) rb.pending_damage -= f.expected_damage;
                        f.expected_damage = 0;
                        f.target_red_base_index = -1;
                        f.state = 0; 
                    }
                }
            }
        }
        
        for(const auto& s : cmds) cout << s << "\n";
        cout << "OK" << endl;
    }
    
    return 0;
}