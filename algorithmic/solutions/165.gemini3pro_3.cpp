#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <climits>
#include <ctime>
#include <cstdlib>

using namespace std;

// Constants and Globals
const int N = 15;
const int M = 200;

struct Point {
    int r, c;
};

struct Op {
    int r, c;
};

int start_r, start_c;
string A[N];
string T[M];
vector<Point> char_locs[26];
int overlaps[M][M];

// Time limit for the heuristic loop
const double TIME_LIMIT = 1.95;

// Static DP buffers to avoid reallocation
int dp_buf[6][300];

int dist(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

int calc_overlap(const string& s1, const string& s2) {
    for (int k = 4; k >= 1; --k) {
        if (s1.substr(5 - k) == s2.substr(0, k)) {
            return k;
        }
    }
    return 0;
}

void precompute() {
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            char_locs[A[r][c] - 'A'].push_back({r, c});
        }
    }

    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) overlaps[i][j] = 0;
            else overlaps[i][j] = calc_overlap(T[i], T[j]);
        }
    }
}

// Optimized function to calculate min cost to type string `s` starting from `start_p`
pair<int, Point> get_path_cost(Point start_p, const string& s) {
    if (s.empty()) return {0, start_p};
    int len = s.length();
    
    // Layer 0
    int c0 = s[0] - 'A';
    const auto& locs0 = char_locs[c0];
    int n0 = locs0.size();
    for(int i = 0; i < n0; ++i) {
        dp_buf[0][i] = abs(start_p.r - locs0[i].r) + abs(start_p.c - locs0[i].c) + 1;
    }
    
    // Layers 1 to len-1
    for(int k = 1; k < len; ++k) {
        int ck = s[k] - 'A';
        int cprev = s[k-1] - 'A';
        const auto& locs_k = char_locs[ck];
        const auto& locs_prev = char_locs[cprev];
        int nk = locs_k.size();
        int nprev = locs_prev.size();
        
        for(int i = 0; i < nk; ++i) {
            int r_curr = locs_k[i].r;
            int c_curr = locs_k[i].c;
            int min_val = 1e9;
            for(int j = 0; j < nprev; ++j) {
                int val = dp_buf[k-1][j] + abs(r_curr - locs_prev[j].r) + abs(c_curr - locs_prev[j].c) + 1;
                if(val < min_val) min_val = val;
            }
            dp_buf[k][i] = min_val;
        }
    }
    
    int last_idx = len - 1;
    int c_last = s[last_idx] - 'A';
    const auto& locs_last = char_locs[c_last];
    int n_last = locs_last.size();
    
    int min_total = 1e9;
    for(int i = 0; i < n_last; ++i) {
        if(dp_buf[last_idx][i] < min_total) min_total = dp_buf[last_idx][i];
    }
    
    // Reservoir sampling for tie-breaking
    int count = 0;
    int chosen_idx = 0;
    for(int i = 0; i < n_last; ++i) {
        if(dp_buf[last_idx][i] == min_total) {
            count++;
            if ((rand() % count) == 0) {
                chosen_idx = i;
            }
        }
    }
    
    return {min_total, locs_last[chosen_idx]};
}

