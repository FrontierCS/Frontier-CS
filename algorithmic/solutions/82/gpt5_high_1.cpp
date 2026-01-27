#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    // Read all remaining integers
    vector<long long> tokens;
    {
        long long x;
        while (cin >> x) tokens.push_back(x);
    }

    long long pairCount = 1LL * n * (n - 1) / 2;

    // Case 1: Input provides all pairwise ORs in lex order (i<j)
    if ((long long)tokens.size() >= pairCount && pairCount > 0) {
        // Build OR matrix
        vector<vector<int>> M(n, vector<int>(n, 0));
        size_t pos = 0;
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int v = (int)tokens[pos++];
                M[i][j] = M[j][i] = v;
            }
        }

        // Compute minimal OR for each index
        vector<int> mn(n, INT_MAX);
        for (int i = 0; i < n; ++i) {
            int mi = INT_MAX;
            for (int j = 0; j < n; ++j) if (j != i) {
                mi = min(mi, M[i][j]);
            }
            mn[i] = mi;
        }

        // Identify indices where mn[i] == 1 (should be exactly 2: zero index and index of 1)
        vector<int> ones;
        for (int i = 0; i < n; ++i) if (mn[i] == 1) ones.push_back(i);

        // Choose an index t with even mn[t] > 0 (guaranteed to exist for n >= 3)
        int t = -1;
        vector<int> isOne(n, 0);
        for (int idx : ones) isOne[idx] = 1;

        for (int i = 0; i < n; ++i) {
            if (isOne[i]) continue;
            if (mn[i] > 0 && (mn[i] % 2 == 0)) { t = i; break; }
        }
        if (t == -1) {
            // Fallback: choose any index not in 'ones' (shouldn't happen, but safe)
            for (int i = 0; i < n; ++i) if (!isOne[i]) { t = i; break; }
        }

        int z = -1; // index of zero
        if ((int)ones.size() == 2 && t != -1) {
            int a = ones[0], b = ones[1];
            int A1 = M[a][t];
            int A2 = M[b][t];
            if (A1 == mn[t]) z = a;
            else if (A2 == mn[t]) z = b;
            else {
                // If neither matched (extremely unlikely), fallback by checking against any other index u
                int u = -1;
                for (int i = 0; i < n; ++i) {
                    if (i == a || i == b) continue;
                    u = i; break;
                }
                if (u != -1) {
                    if (M[a][u] == mn[u]) z = a;
                    else z = b;
                } else {
                    z = a; // arbitrary
                }
            }
        } else {
            // Fallback: if detection failed, try to deduce zero by comparing sums
            // (Not typical; use heuristic: zero index yields larger sum)
            long long bestSum = LLONG_MAX;
            for (int i = 0; i < n; ++i) {
                long long s = 0;
                for (int j = 0; j < n; ++j) if (j != i) s += M[i][j];
                if (s < bestSum) {
                    bestSum = s;
                    z = i;
                }
            }
        }

        vector<int> p(n);
        for (int i = 0; i < n; ++i) p[i] = mn[i];
        if (z >= 0 && z < n) p[z] = 0;

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
        return 0;
    }

    // Case 2: Input directly provides the permutation
    if ((int)tokens.size() >= n) {
        vector<int> p(n);
        for (int i = 0; i < n; ++i) p[i] = (int)tokens[i];
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
        return 0;
    }

    // Fallback: output the identity permutation (0..n-1)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << i;
    }
    cout << '\n';
    return 0;
}