#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <queue>
#include <set>

using namespace std;

// Structure to represent a search task
// We are looking for 'k' candidates in the range [l, r].
// 'off' is the number of candidates strictly to the left of 'l' (i.e., in range [0, l-1]).
struct Task {
    int l, r, k, off;
};

// Global cache to avoid re-querying (though logic minimizes this)
// For n=200000, map might be slow, but query count is low.
// Given strict time limit, direct query is safer, we handle duplicates via logic.
int ask(int i, int &a0, int &a1) {
    cout << "? " << i << endl;
    cin >> a0 >> a1;
    return a0 + a1;
}

void finish(int i) {
    cout << "! " << i << endl;
    exit(0);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Phase 1: Establish M
    // M is the count of "better" boxes relative to the "worst" (most common) prize type.
    // We sample a few random boxes. The maximum sum S = a0 + a1 corresponds to the worst prize found.
    // With high probability, this will be the true worst prize type (type v).
    
    int M = -1;
    int best_p = -1;
    int best_a0 = -1, best_a1 = -1;

    // Try random pivots.
    int num_initial = 25;
    if (n < num_initial) num_initial = n;
    
    set<int> checked_indices;
    
    for(int k=0; k<num_initial; ++k) {
        int p;
        if (n <= num_initial) {
            p = k;
        } else {
            p = uniform_int_distribution<int>(0, n-1)(rng);
            // Simple retry to avoid duplicates
            while(checked_indices.count(p)) {
                p = uniform_int_distribution<int>(0, n-1)(rng);
            }
        }
        checked_indices.insert(p);

        int a0, a1;
        int s = ask(p, a0, a1);
        if (s == 0) finish(p); // Found diamond by luck
        
        if (s > M) {
            M = s;
            best_p = p;
            best_a0 = a0;
            best_a1 = a1;
        }
    }

    queue<Task> q;
    // Initial split using the best pivot found
    // best_p serves as a splitter for the range [0, n-1]
    if (best_p > 0) q.push({0, best_p - 1, best_a0, 0});
    if (best_p < n - 1) q.push({best_p + 1, n - 1, best_a1, best_a0});

    while (!q.empty()) {
        Task t = q.front();
        q.pop();

        if (t.k <= 0) continue;
        if (t.l > t.r) continue;

        // Try to split interval [t.l, t.r]
        // We need a pivot with sum == M (a "standard" box).
        // If we hit a box with sum < M, it's a candidate (not standard), so we can't use it to split the counts accurately.
        // We retry with a new random pivot in that case.
        
        int p = (t.l + t.r) / 2;
        bool first_try = true;
        
        int attempts = 0;
        const int MAX_ATTEMPTS = 50; 

        while (attempts < MAX_ATTEMPTS) {
            if (!first_try) {
                p = uniform_int_distribution<int>(t.l, t.r)(rng);
            }
            
            // Avoid re-querying if we happen to pick same random
            if (checked_indices.count(p)) {
                // If we already checked this index, we know its properties?
                // We didn't store them. For simplicity, just pick another or query again.
                // Since N is large, collision is rare. If range is small, we might collide.
                // If range is small, we might just query everything.
                if (t.r - t.l < 5) {
                    // Just proceed, query cost is low
                } else {
                     if (!first_try) { // Don't skip first try (middle) unless checked
                         continue; 
                     }
                }
            }
            checked_indices.insert(p);
            
            first_try = false;
            attempts++;

            int a0, a1;
            int s = ask(p, a0, a1);

            if (s == 0) finish(p);

            if (s > M) {
                // Found a pivot worse than our current M.
                // This implies M was not the maximum (we started with a 'better' box as reference).
                // We update M and restart the search globally with this new pivot as the root splitter.
                M = s;
                
                // Clear the current queue
                queue<Task> empty;
                swap(q, empty);
                
                // Push tasks based on this new global splitter
                if (p > 0) q.push({0, p - 1, a0, 0});
                if (p < n - 1) q.push({p + 1, n - 1, a1, a0});
                
                break; // Break inner loop, process next task from new queue
            }

            if (s == M) {
                // Good splitter found.
                // a0 is the total count of candidates in [0, p-1].
                // t.off is the count of candidates in [0, t.l-1].
                // So candidates in [t.l, p-1] is a0 - t.off.
                int left_k = a0 - t.off;
                
                // Remaining candidates are on the right
                int right_k = t.k - left_k; 
                
                // Offset for the right range [p+1, t.r] is candidates in [0, p].
                // Since p is type v (not candidate), count is same as [0, p-1], which is a0.
                
                if (p > t.l) q.push({t.l, p - 1, left_k, t.off});
                if (p < t.r) q.push({p + 1, t.r, right_k, a0});
                break;
            }

            if (s < M) {
                // We hit a candidate box!
                // Since s != 0, it's not the diamond.
                // This box 'p' is one of the 'k' candidates we are looking for.
                // We cannot use it to split the range efficiently because 'a0' counts a SUBSET of candidates (those better than p).
                // We simply ignore p and try to find a standard box to split the remaining space.
                // If the range is a single element, we are done with this branch.
                if (t.l == t.r) {
                    break;
                }
                // Continue loop to pick another pivot
            }
        }
    }
    
    // Should generally be unreachable as we exit on finding diamond.
    // Output any index if not found (though guaranteed to find).
    cout << "! 0" << endl;
    return 0;
}