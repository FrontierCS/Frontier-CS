#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <set>

using namespace std;

// Function to interact with the judge
int query(int x, const vector<int>& s) {
    if (s.empty()) return 0;
    cout << "? " << x << " " << s.size();
    for (int idx : s) {
        cout << " " << idx;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    int n;
    cin >> n; // Read n, but we already know n=300 from problem statement. 
    // The input format says: First line t. Then for each test case: n.
    
    // Total positions: 1 to 2n-1
    int L = 2 * n - 1;
    
    // Candidates: initially 1 to n
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // Random number generator
    mt19937 rng(1337);

    // Strategy: Eliminate "split" doubles.
    // In each round, generate a random partition (S, S_complement).
    // Unique element is never split (it is at one position p, so p is either in S or S_c).
    // Double element (u, v) is split if u in S and v in S_c (or vice versa).
    // If a candidate x is split, query results will be:
    // Query(x, S) = 1 (since at least one copy in S)
    // Query(x, S_c) = 1 (since at least one copy in S_c)
    // We discard x if (1, 1).
    // We keep x if (0, 1) or (1, 0).
    // Note: (0, 0) is impossible for valid elements.
    
    // To save queries:
    // 1. Query(x, S). If 0, then x is definitely NOT split (both copies in S_c). Keep x.
    // 2. If 1, then Query(x, S_c). If 0, x is not split (both copies in S). Keep x.
    // 3. If 1 and 1, x is split. Discard.
    
    // Since n=300, we expect ~9 rounds to reduce to 1 candidate.
    // Expected queries ~800-1000. This gives partial points but guarantees correctness.
    
    while (candidates.size() > 1) {
        // Generate random subset S of indices [1, L]
        vector<int> S;
        vector<int> S_c;
        for (int i = 1; i <= L; ++i) {
            if (rng() % 2) {
                S.push_back(i);
            } else {
                S_c.push_back(i);
            }
        }
        
        // If S or S_c is empty, regenerate (unlikely for L=599)
        if (S.empty() || S_c.empty()) continue;

        vector<int> next_candidates;
        for (int x : candidates) {
            int ans1 = query(x, S);
            if (ans1 == 0) {
                // Not in S, must be in S_c (fully). Keep.
                next_candidates.push_back(x);
            } else {
                // Could be split or fully in S. Check S_c.
                int ans2 = query(x, S_c);
                if (ans2 == 0) {
                    // Not in S_c, must be in S (fully). Keep.
                    next_candidates.push_back(x);
                } else {
                    // In S and in S_c -> Split. Discard.
                }
            }
        }
        candidates = next_candidates;
    }

    cout << "! " << candidates[0] << endl;
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