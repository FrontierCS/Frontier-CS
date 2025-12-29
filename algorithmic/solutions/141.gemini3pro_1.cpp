#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Global variables for problem constraints and state
int n, k;
int op_count = 0;
const int MAX_OPS = 100000;

// Helper to perform query
char query(int c) {
    if (op_count >= MAX_OPS) return 'Z'; // Should not happen with logic
    cout << "? " << c << endl;
    op_count++;
    char r;
    cin >> r;
    return r;
}

// Helper to perform reset
void reset() {
    if (op_count >= MAX_OPS) return;
    cout << "R" << endl;
    op_count++;
}

// Helper to print answer and exit
void answer(int d) {
    cout << "! " << d << endl;
    exit(0);
}

// Bitset for checked pairs. n <= 1024, so size ~ 10^6.
// Flattened 1D vector.
vector<bool> checked;

// Map pair (u, v) to unique index. Symmetric.
int get_idx(int u, int v) { // 1-based u, v
    if (u > v) swap(u, v);
    return (u - 1) * n + (v - 1);
}

bool is_checked(int u, int v) {
    return checked[get_idx(u, v)];
}

void set_checked(int u, int v) {
    checked[get_idx(u, v)] = true;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> k)) return 0;

    // Initialize checked matrix
    checked.resize(n * n, false);
    // Elements are "checked" against themselves (trivial)
    for (int i = 1; i <= n; ++i) set_checked(i, i);

    // Initial set of candidates
    vector<int> s(n);
    iota(s.begin(), s.end(), 1);

    mt19937 rng(1337);

    // Flag to force first pass as Identity 1..n
    bool first_pass = true;

    while (true) {
        // If remaining candidates fit in memory, one pass resolves them completely.
        if (s.size() <= (size_t)k) {
            // Safety check for ops
            if (op_count + (int)s.size() + 1 > MAX_OPS) {
                answer(s.size());
            }

            reset();
            int distinct = 0;
            // Query all elements. 
            // 'N' means not in previous (which is all previous candidates).
            // 'Y' means duplicate of a previous candidate.
            for (int x : s) {
                char r = query(x);
                if (r == 'N') distinct++;
            }
            answer(distinct);
        }

        // Check if we are done: are all pairs in s checked?
        bool all_done = true;
        // Optimization: checking all pairs is O(S^2). S <= 1024, ~10^6 ops, fast enough.
        for (size_t i = 0; i < s.size(); ++i) {
            for (size_t j = i + 1; j < s.size(); ++j) {
                if (!is_checked(s[i], s[j])) {
                    all_done = false;
                    break;
                }
            }
            if (!all_done) break;
        }

        if (all_done) {
            answer(s.size());
        }

        // Check if we have enough operations for another pass
        // Needed: 1 (reset) + s.size() (queries)
        if (op_count + (int)s.size() + 1 > MAX_OPS) {
            answer(s.size());
        }

        // Generate permutation for the pass
        vector<int> p;
        p.reserve(s.size());
        
        if (first_pass) {
            p = s;
            first_pass = false;
        } else {
            // Greedy construction of permutation to maximize new checked pairs
            vector<int> remaining = s;
            // Simulate queue content to optimize coverage
            vector<int> q_sim; 
            
            // Randomize consideration order
            shuffle(remaining.begin(), remaining.end(), rng);

            // Selection Logic
            int current_rem_size = remaining.size();
            while (current_rem_size > 0) {
                int best_idx = -1;
                int max_score = -1;
                
                // Heuristic: Check a subset of candidates to save time.
                // If k is large, greedy is slow but we need fewer passes.
                // If k is small, greedy is fast.
                // We cap the number of candidates checked per position.
                int candidates_to_check = current_rem_size;
                if (candidates_to_check > 50) candidates_to_check = 50; 
                
                for (int i = 0; i < candidates_to_check; ++i) {
                    int u = remaining[i];
                    int score = 0;
                    // Calculate how many unchecked pairs (u, v) where v in q_sim
                    for (int v : q_sim) {
                        if (!is_checked(u, v)) {
                            score++;
                        }
                    }
                    if (score > max_score) {
                        max_score = score;
                        best_idx = i;
                    }
                    // If score is max possible (equal to queue size), take it
                    if (score == (int)q_sim.size()) break;
                }
                
                // Add best to p
                int u = remaining[best_idx];
                p.push_back(u);
                
                // Update simulated queue
                q_sim.push_back(u);
                if (q_sim.size() > (size_t)k) q_sim.erase(q_sim.begin());
                
                // Remove u from remaining (swap with last active and decrease size)
                remaining[best_idx] = remaining[current_rem_size - 1];
                current_rem_size--;
            }
        }

        // Execute pass
        reset();
        vector<int> next_s;
        next_s.reserve(s.size());
        
        // Track the actual queue content during query execution
        vector<int> current_queue;
        for (int u : p) {
            char r = query(u);
            
            if (r == 'N') {
                // u is distinct from everything currently in queue.
                // Mark pairs as checked.
                for (int v : current_queue) {
                    set_checked(u, v);
                }
                next_s.push_back(u);
            }
            // If r == 'Y', u is a duplicate. We discard u.
            // We do not need to update checks for u because it's removed.
            
            // Add u to queue regardless of result (as per problem statement)
            current_queue.push_back(u);
            if (current_queue.size() > (size_t)k) {
                current_queue.erase(current_queue.begin());
            }
        }
        
        s = next_s;
    }

    return 0;
}