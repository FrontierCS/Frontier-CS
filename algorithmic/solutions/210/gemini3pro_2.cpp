#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <deque>
#include <algorithm>
#include <tuple>
#include <cmath>

using namespace std;

// --- Data Structures ---

struct Pos {
    int r, c;
    bool operator==(const Pos& other) const { return r == other.r && c == other.c; }
    bool operator!=(const Pos& other) const { return !(*this == other); }
};

struct BlueBase {
    int id;
    Pos p;
    int fuel;
    int missiles;
};

struct RedBase {
    int id;
    Pos p;
    int hp;
    int max_hp;
    int value;
    bool destroyed;
    int planned_damage;
};

struct Action {
    int type; // 0: move, 1: fuel, 2: missile, 3: attack
    int val1; // dir / amt / amt / id
    int val2; // - / - / - / dir
    int val3; // - / - / - / count
};

struct Fighter {
    int id;
    Pos p;
    int fuel;
    int missiles;
    int max_fuel;
    int max_missiles;
    
    deque<Action> action_queue;
    bool busy;
};

// --- Globals ---

int N, M, K;
vector<string> grid_map;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;

int dr[] = {-1, 1, 0, 0}; // 0:up, 1:down
int dc[] = {0, 0, -1, 1}; // 2:left, 3:right

struct BBCache {
    bool valid = false;
    vector<vector<int>> dist;
    vector<vector<int>> parent_dir;
};
vector<BBCache> bb_caches;
vector<vector<int>> dist_to_nearest_blue;
bool map_changed = true;

// --- Helper Functions ---

bool is_valid_pos(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < M;
}

bool is_passable(int r, int c) {
    if (!is_valid_pos(r, c)) return false;
    return grid_map[r][c] != '#';
}

void update_nearest_blue() {
    dist_to_nearest_blue.assign(N, vector<int>(M, 1e9));
    queue<Pos> q;
    for (const auto& bb : blue_bases) {
        dist_to_nearest_blue[bb.p.r][bb.p.c] = 0;
        q.push(bb.p);
    }
    
    while (!q.empty()) {
        Pos curr = q.front(); q.pop();
        int d = dist_to_nearest_blue[curr.r][curr.c];
        
        for (int i = 0; i < 4; i++) {
            int nr = curr.r + dr[i];
            int nc = curr.c + dc[i];
            
            if (is_passable(nr, nc)) {
                if (dist_to_nearest_blue[nr][nc] > d + 1) {
                    dist_to_nearest_blue[nr][nc] = d + 1;
                    q.push({nr, nc});
                }
            }
        }
    }
}

void run_bfs(Pos start, vector<vector<int>>& dist, vector<vector<int>>& parent) {
    dist.assign(N, vector<int>(M, 1e9));
    parent.assign(N, vector<int>(M, -1));
    queue<Pos> q;
    
    dist[start.r][start.c] = 0;
    q.push(start);
    
    while (!q.empty()) {
        Pos curr = q.front(); q.pop();
        int d = dist[curr.r][curr.c];
        
        for (int i = 0; i < 4; i++) {
            int nr = curr.r + dr[i];
            int nc = curr.c + dc[i];
            
            if (is_passable(nr, nc)) {
                if (dist[nr][nc] > d + 1) {
                    dist[nr][nc] = d + 1;
                    parent[nr][nc] = i;
                    q.push({nr, nc});
                }
            }
        }
    }
}

void add_move_commands(Fighter& f, Pos end, const vector<vector<int>>& parent) {
    vector<int> path;
    Pos curr = end;
    while (curr != f.p) {
        int dir = parent[curr.r][curr.c];
        if (dir == -1) break;
        path.push_back(dir);
        curr.r -= dr[dir];
        curr.c -= dc[dir];
    }
    reverse(path.begin(), path.end());
    for (int d : path) {
        f.action_queue.push_back({0, d, 0, 0});
    }
}