// Global DP to reconstruct full path from a string sequence
int solve_full_path(const string& full_s, vector<Op>& ops) {
    if (full_s.empty()) return 0;
    int len = full_s.length();
    
    vector<vector<int>> dp(len);
    vector<vector<int>> parent(len);
    
    int c0 = full_s[0] - 'A';
    int n0 = char_locs[c0].size();
    dp[0].resize(n0);
    parent[0].resize(n0, -1);
    
    Point start = {start_r, start_c};
    for(int i = 0; i < n0; ++i) {
        dp[0][i] = dist(start, char_locs[c0][i]) + 1;
    }
    
    for(int k = 1; k < len; ++k) {
        int cur_c = full_s[k] - 'A';
        int prev_c = full_s[k-1] - 'A';
        int n_cur = char_locs[cur_c].size();
        int n_prev = char_locs[prev_c].size();
        
        dp[k].resize(n_cur);
        parent[k].resize(n_cur);
        
        for(int i = 0; i < n_cur; ++i) {
            Point p_curr = char_locs[cur_c][i];
            int best_val = 1e9;
            int best_p = -1;
            
            for(int j = 0; j < n_prev; ++j) {
                Point p_prev = char_locs[prev_c][j];
                int val = dp[k-1][j] + dist(p_prev, p_curr) + 1;
                if(val < best_val) {
                    best_val = val;
                    best_p = j;
                }
            }
            dp[k][i] = best_val;
            parent[k][i] = best_p;
        }
    }
    
    int last_c = full_s.back() - 'A';
    int best_val = 1e9;
    int curr_idx = -1;
    for(int i = 0; i < (int)dp[len-1].size(); ++i) {
        if(dp[len-1][i] < best_val) {
            best_val = dp[len-1][i];
            curr_idx = i;
        }
    }
    
    ops.resize(len);
    for(int k = len - 1; k >= 0; --k) {
        int char_idx = full_s[k] - 'A';
        Point p = char_locs[char_idx][curr_idx];
        ops[k] = {p.r, p.c};
        curr_idx = parent[k][curr_idx];
    }
    
    return best_val;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    srand(0);
    
    if (!(cin >> N >> M)) return 0;
    cin >> start_r >> start_c;
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < M; ++i) cin >> T[i];
    
    precompute();
    
    clock_t start_time = clock();
    
    int min_total_cost = 1e9;
    vector<Op> best_ops;
    
    while (true) {
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > TIME_LIMIT) break;
        
        vector<int> seq;
        seq.reserve(M);
        vector<bool> visited(M, false);
        
        int start_node = rand() % M;
        seq.push_back(start_node);
        visited[start_node] = true;
        
        Point cur_p = {start_r, start_c};
        pair<int, Point> res = get_path_cost(cur_p, T[start_node]);
        cur_p = res.second;
        
        int curr = start_node;
        
        for (int step = 1; step < M; ++step) {
            int max_ov = -1;
            vector<int> candidates;
            
            for (int i = 0; i < M; ++i) {
                if (!visited[i]) {
                    int ov = overlaps[curr][i];
                    if (ov > max_ov) {
                        max_ov = ov;
                        candidates.clear();
                        candidates.push_back(i);
                    } else if (ov == max_ov) {
                        candidates.push_back(i);
                    }
                }
            }
            
            int max_checks = 20;
            if (candidates.size() > (size_t)max_checks) {
                 for (int k=0; k < (int)candidates.size(); ++k) {
                     int r = rand() % candidates.size();
                     swap(candidates[k], candidates[r]);
                 }
                 candidates.resize(max_checks);
            }
            
            int best_cand_idx = -1;
            int min_move_cost = 1e9;
            Point best_cand_end_pos = cur_p;
            
            for (int next_cand : candidates) {
                string suffix = T[next_cand].substr(max_ov);
                pair<int, Point> path_res = get_path_cost(cur_p, suffix);
                
                if (path_res.first < min_move_cost) {
                    min_move_cost = path_res.first;
                    best_cand_idx = next_cand;
                    best_cand_end_pos = path_res.second;
                }
            }
            
            curr = best_cand_idx;
            visited[curr] = true;
            seq.push_back(curr);
            cur_p = best_cand_end_pos;
        }
        
        string full_s = T[seq[0]];
        for (size_t i = 1; i < seq.size(); ++i) {
            int prev = seq[i-1];
            int curr = seq[i];
            int ov = overlaps[prev][curr];
            full_s += T[curr].substr(ov);
        }
        
        vector<Op> ops;
        int total_cost = solve_full_path(full_s, ops);
        
        if (total_cost < min_total_cost) {
            min_total_cost = total_cost;
            best_ops = ops;
        }
    }
    
    for (const auto& op : best_ops) {
        cout << op.r << " " << op.c << "\n";
    }
    
    return 0;
}