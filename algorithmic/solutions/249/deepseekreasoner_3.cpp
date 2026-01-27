/**
 * Solution for problem: X-OR
 * Strategy:
 * 1. The goal is to find the index of 0. Once 0 is found at index z, we can find all p[i] by asking "? i z" 
 *    which returns p[i] | 0 = p[i].
 * 2. To find 0 efficiently within ~4300 queries for N=2048:
 *    a. Filtering using a randomized pivot: Pick a random index P. Query "? i P" for all i.
 *       The results will be (p[i] | p[P]). The minimum value among all results (and p[P] itself) will be p[P].
 *       Any index j such that (p[j] | p[P]) == p[P] implies p[j] is a submask of p[P].
 *       Index of 0 is always a submask of any p[P].
 *       This reduces the candidate set for 0 from N to the number of submasks of p[P].
 *    b. To ensure the candidate set becomes small (expected ~50), we must avoid picking P such that p[P] has 
 *       many submasks (i.e., high Hamming weight like 111...1). We use a heuristic: sample a few random queries 
 *       with P. If the results lack diversity (meaning P masks many bits), we discard P and try another.
 *    c. After filtering, we have a small set of candidates containing 0. We use pairwise elimination with a 
 *       random external pivot R. Comparing "? a R" and "? b R" allows us to eliminate the non-zero candidate.
 * 3. Total queries roughly N + small_overhead + N, which fits in 2N + 200 approx.
 */

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <map>
#include <set>

using namespace std;

int n;
map<pair<int, int>, int> cache_query;

// Function to perform query with memoization
int ask(int i, int j) {
    if (i > j) swap(i, j);
    if (cache_query.count({i, j})) return cache_query[{i, j}];
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Exit immediately on invalid query/limit exceeded
    return cache_query[{i, j}] = res;
}

int main() {
    // Fast IO not strictly needed for interactive but good habit
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Use high-resolution clock for random seed
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Initially all indices are candidates
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    bool scanner_done = false;
    int try_count = 0;
    
    // Phase 1: Filter candidates
    // We try to find a pivot that effectively reduces the search space
    while (!scanner_done && candidates.size() > 1) {
        // If candidates are already few, no need to filter
        if (candidates.size() <= 2) break; 

        uniform_int_distribution<int> dist(0, candidates.size() - 1);
        int p_idx = dist(rng);
        int p = candidates[p_idx];

        // Check heuristic quality of p to avoid "heavy" masks (e.g. 2047) if N is large
        if (candidates.size() > 60) {
            set<int> outcomes;
            int samples = 12;
            int diverse_threshold = 4; // Expect at least 4 distinct values for a "good" mask
            
            for (int k = 0; k < samples; ++k) {
                // Pick random other index from full range to test p
                int other = (rng() % n) + 1;
                while(other == p) other = (rng() % n) + 1;
                outcomes.insert(ask(p, other));
            }
            
            // If outcomes are too uniform, p likely has many bits set (masking the other operand)
            if ((int)outcomes.size() < diverse_threshold) {
                try_count++;
                if (try_count < 10) {
                    continue; // Try finding a better pivot
                }
            }
        }
        
        // Pivot accepted, perform full scan
        int pivot = p;
        int min_val = -1;
        vector<pair<int, int>> results;
        results.reserve(candidates.size());

        for (int c : candidates) {
            if (c == pivot) continue;
            int val = ask(pivot, c);
            if (min_val == -1 || val < min_val) {
                min_val = val;
            }
            results.push_back({c, val});
        }

        // Keep only candidates that resulted in the minimum value (submasks)
        vector<int> next_candidates;
        next_candidates.push_back(pivot); 
        for (auto& pair : results) {
            if (pair.second == min_val) {
                next_candidates.push_back(pair.first);
            }
        }
        candidates = next_candidates;
        scanner_done = true; 
    }

    // Phase 2: Pairwise elimination on remaining candidates
    shuffle(candidates.begin(), candidates.end(), rng);

    while (candidates.size() > 1) {
        int a = candidates.back();
        candidates.pop_back();
        int b = candidates.back();
        candidates.pop_back();

        // Find a differentiator r
        while (true) {
            int r = (rng() % n) + 1;
            if (r == a || r == b) continue;
            
            int va = ask(a, r);
            int vb = ask(b, r);
            
            if (va < vb) {
                // b cannot be 0 because (b|r) > (a|r) >= r = (0|r)
                // so a is strictly better candidate for 0
                candidates.push_back(a);
                break;
            } else if (vb < va) {
                candidates.push_back(b);
                break;
            }
            // If equal, try another r
        }
    }

    int zero_idx = candidates[0];
    
    // Phase 3: Restore the array
    vector<int> p(n + 1);
    p[zero_idx] = 0;
    
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        // p[i] | 0 = p[i]
        p[i] = ask(i, zero_idx);
    }

    // Output answer
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}