#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>

using namespace std;

// Global N
int N;

// Function to perform a query
// Returns 1 if after k steps from u, we are in S.
// Returns 0 otherwise.
int query(int u, int k, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Function to find the exact node reached from u after k steps.
// Uses binary search on bits (9 queries since N <= 500).
int find_val(int u, int k) {
    int val = 0;
    // Determine each bit
    for (int b = 0; b < 9; ++b) {
        vector<int> S;
        for (int x = 1; x <= N; ++x) {
            if ((x >> b) & 1) {
                S.push_back(x);
            }
        }
        if (S.empty()) continue;
        // If all numbers 1..N have this bit 0, then val bit is 0.
        // If all have 1, then val bit is 1. (Though N <= 500 covers bits well).
        
        int res = query(u, k, S);
        if (res) {
            val |= (1 << b);
        }
    }
    return val;
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    // Step 1: Find z = f^N(1). This node is on the cycle of component 1.
    int z = find_val(1, N);

    // Step 2: Find the length L of the cycle.
    // We check k = 1, 2, ...
    int L = -1;
    for (int k = 1; k <= N; ++k) {
        int res = query(z, k, {z});
        if (res == 1) {
            L = k;
            break;
        }
    }
    
    // Step 3: Determine optimal spacing s and strategy
    // Cost model:
    // Prep cost (finding points on cycle): (L/s) * 207
    // Check cost (querying all N): N * s * (5 + sqrt(L/s) + 2.7)
    
    double best_cost = 1e18;
    int best_s = 1;
    
    for (int s = 1; s <= L; ++s) {
        double m = ceil((double)L / s); // number of points in sparse set
        double prep = m * 207.0; // approx cost to find one point is 207
        // Actually we only find m-1 points because z is known.
        if (m > 0) prep = (m - 1) * 207.0;
        
        double q_cost = 5.0 + sqrt(m) + log10(N + s); // approx log(k)
        double check = N * s * q_cost;
        
        double total = prep + check;
        if (total < best_cost) {
            best_cost = total;
            best_s = s;
        }
    }
    
    int s = best_s;
    
    // Step 4: Construct the sparse set S
    // S contains z, f^s(z), f^2s(z), ...
    vector<int> S_sparse;
    S_sparse.push_back(z);
    
    int curr = z;
    // We need to cover the cycle of length L with steps of size s.
    // We already have z (index 0). We need indices s, 2s, ... until we wrap or cover L.
    // Number of additional steps needed is ceil(L/s) - 1.
    int steps_needed = (L + s - 1) / s - 1;
    
    for (int i = 0; i < steps_needed; ++i) {
        curr = find_val(curr, s);
        S_sparse.push_back(curr);
    }
    
    // Step 5: Identify members of A
    vector<int> A;
    for (int u = 1; u <= N; ++u) {
        bool found = false;
        // Check offsets 0 to s-1
        for (int j = 0; j < s; ++j) {
            // Check if f^{N+j}(u) is in S_sparse
            int res = query(u, N + j, S_sparse);
            if (res == 1) {
                A.push_back(u);
                found = true;
                break;
            }
        }
    }
    
    // Output answer
    sort(A.begin(), A.end());
    cout << "! " << A.size();
    for (int x : A) {
        cout << " " << x;
    }
    cout << endl;

    return 0;
}