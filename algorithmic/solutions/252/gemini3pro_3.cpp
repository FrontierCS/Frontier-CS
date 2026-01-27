#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>
#include <random>

using namespace std;

// Helper to calculate cost
double estimate_cost(int u, int k, int S_size) {
    return 5.0 + sqrt(S_size) + log10(k);
}

// Perform a query
int query(int u, int k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Error
    return res;
}

// Find a_u (f(u)) using binary search
int find_next(int u, int n) {
    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> S;
        for (int i = low; i <= mid; ++i) S.push_back(i);
        if (query(u, 1, S)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

// Find f^k(u) using binary search (generic target finding)
int find_target(int u, int k, int n) {
    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> S;
        for (int i = low; i <= mid; ++i) S.push_back(i);
        if (query(u, k, S)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

int main() {
    int n;
    if (!(cin >> n)) return 0;

    // Parameters
    int SMALL_CYCLE_LIMIT = 40;
    
    // Step 1: Find a reference node on the cycle of component 1.
    // u=1, k=n ensures we land on the cycle.
    int v_ref = find_target(1, n, n);

    // Step 2: Determine if L1 (cycle length of component 1) is small.
    int L1 = -1;
    // Check periodicity up to limit
    for (int k = 1; k <= SMALL_CYCLE_LIMIT; ++k) {
        if (query(v_ref, k, {v_ref})) {
            L1 = k;
            break;
        }
    }

    set<int> A;
    
    if (L1 != -1) {
        // Case: Small Cycle
        // Find all nodes in C1
        vector<int> C1;
        C1.push_back(v_ref);
        int curr = v_ref;
        for (int i = 1; i < L1; ++i) {
            int next = find_next(curr, n);
            C1.push_back(next);
            curr = next;
        }
        
        // Check all nodes against C1
        for (int u = 1; u <= n; ++u) {
            if (query(u, n, C1)) {
                A.insert(u);
            }
        }
    } else {
        // Case: Large Cycle
        // We assume C1 is large. We try to find all other small components.
        // Heuristic: Sample nodes, find their targets.
        // If target has small period, find its cycle and add to C_others.
        // If target has no small period, assume it belongs to C1.
        
        set<int> C_others;
        vector<int> samples;
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 1);
        
        // Use a deterministic seed for reproducibility if needed, but random is fine
        mt19937 rng(1337);
        shuffle(perm.begin(), perm.end(), rng);
        
        int sample_count = min(n, 60); // Budget limited
        for (int i = 0; i < sample_count; ++i) {
            samples.push_back(perm[i]);
        }

        // Add 1 to samples just in case
        samples.push_back(1);

        set<int> processed_targets;
        
        for (int u : samples) {
            // Optimization: check if u already reaches known C_others
            vector<int> C_others_vec(C_others.begin(), C_others.end());
            if (!C_others_vec.empty()) {
                if (query(u, n, C_others_vec)) continue; // u is in non-A
            }
            
            // Find target
            int t = find_target(u, n, n);
            if (processed_targets.count(t)) continue;
            processed_targets.insert(t);
            
            // Check if t is in C_others
            if (C_others.count(t)) continue;
            
            // Check if t has small period (limit slightly larger to be safe)
            // L1 > 40, so if period <= 50, it is NOT C1.
            bool small_period = false;
            // A single check at k=60 (LCM of many small numbers? No, just a bound)
            // Actually check `? t k t` for a few k or just verify if it's C1.
            // If it is C1, it won't return to t quickly (since L1 > 40).
            // Check for k=1..40? Expensive.
            // Check `? t 60 {t}`?
            // If L1 > 40, f^60(t) likely != t unless L1 divides 60.
            // Better: just check period up to 40.
            int cycle_len = -1;
            for (int k = 1; k <= 40; ++k) {
                if (query(t, k, {t})) {
                    cycle_len = k;
                    break;
                }
            }
            
            if (cycle_len != -1) {
                // Found a small cycle, must be C_others
                vector<int> cycle_nodes;
                cycle_nodes.push_back(t);
                int curr = t;
                for (int i = 1; i < cycle_len; ++i) {
                    int next = find_next(curr, n);
                    cycle_nodes.push_back(next);
                    curr = next;
                }
                for(int node : cycle_nodes) C_others.insert(node);
            }
            // else assume C1
        }
        
        // Final classification
        vector<int> C_others_vec(C_others.begin(), C_others.end());
        for (int u = 1; u <= n; ++u) {
            if (C_others_vec.empty()) {
                A.insert(u);
            } else {
                if (!query(u, n, C_others_vec)) {
                    A.insert(u);
                }
            }
        }
    }

    cout << "! " << A.size();
    for (int x : A) cout << " " << x;
    cout << endl;

    return 0;
}