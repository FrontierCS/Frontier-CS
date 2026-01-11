#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        long long m;
        cin >> n >> m;
        vector<vector<int>> G(n + 1, vector<int>(n + 1));
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                cin >> G[i][j];
            }
        }

        // Collect known values f(l,1) and f(l,2) without queries
        vector<int> vals;
        long long maxPossibleVals = 120LL * n + m + 2LL * n;
        vals.reserve((size_t)maxPossibleVals);

        vector<int> row1_pref_max(n + 1, 0);
        for (int j = 1; j <= n; ++j) {
            row1_pref_max[j] = max(row1_pref_max[j - 1], G[1][j]);
        }

        // f(l,1) and f(l,2)
        if (n >= 2) {
            for (int l = 1; l <= n; ++l) {
                // T = 1
                int f1 = row1_pref_max[l];
                vals.push_back(f1);

                // T = 2
                int f2;
                if (l == 1) f2 = G[2][1];
                else f2 = max(G[2][1], row1_pref_max[l - 1]);
                vals.push_back(f2);
            }
        } else {
            // n == 1 is not allowed by constraints (n >= 2)
        }

        long long queryBudget = 120LL * n + m;
        long long queriesUsed = 0;

        int totalPerLengthFull = max(0, 2 * n - 3); // number of T (3..2n-1)
        int K_full = 0;
        if (totalPerLengthFull > 0) {
            long long canFull = queryBudget / totalPerLengthFull;
            if (canFull > n) canFull = n;
            K_full = (int)canFull;
        }

        // Fully query first K_full lengths for T = 3..2n-1
        for (int l = 1; l <= K_full; ++l) {
            for (int Tt = 3; Tt <= 2 * n - 1; ++Tt) {
                if (queriesUsed >= queryBudget) break;
                cout << "? " << l << ' ' << Tt << endl;
                cout.flush();
                int x;
                if (!(cin >> x)) return 0;
                vals.push_back(x);
                ++queriesUsed;
            }
            if (queriesUsed >= queryBudget) break;
        }

        long long R = queryBudget - queriesUsed;

        // Use remaining queries to sample a few T for remaining lengths
        for (int l = K_full + 1; l <= n && R > 0; ++l) {
            long long rem_len = n - l + 1;
            if (rem_len <= 0) break;
            long long max_per_this = R / rem_len;
            if (max_per_this <= 0) continue;
            int q_num = (int)min<long long>(10, min<long long>(2 * n - 3, max_per_this));
            for (int k = 0; k < q_num && R > 0; ++k) {
                int Tt = 3 + k;
                if (Tt > 2 * n - 1) break;
                cout << "? " << l << ' ' << Tt << endl;
                cout.flush();
                int x;
                if (!(cin >> x)) return 0;
                vals.push_back(x);
                ++queriesUsed;
                --R;
            }
        }

        if ((long long)vals.size() < m) {
            // Ensure we have at least m values to output (pad with large values if needed)
            int padVal = (int)1e9;
            while ((long long)vals.size() < m) vals.push_back(padVal);
        }

        sort(vals.begin(), vals.end());
        cout << "!";
        for (long long i = 0; i < m; ++i) {
            cout << ' ' << vals[i];
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}