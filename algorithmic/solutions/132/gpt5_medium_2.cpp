#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int q = 7;       // field size
    const int k = 4;       // polynomial degree < 4
    const int t = 7;       // number of evaluation points (0..6), t > 2*(k-1) = 6
    const int m = t * q;   // total number of tests = 49
    const int N = 1000;    // number of positions
    
    // Precompute tests: each row r corresponds to (j in [0..6], s in [0..6]) with r = j*q + s
    vector<vector<int>> tests(m);
    // Also precompute mask per position for decoding
    vector<uint64_t> posMask(N, 0);

    for (int idx = 0; idx < N; ++idx) {
        // Map index to polynomial coefficients (a0 + a1*x + a2*x^2 + a3*x^3) over GF(7)
        int x = idx;
        int a0 = x % q; x /= q;
        int a1 = x % q; x /= q;
        int a2 = x % q; x /= q;
        int a3 = x % q;

        for (int j = 0; j < t; ++j) {
            int x1 = j % q;
            int x2 = (x1 * x1) % q;
            int x3 = (x2 * x1) % q;
            int val = (a0 + a1 * x1 + a2 * x2 + a3 * x3) % q;
            if (val < 0) val += q;
            int r = j * q + val;
            tests[r].push_back(idx + 1); // positions are 1-based
            posMask[idx] |= (1ULL << r);
        }
    }

    // Send all queries
    int robots_sent = 0;
    for (int r = 0; r < m; ++r) {
        cout << "? " << tests[r].size();
        for (int p : tests[r]) cout << " " << p;
        cout << "\n";
        cout.flush();
        robots_sent++;
    }
    
    // Get answers
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    // Build answer mask
    uint64_t ymask = 0;
    for (int i = 0; i < min(L, m); ++i) {
        if (ans[i]) ymask |= (1ULL << i);
    }

    // Decode using disjunctness: select columns whose support is subset of observed positives
    vector<int> candidates;
    for (int i = 0; i < N; ++i) {
        if ((posMask[i] & (~ymask)) == 0ULL) {
            candidates.push_back(i + 1);
        }
    }

    int a = 1, b = 1;
    if (candidates.size() >= 2) {
        a = candidates[0];
        b = candidates[1];
    } else if (candidates.size() == 1) {
        a = b = candidates[0];
    } else {
        // Fallback (should not happen with correct disjunct matrix)
        a = 1; b = 1;
    }

    cout << "! " << a << " " << b << "\n";
    cout.flush();

    return 0;
}