#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Function to send queries and receive results
// Returns a vector of results (0 or 1) corresponding to the queries sent
vector<int> send_robots(const vector<vector<int>>& queries) {
    if (queries.empty()) return {};
    for (const auto& q : queries) {
        cout << "? " << q.size();
        for (int x : q) cout << " " << x;
        cout << "\n";
    }
    cout.flush();
    cout << "@" << endl;
    int L;
    if (!(cin >> L)) exit(0);
    vector<int> res(L);
    for (int i = 0; i < L; ++i) cin >> res[i];
    return res;
}

// Adaptive strategy using binary splitting of ranges
// Efficient for H >= 12, typically uses ~20 robots.
void solve_adaptive(int R_limit, int H_limit) {
    struct Range {
        int L, R;
        int count; // Number of chairmen known to be in this range
    };
    
    vector<Range> state;
    state.push_back({1, 1000, 2});
    
    vector<int> final_positions;
    
    for (int h = 0; h < H_limit; ++h) {
        if (state.empty()) break;
        
        vector<vector<int>> current_batch;
        
        // Check if there are any active ranges to query
        bool any_query = false;
        for (const auto& r : state) {
            if (r.count > 0 && r.L < r.R) {
                any_query = true;
                break;
            }
        }
        if (!any_query) break;

        // Generate queries based on current state
        for (int i = 0; i < state.size(); ++i) {
            if (state[i].count == 0 || state[i].L == state[i].R) continue;
            
            int mid = (state[i].L + state[i].R) / 2;
            
            if (state[i].count == 2) {
                // Split 2 items: check left and check right
                vector<int> q1, q2;
                for (int x = state[i].L; x <= mid; ++x) q1.push_back(x);
                for (int x = mid + 1; x <= state[i].R; ++x) q2.push_back(x);
                current_batch.push_back(q1);
                current_batch.push_back(q2);
            } else if (state[i].count == 1) {
                // Split 1 item: check left
                vector<int> q1;
                for (int x = state[i].L; x <= mid; ++x) q1.push_back(x);
                current_batch.push_back(q1);
            }
        }
        
        vector<int> results = send_robots(current_batch);
        
        vector<Range> next_state;
        int res_idx = 0;
        
        for (const auto& r : state) {
            if (r.count == 0) continue;
            
            if (r.L == r.R) {
                // Range collapsed to a single point, record it
                for(int k=0; k<r.count; ++k) final_positions.push_back(r.L);
                continue;
            }
            
            int mid = (r.L + r.R) / 2;
            if (r.count == 2) {
                int left_res = results[res_idx++];
                int right_res = results[res_idx++];
                
                if (left_res && !right_res) {
                    next_state.push_back({r.L, mid, 2});
                } else if (!left_res && right_res) {
                    next_state.push_back({mid + 1, r.R, 2});
                } else { // 1, 1 implies one in each
                    next_state.push_back({r.L, mid, 1});
                    next_state.push_back({mid + 1, r.R, 1});
                }
            } else { // count == 1
                int left_res = results[res_idx++];
                if (left_res) {
                    next_state.push_back({r.L, mid, 1});
                } else {
                    next_state.push_back({mid + 1, r.R, 1});
                }
            }
        }
        state = next_state;
        
        // Early exit if found both positions
        if (state.empty() && final_positions.size() == 2) break;
    }
    
    // Collect any remaining fully resolved ranges
    for (const auto& r : state) {
        if (r.L == r.R) {
            for(int k=0; k<r.count; ++k) final_positions.push_back(r.L);
        }
    }
    
    sort(final_positions.begin(), final_positions.end());
    // Ensure we print two positions even if logic glitch (though logic should guarantee 2)
    if (final_positions.size() < 2) final_positions.resize(2, final_positions.empty() ? 1 : final_positions[0]);
    
    cout << "! " << final_positions[0] << " " << final_positions[1] << endl;
}

// Non-adaptive strategy using random code
// Used when H is small.
// If H=1, sends R=60 queries to minimize collision probability.
// If H>1, sends R=30 queries and uses subsequent hours to resolve collisions.
void solve_non_adaptive(int R_in, int H_in) {
    int K = (H_in == 1) ? 60 : 30;
    
    mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    vector<vector<int>> queries(K);
    vector<unsigned long long> pos_sig(1001, 0);
    
    // Generate random code with p=0.3
    for (int i = 0; i < K; ++i) {
        for (int p = 1; p <= 1000; ++p) {
            if (std::uniform_real_distribution<>(0, 1)(rng) < 0.3) {
                queries[i].push_back(p);
                pos_sig[p] |= (1ULL << i);
            }
        }
    }
    
    vector<int> res = send_robots(queries);
    
    unsigned long long result_mask = 0;
    for (int i = 0; i < K; ++i) {
        if (res[i]) result_mask |= (1ULL << i);
    }
    
    vector<pair<int, int>> candidates;
    for (int i = 1; i <= 1000; ++i) {
        for (int j = i; j <= 1000; ++j) {
            if ((pos_sig[i] | pos_sig[j]) == result_mask) {
                candidates.push_back({i, j});
            }
        }
    }
    
    if (candidates.empty()) {
        cout << "! 1 2" << endl;
        return;
    }
    
    if (candidates.size() == 1) {
        cout << "! " << candidates[0].first << " " << candidates[0].second << endl;
    } else {
        // Disambiguate loop (only runs if H > 1)
        while (candidates.size() > 1) {
            int n_cands = candidates.size();
            int bits = 0;
            while((1<<bits) < n_cands) bits++;
            bits += 2; // Add margin
            
            vector<vector<int>> fix_queries;
            for (int b = 0; b < bits; ++b) {
                vector<int> q;
                for (int x = 1; x <= 1000; ++x) {
                     if (std::uniform_int_distribution<>(0, 1)(rng)) q.push_back(x);
                }
                fix_queries.push_back(q);
            }
            
            vector<int> fix_res = send_robots(fix_queries);
            if (fix_res.empty()) break; // Should not happen unless H exhausted
            
            vector<pair<int, int>> next_candidates;
            for (auto p : candidates) {
                bool ok = true;
                for (int b = 0; b < fix_queries.size(); ++b) {
                    bool has_chair = false;
                    for (int x : fix_queries[b]) {
                        if (x == p.first || x == p.second) {
                            has_chair = true;
                            break;
                        }
                    }
                    if ((has_chair ? 1 : 0) != fix_res[b]) {
                        ok = false;
                        break;
                    }
                }
                if (ok) next_candidates.push_back(p);
            }
            candidates = next_candidates;
            if (candidates.empty()) break; 
        }
        
        if (candidates.empty()) {
             cout << "! 1 2" << endl;
        } else {
             cout << "! " << candidates[0].first << " " << candidates[0].second << endl;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int R, H;
    if (cin >> R >> H) {
        // Use adaptive strategy if we have enough hours (binary search depth approx 10)
        if (H >= 12) {
            solve_adaptive(R, H);
        } else {
            solve_non_adaptive(R, H);
        }
    }
    return 0;
}