#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

using namespace std;

// Constants
const int MAX_COORD = 10000;
const int LIMIT_COORD = 1000000000;

// Inputs
int N;
int K_input;
int A[11];
struct Point {
    int x, y, id;
};
vector<Point> points;
vector<int> sorted_by_x; // stores point indices
vector<int> sorted_by_y;
vector<int> rank_x; // point id -> rank in sorted_by_x
vector<int> rank_y;

// Occupied coordinates for avoiding strawberry cuts
bool occ_x[20005];
bool occ_y[20005];

// Scoring state
struct State {
    int Kx, Ky;
    vector<int> cut_x; // indices in sorted_by_x
    vector<int> cut_y; 
    
    // Grid counts: flattened (Kx+1) * (Ky+1)
    vector<int> grid_counts;
    
    // Distribution of piece sizes
    int piece_counts[5505];
    
    long long current_score_numerator;

    State() {}
    
    void init(int kx, int ky) {
        Kx = kx;
        Ky = ky;
        cut_x.resize(Kx);
        cut_y.resize(Ky);
        grid_counts.assign((Kx + 1) * (Ky + 1), 0);
        for(int i=0; i<=N; ++i) piece_counts[i] = 0;
        current_score_numerator = 0;
    }
};

// Global Best
long long best_score = -1;
vector<pair<pair<int,int>, pair<int,int>>> best_lines;

// Random
mt19937 rng(123);

void parse_input() {
    if (!(cin >> N >> K_input)) return;
    for (int d = 1; d <= 10; ++d) cin >> A[d];
    points.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> points[i].x >> points[i].y;
        points[i].id = i;
        occ_x[points[i].x + MAX_COORD] = true;
        occ_y[points[i].y + MAX_COORD] = true;
    }
}

void precompute() {
    vector<Point> px = points;
    sort(px.begin(), px.end(), [](const Point& a, const Point& b){
        return a.x < b.x;
    });
    sorted_by_x.resize(N);
    rank_x.resize(N);
    for(int i=0; i<N; ++i) {
        sorted_by_x[i] = px[i].id;
        rank_x[px[i].id] = i;
    }

    vector<Point> py = points;
    sort(py.begin(), py.end(), [](const Point& a, const Point& b){
        return a.y < b.y;
    });
    sorted_by_y.resize(N);
    rank_y.resize(N);
    for(int i=0; i<N; ++i) {
        sorted_by_y[i] = py[i].id;
        rank_y[py[i].id] = i;
    }
}

long long calc_score(const int* piece_counts) {
    long long num = 0;
    for (int d = 1; d <= 10; ++d) {
        num += min(A[d], piece_counts[d]);
    }
    return num;
}

// Global timer
auto global_start_time = chrono::steady_clock::now();

