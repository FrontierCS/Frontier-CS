#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>

using namespace std;

// Global variables for problem data
int N;
vector<int> S;
int M;
vector<pair<int, int>> jerry_moves;
vector<pair<int, int>> my_moves;

// Structures for the solver
vector<int> bad_indices;
vector<int> pos_in_bad; // -1 if not in bad_indices, else index in bad_indices
vector<vector<int>> swap_times; // swap_times[i] contains list of round indices where i is swapped
vector<int> next_swap_idx; // points to the next relevant entry in swap_times[i]

void add_bad(int idx) {
    if (pos_in_bad[idx] != -1) return;
    pos_in_bad[idx] = bad_indices.size();
    bad_indices.push_back(idx);
}

void remove_bad(int idx) {
    if (pos_in_bad[idx] == -1) return;
    int pos = pos_in_bad[idx];
    int last_idx = bad_indices.back();
    
    if (pos != (int)bad_indices.size() - 1) {
        bad_indices[pos] = last_idx;
        pos_in_bad[last_idx] = pos;
    }
    bad_indices.pop_back();
    pos_in_bad[idx] = -1;
}

void update_status(int idx) {
    if (S[idx] != idx) {
        add_bad(idx);
    } else {
        remove_bad(idx);
    }
}

void perform_swap(int u, int v) {
    swap(S[u], S[v]);
    update_status(u);
    update_status(v);
}

int get_stability(int idx, int current_round) {
    if (next_swap_idx[idx] >= (int)swap_times[idx].size()) {
        return 2000000; // Infinity effectively (larger than M)
    }
    return swap_times[idx][next_swap_idx[idx]] - current_round;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    S.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> S[i];
    }

    cin >> M;
    jerry_moves.resize(M);
    swap_times.resize(N);
    for (int i = 0; i < M; ++i) {
        cin >> jerry_moves[i].first >> jerry_moves[i].second;
        swap_times[jerry_moves[i].first].push_back(i);
        swap_times[jerry_moves[i].second].push_back(i);
    }
    
    // Initialize solver state
    pos_in_bad.assign(N, -1);
    next_swap_idx.assign(N, 0);
    
    for (int i = 0; i < N; ++i) {
        update_status(i);
    }

    if (bad_indices.empty()) {
        cout << "0\n0" << endl;
        return 0;
    }

    long long total_dist = 0;
    int current_round = 0;
    
    // Random generator for sampling
    mt19937 rng(1337);

    // Main loop
    while (current_round < M) {
        // 1. Jerry's move
        int jx = jerry_moves[current_round].first;
        int jy = jerry_moves[current_round].second;
        
        // Update swap pointers to indicate these indices have been swapped at this round
        next_swap_idx[jx]++;
        next_swap_idx[jy]++;
        
        perform_swap(jx, jy);

        // Check if sorted
        if (bad_indices.empty()) {
            // Must complete the round with a move. Dummy move.
            my_moves.push_back({0, 0});
            current_round++;
            break;
        }

        // 2. My move
        // Strategy: Sample candidates from bad_indices
        
        int best_u = -1;
        int best_v = -1;
        long long best_score = -4e18; // Negative infinity

        int sample_count = 100; // Sample size
        
        int bsize = bad_indices.size();
        for (int k = 0; k < sample_count; ++k) {
            int idx_in_bad;
            // Use random sampling to find good candidates
            idx_in_bad = rng() % bsize;
            
            int u = bad_indices[idx_in_bad];
            int val = S[u];
            int v = val; // Target index for element at u
            
            // Candidate swap: (u, v)
            // This puts value 'val' at index 'v'.
            
            // Check for 2-cycle: if the element at target v wants to go to u
            bool is_2_cycle = (S[v] == u);
            
            // Stability: Time until Jerry moves the fixed position again
            int stab_v = get_stability(v, current_round);
            int stab_u = 0;
            if (is_2_cycle) {
                stab_u = get_stability(u, current_round);
            }
            
            long long dist = abs(u - v);
            
            // Heuristic Score Calculation
            long long score = 0;
            if (is_2_cycle) {
                // Large bonus for fixing 2 elements at once
                score += 1000000000000000LL; 
                score += (long long)stab_v * 1000000;
                score += (long long)stab_u * 1000000;
            } else {
                // Bonus for stability of the one fixed element
                score += (long long)stab_v * 1000000;
            }
            
            score -= dist; // Penalize distance
            
            if (score > best_score) {
                best_score = score;
                best_u = u;
                best_v = v;
            }
        }
        
        // Fallback if no candidate found (should be rare with non-empty bad_indices)
        if (best_u == -1) {
            best_u = bad_indices[0];
            best_v = S[best_u];
        }

        my_moves.push_back({best_u, best_v});
        total_dist += abs(best_u - best_v);
        perform_swap(best_u, best_v);
        
        current_round++;
        
        if (bad_indices.empty()) {
            break;
        }
    }

    cout << current_round << "\n";
    for (const auto& p : my_moves) {
        cout << p.first << " " << p.second << "\n";
    }
    
    long long V = (long long)current_round * total_dist;
    cout << V << "\n";

    return 0;
}