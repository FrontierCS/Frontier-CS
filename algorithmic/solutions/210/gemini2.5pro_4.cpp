#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <deque>
#include <cmath>
#include <map>
#include <algorithm>
#include <tuple>

using namespace std;

// --- Data Structures ---

using Point = pair<int, int>;

// Map: y, x for (row, col)
int N, M, K;
vector<string> grid_map;

struct BlueBase {
    int id;
    Point pos;
    long long fuel_supply;
    long long missile_supply;
};
vector<BlueBase> blue_bases;

struct RedBase {
    int id;
    Point pos;
    int defense;
    int value;
    int damage_taken;
    bool is_destroyed;
};
vector<RedBase> red_bases;

struct Fighter {
    int id;
    Point pos;
    long long fuel;
    long long missiles;
    long long max_fuel;
    long long max_missiles;

    enum State {
        IDLE,
        GOING_TO_BASE,
        RESUPPLYING,
        GOING_TO_TARGET,
        ATTACKING,
        RETURNING_TO_BASE
    } state = IDLE;

    int target_red_base_id = -1;
    int assigned_blue_base_id = -1;
    Point attack_pos;
    deque<Point> path;
};
vector<Fighter> fighters;

map<int, long long> red_base_assigned_missiles;
vector<vector<int>> bb_to_rb_dist;

// --- Pathfinding ---

const int dr[] = {-1, 1, 0, 0}; // 0:U, 1:D, 2:L, 3:R
const int dc[] = {0, 0, -1, 1};

struct BFSResult {
    vector<vector<int>> dist;
    vector<vector<Point>> parent;
};

BFSResult bfs(Point start) {
    BFSResult res;
    res.dist.assign(N, vector<int>(M, -1));
    res.parent.assign(N, vector<Point>(M, {-1, -1}));
    
    queue<Point> q;

    if (start.first < 0 || start.first >= N || start.second < 0 || start.second >= M) return res;

    res.dist[start.first][start.second] = 0;
    q.push(start);

    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        for (int i = 0; i < 4; ++i) {
            int nr = curr.first + dr[i];
            int nc = curr.second + dc[i];

            if (nr >= 0 && nr < N && nc >= 0 && nc < M && grid_map[nr][nc] != '#' && res.dist[nr][nc] == -1) {
                res.dist[nr][nc] = res.dist[curr.first][curr.second] + 1;
                res.parent[nr][nc] = curr;
                q.push({nr, nc});
            }
        }
    }
    return res;
}

deque<Point> reconstruct_path(Point start, Point end, const BFSResult& bfs_res) {
    deque<Point> path;
    if (bfs_res.dist[end.first][end.second] == -1) return path;

    Point curr = end;
    while (curr.first != start.first || curr.second != start.second) {
        path.push_front(curr);
        curr = bfs_res.parent[curr.first][curr.second];
        if (curr.first == -1) return {};
    }
    return path;
}

int get_direction(Point from, Point to) {
    if (to.first < from.first) return 0; // Up
    if (to.first > from.first) return 1; // Down
    if (to.second < from.second) return 2; // Left
    if (to.second > from.second) return 3; // Right
    return -1;
}

void precompute_distances() {
    bb_to_rb_dist.assign(blue_bases.size(), vector<int>(red_bases.size()));
    for(size_t i = 0; i < blue_bases.size(); ++i) {
        BFSResult res = bfs(blue_bases[i].pos);
        for(size_t j = 0; j < red_bases.size(); ++j) {
            int min_dist = 1e9;
            Point target_pos = red_bases[j].pos;
            for(int k=0; k<4; ++k){
                int nr = target_pos.first + dr[k];
                int nc = target_pos.second + dc[k];
                if(nr >= 0 && nr < N && nc >= 0 && nc < M && grid_map[nr][nc] != '#'){
                    if(res.dist[nr][nc] != -1) {
                        min_dist = min(min_dist, res.dist[nr][nc]);
                    }
                }
            }
            bb_to_rb_dist[i][j] = min_dist;
        }
    }
}

