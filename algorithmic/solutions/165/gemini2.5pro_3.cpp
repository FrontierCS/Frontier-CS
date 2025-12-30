#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <chrono>
#include <random>

using namespace std;

const int N_GRID = 15;
const int M_TARGETS = 200;

struct Pos {
    int r, c;
};

int si, sj;
char A[N_GRID][N_GRID];
vector<string> t(M_TARGETS);
vector<Pos> char_pos[26];
unordered_map<string, int> t_to_idx;
int overlaps[M_TARGETS][M_TARGETS];

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

struct TypingResult {
    int cost;
    Pos end_pos;
    vector<Pos> moves;
};

TypingResult solve_typing(const string& p, Pos start_pos) {
    if (p.empty()) {
        return {0, start_pos, {}};
    }

    vector<vector<int>> dp(p.length());
    vector<vector<int>> bp(p.length());

    int p_start_char_idx = p[0] - 'A';
    dp[0].resize(char_pos[p_start_char_idx].size());
    bp[0].resize(char_pos[p_start_char_idx].size());

    for (size_t k = 0; k < char_pos[p_start_char_idx].size(); ++k) {
        Pos current_p = char_pos[p_start_char_idx][k];
        dp[0][k] = abs(current_p.r - start_pos.r) + abs(current_p.c - start_pos.c) + 1;
    }

    for (size_t i = 1; i < p.length(); ++i) {
        int p_curr_char_idx = p[i] - 'A';
        int p_prev_char_idx = p[i - 1] - 'A';
        dp[i].resize(char_pos[p_curr_char_idx].size());
        bp[i].resize(char_pos[p_curr_char_idx].size());

        for (size_t k = 0; k < char_pos[p_curr_char_idx].size(); ++k) {
            Pos current_p = char_pos[p_curr_char_idx][k];
            int min_cost = 1e9;
            int best_prev_k = -1;
            for (size_t prev_k = 0; prev_k < char_pos[p_prev_char_idx].size(); ++prev_k) {
                Pos prev_p = char_pos[p_prev_char_idx][prev_k];
                int move_cost = abs(current_p.r - prev_p.r) + abs(current_p.c - prev_p.c) + 1;
                if (dp[i - 1][prev_k] + move_cost < min_cost) {
                    min_cost = dp[i - 1][prev_k] + move_cost;
                    best_prev_k = prev_k;
                }
            }
            dp[i][k] = min_cost;
            bp[i][k] = best_prev_k;
        }
    }

    int min_total_cost = 1e9;
    int best_final_k = -1;
    int last_char_idx = p.back() - 'A';
    for (size_t k = 0; k < char_pos[last_char_idx].size(); ++k) {
        if (dp[p.length() - 1][k] < min_total_cost) {
            min_total_cost = dp[p.length() - 1][k];
            best_final_k = k;
        }
    }

    vector<Pos> moves;
    Pos end_pos = char_pos[last_char_idx][best_final_k];
    int current_k = best_final_k;
    for (int i = p.length() - 1; i >= 0; --i) {
        moves.push_back(char_pos[p[i] - 'A'][current_k]);
        if (i > 0) {
            current_k = bp[i][current_k];
        }
    }
    reverse(moves.begin(), moves.end());

    return {min_total_cost, end_pos, moves};
}

struct CostResult {
    int cost;
    int fulfilled_count;
};

