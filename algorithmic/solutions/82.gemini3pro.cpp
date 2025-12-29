#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Helper to perform query according to protocol
// Returns the bitwise OR of p[i] and p[j]
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Error or limit exceeded
    return res;
}

int main() {
    // Optimize I/O operations (flushing is still done via endl)
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Initial candidates: all indices 1 to n
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // Random number generator seeded with time
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Phase 1: Filter candidates for the value 0
    // We use a tournament strategy. In each round, we pair up candidates and keep
    // those that produce smaller OR values. Since 0 | x = x (which is statistically smaller
    // than random a | b), 0 will likely survive in the pool of "small result" pairs.
    // We stop when candidates are few enough (<= 12) to verify rigorously.
    while (candidates.size() > 12) {
        shuffle(candidates.begin(), candidates.end(), rng);
        
        vector<int> next_candidates;
        vector<pair<int, pair<int, int>>> results;
        
        int sz = candidates.size();
        // Pair up candidates
        for (int i = 0; i + 1 < sz; i += 2) {
            int u = candidates[i];
            int v = candidates[i+1];
            int res = query(u, v);
            results.push_back({res, {u, v}});
        }
        
        // Handle odd one out: simply advance to next round to avoid unfair elimination
        if (sz % 2 == 1) {
            next_candidates.push_back(candidates.back());
        }
        
        // Sort pairs by result value (ascending)
        sort(results.begin(), results.end());
        
        // Keep candidates from the pairs with smallest results.
        // Keeping bottom 40% reduces the set size by factor ~0.4 per round for queries.
        // This geometric reduction ensures we stay well within query limits.
        int pairs_cnt = results.size();
        int keep = max(1, (int)(pairs_cnt * 0.40)); 
        
        for (int i = 0; i < keep; ++i) {
            next_candidates.push_back(results[i].second.first);
            next_candidates.push_back(results[i].second.second);
        }
        
        candidates = next_candidates;
    }

    // Phase 2: Verification
    // Identify 0 among the few survivors by checking against random probes.
    // The candidate that produces the smallest sum of ORs against random indices is 0.
    int best_cand = -1;
    long long min_score = -1;
    
    // 18 probes give high confidence with low query cost
    int probes_count = 18; 
    
    for (int cand : candidates) {
        long long current_score = 0;
        for (int k = 0; k < probes_count; ++k) {
            int other;
            // Pick a random other index
            do {
                other = (rng() % n) + 1;
            } while (other == cand);
            
            current_score += query(cand, other);
        }
        
        if (best_cand == -1 || current_score < min_score) {
            min_score = current_score;
            best_cand = cand;
        }
    }

    // Phase 3: Recover permutation
    // We assume p[best_cand] is 0. Thus p[i] = p[best_cand] | p[i] = query(best_cand, i).
    int zero_idx = best_cand;
    vector<int> p(n + 1);
    p[zero_idx] = 0;
    
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        p[i] = query(zero_idx, i);
    }

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}