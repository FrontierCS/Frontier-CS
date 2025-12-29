#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>

using namespace std;

// --- Utilities ---
struct Pos {
    int r, c;

    bool operator==(const Pos& other) const {
        return r == other.r && c == other.c;
    }
    bool operator!=(const Pos& other) const {
        return !(*this == other);
    }
    bool operator<(const Pos& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

int dist_mah(const Pos& a, const Pos& b) {
    return abs(a.r - b.r) + abs(a.c - b.c);
}

// --- Constants and Global State ---
int N, M;
struct Pet { Pos pos; int type; };
vector<Pet> pets;
vector<Pos> humans;
bool is_impassable[32][32];

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_chars[] = {'U', 'D', 'L', 'R'};
char build_chars[] = {'u', 'd', 'l', 'r'};

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// --- Pathfinding ---
int dists[32][32];
Pos parent[32][32];
const int INF = 1e9;

void bfs(Pos start, const vector<vector<int>>& costs) {
    for (int i = 1; i <= 30; ++i) {
        for (int j = 1; j <= 30; ++j) {
            dists[i][j] = INF;
            parent[i][j] = {-1, -1};
        }
    }

    deque<Pos> q;
    dists[start.r][start.c] = 0;
    q.push_back(start);

    while (!q.empty()) {
        Pos curr = q.front();
        q.pop_front();

        for (int i = 0; i < 4; ++i) {
            Pos next = {curr.r + dr[i], curr.c + dc[i]};
            if (next.r < 1 || next.r > 30 || next.c < 1 || next.c > 30 || is_impassable[next.r][next.c]) {
                continue;
            }
            int cost = costs[next.r][next.c];
            if (dists[curr.r][curr.c] + cost < dists[next.r][next.c]) {
                dists[next.r][next.c] = dists[curr.r][curr.c] + cost;
                parent[next.r][next.c] = curr;
                if (cost == 1) q.push_front(next);
                else q.push_back(next);
            }
        }
    }
}

// --- Main Strategy ---
vector<Pos> walls_to_build;
Pos enclosure_tl, enclosure_br;
Pos safe_spot;

void plan_enclosure() {
    int side_len = 15 + M;
    if (side_len > 28) side_len = 28;

    vector<pair<Pos, Pos>> candidates;
    candidates.push_back({{1, 1}, {side_len, side_len}}); // TL
    candidates.push_back({{1, 30 - side_len + 1}, {side_len, 30}}); // TR
    candidates.push_back({{30 - side_len + 1, 1}, {30, side_len}}); // BL
    candidates.push_back({{30 - side_len + 1, 30 - side_len + 1}, {30, 30}}); // BR

    double best_score = -1e18;
    int best_idx = -1;

    for (int i = 0; i < 4; ++i) {
        auto [tl, br] = candidates[i];
        int pets_inside = 0;
        for (const auto& pet : pets) {
            if (pet.pos.r >= tl.r && pet.pos.r <= br.r && pet.pos.c >= tl.c && pet.pos.c <= br.c) {
                pets_inside++;
            }
        }

        long long human_dist_sum = 0;
        for (const auto& h : humans) {
            int min_dist = INF;
            if (tl.r > 1) for(int c=tl.c; c<=br.c; ++c) min_dist = min(min_dist, dist_mah(h, {tl.r-1,c}));
            if (br.r < 30) for(int c=tl.c; c<=br.c; ++c) min_dist = min(min_dist, dist_mah(h, {br.r+1,c}));
            if (tl.c > 1) for(int r=tl.r; r<=br.r; ++r) min_dist = min(min_dist, dist_mah(h, {r,tl.c-1}));
            if (br.c < 30) for(int r=tl.r; r<=br.r; ++r) min_dist = min(min_dist, dist_mah(h, {r,br.c+1}));
            human_dist_sum += min_dist;
        }

        double score = -pets_inside * 10000.0 - human_dist_sum;
        if (score > best_score) {
            best_score = score;
            best_idx = i;
        }
    }
    
    enclosure_tl = candidates[best_idx].first;
    enclosure_br = candidates[best_idx].second;
    safe_spot = {(enclosure_tl.r + enclosure_br.r) / 2, (enclosure_tl.c + enclosure_br.c) / 2};

    if (enclosure_tl.r > 1) { // Top wall
        for (int c = enclosure_tl.c; c <= enclosure_br.c; ++c) walls_to_build.push_back({enclosure_tl.r - 1, c});
    }
    if (enclosure_br.r < 30) { // Bottom wall
        for (int c = enclosure_tl.c; c <= enclosure_br.c; ++c) walls_to_build.push_back({enclosure_br.r + 1, c});
    }
    if (enclosure_tl.c > 1) { // Left wall
        for (int r = enclosure_tl.r; r <= enclosure_br.r; ++r) walls_to_build.push_back({r, enclosure_tl.c - 1});
    }
    if (enclosure_br.c < 30) { // Right wall
        for (int r = enclosure_tl.r; r <= enclosure_br.r; ++r) walls_to_build.push_back({r, enclosure_br.c + 1});
    }
    sort(walls_to_build.begin(), walls_to_build.end());
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].pos.r >> pets[i].pos.c >> pets[i].type;
    }
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].r >> humans[i].c;
    }

    plan_enclosure();

    bool human_finished[M];
    fill(human_finished, human_finished + M, false);
    vector<Pos> human_targets(M, {-1, -1});

    for (int turn = 0; turn < 300; ++turn) {
        walls_to_build.erase(remove_if(walls_to_build.begin(), walls_to_build.end(), [&](const Pos& p){
            return is_impassable[p.r][p.c];
        }), walls_to_build.end());

        bool all_done = walls_to_build.empty();
        if(turn > 285) all_done = true;
        
        vector<vector<int>> path_costs(32, vector<int>(32, 1));
        bool is_pet_or_human[32][32] = {};
        for(const auto& p : pets) is_pet_or_human[p.pos.r][p.pos.c] = true;
        for(const auto& h : humans) is_pet_or_human[h.r][h.c] = true;
        
        for (const auto& p : pets) {
            for(int i=-1; i<=1; ++i) for(int j=-1; j<=1; ++j) {
                int nr = p.pos.r + i, nc = p.pos.c + j;
                if(nr >=1 && nr <= 30 && nc >= 1 && nc <= 30) {
                     path_costs[nr][nc] = 100;
                }
            }
        }

        string actions_str(M, '.');
        vector<int> p_order(M);
        iota(p_order.begin(), p_order.end(), 0);
        shuffle(p_order.begin(), p_order.end(), rng);
        
        bool pos_claimed[32][32] = {};

        if (!all_done) {
            vector<bool> wall_targeted(walls_to_build.size(), false);

            for (int i = 0; i < M; ++i) {
                bool needs_target = true;
                if (human_targets[i].r != -1) {
                    if (!is_impassable[human_targets[i].r][human_targets[i].c]) {
                        bool found = false;
                        for(size_t j = 0; j < walls_to_build.size(); ++j) {
                            if (walls_to_build[j] == human_targets[i]) {
                                wall_targeted[j] = true;
                                found = true;
                                break;
                            }
                        }
                        if (found) needs_target = false;
                    }
                }
                if (needs_target) human_targets[i] = {-1, -1};
            }

            for (int human_idx : p_order) {
                if(human_targets[human_idx].r != -1) continue;
                
                bfs(humans[human_idx], path_costs);
                int best_dist = INF;
                int best_wall_idx = -1;

                for (size_t i = 0; i < walls_to_build.size(); ++i) {
                    if (wall_targeted[i]) continue;
                    const auto& wall_pos = walls_to_build[i];
                    for(int j=0; j<4; ++j) {
                        Pos build_spot = {wall_pos.r - dr[j], wall_pos.c - dc[j]};
                        if (build_spot.r >= 1 && build_spot.r <= 30 && build_spot.c >= 1 && build_spot.c <= 30 && !is_impassable[build_spot.r][build_spot.c]) {
                            if (dists[build_spot.r][build_spot.c] < best_dist) {
                                best_dist = dists[build_spot.r][build_spot.c];
                                best_wall_idx = i;
                            }
                        }
                    }
                }
                if (best_wall_idx != -1) {
                    human_targets[human_idx] = walls_to_build[best_wall_idx];
                    wall_targeted[best_wall_idx] = true;
                } else {
                    human_finished[human_idx] = true;
                }
            }
        }

        bool built_wall[32][32] = {};
        for (int i = 0; i < M; ++i) {
            if (all_done || human_finished[i]) continue;
            if(human_targets[i].r == -1) continue;
            
            Pos wall_pos = human_targets[i];
            for (int j = 0; j < 4; ++j) {
                if (humans[i].r + dr[j] == wall_pos.r && humans[i].c + dc[j] == wall_pos.c) {
                    bool is_valid_build = !is_impassable[wall_pos.r][wall_pos.c] && !is_pet_or_human[wall_pos.r][wall_pos.c];
                    if (is_valid_build) {
                        for (const auto& p : pets) {
                            if (dist_mah(p.pos, wall_pos) <= 1) {
                                is_valid_build = false;
                                break;
                            }
                        }
                    }
                    if (is_valid_build) {
                        actions_str[i] = build_chars[j];
                        built_wall[wall_pos.r][wall_pos.c] = true;
                    }
                    break;
                }
            }
        }

        for (int human_idx : p_order) {
            if (actions_str[human_idx] != '.') continue;

            Pos target_dest;
            if (all_done || human_finished[human_idx]) {
                target_dest = safe_spot;
            } else {
                 if (human_targets[human_idx].r == -1) continue;
                 Pos wall_pos = human_targets[human_idx];
                 
                 bfs(humans[human_idx], path_costs);
                 int best_dist = INF;
                 Pos best_build_spot = {-1,-1};
                 for(int i=0; i<4; ++i) {
                     Pos build_spot = {wall_pos.r - dr[i], wall_pos.c - dc[i]};
                     if (build_spot.r >= 1 && build_spot.r <= 30 && build_spot.c >= 1 && build_spot.c <= 30 && !is_impassable[build_spot.r][build_spot.c]) {
                        if (dists[build_spot.r][build_spot.c] < best_dist) {
                            best_dist = dists[build_spot.r][build_spot.c];
                            best_build_spot = build_spot;
                        }
                    }
                 }
                 target_dest = best_build_spot;
            }
            if (target_dest.r == -1 || humans[human_idx] == target_dest) {
                continue;
            }

            bfs(humans[human_idx], path_costs);
            Pos step = target_dest;
            if (parent[step.r][step.c].r != -1 || step == humans[human_idx]) {
                 if (step == humans[human_idx]) {}
                 else {
                    while(parent[step.r][step.c].r != -1 && parent[step.r][step.c] != humans[human_idx]){
                        step = parent[step.r][step.c];
                    }
                 }
            } else {
                continue;
            }
            
            if(!pos_claimed[step.r][step.c] && !built_wall[step.r][step.c]) {
                for(int i=0; i<4; ++i) {
                    if (humans[human_idx].r + dr[i] == step.r && humans[human_idx].c + dc[i] == step.c) {
                        actions_str[human_idx] = move_chars[i];
                        pos_claimed[step.r][step.c] = true;
                        break;
                    }
                }
            }
        }
        
        cout << actions_str << endl;

        for (int i = 0; i < M; ++i) {
            char act = actions_str[i];
            if (act >= 'A' && act <= 'Z') { // Move
                if (act == 'U') humans[i].r--;
                if (act == 'D') humans[i].r++;
                if (act == 'L') humans[i].c--;
                if (act == 'R') humans[i].c++;
            } else if (act >= 'a' && act <= 'z') { // Build
                Pos p = humans[i];
                if (act == 'u') p.r--;
                if (act == 'd') p.r++;
                if (act == 'l') p.c--;
                if (act == 'r') p.c++;
                is_impassable[p.r][p.c] = true;
            }
        }
        
        for (int i = 0; i < N; ++i) {
            string move;
            cin >> move;
            if (move != ".") {
                for (char m : move) {
                    if (m == 'U') pets[i].pos.r--;
                    if (m == 'D') pets[i].pos.r++;
                    if (m == 'L') pets[i].pos.c--;
                    if (m == 'R') pets[i].pos.c++;
                }
            }
        }
    }

    return 0;
}