void dispatcher() {
    vector<int> idle_fighters;
    for (const auto& f : fighters) {
        if (f.state == Fighter::IDLE) {
            idle_fighters.push_back(f.id);
        }
    }

    if (idle_fighters.empty()) return;

    vector<int> available_targets;
    for(const auto& rb : red_bases) {
        if (!rb.is_destroyed) {
            available_targets.push_back(rb.id);
        }
    }

    for (int f_id : idle_fighters) {
        double best_score = -1.0;
        int best_target_id = -1;

        for (int rb_id : available_targets) {
            const auto& rb = red_bases[rb_id];
            
            long long needed_missiles = rb.defense - (rb.damage_taken + red_base_assigned_missiles[rb.id]);
            if (needed_missiles <= 0) continue;

            int best_dist_to_blue_base = 1e9;
            for(size_t bb_id = 0; bb_id < blue_bases.size(); ++bb_id) {
                best_dist_to_blue_base = min(best_dist_to_blue_base, bb_to_rb_dist[bb_id][rb_id]);
            }
            if(best_dist_to_blue_base == 1e9) continue;
            
            double score = (double)rb.value / (double)(max(1LL, needed_missiles) * max(1, best_dist_to_blue_base));
            if (score > best_score) {
                best_score = score;
                best_target_id = rb_id;
            }
        }
        
        if (best_target_id != -1) {
            auto& f = fighters[f_id];
            f.target_red_base_id = best_target_id;
            
            int best_bb_id = -1;
            int min_dist = 1e9;
            for (size_t bb_id=0; bb_id < blue_bases.size(); ++bb_id) {
                if (bb_to_rb_dist[bb_id][best_target_id] < min_dist) {
                    min_dist = bb_to_rb_dist[bb_id][best_target_id];
                    best_bb_id = bb_id;
                }
            }
            if (best_bb_id == -1) continue;
            f.assigned_blue_base_id = best_bb_id;

            red_base_assigned_missiles[f.target_red_base_id] += f.max_missiles * 10; 

            if (f.pos == blue_bases[best_bb_id].pos) {
                f.state = Fighter::RESUPPLYING;
            } else {
                f.state = Fighter::GOING_TO_BASE;
                BFSResult res = bfs(f.pos);
                f.path = reconstruct_path(f.pos, blue_bases[best_bb_id].pos, res);
            }
        }
    }
}

