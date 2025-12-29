#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>

using namespace std;

// Function to perform a query
int query(int n, const vector<int>& a) {
    cout << "? " << n;
    for (int i = 0; i < n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    int B1 = 320;
    int N = 100000;
    
    // Query 1 with blocks of size B1
    vector<int> q1(N, B1);
    int l1 = query(N, q1);
    
    set<int> candidates;

    if (l1 == 0) {
        // W < B1
        // Query 2 with blocks of size 1 (all 1s) to find exact W in [1, 319]
        vector<int> q2(N, 1);
        int l2 = query(N, q2);
        for (int w = 1; w < B1; ++w) {
            // With all 1s, lines = ceil(N / w)
            // (N + w - 1) / w is integer arithmetic for ceil
            long long expected = (N + w - 1) / w;
            if (expected == l2) {
                candidates.insert(w);
            }
        }
    } else {
        // W >= B1
        // We determine possible values of Y = floor(W / B1)
        // From the lines L = ceil(N / Y)
        // We iterate possible Y values around the theoretical range
        
        int approxY = N / l1;
        vector<int> possible_Ys;
        
        // Y can be at most 100000 / B1 approx 312
        // We check a generous range around N/l1
        for (int Y = max(1, approxY - 5); Y <= approxY + 5; ++Y) {
            if (Y > 100000 / B1) continue; // Upper bound based on W constraint
            long long expected = (N + Y - 1) / Y;
            if (expected == l1) {
                possible_Ys.push_back(Y);
            }
        }
        // Also check if l1 was small, Y could be larger
        if (possible_Ys.empty()) {
             // Fallback full scan if range estimate failed (should not happen with correct math)
             for (int Y = 1; Y <= 100000 / B1; ++Y) {
                long long expected = (N + Y - 1) / Y;
                if (expected == l1) {
                    possible_Ys.push_back(Y);
                }
             }
        }
        
        // Generate candidate W values
        for (int Y : possible_Ys) {
            int base = B1 * Y;
            for (int r = 0; r < B1; ++r) {
                int w = base + r;
                if (w > 100000) break;
                candidates.insert(w);
            }
        }
        
        // Query 2 with blocks of size B2 = 321
        // This helps intersect the sets of candidates
        int B2 = 321;
        vector<int> q2(N, B2);
        int l2 = query(N, q2);
        
        set<int> final_candidates;
        for (int w : candidates) {
            // Check consistency with l2
            if (w < B2) {
                // If w < B2, words of size B2 don't fit -> l2 should be 0
                if (l2 == 0) final_candidates.insert(w);
            } else {
                // If w >= B2, words fit. Lines = ceil(N / floor(w / B2))
                if (l2 == 0) continue; // Should have been > 0
                int Z = w / B2;
                long long expected = (N + Z - 1) / Z;
                if (expected == l2) final_candidates.insert(w);
            }
        }
        candidates = final_candidates;
    }
    
    // Output result
    if (!candidates.empty()) {
        cout << "! " << *candidates.begin() << endl;
    } else {
        // Fallback, though logical flow guarantees a candidate if W in [1, 100000]
        exit(0);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}