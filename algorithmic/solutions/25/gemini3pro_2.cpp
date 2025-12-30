#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <string>

using namespace std;

// Global random engine
mt19937 rng(1337);

int query(int n, const vector<int>& s) {
    if (s.empty()) return 0;
    string q(n, '0');
    for (int x : s) {
        q[x] = '1'; // 0-indexed in logic, but problem uses 1-based? No, input string length n.
                    // Problem description: "s_i is 1 if node i \in S".
                    // Input format: "? s". Vertices usually 1..N or 0..N-1.
                    // Example shows indices 1,2,3,4. String length 4.
                    // s[0] corresponds to vertex 1.
    }
    // Indices in s are 0-based (0 to n-1).
    // String s_0 s_1 ... s_{n-1}.
    // s_i corresponds to vertex i+1.
    cout << "? " << q << endl;
    int ans;
    cin >> ans;
    return ans;
}

// Check cuts recursively
// Returns true if connected (no 0-cut found), false if disconnected (0-cut found)
bool check(int n, vector<int>& subset, const vector<int>& outside_initial) {
    if (subset.empty()) return true;

    // Check cut (subset, V \ subset)
    // V \ subset is implicit. We query "subset" (or complement).
    // query(S) returns neighbors of S in V \ S.
    // If query(S) == 0, then S is isolated from V \ S.
    // Since we assume 0 is in V \ S (passed implicitly or handled at top), if result is 0, disconnected.
    
    // We need to query V \ subset.
    // Construct V \ subset
    vector<int> complement;
    vector<bool> in_subset(n, false);
    for (int x : subset) in_subset[x] = true;
    for (int i = 0; i < n; ++i) {
        if (!in_subset[i]) complement.push_back(i);
    }
    
    // If complement is empty (subset = V), query is 0, but valid.
    // But we only call this for proper subsets of U = V \ {root}.
    // So complement contains at least root.
    
    if (complement.empty()) {
        // Should not happen with current logic
        return true; 
    }
    
    int q = query(n, complement);
    if (q == 0) return false;

    if (subset.size() == 1) return true;

    // Split
    int mid = subset.size() / 2;
    vector<int> L(subset.begin(), subset.begin() + mid);
    vector<int> R(subset.begin() + mid, subset.end());

    if (!check(n, L, outside_initial)) return false;
    if (!check(n, R, outside_initial)) return false;

    return true;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }

    // Try multiple random shuffles
    // We have 3500 queries. One pass takes approx 2*N queries.
    // For N=200, 400 queries. 8 passes.
    int max_passes = 8;
    if (n > 100) max_passes = 5; 
    
    for (int iter = 0; iter < max_passes; ++iter) {
        vector<int> p(n);
        iota(p.begin(), p.end(), 0);
        shuffle(p.begin(), p.end(), rng);

        // Root is p[0]
        // Check root isolation first
        int q = query(n, {p[0]});
        if (q == 0) {
            cout << "! 0" << endl;
            return;
        }

        // Check recursive cuts on p[1...n-1]
        vector<int> u(p.begin() + 1, p.end());
        if (!check(n, u, {p[0]})) {
            cout << "! 0" << endl;
            return;
        }
    }

    cout << "! 1" << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}