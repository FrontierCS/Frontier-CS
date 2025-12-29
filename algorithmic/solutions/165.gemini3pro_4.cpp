#pragma GCC optimize("O3")
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <climits>
#include <random>
#include <chrono>

using namespace std;

// Problem Constants
int N, M;
int SI, SJ;
string Grid[20];
string T[205];
vector<pair<int, int>> char_locs[26];
int overlaps[205][205];

struct Move {
    int r, c;
};

struct CostResult {
    int cost;
    int end_r, end_c;
};

inline int dist(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

// Efficiently calculate the minimum cost to type string 's' starting from (sr, sc)
// Returns {min_cost, end_row, end_col}
CostResult calc_cost_query(int sr, int sc, const string& s) {
    if (s.empty()) return {0, sr, sc};
    int len = s.length();
    
    // Static buffers to avoid reallocation overhead
    static vector<int> rs, cs, costs;
    static vector<int> n_rs, n_cs, n_costs;
    
    rs.clear(); cs.clear(); costs.clear();
    rs.reserve(16); cs.reserve(16); costs.reserve(16);
    rs.push_back(sr); cs.push_back(sc); costs.push_back(0);
    
    for (int k = 0; k < len; ++k) {
        int char_idx = s[k] - 'A';
        const auto& next_locs = char_locs[char_idx];
        
        n_rs.clear(); n_cs.clear(); n_costs.clear();
        n_rs.reserve(next_locs.size());
        n_cs.reserve(next_locs.size());
        n_costs.reserve(next_locs.size());
        
        for (const auto& loc : next_locs) {
            int nr = loc.first;
            int nc = loc.second;
            int min_c = 1e9;
            
            for (size_t i = 0; i < rs.size(); ++i) {
                int d = abs(rs[i] - nr) + abs(cs[i] - nc);
                int total = costs[i] + d + 1;
                if (total < min_c) min_c = total;
            }
            n_rs.push_back(nr);
            n_cs.push_back(nc);
            n_costs.push_back(min_c);
        }
        rs = n_rs; cs = n_cs; costs = n_costs;
    }
    
    // Find the best ending position among minimal costs
    int min_total = 1e9;
    int best_idx = 0;
    for (size_t i = 0; i < costs.size(); ++i) {
        if (costs[i] < min_total) {
            min_total = costs[i];
            best_idx = i;
        } else if (costs[i] == min_total) {
            // Tie-breaker: prioritize ending closer to the center of the grid
            if (abs(rs[i]-7)+abs(cs[i]-7) < abs(rs[best_idx]-7)+abs(cs[best_idx]-7)) {
                best_idx = i;
            }
        }
    }
    return {min_total, rs[best_idx], cs[best_idx]};
}

// Reconstruct the actual path of moves for the optimal typing of string 's'
vector<Move> get_path(int sr, int sc, const string& s) {
    vector<Move> path;
    if (s.empty()) return path;
    int len = s.length();
    
    vector<vector<int>> layer_costs(len);
    vector<vector<int>> parent_indices(len);
    
    vector<pair<int, int>> prev_locs;
    prev_locs.push_back({sr, sc});
    vector<int> prev_costs;
    prev_costs.push_back(0);
    
    for (int k = 0; k < len; ++k) {
        int char_idx = s[k] - 'A';
        const auto& curr_locs = char_locs[char_idx];
        vector<int> curr_costs(curr_locs.size(), 1e9);
        vector<int> parents(curr_locs.size(), -1);
        
        for (size_t j = 0; j < curr_locs.size(); ++j) {
            int r = curr_locs[j].first;
            int c = curr_locs[j].second;
            for (size_t p = 0; p < prev_locs.size(); ++p) {
                int d = abs(prev_locs[p].first - r) + abs(prev_locs[p].second - c);
                int total = prev_costs[p] + d + 1;
                if (total < curr_costs[j]) {
                    curr_costs[j] = total;
                    parents[j] = p;
                }
            }
        }
        layer_costs[k] = curr_costs;
        parent_indices[k] = parents;
        prev_locs = curr_locs;
        prev_costs = curr_costs;
    }
    
    int min_total = 1e9;
    int best_idx = 0;
    for (size_t i = 0; i < prev_costs.size(); ++i) {
        if (prev_costs[i] < min_total) {
            min_total = prev_costs[i];
            best_idx = i;
        } else if (prev_costs[i] == min_total) {
             if (abs(prev_locs[i].first-7)+abs(prev_locs[i].second-7) < 
                 abs(prev_locs[best_idx].first-7)+abs(prev_locs[best_idx].second-7)) {
                best_idx = i;
            }
        }
    }
    
    int curr = best_idx;
    for (int k = len - 1; k >= 0; --k) {
        int char_idx = s[k] - 'A';
        const auto& locs = char_locs[char_idx];
        path.push_back({locs[curr].first, locs[curr].second});
        curr = parent_indices[k][curr];
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    cin >> SI >> SJ;
    for (int i = 0; i < N; ++i) {
        cin >> Grid[i];
        for (int j = 0; j < N; ++j) {
            char_locs[Grid[i][j] - 'A'].push_back({i, j});
        }
    }
    for (int i = 0; i < M; ++i) cin >> T[i];
    
    // Precompute overlaps between all pairs of strings
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) { overlaps[i][j] = 0; continue; }
            int max_ov = 0;
            // t_k are length 5, distinct. Max overlap is 4.
            for (int k = 1; k <= 4; ++k) {
                if (T[i].substr(5 - k) == T[j].substr(0, k)) {
                    max_ov = k;
                }
            }
            overlaps[i][j] = max_ov;
        }
    }
    
    auto start_time = chrono::steady_clock::now();
    
    vector<Move> best_moves;
    int best_cost = 1e9;
    
    // Randomized Greedy Approach
    mt19937 rng(12345);
    uniform_real_distribution<double> noise_dist(0.8, 1.2);
    
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        // Time limit check (1.85s to leave buffer)
        if (chrono::duration_cast<chrono::milliseconds>(curr_time - start_time).count() > 1850) break;
        
        vector<bool> visited(M, false);
        vector<Move> current_path;
        current_path.reserve(M * 5);
        int current_total_cost = 0;
        int cur_r = SI, cur_c = SJ;
        int last_idx = -1;
        
        for (int count = 0; count < M; ++count) {
            int best_cand = -1;
            double best_score = 1e18;
            int best_ov = -1;
            
            // Evaluate all unvisited strings
            for (int i = 0; i < M; ++i) {
                if (!visited[i]) {
                    string suffix;
                    int ov = 0;
                    if (last_idx == -1) {
                        suffix = T[i];
                    } else {
                        ov = overlaps[last_idx][i];
                        suffix = T[i].substr(ov);
                    }
                    
                    CostResult cr = calc_cost_query(cur_r, cur_c, suffix);
                    
                    // Score is the cost modified by random noise to explore different paths
                    double score = cr.cost;
                    score *= noise_dist(rng);
                    
                    if (score < best_score) {
                        best_score = score;
                        best_cand = i;
                        best_ov = ov;
                    }
                }
            }
            
            // Apply the best candidate
            visited[best_cand] = true;
            string suffix = (last_idx == -1) ? T[best_cand] : T[best_cand].substr(best_ov);
            vector<Move> path = get_path(cur_r, cur_c, suffix);
            
            for (auto& m : path) current_path.push_back(m);
            
            int segment_cost = 0;
            int rr = cur_r, cc = cur_c;
            for (auto& m : path) {
                segment_cost += dist(rr, cc, m.r, m.c) + 1;
                rr = m.r; cc = m.c;
            }
            current_total_cost += segment_cost;
            cur_r = rr; cur_c = cc;
            last_idx = best_cand;
        }
        
        if (current_total_cost < best_cost) {
            best_cost = current_total_cost;
            best_moves = current_path;
        }
    }
    
    // Output the sequence of moves
    for (auto& m : best_moves) {
        cout << m.r << " " << m.c << "\n";
    }
    
    return 0;
}