void read_input() {
    cin >> N >> M;
    grid_map.resize(N);
    for (int i = 0; i < N; ++i) cin >> grid_map[i];

    int num_blue_bases;
    cin >> num_blue_bases;
    blue_bases.resize(num_blue_bases);
    for (int i = 0; i < num_blue_bases; ++i) {
        blue_bases[i].id = i;
        cin >> blue_bases[i].pos.second >> blue_bases[i].pos.first;
        long long d, v;
        cin >> blue_bases[i].fuel_supply >> blue_bases[i].missile_supply >> d >> v;
    }

    int num_red_bases;
    cin >> num_red_bases;
    red_bases.resize(num_red_bases);
    for (int i = 0; i < num_red_bases; ++i) {
        red_bases[i].id = i;
        cin >> red_bases[i].pos.second >> red_bases[i].pos.first;
        long long g, c;
        cin >> g >> c >> red_bases[i].defense >> red_bases[i].value;
        red_bases[i].damage_taken = 0;
        red_bases[i].is_destroyed = false;
    }

    cin >> K;
    fighters.resize(K);
    for (int i = 0; i < K; ++i) {
        fighters[i].id = i;
        cin >> fighters[i].pos.second >> fighters[i].pos.first;
        cin >> fighters[i].max_fuel >> fighters[i].max_missiles;
        fighters[i].fuel = 0;
        fighters[i].missiles = 0;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    read_input();
    precompute_distances();

    for (int frame = 0; frame < 15000; ++frame) {
        bool all_destroyed = true;
        for (const auto& rb : red_bases) {
            if (!rb.is_destroyed) {
                all_destroyed = false;
                break;
            }
        }
        if (all_destroyed) break;

        dispatcher();

        vector<string> commands;

        for (auto& f : fighters) {
            if (f.state == Fighter::IDLE) {
                // Do nothing
            } else if (f.state == Fighter::GOING_TO_BASE) {
                if (f.path.empty()) {
                    if (f.pos == blue_bases[f.assigned_blue_base_id].pos) {
                        f.state = Fighter::RESUPPLYING;
                    } else {
                        f.state = Fighter::IDLE;
                    }
                    continue;
                }
                Point next_pos = f.path.front();
                int dir = get_direction(f.pos, next_pos);
                commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                f.pos = next_pos;
                f.fuel--;
                f.path.pop_front();
                 if (f.path.empty()) {
                    f.state = Fighter::RESUPPLYING;
                }
            } else if (f.state == Fighter::RESUPPLYING) {
                auto& bb = blue_bases[f.assigned_blue_base_id];

                long long fuel_to_take = min(f.max_fuel - f.fuel, bb.fuel_supply);
                if (fuel_to_take > 0) {
                    commands.push_back("fuel " + to_string(f.id) + " " + to_string(fuel_to_take));
                    f.fuel += fuel_to_take;
                    bb.fuel_supply -= fuel_to_take;
                }

                long long missiles_to_take = min(f.max_missiles - f.missiles, bb.missile_supply);
                if (missiles_to_take > 0) {
                    commands.push_back("missile " + to_string(f.id) + " " + to_string(missiles_to_take));
                    f.missiles += missiles_to_take;
                    bb.missile_supply -= missiles_to_take;
                }
                
                f.state = Fighter::GOING_TO_TARGET;
                Point target_pos = red_bases[f.target_red_base_id].pos;
                
                BFSResult res = bfs(f.pos);
                int min_dist = 1e9;
                Point best_attack_pos = {-1,-1};
                for(int i=0; i<4; ++i){
                    int nr = target_pos.first + dr[i];
                    int nc = target_pos.second + dc[i];
                    if(nr >= 0 && nr < N && nc >= 0 && nc < M && grid_map[nr][nc] != '#'){
                        if(res.dist[nr][nc] != -1 && res.dist[nr][nc] < min_dist){
                            min_dist = res.dist[nr][nc];
                            best_attack_pos = {nr, nc};
                        }
                    }
                }
                if(best_attack_pos.first != -1) {
                    f.attack_pos = best_attack_pos;
                    f.path = reconstruct_path(f.pos, f.attack_pos, res);
                } else {
                    f.state = Fighter::IDLE;
                }
            } else if (f.state == Fighter::GOING_TO_TARGET) {
                int dist_to_safety = 1e9;
                BFSResult res = bfs(f.pos);
                for(const auto& bb: blue_bases) {
                    if(res.dist[bb.pos.first][bb.pos.second] != -1)
                        dist_to_safety = min(dist_to_safety, res.dist[bb.pos.first][bb.pos.second]);
                }
                if(f.fuel <= dist_to_safety + 2) {
                    f.state = Fighter::RETURNING_TO_BASE;
                    int nearest_bb_id = -1;
                    if(dist_to_safety != 1e9) {
                        for(const auto& bb: blue_bases) {
                            if(res.dist[bb.pos.first][bb.pos.second] == dist_to_safety) {
                                nearest_bb_id = bb.id;
                                break;
                            }
                        }
                    }
                    if(nearest_bb_id != -1) {
                        f.assigned_blue_base_id = nearest_bb_id;
                        f.path = reconstruct_path(f.pos, blue_bases[nearest_bb_id].pos, res);
                    } else {
                        f.state = Fighter::IDLE;
                    }
                    continue;
                }

                if (f.path.empty()) {
                     if (f.pos == f.attack_pos) {
                        f.state = Fighter::ATTACKING;
                    } else {
                        f.state = Fighter::IDLE;
                    }
                    continue;
                }
                Point next_pos = f.path.front();
                int dir = get_direction(f.pos, next_pos);
                commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                f.pos = next_pos;
                f.fuel--;
                f.path.pop_front();
                 if (f.path.empty()) {
                    f.state = Fighter::ATTACKING;
                }
            } else if (f.state == Fighter::ATTACKING) {
                auto& rb = red_bases[f.target_red_base_id];
                if (rb.is_destroyed) {
                    f.state = Fighter::IDLE;
                    continue;
                }

                int missiles_to_fire = min((long long)f.missiles, (long long)rb.defense - rb.damage_taken);
                if (missiles_to_fire > 0) {
                    Point target_pos = rb.pos;
                    int dir = get_direction(f.pos, target_pos);
                    commands.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(missiles_to_fire));
                    f.missiles -= missiles_to_fire;
                    rb.damage_taken += missiles_to_fire;

                    if (rb.damage_taken >= rb.defense) {
                        rb.is_destroyed = true;
                        grid_map[rb.pos.first][rb.pos.second] = '.';
                        red_base_assigned_missiles.erase(rb.id);

                        for(auto& other_f : fighters) {
                            if (other_f.target_red_base_id == rb.id) {
                                other_f.state = Fighter::IDLE;
                                other_f.target_red_base_id = -1;
                            }
                        }
                    }
                }
                
                if (f.missiles == 0 && !rb.is_destroyed) {
                    f.state = Fighter::RETURNING_TO_BASE;
                    BFSResult res = bfs(f.pos);
                    f.path = reconstruct_path(f.pos, blue_bases[f.assigned_blue_base_id].pos, res);
                } else if (rb.is_destroyed) {
                    f.state = Fighter::IDLE;
                }
            } else if (f.state == Fighter::RETURNING_TO_BASE) {
                if (f.path.empty()) {
                    if (f.pos == blue_bases[f.assigned_blue_base_id].pos) {
                        if (f.target_red_base_id != -1 && !red_bases[f.target_red_base_id].is_destroyed) {
                             f.state = Fighter::RESUPPLYING;
                        } else {
                            f.state = Fighter::IDLE;
                        }
                    } else {
                        f.state = Fighter::IDLE;
                    }
                    continue;
                }
                Point next_pos = f.path.front();
                int dir = get_direction(f.pos, next_pos);
                commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                f.pos = next_pos;
                f.fuel--;
                f.path.pop_front();
                if (f.path.empty()) {
                     if (f.target_red_base_id != -1 && !red_bases[f.target_red_base_id].is_destroyed) {
                        f.state = Fighter::RESUPPLYING;
                    } else {
                        f.state = Fighter::IDLE;
                    }
                }
            }
        }

        for (const auto& cmd : commands) {
            cout << cmd << endl;
        }
        cout << "OK" << endl;
    }

    return 0;
}