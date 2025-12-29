#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <cstdlib>

using namespace std;

const int N = 20;

struct Oni {
    int id;
    int r, c;
};

struct Option {
    int actuator_id; // 0-19: L, 20-39: R, 40-59: U, 60-79: D
    int depth;       // 0-based index from edge needed to clear
    int cost;        // 2 * (depth + 1)
};

vector<string> board(N);
vector<Oni> onis;
vector<vector<Option>> oni_options;

vector<int> assignment; 
vector<vector<int>> actuator_onis(80); 
int actuator_costs[80];
long long current_total_cost = 0;

int calculate_actuator_cost(int act_id) {
    if (actuator_onis[act_id].empty()) return 0;
    int max_d = -1;
    for (int oid : actuator_onis[act_id]) {
        max_d = max(max_d, oni_options[oid][assignment[oid]].depth);
    }
    return 2 * (max_d + 1);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    int n_in;
    if (cin >> n_in) {} 
    for (int i = 0; i < N; ++i) {
        cin >> board[i];
    }

    int oni_cnt = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (board[r][c] == 'x') {
                onis.push_back({oni_cnt++, r, c});
            }
        }
    }

    oni_options.resize(oni_cnt);
    for (const auto& oni : onis) {
        bool safe = true;
        for (int c = 0; c < oni.c; ++c) {
            if (board[oni.r][c] == 'o') { safe = false; break; }
        }
        if (safe) {
            oni_options[oni.id].push_back({oni.r, oni.c, 2 * (oni.c + 1)});
        }
        
        safe = true;
        for (int c = oni.c + 1; c < N; ++c) {
            if (board[oni.r][c] == 'o') { safe = false; break; }
        }
        if (safe) {
            oni_options[oni.id].push_back({20 + oni.r, N - 1 - oni.c, 2 * (N - oni.c)});
        }

        safe = true;
        for (int r = 0; r < oni.r; ++r) {
            if (board[r][oni.c] == 'o') { safe = false; break; }
        }
        if (safe) {
            oni_options[oni.id].push_back({40 + oni.c, oni.r, 2 * (oni.r + 1)});
        }

        safe = true;
        for (int r = oni.r + 1; r < N; ++r) {
            if (board[r][oni.c] == 'o') { safe = false; break; }
        }
        if (safe) {
            oni_options[oni.id].push_back({60 + oni.c, N - 1 - oni.r, 2 * (N - oni.r)});
        }
    }

    assignment.resize(oni_cnt);
    for (int i = 0; i < oni_cnt; ++i) {
        int best_opt = -1;
        int min_c = 99999;
        for (int j = 0; j < oni_options[i].size(); ++j) {
            if (oni_options[i][j].cost < min_c) {
                min_c = oni_options[i][j].cost;
                best_opt = j;
            }
        }
        assignment[i] = best_opt;
        int act = oni_options[i][best_opt].actuator_id;
        actuator_onis[act].push_back(i);
    }

    for (int a = 0; a < 80; ++a) {
        actuator_costs[a] = calculate_actuator_cost(a);
        current_total_cost += actuator_costs[a];
    }

    double time_limit = 1.85 * CLOCKS_PER_SEC;
    double start_time = clock();
    double temp = 10.0;

    while (true) {
        double curr_time = clock();
        if (curr_time - start_time > time_limit) break;

        int oid = rand() % oni_cnt;
        if (oni_options[oid].size() <= 1) continue;

        int curr_opt_idx = assignment[oid];
        int next_opt_idx = rand() % oni_options[oid].size();
        if (curr_opt_idx == next_opt_idx) continue;

        int old_act = oni_options[oid][curr_opt_idx].actuator_id;
        int new_act = oni_options[oid][next_opt_idx].actuator_id;

        int cost_old_before = actuator_costs[old_act];
        int cost_new_before = actuator_costs[new_act];

        int max_d_old = -1;
        for (int id : actuator_onis[old_act]) {
            if (id == oid) continue;
            max_d_old = max(max_d_old, oni_options[id][assignment[id]].depth);
        }
        int cost_old_after = (max_d_old == -1) ? 0 : 2 * (max_d_old + 1);

        int max_d_new = oni_options[oid][next_opt_idx].depth;
        for (int id : actuator_onis[new_act]) {
            max_d_new = max(max_d_new, oni_options[id][assignment[id]].depth);
        }
        int cost_new_after = 2 * (max_d_new + 1);

        long long delta = (long long)cost_old_after + cost_new_after - cost_old_before - cost_new_before;

        bool accept = false;
        if (delta <= 0) accept = true;
        else {
            if ((double)rand() / RAND_MAX < exp(-delta / temp)) accept = true;
        }

        if (accept) {
            current_total_cost += delta;
            assignment[oid] = next_opt_idx;
            
            for (size_t k = 0; k < actuator_onis[old_act].size(); ++k) {
                if (actuator_onis[old_act][k] == oid) {
                    actuator_onis[old_act][k] = actuator_onis[old_act].back();
                    actuator_onis[old_act].pop_back();
                    break;
                }
            }
            actuator_onis[new_act].push_back(oid);
            
            actuator_costs[old_act] = cost_old_after;
            actuator_costs[new_act] = cost_new_after;
        }

        temp *= 0.999995;
    }

    for (int a = 0; a < 80; ++a) {
        if (actuator_costs[a] == 0) continue;
        int moves = actuator_costs[a] / 2;
        
        char type; int idx;
        if (a < 20) { type = 'L'; idx = a; }
        else if (a < 40) { type = 'R'; idx = a - 20; }
        else if (a < 60) { type = 'U'; idx = a - 40; }
        else { type = 'D'; idx = a - 60; }
        
        char rev;
        if (type == 'L') rev = 'R';
        else if (type == 'R') rev = 'L';
        else if (type == 'U') rev = 'D';
        else rev = 'U';

        for (int k=0; k<moves; ++k) cout << type << " " << idx << "\n";
        for (int k=0; k<moves; ++k) cout << rev << " " << idx << "\n";
    }

    return 0;
}