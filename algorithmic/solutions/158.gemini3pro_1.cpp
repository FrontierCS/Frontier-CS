#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>
#include <numeric>

using namespace std;

// Constants
const int MAX_COORD = 1000000000;
const double TIME_LIMIT = 1.95;

struct Point {
    int id;
    int x, y;
    int rank_x, rank_y;
};

int N, K;
int A[11];
vector<Point> points;
vector<int> uniq_x, uniq_y;
vector<vector<int>> pts_at_x_rank, pts_at_y_rank;

// State
vector<int> x_cuts; // indices in uniq_x. cut[i] means cut is after uniq_x[cut[i]]
vector<int> y_cuts;
int grid[105][105];
int freq[10005]; // Piece sizes can be up to N
int current_score_raw; // sum min(a_d, freq[d])
int total_target;

// Point location cache
vector<pair<int, int>> pt_loc; // {col, row}

// RNG
mt19937 rng(12345);

void compute_score() {
    current_score_raw = 0;
    for (int d = 1; d <= 10; ++d) {
        current_score_raw += min(A[d], freq[d]);
    }
}

void full_rebuild() {
    // Clear grid and freq
    for (int i = 0; i <= (int)x_cuts.size(); ++i) {
        for (int j = 0; j <= (int)y_cuts.size(); ++j) {
            grid[i][j] = 0;
        }
    }
    fill(freq, freq + N + 1, 0);
    
    // Recalculate locations
    for (int i = 0; i < N; ++i) {
        int r_x = points[i].rank_x;
        int r_y = points[i].rank_y;
        
        int c = lower_bound(x_cuts.begin(), x_cuts.end(), r_x) - x_cuts.begin();
        int r = lower_bound(y_cuts.begin(), y_cuts.end(), r_y) - y_cuts.begin();
        
        pt_loc[i] = {c, r};
        grid[c][r]++;
    }
    
    // Update freq
    for (int i = 0; i <= (int)x_cuts.size(); ++i) {
        for (int j = 0; j <= (int)y_cuts.size(); ++j) {
            if (grid[i][j] > 0) freq[grid[i][j]]++;
        }
    }
    
    compute_score();
}

void update_freq(int old_cnt, int new_cnt) {
    if (old_cnt > 0) {
        if (old_cnt <= 10) current_score_raw -= min(A[old_cnt], freq[old_cnt]);
        freq[old_cnt]--;
        if (old_cnt <= 10) current_score_raw += min(A[old_cnt], freq[old_cnt]);
    }
    if (new_cnt > 0) {
        if (new_cnt <= 10) current_score_raw -= min(A[new_cnt], freq[new_cnt]);
        freq[new_cnt]++;
        if (new_cnt <= 10) current_score_raw += min(A[new_cnt], freq[new_cnt]);
    }
}

// Move x_cuts[idx] from val to val + 1
// This means the cut boundary moves to the right.
// Points at rank (val + 1) move from column (idx+1) to column (idx).
void move_x_cut_right(int idx) {
    int val = x_cuts[idx];
    int rank_to_move = val + 1;
    if (rank_to_move >= (int)pts_at_x_rank.size()) return; 
    
    for (int p_idx : pts_at_x_rank[rank_to_move]) {
        int r = pt_loc[p_idx].second;
        int c_old = idx + 1;
        int c_new = idx;
        
        update_freq(grid[c_old][r], grid[c_old][r] - 1);
        grid[c_old][r]--;
        
        update_freq(grid[c_new][r], grid[c_new][r] + 1);
        grid[c_new][r]++;
        
        pt_loc[p_idx].first = c_new;
    }
    x_cuts[idx]++;
}

// Move x_cuts[idx] from val to val - 1
// Cut moves left. Points at rank (val) move from col (idx) to col (idx+1).
void move_x_cut_left(int idx) {
    int val = x_cuts[idx];
    int rank_to_move = val;
    
    for (int p_idx : pts_at_x_rank[rank_to_move]) {
        int r = pt_loc[p_idx].second;
        int c_old = idx;
        int c_new = idx + 1;
        
        update_freq(grid[c_old][r], grid[c_old][r] - 1);
        grid[c_old][r]--;
        
        update_freq(grid[c_new][r], grid[c_new][r] + 1);
        grid[c_new][r]++;
        
        pt_loc[p_idx].first = c_new;
    }
    x_cuts[idx]--;
}

void move_y_cut_right(int idx) {
    int val = y_cuts[idx];
    int rank_to_move = val + 1;
    if (rank_to_move >= (int)pts_at_y_rank.size()) return;
    
    for (int p_idx : pts_at_y_rank[rank_to_move]) {
        int c = pt_loc[p_idx].first;
        int r_old = idx + 1;
        int r_new = idx;
        
        update_freq(grid[c][r_old], grid[c][r_old] - 1);
        grid[c][r_old]--;
        
        update_freq(grid[c][r_new], grid[c][r_new] + 1);
        grid[c][r_new]++;
        
        pt_loc[p_idx].second = r_new;
    }
    y_cuts[idx]++;
}

