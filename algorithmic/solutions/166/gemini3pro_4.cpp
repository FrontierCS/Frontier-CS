#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Problem specific constants and variables
const int N = 20;
long long grid[N][N];
int cur_r = 0, cur_c = 0;
long long cur_load = 0;

// Function to calculate Manhattan distance
int get_dist(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

// Function to output movement commands and update current position
void move_to(int r, int c) {
    while (cur_r < r) { cout << "D\n"; cur_r++; }
    while (cur_r > r) { cout << "U\n"; cur_r--; }
    while (cur_c < c) { cout << "R\n"; cur_c++; }
    while (cur_c > c) { cout << "L\n"; cur_c--; }
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in;
    if (cin >> n_in) {
        // N is fixed at 20 but reading it as per format
    }
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> grid[i][j];
        }
    }

    // Heuristic parameter
    // If load exceeds this, we prioritize unloading even if a source is slightly closer.
    // However, the logic below primarily uses distance, using this only as a hard switch or tie breaker bias.
    const long long HIGH_LOAD = 400; 

    while (true) {
        // Identify all sources and sinks
        vector<pair<int, int>> sources;
        vector<pair<int, int>> sinks;
        bool all_zero = true;

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] > 0) {
                    sources.push_back({i, j});
                    all_zero = false;
                } else if (grid[i][j] < 0) {
                    sinks.push_back({i, j});
                    all_zero = false;
                }
            }
        }

        if (all_zero && cur_load == 0) break;

        int target_r = -1, target_c = -1;
        bool target_is_source = false;

        // Find nearest source
        int best_s_idx = -1;
        int min_s_dist = 1e9;
        // Tie-breaking: maximize amount at source
        long long max_s_val = -1;

        for (int i = 0; i < sources.size(); ++i) {
            int d = get_dist(cur_r, cur_c, sources[i].first, sources[i].second);
            if (d < min_s_dist) {
                min_s_dist = d;
                best_s_idx = i;
                max_s_val = grid[sources[i].first][sources[i].second];
            } else if (d == min_s_dist) {
                if (grid[sources[i].first][sources[i].second] > max_s_val) {
                    max_s_val = grid[sources[i].first][sources[i].second];
                    best_s_idx = i;
                }
            }
        }

        // Find nearest sink
        int best_t_idx = -1;
        int min_t_dist = 1e9;
        // Tie-breaking: maximize need at sink (magnitude)
        long long max_t_need = -1;

        for (int i = 0; i < sinks.size(); ++i) {
            int d = get_dist(cur_r, cur_c, sinks[i].first, sinks[i].second);
            if (d < min_t_dist) {
                min_t_dist = d;
                best_t_idx = i;
                max_t_need = abs(grid[sinks[i].first][sinks[i].second]);
            } else if (d == min_t_dist) {
                if (abs(grid[sinks[i].first][sinks[i].second]) > max_t_need) {
                    max_t_need = abs(grid[sinks[i].first][sinks[i].second]);
                    best_t_idx = i;
                }
            }
        }

        // Decision Strategy
        if (cur_load == 0) {
            // Must go to source
            if (best_s_idx != -1) {
                target_r = sources[best_s_idx].first;
                target_c = sources[best_s_idx].second;
                target_is_source = true;
            } else {
                // Should be done
                break;
            }
        } else {
            // Can go source or sink
            if (best_s_idx == -1) {
                // No sources left, go to sink
                if (best_t_idx != -1) {
                    target_r = sinks[best_t_idx].first;
                    target_c = sinks[best_t_idx].second;
                    target_is_source = false;
                } else {
                    // No sinks? (Should imply load=0 if sum=0, but loop check handles this)
                    break;
                }
            } else if (best_t_idx == -1) {
                // No sinks left? (Possible if we have load equal to remaining sources? No sum is 0.)
                // This case technically implies sum(grid) > 0 which violates problem statement unless load balances it.
                // If sum(grid) = -load, and load > 0, then sum(grid) < 0. Must be sinks.
                // So this branch is unlikely/impossible.
                break;
            } else {
                // Both exist.
                // If load is very high, force sink
                if (cur_load > HIGH_LOAD) {
                    target_r = sinks[best_t_idx].first;
                    target_c = sinks[best_t_idx].second;
                    target_is_source = false;
                } else {
                    // Go to the nearest interesting point
                    // Bias towards collecting if equal? Or distributing?
                    // Moving with load is expensive. If sink is closer, unloading is good.
                    // If source is closer, collecting is good (cluster handling).
                    if (min_s_dist <= min_t_dist) {
                        target_r = sources[best_s_idx].first;
                        target_c = sources[best_s_idx].second;
                        target_is_source = true;
                    } else {
                        target_r = sinks[best_t_idx].first;
                        target_c = sinks[best_t_idx].second;
                        target_is_source = false;
                    }
                }
            }
        }

        // Execute move and operation
        move_to(target_r, target_c);
        
        if (target_is_source) {
            long long amt = grid[target_r][target_c];
            cout << "+" << amt << "\n";
            cur_load += amt;
            grid[target_r][target_c] = 0;
        } else {
            long long need = -grid[target_r][target_c]; // grid is negative
            long long give = min(cur_load, need);
            cout << "-" << give << "\n";
            cur_load -= give;
            grid[target_r][target_c] += give;
        }
    }

    return 0;
}