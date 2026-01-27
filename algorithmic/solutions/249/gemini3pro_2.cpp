/**
 * Problem: X-OR
 * Time limit: 1 second
 * Memory limit: 256 MB
 * 
 * Strategy:
 * We need to find the index of 0 in the hidden permutation using bitwise OR queries.
 * Once 0 is found at index z, any other element p[i] can be found by querying ? z i,
 * since 0 | x = x.
 * 
 * To find 0 efficiently (within ~N queries):
 * We maintain a set of candidate indices. Initially, all indices [1, N].
 * In each step, we pick a random 'pivot' from the candidates.
 * We query the OR sum of this pivot with every other candidate.
 * Let the pivot be P.
 * If P corresponds to 0, then query(P, x) = p[x]. The minimum result will correspond to the smallest elements in the set.
 * If P corresponds to some value V != 0, then query(P, x) = V | p[x] >= V. The minimum result will be exactly V (if there is any x such that p[x] is a submask of V, including 0).
 * 
 * In both cases, the index of 0 (if present in the "others" set) will result in the minimal value in the queries.
 * If P was 0, we identify candidates with small values.
 * If P != 0, we identify candidates that are submasks of P.
 * 
 * We restrict the candidate set to those that produced the minimum query result, plus the pivot itself (since the pivot could be 0).
 * The size of the candidate set decreases rapidly (roughly by factor of 1.5 bits or more effectively).
 * 
 * When the set size is reduced to 2, we have candidates {u, v}. One is 0.
 * To distinguish, we pick a random w and compare query(u, w) vs query(v, w).
 * If u is 0, query(u, w) = p[w]. query(v, w) = p[v] | p[w].
 * Since a | b >= b, query(v, w) >= query(u, w).
 * If strict inequality holds, u is 0.
 * If equality holds (p[v] is a submask of p[w]), we try another random w.
 * 
 * Total queries: ~N for the first pass, then rapidly decreasing sums (N/20, etc.), plus recovery N. Total approx 2N.
 * Constraints: N=2048, Queries=4300. 2*2048 = 4096 < 4300.
 */

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Function to interact with the judge
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Initialize random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Initial candidates are all indices 1 to n
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // Filter candidates until we have at most 2 left
    while (candidates.size() > 2) {
        // Pick a random pivot from the current candidates
        uniform_int_distribution<int> dist(0, candidates.size() - 1);
        int pivot_idx = dist(rng);
        int pivot = candidates[pivot_idx];

        vector<int> others;
        others.reserve(candidates.size() - 1);
        for (int x : candidates) {
            if (x != pivot) others.push_back(x);
        }

        // We should always have candidates to compare since size > 2
        int min_val = -1;
        vector<int> subset;

        // Query pivot against all other candidates
        for (int x : others) {
            int val = query(pivot, x);
            if (min_val == -1 || val < min_val) {
                min_val = val;
                subset.clear();
                subset.push_back(x);
            } else if (val == min_val) {
                subset.push_back(x);
            }
        }

        // The pivot itself is always kept as a potential candidate for 0
        subset.push_back(pivot);
        candidates = subset;
    }

    int zero_idx = -1;
    if (candidates.size() == 2) {
        int u = candidates[0];
        int v = candidates[1];
        
        // We have two candidates, one is 0. 
        // We query against a random third index w to determine which one.
        while (true) {
            int w = (rng() % n) + 1;
            while (w == u || w == v) {
                w = (rng() % n) + 1;
            }
            
            int val_u = query(u, w);
            int val_v = query(v, w);
            
            if (val_u < val_v) {
                zero_idx = u;
                break;
            } else if (val_v < val_u) {
                zero_idx = v;
                break;
            }
            // If values are equal, retry with a different w.
        }
    } else {
        // Fallback, though with N >= 3 loop should end with size 2.
        zero_idx = candidates[0];
    }

    // Now recover the array using zero_idx
    vector<int> p(n + 1);
    p[zero_idx] = 0;
    
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        p[i] = query(zero_idx, i);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}