void solve_grid(int kx, int ky, double time_limit_sec) {
    State st;
    st.init(kx, ky);
    
    // Initial cuts: quantiles
    // Try to ensure initial cuts are valid (not between equal coords)
    // If impossible, just place them; local search will fix or we use slanted lines
    for(int i=0; i<kx; ++i) {
        st.cut_x[i] = (long long)(i + 1) * N / (kx + 1) - 1;
    }
    for(int i=0; i<ky; ++i) {
        st.cut_y[i] = (long long)(i + 1) * N / (ky + 1) - 1;
    }
    
    // Assign points to grid cells
    vector<int> p_reg_x(N), p_reg_y(N);
    
    for(int i=0; i<N; ++i) {
        int r = 0;
        while(r < kx && rank_x[i] > st.cut_x[r]) r++;
        p_reg_x[i] = r;
        
        int c = 0;
        while(c < ky && rank_y[i] > st.cut_y[c]) c++;
        p_reg_y[i] = c;
        
        st.grid_counts[r * (ky + 1) + c]++;
    }
    
    for(auto c : st.grid_counts) {
        if(c <= 5500) st.piece_counts[c]++;
    }
    
    st.current_score_numerator = calc_score(st.piece_counts);
    
    auto start_time = chrono::steady_clock::now();
    
    int iter = 0;
    while(true) {
        iter++;
        if((iter & 511) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration<double>(now - start_time).count() > time_limit_sec) break;
            if (chrono::duration<double>(now - global_start_time).count() > 2.85) break;
        }

        bool is_x = std::uniform_int_distribution<>(0, 1)(rng);
        int cut_idx = -1;
        int old_pos = -1;
        int new_pos = -1;

        if (is_x) {
            if (kx == 0) continue;
            cut_idx = std::uniform_int_distribution<>(0, kx - 1)(rng);
            old_pos = st.cut_x[cut_idx];
            int delta = std::uniform_int_distribution<>(-N/10, N/10)(rng);
            if (delta == 0) continue;
            new_pos = old_pos + delta;
        } else {
            if (ky == 0) continue;
            cut_idx = std::uniform_int_distribution<>(0, ky - 1)(rng);
            old_pos = st.cut_y[cut_idx];
            int delta = std::uniform_int_distribution<>(-N/10, N/10)(rng);
            if (delta == 0) continue;
            new_pos = old_pos + delta;
        }

        if(new_pos < -1) new_pos = -1;
        if(new_pos > N - 1) new_pos = N - 1;

        // Check constraints
        if(is_x) {
            int lower = (cut_idx == 0) ? -1 : st.cut_x[cut_idx - 1];
            int upper = (cut_idx == kx - 1) ? N - 1 : st.cut_x[cut_idx + 1];
            if(new_pos < lower) new_pos = lower;
            if(new_pos > upper) new_pos = upper;
        } else {
            int lower = (cut_idx == 0) ? -1 : st.cut_y[cut_idx - 1];
            int upper = (cut_idx == ky - 1) ? N - 1 : st.cut_y[cut_idx + 1];
            if(new_pos < lower) new_pos = lower;
            if(new_pos > upper) new_pos = upper;
        }

        if (new_pos == old_pos) continue;

        // Ensure realizability: cannot cut between identical coordinates
        if (new_pos >= 0 && new_pos < N - 1) {
            if (is_x) {
                if (points[sorted_by_x[new_pos]].x == points[sorted_by_x[new_pos+1]].x) continue;
            } else {
                if (points[sorted_by_y[new_pos]].y == points[sorted_by_y[new_pos+1]].y) continue;
            }
        }
        
        long long current_score = st.current_score_numerator;
        
        int r_low, r_high;
        if(old_pos < new_pos) { r_low = old_pos + 1; r_high = new_pos; }
        else { r_low = new_pos + 1; r_high = old_pos; }

        vector<int> affected_points;
        affected_points.reserve(r_high - r_low + 1);
        if (is_x) {
            for(int k = r_low; k <= r_high; ++k) affected_points.push_back(sorted_by_x[k]);
        } else {
            for(int k = r_low; k <= r_high; ++k) affected_points.push_back(sorted_by_y[k]);
        }
        
        if (affected_points.empty()) {
            if (is_x) st.cut_x[cut_idx] = new_pos;
            else st.cut_y[cut_idx] = new_pos;
            continue;
        }

        long long new_score = current_score;
        
        for (int pid : affected_points) {
            int old_rx = p_reg_x[pid];
            int old_ry = p_reg_y[pid];
            
            int new_rx = old_rx;
            int new_ry = old_ry;
            
            if (is_x) {
                if (old_pos < new_pos) new_rx = cut_idx;
                else new_rx = cut_idx + 1;
            } else {
                if (old_pos < new_pos) new_ry = cut_idx;
                else new_ry = cut_idx + 1;
            }
            
            int old_gidx = old_rx * (ky + 1) + old_ry;
            int new_gidx = new_rx * (ky + 1) + new_ry;
            
            if (old_gidx == new_gidx) continue;
            
            int cnt = st.grid_counts[old_gidx];
            if (cnt <= 5500) {
                 if (cnt <= 10 && cnt > 0) new_score -= min(A[cnt], st.piece_counts[cnt]);
                 st.piece_counts[cnt]--;
                 if (cnt <= 10 && cnt > 0) new_score += min(A[cnt], st.piece_counts[cnt]);
            }
            
            st.grid_counts[old_gidx]--;
            int next_cnt = cnt - 1;
            if (next_cnt <= 5500) {
                if (next_cnt <= 10 && next_cnt > 0) new_score -= min(A[next_cnt], st.piece_counts[next_cnt]);
                st.piece_counts[next_cnt]++;
                if (next_cnt <= 10 && next_cnt > 0) new_score += min(A[next_cnt], st.piece_counts[next_cnt]);
            }
            
            cnt = st.grid_counts[new_gidx];
            if (cnt <= 5500) {
                 if (cnt <= 10 && cnt > 0) new_score -= min(A[cnt], st.piece_counts[cnt]);
                 st.piece_counts[cnt]--;
                 if (cnt <= 10 && cnt > 0) new_score += min(A[cnt], st.piece_counts[cnt]);
            }
            
            st.grid_counts[new_gidx]++;
            next_cnt = cnt + 1;
            if (next_cnt <= 5500) {
                if (next_cnt <= 10) new_score -= min(A[next_cnt], st.piece_counts[next_cnt]);
                st.piece_counts[next_cnt]++;
                if (next_cnt <= 10) new_score += min(A[next_cnt], st.piece_counts[next_cnt]);
            }
            
            p_reg_x[pid] = new_rx;
            p_reg_y[pid] = new_ry;
        }

        if (new_score >= current_score) {
            st.current_score_numerator = new_score;
            if (is_x) st.cut_x[cut_idx] = new_pos;
            else st.cut_y[cut_idx] = new_pos;
        } else {
            // Revert
            for (int pid : affected_points) {
                int cur_rx = p_reg_x[pid];
                int cur_ry = p_reg_y[pid];
                
                int orig_rx = cur_rx;
                int orig_ry = cur_ry;
                
                if (is_x) {
                    if (old_pos < new_pos) orig_rx = cut_idx + 1;
                    else orig_rx = cut_idx;
                } else {
                    if (old_pos < new_pos) orig_ry = cut_idx + 1;
                    else orig_ry = cut_idx;
                }
                
                 int old_gidx = cur_rx * (ky + 1) + cur_ry;
                 int new_gidx = orig_rx * (ky + 1) + orig_ry;
                 
                 int cnt = st.grid_counts[old_gidx];
                 st.piece_counts[cnt]--;
                 st.grid_counts[old_gidx]--;
                 st.piece_counts[cnt-1]++;
                 
                 cnt = st.grid_counts[new_gidx];
                 st.piece_counts[cnt]--;
                 st.grid_counts[new_gidx]++;
                 st.piece_counts[cnt+1]++;
                 
                 p_reg_x[pid] = orig_rx;
                 p_reg_y[pid] = orig_ry;
            }
        }
    }
    
    if (st.current_score_numerator > best_score) {
        best_score = st.current_score_numerator;
        best_lines.clear();
        
        for(int x_idx : st.cut_x) {
            int x1 = (x_idx == -1) ? -MAX_COORD - 100 : points[sorted_by_x[x_idx]].x;
            int x2 = (x_idx == N - 1) ? MAX_COORD + 100 : points[sorted_by_x[x_idx+1]].x;
            
            int mid = (int)floor((x1 + x2) / 2.0);
            int best_c = -20000;
            
            for(int d=0; d<100; ++d) {
                int c1 = mid + d;
                if(c1 >= -MAX_COORD && c1 <= MAX_COORD && !occ_x[c1 + MAX_COORD]) { best_c = c1; break; }
                int c2 = mid - d;
                if(c2 >= -MAX_COORD && c2 <= MAX_COORD && !occ_x[c2 + MAX_COORD]) { best_c = c2; break; }
            }
            
            if(best_c != -20000) {
                best_lines.push_back({{best_c, -LIMIT_COORD}, {best_c, LIMIT_COORD}});
            } else {
                // Use slanted line if no integer coordinate found
                // Pass between x1 and x2
                best_lines.push_back({{x1, -LIMIT_COORD}, {x2, LIMIT_COORD}});
            }
        }
        for(int y_idx : st.cut_y) {
            int y1 = (y_idx == -1) ? -MAX_COORD - 100 : points[sorted_by_y[y_idx]].y;
            int y2 = (y_idx == N - 1) ? MAX_COORD + 100 : points[sorted_by_y[y_idx+1]].y;
            
            int mid = (int)floor((y1 + y2) / 2.0);
            int best_c = -20000;
            for(int d=0; d<100; ++d) {
                int c1 = mid + d;
                if(c1 >= -MAX_COORD && c1 <= MAX_COORD && !occ_y[c1 + MAX_COORD]) { best_c = c1; break; }
                int c2 = mid - d;
                if(c2 >= -MAX_COORD && c2 <= MAX_COORD && !occ_y[c2 + MAX_COORD]) { best_c = c2; break; }
            }
            if(best_c != -20000) {
                best_lines.push_back({{-LIMIT_COORD, best_c}, {LIMIT_COORD, best_c}});
            } else {
                best_lines.push_back({{-LIMIT_COORD, y1}, {LIMIT_COORD, y2}});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    parse_input();
    precompute();
    
    int sum_a = 0;
    for(int d=1;d<=10;++d) sum_a += A[d];
    
    int min_k = sqrt(sum_a) / 2; 
    if (min_k < 2) min_k = 2;
    int max_k = 50; 
    if (max_k > K_input / 2) max_k = K_input / 2;
    
    vector<int> sizes;
    for(int k=min_k; k<=max_k; ++k) sizes.push_back(k);
    
    double total_time = 2.8;
    double time_per_config = total_time / (sizes.size() + 1);
    if(time_per_config < 0.02) time_per_config = 0.02;
    
    for(int k : sizes) {
        if (chrono::duration<double>(chrono::steady_clock::now() - global_start_time).count() > 2.85) break;
        solve_grid(k, k, time_per_config);
    }
    
    cout << best_lines.size() << "\n";
    for(auto& l : best_lines) {
        cout << l.first.first << " " << l.first.second << " " << l.second.first << " " << l.second.second << "\n";
    }
    
    return 0;
}