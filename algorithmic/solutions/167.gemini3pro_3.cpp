#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int MAX_COORD = 100000;
const int STRIP_WIDTH = 500;
const int NUM_STRIPS = MAX_COORD / STRIP_WIDTH; // 200
const int MAX_VERTICES = 1000;
const int MAX_PERIMETER = 400000;

struct Point {
    int x, y;
    int id;
    int type; // 1 for mackerel, -1 for sardine
};

int N;
vector<Point> mackerels;
vector<Point> sardines;
vector<Point> all_points;
vector<int> points_in_strip[NUM_STRIPS];

// Global state trackers
int cur_m = 0, cur_s = 0;

void update_counts(int idx, int old_yb, int old_yt, int new_yb, int new_yt) {
    // Subtract old range
    if (old_yb <= old_yt) {
        for (int pid : points_in_strip[idx]) {
            int y = all_points[pid].y;
            if (y >= old_yb && y <= old_yt) {
                if (all_points[pid].type == 1) cur_m--;
                else cur_s--;
            }
        }
    }
    // Add new range
    if (new_yb <= new_yt) {
        for (int pid : points_in_strip[idx]) {
            int y = all_points[pid].y;
            if (y >= new_yb && y <= new_yt) {
                if (all_points[pid].type == 1) cur_m++;
                else cur_s++;
            }
        }
    }
}

struct Solver {
    int S, E;
    int hb[NUM_STRIPS];
    int ht[NUM_STRIPS];
    int best_sc;
    
    void init() {
        S = 0; E = 0;
        fill(hb, hb + NUM_STRIPS, 0);
        fill(ht, ht + NUM_STRIPS, 0);
        best_sc = 0;
    }
};

Solver state;
mt19937 rng(12345);

void apply_update(int u, int v, int val, bool is_top, vector<int>& saved_vals) {
    saved_vals.resize(v - u + 1);
    for (int k = u; k <= v; ++k) {
        saved_vals[k - u] = is_top ? state.ht[k] : state.hb[k];
        int ob = state.hb[k];
        int ot = state.ht[k];
        int nb = is_top ? ob : val;
        int nt = is_top ? val : ot;
        
        update_counts(k, ob, ot, nb, nt);
        state.hb[k] = nb;
        state.ht[k] = nt;
    }
}

