#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<vector<int>> G(n + 1, vector<int>(n + 1));
        vector<pair<int,int>> pos(n * n + 1, {-1, -1});
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                cin >> G[i][j];
                pos[G[i][j]] = {i, j};
            }
        }

        int len = 2 * n - 1;
        vector<int> headVal(len + 1, 0);
        for (int T = 1; T <= len; ++T) {
            cout << "? " << 1 << " " << T << endl;
            cout.flush();
            int v;
            if (!(cin >> v)) return 0;
            headVal[T] = v;
        }

        // Build RMQ (sparse table) for headVal[1..len]
        vector<int> lg(len + 1, 0);
        for (int i = 2; i <= len; ++i) lg[i] = lg[i / 2] + 1;
        int K = lg[len] + 1;
        vector<vector<int>> st(K, vector<int>(len + 1, 0));
        for (int i = 1; i <= len; ++i) st[0][i] = headVal[i];
        for (int k = 1; k < K; ++k) {
            int span = 1 << k;
            int half = span >> 1;
            for (int i = 1; i + span - 1 <= len; ++i) {
                st[k][i] = max(st[k - 1][i], st[k - 1][i + half]);
            }
        }
        auto rmq = [&](int L, int R) -> int {
            if (L > R) return 0;
            int k = lg[R - L + 1];
            return max(st[k][L], st[k][R - (1 << k) + 1]);
        };

        // Prefix maxima for first row extras: max over G[1][2..y]
        vector<int> row1pref(n + 2, 0);
        for (int y = 2; y <= n; ++y) {
            row1pref[y] = max(row1pref[y - 1], G[1][y]);
        }

        // Compute all f(l,T), keep m smallest
        vector<int> vals;
        vals.reserve(n * (2 * n - 1));
        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= len; ++T) {
                int L = max(1, T - l + 1);
                int maxWindow = rmq(L, T);
                int extrasLen = max(0, l - T);
                int extrasMax = row1pref[extrasLen + 1]; // max over y in [2..extrasLen+1]
                int f = max(maxWindow, extrasMax);
                vals.push_back(f);
            }
        }

        if ((int)vals.size() > m) {
            nth_element(vals.begin(), vals.begin() + m, vals.end());
            vals.resize(m);
        }
        sort(vals.begin(), vals.end());

        cout << "!";
        for (int i = 0; i < m; ++i) {
            cout << " " << vals[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}