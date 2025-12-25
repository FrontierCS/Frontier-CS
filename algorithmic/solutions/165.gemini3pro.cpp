#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <climits>
#include <random>
#include <chrono>

using namespace std;

const int N_GRID = 15;
const int M_MAX = 200;
const int INF = 1e9;

int N, M;
int start_r, start_c;
string grid_str[N_GRID];
char grid[N_GRID][N_GRID];
vector<pair<int, int>> char_pos[26];
vector<string> targets;

int dist_weights[M_MAX + 1][M_MAX]; 
int overlaps[M_MAX][M_MAX];

inline int grid_dist(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

int compute_weight(int from_idx, int to_idx) {
    string s;
    vector<pair<int, int>> starts;
    
    if (from_idx == -1) {
        s = targets[to_idx];
        starts.push_back({start_r, start_c});
    } else {
        int ov = overlaps[from_idx][to_idx];
        s = targets[to_idx].substr(ov);
        if (s.empty()) return 0;
        char last_c = targets[from_idx].back();
        starts = char_pos[last_c - 'A'];
    }
    
    vector<int> prev_costs(starts.size(), 0);
    vector<pair<int, int>> prev_pos = starts;
    
    for (char c : s) {
        int char_idx = c - 'A';
        const auto& next_positions = char_pos[char_idx];
        vector<int> next_costs(next_positions.size(), INF);
        
        for (size_t i = 0; i < prev_pos.size(); ++i) {
            int r_prev = prev_pos[i].first;
            int c_prev = prev_pos[i].second;
            int cost_so_far = prev_costs[i];
            
            for (size_t j = 0; j < next_positions.size(); ++j) {
                int r_next = next_positions[j].first;
                int c_next = next_positions[j].second;
                int move_cost = grid_dist(r_prev, c_prev, r_next, c_next) + 1;
                if (cost_so_far + move_cost < next_costs[j]) {
                    next_costs[j] = cost_so_far + move_cost;
                }
            }
        }
        prev_costs = next_costs;
        prev_pos = next_positions;
    }
    
    int min_total = INF;
    for (int c : prev_costs) min_total = min(min_total, c);
    return min_total;
}

int compute_overlap_val(const string& s1, const string& s2) {
    for (int len = 4; len >= 0; --len) { 
        if (s1.substr(5 - len) == s2.substr(0, len)) {
            return len;
        }
    }
    return 0;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    cin >> N >> M;
    cin >> start_r >> start_c;
    
    for (int i = 0; i < N; ++i) {
        string row;
        cin >> row;
        grid_str[i] = row;
        for (int j = 0; j < N; ++j) {
            grid[i][j] = row[j];
            char_pos[row[j] - 'A'].push_back({i, j});
        }
    }
    
    targets.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> targets[i];
    }
    
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) overlaps[i][j] = 0;
            else overlaps[i][j] = compute_overlap_val(targets[i], targets[j]);
        }
    }
    
    for (int j = 0; j < M; ++j) {
        dist_weights[M][j] = compute_weight(-1, j); 
    }
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) dist_weights[i][j] = INF;
            else dist_weights[i][j] = compute_weight(i, j);
        }
    }
    
    vector<int> path;
    path.reserve(M);
    vector<bool> visited(M, false);
    
    int current = M; 
    for (int step = 0; step < M; ++step) {
        int best_next = -1;
        int best_cost = INF;
        for (int i = 0; i < M; ++i) {
            if (!visited[i]) {
                int c = dist_weights[current][i];
                if (c < best_cost) {
                    best_cost = c;
                    best_next = i;
                }
            }
        }
        path.push_back(best_next);
        visited[best_next] = true;
        current = best_next;
    }
    
    auto start_time = chrono::steady_clock::now();
    
    auto calc_path_cost = [&](const vector<int>& p) {
        int cost = dist_weights[M][p[0]];
        for (size_t i = 0; i < p.size() - 1; ++i) {
            cost += dist_weights[p[i]][p[i+1]];
        }
        return cost;
    };
    
    int current_cost = calc_path_cost(path);
    mt19937 rng(42);
    double temp = 100.0;
    double cool_rate = 0.99995;
    
    while (true) {
        auto now = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 1800) break;
        
        int type = rng() % 2; 
        
        if (type == 0) { 
             int i = rng() % M;
             int k = rng() % M;
             if (i == k) continue;
             
             vector<int> next_path = path;
             int val = next_path[i];
             next_path.erase(next_path.begin() + i);
             if (k > next_path.size()) k = next_path.size();
             next_path.insert(next_path.begin() + k, val);
             
             int new_cost = calc_path_cost(next_path);
             if (new_cost < current_cost) {
                 path = next_path;
                 current_cost = new_cost;
             } else {
                 if (exp((current_cost - new_cost) / temp) > (double)(rng() % 10000) / 10000.0) {
                     path = next_path;
                     current_cost = new_cost;
                 }
             }
        } else { 
            int i = rng() % M;
            int j = rng() % M;
            if (i == j) continue;
            swap(path[i], path[j]);
            int new_cost = calc_path_cost(path);
            if (new_cost < current_cost) {
                current_cost = new_cost;
            } else {
                if (exp((current_cost - new_cost) / temp) > (double)(rng() % 10000) / 10000.0) {
                     current_cost = new_cost;
                } else {
                    swap(path[i], path[j]); 
                }
            }
        }
        temp *= cool_rate;
    }
    
    string final_s = "";
    int curr_idx = path[0];
    final_s += targets[curr_idx];
    
    for (size_t k = 1; k < path.size(); ++k) {
        int next_idx = path[k];
        int ov = overlaps[curr_idx][next_idx];
        final_s += targets[next_idx].substr(ov);
        curr_idx = next_idx;
    }
    
    int L = final_s.length();
    
    struct State {
        int cost;
        int prev_pos_index; 
    };
    
    vector<vector<State>> dp(L); 
    
    char c0 = final_s[0];
    int c0_idx = c0 - 'A';
    dp[0].resize(char_pos[c0_idx].size());
    for (size_t i = 0; i < char_pos[c0_idx].size(); ++i) {
        int r = char_pos[c0_idx][i].first;
        int c = char_pos[c0_idx][i].second;
        dp[0][i] = { grid_dist(start_r, start_c, r, c) + 1, -1 };
    }
    
    for (int k = 1; k < L; ++k) {
        char c_curr = final_s[k];
        int curr_char_idx = c_curr - 'A';
        const auto& curr_positions = char_pos[curr_char_idx];
        
        char c_prev = final_s[k-1];
        int prev_char_idx = c_prev - 'A';
        const auto& prev_positions = char_pos[prev_char_idx];
        
        dp[k].resize(curr_positions.size());
        
        for (size_t i = 0; i < curr_positions.size(); ++i) {
            int r_curr = curr_positions[i].first;
            int c_curr = curr_positions[i].second;
            
            int best_cost = INF;
            int best_prev = -1;
            
            for (size_t j = 0; j < prev_positions.size(); ++j) {
                int r_prev = prev_positions[j].first;
                int c_prev = prev_positions[j].second;
                
                int val = dp[k-1][j].cost + grid_dist(r_prev, c_prev, r_curr, c_curr) + 1;
                if (val < best_cost) {
                    best_cost = val;
                    best_prev = j;
                }
            }
            dp[k][i] = { best_cost, best_prev };
        }
    }
    
    int last_idx = -1;
    int min_final_cost = INF;
    for (size_t i = 0; i < dp[L-1].size(); ++i) {
        if (dp[L-1][i].cost < min_final_cost) {
            min_final_cost = dp[L-1][i].cost;
            last_idx = i;
        }
    }
    
    vector<pair<int, int>> result_path(L);
    int curr_pos_idx = last_idx;
    for (int k = L - 1; k >= 0; --k) {
        char c = final_s[k];
        int c_id = c - 'A';
        result_path[k] = char_pos[c_id][curr_pos_idx];
        curr_pos_idx = dp[k][curr_pos_idx].prev_pos_index;
    }
    
    for (const auto& p : result_path) {
        cout << p.first << " " << p.second << "\n";
    }
    
    return 0;
}