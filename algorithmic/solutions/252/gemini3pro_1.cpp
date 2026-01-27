#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Helper to make a query
// Returns true if result is 1, false otherwise
bool query(int u, int k, const vector<int>& S) {
    if (S.empty()) return false;
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); 
    return res == 1;
}

// Find the room reached after k steps from u
// Uses binary search to minimize cost
int find_dest(int u, int k, int n) {
    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        // Query if destination is in [low, mid]
        vector<int> S;
        S.reserve(mid - low + 1);
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
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (!(cin >> n)) return 0;

    // Step 1: Find v1 = f^N(1). This node is guaranteed to be on the cycle reachable from 1.
    // Finding destination uses binary search.
    int v1 = find_dest(1, n, n);

    // Step 2: Find cycle length L.
    // Iterate k from 1 to N to find first k such that f^k(v1) = v1.
    // Since v1 is on a cycle, L <= component size <= N.
    int L = -1;
    vector<int> S_v1 = {v1};
    for (int k = 1; k <= n; ++k) {
        if (query(v1, k, S_v1)) {
            L = k;
            break;
        }
    }
    if (L == -1) L = 1; // Should not happen

    // Step 3: Optimize stride s
    // We want to construct a subset T of the cycle Z such that T has spacing s.
    // Then for each node x, we check if f^{N+j}(x) in T for j = 0..s-1.
    // Cost analysis:
    // BS Cost (finding one node): depends on N.
    
    double bs_cost = 0;
    {
        int r = n;
        while(r > 1) {
            int s_sz = (r + 1) / 2;
            bs_cost += 5.0 + sqrt(s_sz) + 2.7; // log10(k) roughly 2.7 for k=N
            r = s_sz; 
        }
    }

    int best_s = 1;
    double min_total_cost = 1e18;

    for (int s = 1; s <= L; ++s) {
        int T_size = (L + s - 1) / s; // ceil(L/s)
        double construction_cost = 0;
        if (T_size > 1) {
             construction_cost = (T_size - 1) * bs_cost;
        }

        // Cost to check all N nodes
        // Each node takes at most s queries
        // Set size is T_size
        double check_cost_per_node = s * (5.0 + sqrt(T_size) + 2.7);
        double total_check_cost = n * check_cost_per_node;
        
        double total = construction_cost + total_check_cost;
        if (total < min_total_cost) {
            min_total_cost = total;
            best_s = s;
        }
    }

    // Step 4: Construct T
    // T contains points on the cycle: v1, f^s(v1), f^2s(v1), ...
    // Elements are found by stepping 'best_s' forward.
    vector<int> T;
    T.push_back(v1);
    int curr = v1;
    int steps_needed = (L + best_s - 1) / best_s;
    
    for (int i = 1; i < steps_needed; ++i) {
        int next_node = find_dest(curr, best_s, n);
        T.push_back(next_node);
        curr = next_node;
    }

    // Step 5: Determine A
    // x in A iff f^N(x) is in Z (the cycle of 1).
    // The set T covers Z with spacing best_s.
    // So f^N(x) in Z implies there exists j in [0, best_s-1] such that f^{N+j}(x) in T.
    vector<int> A;
    for (int x = 1; x <= n; ++x) {
        bool possible = false;
        for (int j = 0; j < best_s; ++j) {
            if (query(x, n + j, T)) {
                possible = true;
                break;
            }
        }
        if (possible) {
            A.push_back(x);
        }
    }

    // Output answer
    cout << "! " << A.size();
    for (int x : A) {
        cout << " " << x;
    }
    cout << endl;

    return 0;
}