void move_y_cut_left(int idx) {
    int val = y_cuts[idx];
    int rank_to_move = val;
    
    for (int p_idx : pts_at_y_rank[rank_to_move]) {
        int c = pt_loc[p_idx].first;
        int r_old = idx;
        int r_new = idx + 1;
        
        update_freq(grid[c][r_old], grid[c][r_old] - 1);
        grid[c][r_old]--;
        
        update_freq(grid[c][r_new], grid[c][r_new] + 1);
        grid[c][r_new]++;
        
        pt_loc[p_idx].second = r_new;
    }
    y_cuts[idx]--;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::steady_clock::now();

    cin >> N >> K;
    total_target = 0;
    for (int d = 1; d <= 10; ++d) {
        cin >> A[d];
        total_target += A[d];
    }
    
    points.resize(N);
    vector<int> raw_x(N), raw_y(N);
    for (int i = 0; i < N; ++i) {
        cin >> points[i].x >> points[i].y;
        points[i].id = i;
        raw_x[i] = points[i].x;
        raw_y[i] = points[i].y;
    }
    
    sort(raw_x.begin(), raw_x.end());
    raw_x.erase(unique(raw_x.begin(), raw_x.end()), raw_x.end());
    uniq_x = raw_x;
    
    sort(raw_y.begin(), raw_y.end());
    raw_y.erase(unique(raw_y.begin(), raw_y.end()), raw_y.end());
    uniq_y = raw_y;
    
    pts_at_x_rank.resize(uniq_x.size());
    pts_at_y_rank.resize(uniq_y.size());
    
    for (int i = 0; i < N; ++i) {
        points[i].rank_x = lower_bound(uniq_x.begin(), uniq_x.end(), points[i].x) - uniq_x.begin();
        points[i].rank_y = lower_bound(uniq_y.begin(), uniq_y.end(), points[i].y) - uniq_y.begin();
        pts_at_x_rank[points[i].rank_x].push_back(i);
        pts_at_y_rank[points[i].rank_y].push_back(i);
    }
    
    pt_loc.resize(N);
    
    // Initial solution: distribute cuts evenly
    int k_x = 50;
    int k_y = 50;
    if (k_x > (int)uniq_x.size() - 1) k_x = max(0, (int)uniq_x.size() - 1);
    if (k_y > (int)uniq_y.size() - 1) k_y = max(0, (int)uniq_y.size() - 1);
    
    if (k_x + k_y > K) {
        k_x = K / 2;
        k_y = K - k_x;
    }

    // Initialize cuts based on rank percentiles
    for (int i = 0; i < k_x; ++i) {
        x_cuts.push_back((long long)(i + 1) * (uniq_x.size() - 1) / (k_x + 1));
    }
    for (int i = 0; i < k_y; ++i) {
        y_cuts.push_back((long long)(i + 1) * (uniq_y.size() - 1) / (k_y + 1));
    }
    // Clean up
    sort(x_cuts.begin(), x_cuts.end());
    x_cuts.erase(unique(x_cuts.begin(), x_cuts.end()), x_cuts.end());
    sort(y_cuts.begin(), y_cuts.end());
    y_cuts.erase(unique(y_cuts.begin(), y_cuts.end()), y_cuts.end());
    
    full_rebuild();
    
    int best_score = current_score_raw;
    vector<int> best_x = x_cuts;
    vector<int> best_y = y_cuts;
    
    // SA parameters
    double t0 = 2.0;
    double t1 = 0.0;
    double current_temp = t0;
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > TIME_LIMIT) break;
            current_temp = t0 + (t1 - t0) * (elapsed / TIME_LIMIT);
        }
        
        int type = rng() % 100;
        int prev_score = current_score_raw;
        
        if (type < 4 && (int)(x_cuts.size() + y_cuts.size()) < K) { // Add cut
            bool is_x = rng() % 2;
            if (is_x) {
                if (uniq_x.size() <= 1) continue;
                int val = rng() % (uniq_x.size() - 1);
                bool exists = false;
                for(int v : x_cuts) if(v == val) exists = true;
                if (!exists) {
                    x_cuts.push_back(val);
                    sort(x_cuts.begin(), x_cuts.end());
                    full_rebuild();
                    int diff = current_score_raw - prev_score;
                    if (diff >= 0 || (current_temp > 1e-9 && exp(diff / current_temp) > (double)(rng() % 10000) / 10000.0)) {
                        // Accept
                    } else {
                        // Revert
                        for(size_t i=0; i<x_cuts.size(); ++i) {
                            if (x_cuts[i] == val) {
                                x_cuts.erase(x_cuts.begin() + i);
                                break;
                            }
                        }
                        full_rebuild();
                    }
                }
            } else {
                if (uniq_y.size() <= 1) continue;
                int val = rng() % (uniq_y.size() - 1);
                bool exists = false;
                for(int v : y_cuts) if(v == val) exists = true;
                if (!exists) {
                    y_cuts.push_back(val);
                    sort(y_cuts.begin(), y_cuts.end());
                    full_rebuild();
                    int diff = current_score_raw - prev_score;
                    if (diff >= 0 || (current_temp > 1e-9 && exp(diff / current_temp) > (double)(rng() % 10000) / 10000.0)) {
                    } else {
                         for(size_t i=0; i<y_cuts.size(); ++i) {
                            if (y_cuts[i] == val) {
                                y_cuts.erase(y_cuts.begin() + i);
                                break;
                            }
                        }
                        full_rebuild();
                    }
                }
            }
        } else if (type < 8 && x_cuts.size() + y_cuts.size() > 0) { // Remove cut
            bool is_x = rng() % 2;
            if (x_cuts.empty()) is_x = false;
            if (y_cuts.empty()) is_x = true;
            
            if (is_x && !x_cuts.empty()) {
                int idx = rng() % x_cuts.size();
                int val = x_cuts[idx];
                x_cuts.erase(x_cuts.begin() + idx);
                full_rebuild();
                int diff = current_score_raw - prev_score;
                if (diff >= 0 || (current_temp > 1e-9 && exp(diff / current_temp) > (double)(rng() % 10000) / 10000.0)) {
                } else {
                    x_cuts.insert(x_cuts.begin() + idx, val); 
                    full_rebuild();
                }
            } else if (!is_x && !y_cuts.empty()) {
                int idx = rng() % y_cuts.size();
                int val = y_cuts[idx];
                y_cuts.erase(y_cuts.begin() + idx);
                full_rebuild();
                int diff = current_score_raw - prev_score;
                if (diff >= 0 || (current_temp > 1e-9 && exp(diff / current_temp) > (double)(rng() % 10000) / 10000.0)) {
                } else {
                    y_cuts.insert(y_cuts.begin() + idx, val);
                    full_rebuild();
                }
            }
        } else { // Move cut
            bool is_x = rng() % 2;
            if (x_cuts.empty()) is_x = false;
            if (y_cuts.empty()) is_x = true;
            if (x_cuts.empty() && y_cuts.empty()) continue;
            
            if (is_x) {
                int idx = rng() % x_cuts.size();
                int dir = (rng() % 2) ? 1 : -1;
                
                int val = x_cuts[idx];
                int next_val = val + dir;
                
                if (next_val < 0 || next_val >= (int)uniq_x.size() - 1) continue;
                if (idx > 0 && dir == -1 && next_val <= x_cuts[idx-1]) continue;
                if (idx < (int)x_cuts.size() - 1 && dir == 1 && next_val >= x_cuts[idx+1]) continue;
                
                if (dir == 1) move_x_cut_right(idx);
                else move_x_cut_left(idx);
                
                int diff = current_score_raw - prev_score;
                if (diff >= 0 || (current_temp > 1e-9 && exp(diff / current_temp) > (double)(rng() % 10000) / 10000.0)) {
                } else {
                    if (dir == 1) move_x_cut_left(idx);
                    else move_x_cut_right(idx);
                }
            } else {
                int idx = rng() % y_cuts.size();
                int dir = (rng() % 2) ? 1 : -1;
                
                int val = y_cuts[idx];
                int next_val = val + dir;
                
                if (next_val < 0 || next_val >= (int)uniq_y.size() - 1) continue;
                if (idx > 0 && dir == -1 && next_val <= y_cuts[idx-1]) continue;
                if (idx < (int)y_cuts.size() - 1 && dir == 1 && next_val >= y_cuts[idx+1]) continue;
                
                if (dir == 1) move_y_cut_right(idx);
                else move_y_cut_left(idx);
                
                int diff = current_score_raw - prev_score;
                if (diff >= 0 || (current_temp > 1e-9 && exp(diff / current_temp) > (double)(rng() % 10000) / 10000.0)) {
                } else {
                    if (dir == 1) move_y_cut_left(idx);
                    else move_y_cut_right(idx);
                }
            }
        }
        
        if (current_score_raw > best_score) {
            best_score = current_score_raw;
            best_x = x_cuts;
            best_y = y_cuts;
        }
    }
    
    // Output
    cout << best_x.size() + best_y.size() << "\n";
    for (int idx : best_x) {
        int val = uniq_x[idx];
        cout << val << " " << -1000000000 << " " << val + 1 << " " << 1000000000 << "\n";
    }
    for (int idx : best_y) {
        int val = uniq_y[idx];
        cout << -1000000000 << " " << val << " " << 1000000000 << " " << val + 1 << "\n";
    }

    return 0;
}