CostResult calculate_total_cost(const vector<int>& order) {
    vector<bool> fulfilled(M_TARGETS, false);
    string S = "";
    Pos current_pos = {si, sj};
    int total_cost = 0;
    int fulfilled_count = 0;

    for (int idx : order) {
        if (fulfilled[idx]) continue;

        int k = 0;
        if (!S.empty()) {
            for (int i = min((int)S.length(), 4); i >= 1; --i) {
                if (S.length() >= (size_t)i && S.substr(S.length() - i) == t[idx].substr(0, i)) {
                    k = i;
                    break;
                }
            }
        }
        
        string p = t[idx].substr(k);
        
        TypingResult res = solve_typing(p, current_pos);
        total_cost += res.cost;
        current_pos = res.end_pos;
        
        string temp_S = S.substr(max(0, (int)S.length() - 4));
        S += p;

        string check_str = temp_S + p;
        if(check_str.length() >= 5) {
            for (size_t i = 0; i <= check_str.length() - 5; ++i) {
                string sub = check_str.substr(i, 5);
                auto it = t_to_idx.find(sub);
                if (it != t_to_idx.end()) {
                    if (!fulfilled[it->second]) {
                        fulfilled[it->second] = true;
                        fulfilled_count++;
                    }
                }
            }
        }
    }
    return {total_cost, fulfilled_count};
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    int N_dummy, M_dummy;
    cin >> N_dummy >> M_dummy;
    cin >> si >> sj;
    for (int i = 0; i < N_GRID; ++i) {
        string row;
        cin >> row;
        for (int j = 0; j < N_GRID; ++j) {
            A[i][j] = row[j];
            char_pos[A[i][j] - 'A'].push_back({i, j});
        }
    }
    for (int i = 0; i < M_TARGETS; ++i) {
        cin >> t[i];
        t_to_idx[t[i]] = i;
    }

    for (int i = 0; i < M_TARGETS; ++i) {
        for (int j = 0; j < M_TARGETS; ++j) {
            if (i == j) continue;
            for (int k = 4; k >= 1; --k) {
                if (t[i].substr(5 - k) == t[j].substr(0, k)) {
                    overlaps[i][j] = k;
                    break;
                }
            }
        }
    }

    vector<int> current_order;
    { 
        vector<bool> used(M_TARGETS, false);
        current_order.reserve(M_TARGETS);
        
        int best_first = 0;
        int min_cost = 1e9;
        for(int i = 0; i < M_TARGETS; ++i) {
            int cost = solve_typing(t[i], {si, sj}).cost;
            if(cost < min_cost) {
                min_cost = cost;
                best_first = i;
            }
        }
        
        current_order.push_back(best_first);
        used[best_first] = true;
        
        while(current_order.size() < M_TARGETS) {
            int last_idx = current_order.back();
            int best_next = -1;
            int max_overlap = -1;
            for(int i = 0; i < M_TARGETS; ++i) {
                if(!used[i]) {
                    if(overlaps[last_idx][i] > max_overlap) {
                        max_overlap = overlaps[last_idx][i];
                        best_next = i;
                    }
                }
            }
            if (best_next == -1) {
                for(int i = 0; i < M_TARGETS; ++i) if(!used[i]) { best_next = i; break; }
            }
            current_order.push_back(best_next);
            used[best_next] = true;
        }
    }

    CostResult current_res = calculate_total_cost(current_order);
    vector<int> best_order = current_order;
    double best_energy;

    auto to_energy = [&](const CostResult& res) {
        return (double)(M_TARGETS - res.fulfilled_count) * 20000.0 + res.cost;
    };
    
    double current_energy = to_energy(current_res);
    best_energy = current_energy;

    double T_start = 500.0;
    double T_end = 0.1;
    const double TIME_LIMIT = 2.8;

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        double elapsed_seconds = chrono::duration_cast<chrono::duration<double>>(current_time - start_time).count();
        if (elapsed_seconds > TIME_LIMIT) break;

        vector<int> next_order = current_order;
        int i = uniform_int_distribution<int>(0, M_TARGETS - 1)(rng);
        int j = uniform_int_distribution<int>(0, M_TARGETS - 1)(rng);
        if(i == j) continue;
        
        int r = uniform_int_distribution<int>(0, 1)(rng);
        if (r == 0) {
            if (i > j) swap(i, j);
            reverse(next_order.begin() + i, next_order.begin() + j + 1);
        } else {
            swap(next_order[i], next_order[j]);
        }
        
        CostResult next_res = calculate_total_cost(next_order);
        double next_energy = to_energy(next_res);
        
        double T = T_start * pow(T_end / T_start, elapsed_seconds / TIME_LIMIT);
        
        if (next_energy < current_energy ||
            (uniform_real_distribution<double>(0.0, 1.0)(rng) < exp((current_energy - next_energy) / T)))
        {
            current_order = next_order;
            current_energy = next_energy;
            if (current_energy < best_energy) {
                best_energy = current_energy;
                best_order = current_order;
            }
        }
    }

    vector<Pos> final_moves;
    vector<bool> fulfilled(M_TARGETS, false);
    Pos current_pos = {si, sj};
    string S = "";

    for (int idx : best_order) {
        if (fulfilled[idx]) continue;
        int k = 0;
        if (!S.empty()) {
            for (int i = min((int)S.length(), 4); i >= 1; --i) {
                if (S.length() >= (size_t)i && S.substr(S.length() - i) == t[idx].substr(0, i)) {
                    k = i;
                    break;
                }
            }
        }
        string p = t[idx].substr(k);
        TypingResult res = solve_typing(p, current_pos);
        final_moves.insert(final_moves.end(), res.moves.begin(), res.moves.end());
        current_pos = res.end_pos;

        string temp_S = S.substr(max(0, (int)S.length() - 4));
        S += p;

        string check_str = temp_S + p;
        if (check_str.length() >= 5) {
            for (size_t i = 0; i <= check_str.length() - 5; ++i) {
                string sub = check_str.substr(i, 5);
                auto it = t_to_idx.find(sub);
                if (it != t_to_idx.end()) {
                    fulfilled[it->second] = true;
                }
            }
        }
    }
    
    for(int i = 0; i < M_TARGETS; ++i) {
        if(!fulfilled[i]) {
            int k = 0;
             if (!S.empty()) {
                for (int j = min((int)S.length(), 4); j >= 1; --j) {
                    if (S.length() >= (size_t)j && S.substr(S.length() - j) == t[i].substr(0, j)) {
                        k = j;
                        break;
                    }
                }
            }
            string p = t[i].substr(k);
            TypingResult res = solve_typing(p, current_pos);
            final_moves.insert(final_moves.end(), res.moves.begin(), res.moves.end());
            current_pos = res.end_pos;
            S += p;
        }
    }

    for (const auto& move : final_moves) {
        cout << move.r << " " << move.c << "\n";
    }

    return 0;
}