void add_move_commands_from_base(Fighter& f, Pos start, Pos end, const vector<vector<int>>& parent) {
    vector<int> path;
    Pos curr = end;
    while (curr != start) {
        int dir = parent[curr.r][curr.c];
        if (dir == -1) break;
        path.push_back(dir);
        curr.r -= dr[dir];
        curr.c -= dc[dir];
    }
    reverse(path.begin(), path.end());
    for (int d : path) {
        f.action_queue.push_back({0, d, 0, 0});
    }
}

void plan_mission(int fid) {
    if (map_changed) {
        update_nearest_blue();
        for(auto& c : bb_caches) c.valid = false;
        map_changed = false;
    }
    
    Fighter& f = fighters[fid];
    
    vector<vector<int>> dist_f, parent_f;
    run_bfs(f.p, dist_f, parent_f);
    
    double best_score = -1.0;
    int best_bb_idx = -1;
    int best_rb_idx = -1;
    Pos best_attack_pos = {-1, -1};
    int best_fuel_to_take = 0;
    int best_missiles_to_take = 0;
    
    for (int i = 0; i < blue_bases.size(); i++) {
        BlueBase& bb = blue_bases[i];
        int dist_to_bb = dist_f[bb.p.r][bb.p.c];
        
        if (dist_to_bb > f.fuel) continue;
        if (bb.fuel <= 0 && bb.missiles <= 0) continue;
        
        if (!bb_caches[i].valid) {
            run_bfs(bb.p, bb_caches[i].dist, bb_caches[i].parent_dir);
            bb_caches[i].valid = true;
        }
        const auto& dist_b = bb_caches[i].dist;
        
        for (int j = 0; j < red_bases.size(); j++) {
            RedBase& rb = red_bases[j];
            if (rb.destroyed) continue;
            if (rb.planned_damage >= rb.hp) continue;
            
            Pos attack_pos = {-1, -1};
            int min_dist = 1e9;
            
            for (int d = 0; d < 4; d++) {
                int nr = rb.p.r + dr[d];
                int nc = rb.p.c + dc[d];
                if (is_passable(nr, nc)) {
                    if (dist_b[nr][nc] < min_dist) {
                        min_dist = dist_b[nr][nc];
                        attack_pos = {nr, nc};
                    }
                }
            }
            
            if (min_dist == 1e9) continue;
            
            int dist_bb_to_atk = min_dist;
            int dist_return = dist_to_nearest_blue[attack_pos.r][attack_pos.c];
            
            if (dist_return == 1e9) continue;
            
            int fuel_needed_for_trip = dist_bb_to_atk;
            int total_fuel_req = fuel_needed_for_trip + dist_return;
            
            if (total_fuel_req > f.max_fuel) continue;
            if (fuel_needed_for_trip > bb.fuel) continue;
            
            int missiles_needed = min({f.max_missiles, rb.hp - rb.planned_damage, bb.missiles});
            if (missiles_needed <= 0) continue;
            
            double time_cost = dist_to_bb + dist_bb_to_atk + 1.0;
            double score = (double)rb.value / (time_cost + 1e-5);
            score += (double)rb.value * 0.0001; 
            
            if (score > best_score) {
                best_score = score;
                best_bb_idx = i;
                best_rb_idx = j;
                best_attack_pos = attack_pos;
                best_missiles_to_take = missiles_needed;
                
                int desired_fuel = total_fuel_req + 15; // Safety margin
                best_fuel_to_take = min(f.max_fuel, desired_fuel);
                best_fuel_to_take = min(best_fuel_to_take, bb.fuel);
            }
        }
    }
    
    if (best_bb_idx != -1) {
        f.busy = true;
        BlueBase& bb = blue_bases[best_bb_idx];
        RedBase& rb = red_bases[best_rb_idx];
        
        add_move_commands(f, bb.p, parent_f);
        
        f.action_queue.push_back({1, best_fuel_to_take, 0, 0});
        f.action_queue.push_back({2, best_missiles_to_take, 0, 0});
        
        bb.fuel -= best_fuel_to_take;
        bb.missiles -= best_missiles_to_take;
        rb.planned_damage += best_missiles_to_take;
        
        add_move_commands_from_base(f, bb.p, best_attack_pos, bb_caches[best_bb_idx].parent_dir);
        
        int dir = -1;
        for (int d = 0; d < 4; d++) {
            if (best_attack_pos.r + dr[d] == rb.p.r && best_attack_pos.c + dc[d] == rb.p.c) {
                dir = d; break;
            }
        }
        f.action_queue.push_back({3, rb.id, dir, best_missiles_to_take});
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    grid_map.resize(N);
    for(int i=0; i<N; i++) cin >> grid_map[i];
    
    int num_blue; cin >> num_blue;
    blue_bases.resize(num_blue);
    bb_caches.resize(num_blue);
    for(int i=0; i<num_blue; i++) {
        blue_bases[i].id = i;
        cin >> blue_bases[i].p.r >> blue_bases[i].p.c;
        int dummy_d, dummy_v;
        cin >> blue_bases[i].fuel >> blue_bases[i].missiles >> dummy_d >> dummy_v;
    }
    
    int num_red; cin >> num_red;
    red_bases.resize(num_red);
    for(int i=0; i<num_red; i++) {
        red_bases[i].id = i;
        cin >> red_bases[i].p.r >> red_bases[i].p.c;
        int dummy_g, dummy_c;
        cin >> dummy_g >> dummy_c >> red_bases[i].hp >> red_bases[i].value;
        red_bases[i].max_hp = red_bases[i].hp;
        red_bases[i].destroyed = false;
        red_bases[i].planned_damage = 0;
    }
    
    cin >> K;
    fighters.resize(K);
    for(int i=0; i<K; i++) {
        fighters[i].id = i;
        cin >> fighters[i].p.r >> fighters[i].p.c >> fighters[i].max_fuel >> fighters[i].max_missiles;
        fighters[i].fuel = 0;
        fighters[i].missiles = 0;
        fighters[i].busy = false;
    }
    
    for (int frame = 0; frame < 15000; frame++) {
        bool any_active = false;
        
        for (int i = 0; i < K; i++) {
            Fighter& f = fighters[i];
            
            if (f.action_queue.empty()) {
                f.busy = false;
                plan_mission(i);
            }
            
            if (!f.action_queue.empty()) {
                any_active = true;
                Action act = f.action_queue.front();
                f.action_queue.pop_front();
                
                if (act.type == 0) {
                    cout << "move " << f.id << " " << act.val1 << "\n";
                    f.p.r += dr[act.val1];
                    f.p.c += dc[act.val1];
                    f.fuel--;
                } else if (act.type == 1) {
                    cout << "fuel " << f.id << " " << act.val1 << "\n";
                    f.fuel += act.val1;
                } else if (act.type == 2) {
                    cout << "missile " << f.id << " " << act.val1 << "\n";
                    f.missiles += act.val1;
                } else if (act.type == 3) {
                    cout << "attack " << f.id << " " << act.val2 << " " << act.val3 << "\n";
                    f.missiles -= act.val3;
                    
                    int tr = f.p.r + dr[act.val2];
                    int tc = f.p.c + dc[act.val2];
                    for (auto& rb : red_bases) {
                        if (!rb.destroyed && rb.p.r == tr && rb.p.c == tc) {
                            rb.hp -= act.val3;
                            if (rb.hp <= 0) {
                                rb.destroyed = true;
                                grid_map[tr][tc] = '.';
                                map_changed = true;
                            }
                            break;
                        }
                    }
                }
            }
        }
        
        cout << "OK" << endl;
        
        if (!any_active) {
            bool all_idle = true;
            for(const auto& f : fighters) if(f.busy) all_idle = false;
            if(all_idle) break;
        }
    }
    
    return 0;
}