void revert_update(int u, int v, bool is_top, const vector<int>& saved_vals) {
    for (int k = u; k <= v; ++k) {
        int ob = state.hb[k];
        int ot = state.ht[k];
        int old_val = saved_vals[k - u];
        int nb = is_top ? ob : old_val;
        int nt = is_top ? old_val : ot;
        
        update_counts(k, ob, ot, nb, nt);
        state.hb[k] = nb;
        state.ht[k] = nt;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    mackerels.resize(N);
    all_points.resize(2 * N);
    for (int i = 0; i < N; ++i) {
        cin >> mackerels[i].x >> mackerels[i].y;
        mackerels[i].id = i;
        mackerels[i].type = 1;
        all_points[i] = mackerels[i];
    }
    sardines.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> sardines[i].x >> sardines[i].y;
        sardines[i].id = N + i;
        sardines[i].type = -1;
        all_points[N + i] = sardines[i];
    }

    // Bin points
    for (int i = 0; i < 2 * N; ++i) {
        int s = min(all_points[i].x / STRIP_WIDTH, NUM_STRIPS - 1);
        points_in_strip[s].push_back(i);
    }

    state.init();
    
    // Initial solution using random rectangles
    int best_init_score = -1;
    int best_s = 0, best_e = 0, best_yb = 0, best_yt = 1;
    
    for (int iter = 0; iter < 1000; ++iter) {
        int m1 = rng() % N;
        int m2 = rng() % N;
        int xl = min(mackerels[m1].x, mackerels[m2].x);
        int xr = max(mackerels[m1].x, mackerels[m2].x);
        int yb = min(mackerels[m1].y, mackerels[m2].y);
        int yt = max(mackerels[m1].y, mackerels[m2].y);
        if (yt <= yb) yt = yb + 1;
        
        int s = min(xl / STRIP_WIDTH, NUM_STRIPS - 1);
        int e = min(xr / STRIP_WIDTH, NUM_STRIPS - 1);
        if (s > e) swap(s, e);
        
        long long perim = 2LL * (e - s + 1) * STRIP_WIDTH + 2LL * (yt - yb);
        if (perim > MAX_PERIMETER) continue;
        
        int tm = 0, ts = 0;
        for (int i = s; i <= e; ++i) {
             for (int pid : points_in_strip[i]) {
                 int py = all_points[pid].y;
                 if (py >= yb && py <= yt) {
                     if (all_points[pid].type == 1) tm++;
                     else ts++;
                 }
             }
        }
        int sc = max(0, tm - ts + 1);
        if (sc > best_init_score) {
            best_init_score = sc;
            best_s = s; best_e = e;
            best_yb = yb; best_yt = yt;
        }
    }
    
    state.S = best_s; state.E = best_e;
    for (int k = best_s; k <= best_e; ++k) {
        state.hb[k] = best_yb;
        state.ht[k] = best_yt;
    }
    
    // Calculate initial current counts
    cur_m = 0; cur_s = 0;
    for (int k = state.S; k <= state.E; ++k) {
        for (int pid : points_in_strip[k]) {
            int py = all_points[pid].y;
            if (py >= state.hb[k] && py <= state.ht[k]) {
                if (all_points[pid].type == 1) cur_m++;
                else cur_s++;
            }
        }
    }
    state.best_sc = best_init_score;

    auto start_time = chrono::steady_clock::now();
    vector<int> saved_vals;
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 511) == 0) {
            if (chrono::duration<double>(chrono::steady_clock::now() - start_time).count() > 1.85) break;
        }
        
        int op = rng() % 100;
        int old_m = cur_m;
        int old_s = cur_s;
        int old_S = state.S;
        int old_E = state.E;
        
        bool valid_move = false;
        int u = -1, v = -1;
        bool is_top = false;
        
        if (op < 80) { // Height change
            is_top = (rng() % 2 == 0);
            int len = rng() % 30 + 1;
            u = state.S + rng() % (state.E - state.S + 1);
            v = min(state.E, u + len - 1);
            
            int new_val;
            int mode = rng() % 10;
            if (mode < 4 && u > state.S) {
                new_val = is_top ? state.ht[u-1] : state.hb[u-1];
            } else if (mode < 8 && v < state.E) {
                new_val = is_top ? state.ht[v+1] : state.hb[v+1];
            } else {
                int k = u + rng() % (v - u + 1);
                if (!points_in_strip[k].empty()) {
                    int pid = points_in_strip[k][rng() % points_in_strip[k].size()];
                    new_val = all_points[pid].y;
                    if(rng()%2) new_val += (rng()%3 - 1);
                } else new_val = rng() % MAX_COORD;
            }
            new_val = max(0, min(MAX_COORD, new_val));
            
            bool possible = true;
            for (int k = u; k <= v; ++k) {
                if (is_top) { if (new_val <= state.hb[k]) possible = false; }
                else { if (new_val >= state.ht[k]) possible = false; }
            }
            
            if (possible) {
                apply_update(u, v, new_val, is_top, saved_vals);
                valid_move = true;
            }
        } else if (op < 90) { // Change S
            if (rng() % 2 && state.S > 0) { // Expand left
                state.S--;
                state.hb[state.S] = state.hb[state.S+1];
                state.ht[state.S] = state.ht[state.S+1];
                update_counts(state.S, 0, -1, state.hb[state.S], state.ht[state.S]);
                valid_move = true;
            } else if (state.S < state.E) { // Shrink left
                update_counts(state.S, state.hb[state.S], state.ht[state.S], 0, -1);
                state.S++;
                valid_move = true;
            }
        } else { // Change E
             if (rng() % 2 && state.E < NUM_STRIPS - 1) { // Expand right
                 state.E++;
                 state.hb[state.E] = state.hb[state.E-1];
                 state.ht[state.E] = state.ht[state.E-1];
                 update_counts(state.E, 0, -1, state.hb[state.E], state.ht[state.E]);
                 valid_move = true;
             } else if (state.E > state.S) { // Shrink right
                 update_counts(state.E, state.hb[state.E], state.ht[state.E], 0, -1);
                 state.E--;
                 valid_move = true;
             }
        }
        
        if (valid_move) {
            int perim = 0;
            perim += 2 * (state.E - state.S + 1) * STRIP_WIDTH;
            perim += (state.ht[state.S] - state.hb[state.S]);
            perim += (state.ht[state.E] - state.hb[state.E]);
            for (int k = state.S; k < state.E; ++k) {
                perim += abs(state.ht[k+1] - state.ht[k]);
                perim += abs(state.hb[k+1] - state.hb[k]);
            }
            
            int v_count = 4;
            for (int k = state.S; k < state.E; ++k) {
                if (state.hb[k+1] != state.hb[k]) v_count += 2;
                if (state.ht[k+1] != state.ht[k]) v_count += 2;
            }
            
            bool accepted = false;
            if (perim <= MAX_PERIMETER && v_count <= MAX_VERTICES) {
                int score = max(0, cur_m - cur_s + 1);
                if (score >= state.best_sc) {
                    state.best_sc = score;
                    accepted = true;
                }
            }
            
            if (!accepted) {
                cur_m = old_m;
                cur_s = old_s;
                if (op < 80) {
                    revert_update(u, v, is_top, saved_vals);
                } else {
                    if (op < 90) { // S
                        if (state.S < old_S) { // Expanded left -> undo (shrink)
                             update_counts(state.S, state.hb[state.S], state.ht[state.S], 0, -1);
                             state.S = old_S;
                        } else { // Shrunk left -> undo (expand)
                             state.S = old_S;
                             update_counts(state.S, 0, -1, state.hb[state.S], state.ht[state.S]);
                        }
                    } else { // E
                        if (state.E > old_E) { // Expanded right -> undo (shrink)
                            update_counts(state.E, state.hb[state.E], state.ht[state.E], 0, -1);
                            state.E = old_E;
                        } else { // Shrunk right -> undo (expand)
                            state.E = old_E;
                            update_counts(state.E, 0, -1, state.hb[state.E], state.ht[state.E]);
                        }
                    }
                }
            }
        }
    }
    
    // Generate output
    vector<pair<int, int>> verts;
    verts.push_back({state.S * STRIP_WIDTH, state.hb[state.S]});
    
    // Bottom profile
    for (int i = state.S; i <= state.E; ++i) {
        int x_next = (i + 1) * STRIP_WIDTH;
        if (i < state.E) {
            if (state.hb[i+1] != state.hb[i]) {
                verts.push_back({x_next, state.hb[i]});
                verts.push_back({x_next, state.hb[i+1]});
            }
        } else {
            verts.push_back({x_next, state.hb[i]});
        }
    }
    
    verts.push_back({(state.E + 1) * STRIP_WIDTH, state.ht[state.E]});
    
    // Top profile
    for (int i = state.E; i >= state.S; --i) {
        int x_curr = i * STRIP_WIDTH;
        if (i > state.S) {
            if (state.ht[i-1] != state.ht[i]) {
                verts.push_back({x_curr, state.ht[i]});
                verts.push_back({x_curr, state.ht[i-1]});
            }
        } else {
            verts.push_back({x_curr, state.ht[i]});
        }
    }
    
    // Clean up
    vector<pair<int, int>> final_verts;
    if (!verts.empty()) final_verts.push_back(verts[0]);
    for (size_t i = 1; i < verts.size(); ++i) {
        if (verts[i] != verts[i-1]) final_verts.push_back(verts[i]);
    }
    if (final_verts.size() > 1 && final_verts.back() == final_verts[0]) final_verts.pop_back();

    cout << final_verts.size() << "\n";
    for (auto p : final_verts) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}