#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <climits>

using namespace std;

const int N = 20;
const int BASE_MOVE_COST = 100;

struct Point {
    int r, c;
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
};

int dist(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

struct State {
    int grid[N][N];
    Point truck;
    int load;
    
    State() {
        truck = {0, 0};
        load = 0;
    }
};

string get_path(Point from, Point to) {
    string path = "";
    if (to.r > from.r) path += string(to.r - from.r, 'D');
    else if (to.r < from.r) path += string(from.r - to.r, 'U');
    if (to.c > from.c) path += string(to.c - from.c, 'R');
    else if (to.c < from.c) path += string(from.c - to.c, 'L');
    return path;
}

struct MoveResult {
    int new_load;
    int final_h_target;
};

// Simulate what happens at target
MoveResult simulate_op(const State& s, Point target) {
    MoveResult res;
    int h = s.grid[target.r][target.c];
    res.new_load = s.load;
    res.final_h_target = h;

    if (h > 0) {
        res.new_load += h;
        res.final_h_target = 0;
    } else if (h < 0) {
        if (s.load > 0) {
            int can_drop = min(s.load, -h);
            res.new_load -= can_drop;
            res.final_h_target = h + can_drop;
        }
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in;
    if (!(cin >> n_in)) return 0;
    
    State current_state;
    // Reading input
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> current_state.grid[i][j];
        }
    }

    // Heuristic parameters
    const int K1 = 20; // Search width for first step
    const int K2 = 5;  // Search width for second step

    while (true) {
        vector<Point> non_zeros;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (current_state.grid[i][j] != 0) {
                    non_zeros.push_back({i, j});
                }
            }
        }
        
        if (non_zeros.empty() && current_state.load == 0) break;
        
        vector<pair<int, Point>> candidates;
        for (auto p : non_zeros) {
            // If truck is empty, we must go to a source (positive h)
            if (current_state.load == 0 && current_state.grid[p.r][p.c] < 0) continue;
            candidates.push_back({dist(current_state.truck, p), p});
        }
        
        if (candidates.empty()) break;
        
        // Sort by distance
        sort(candidates.begin(), candidates.end(), [](const pair<int, Point>& a, const pair<int, Point>& b){
            return a.first < b.first;
        });
        
        if (candidates.size() > K1) candidates.resize(K1);
        
        long long best_score = -1;
        Point best_target = candidates[0].second; 
        
        for (auto cand1 : candidates) {
            Point p1 = cand1.second;
            int d1 = cand1.first;
            long long cost1 = (long long)d1 * (BASE_MOVE_COST + current_state.load);
            
            MoveResult r1 = simulate_op(current_state, p1);
            
            // Step 2 candidates
            vector<pair<int, Point>> next_candidates;
            for (auto p : non_zeros) {
                // Determine if p is still valid target
                if (p == p1) {
                    // Check if it's still interesting after op
                    if (r1.final_h_target == 0) continue; 
                    // Usually we don't operate on same cell immediately unless needed, 
                    // but simple heuristic is to skip to encourage movement
                    continue;
                }
                
                if (r1.new_load == 0 && current_state.grid[p.r][p.c] < 0) continue;
                
                next_candidates.push_back({dist(p1, p), p});
            }
            
            sort(next_candidates.begin(), next_candidates.end(), [](const pair<int, Point>& a, const pair<int, Point>& b){
                return a.first < b.first;
            });
            if (next_candidates.size() > K2) next_candidates.resize(K2);
            
            long long min_cost2_and_future = -1;
            
            if (next_candidates.empty()) {
                // Check if done
                bool all_cleared = true;
                for(auto p : non_zeros) {
                    if (p != p1) { all_cleared = false; break; }
                    else if (r1.final_h_target != 0) { all_cleared = false; break; }
                }
                if (all_cleared) min_cost2_and_future = 0;
                else min_cost2_and_future = 1e9; // Penalty for dead end
            } else {
                for (auto cand2 : next_candidates) {
                    Point p2 = cand2.second;
                    int d2 = cand2.first;
                    long long cost2 = (long long)d2 * (BASE_MOVE_COST + r1.new_load);
                    
                    int h2 = current_state.grid[p2.r][p2.c];
                    int load2 = r1.new_load;
                    int final_h2 = h2;
                    
                    if (h2 > 0) {
                        load2 += h2;
                        final_h2 = 0;
                    } else if (h2 < 0) {
                        if (load2 > 0) {
                            int drop = min(load2, -h2);
                            load2 -= drop;
                            final_h2 = h2 + drop;
                        }
                    }
                    
                    // Heuristic future estimate
                    int est_dist = 0;
                    if (load2 > 0) {
                        // Nearest Sink
                        int min_d = 1000;
                        for (auto p : non_zeros) {
                            // Check valid sink state
                            if (p == p1) { if (r1.final_h_target >= 0) continue; }
                            else if (p == p2) { if (final_h2 >= 0) continue; }
                            else if (current_state.grid[p.r][p.c] >= 0) continue;
                            
                            min_d = min(min_d, dist(p2, p));
                        }
                        if (min_d == 1000) min_d = 0; 
                        est_dist = min_d;
                    } else {
                        // Nearest Source
                        int min_d = 1000;
                        for (auto p : non_zeros) {
                            if (p == p1) { if (r1.final_h_target <= 0) continue; }
                            else if (p == p2) { if (final_h2 <= 0) continue; }
                            else if (current_state.grid[p.r][p.c] <= 0) continue;
                            
                            min_d = min(min_d, dist(p2, p));
                        }
                        if (min_d == 1000) min_d = 0;
                        est_dist = min_d;
                    }
                    
                    // Estimated future cost + step 2 cost
                    long long heuristic = cost2 + (long long)est_dist * (BASE_MOVE_COST + load2);
                    if (min_cost2_and_future == -1 || heuristic < min_cost2_and_future) {
                        min_cost2_and_future = heuristic;
                    }
                }
            }
            
            long long total = cost1 + min_cost2_and_future;
            if (best_score == -1 || total < best_score) {
                best_score = total;
                best_target = p1;
            }
        }
        
        Point target = best_target;
        string p_str = get_path(current_state.truck, target);
        for(char c : p_str) cout << c << "\n";
        
        int h = current_state.grid[target.r][target.c];
        if (h > 0) {
            cout << "+" << h << "\n";
            current_state.load += h;
            current_state.grid[target.r][target.c] = 0;
        } else if (h < 0) {
            if (current_state.load > 0) {
                int drop = min(current_state.load, -h);
                cout << "-" << drop << "\n";
                current_state.load -= drop;
                current_state.grid[target.r][target.c] += drop;
            }
        }
        current_state.truck = target;
    }

    return 0;
}