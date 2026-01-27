#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    long long addEdges = 1LL * n * (n - 1) / 2;
    long long K = m + addEdges;
    cout << K << '\n';

    // Remove all existing edges
    for (int i = 0; i < m; ++i) {
        cout << "- " << edges[i].first << ' ' << edges[i].second << '\n';
    }

    // Add chain edges: for i > 1, add edges to all j < i
    for (int i = 2; i <= n; ++i) {
        for (int j = 1; j < i; ++j) {
            cout << "+ " << i << ' ' << j << '\n';
        }
    }
    cout.flush();

    // Grundy numbers after modifications: g[i] = i - 1
    // Precompute basis vertices for powers of two
    int B = 0;
    while ((1 << B) < n) ++B;
    vector<int> basis(B);
    for (int b = 0; b < B; ++b) {
        basis[b] = (1 << b) + 1;  // vertex with Grundy 2^b
    }

    for (int t = 0; t < T; ++t) {
        bool found = false;
        for (int k = 0; k < n; ++k) {
            vector<int> S;
            for (int b = 0; b < B; ++b) {
                if (k & (1 << b)) {
                    int idx = basis[b];
                    if (idx <= n) S.push_back(idx);
                }
            }

            cout << "? " << S.size();
            for (int x : S) cout << ' ' << x;
            cout << '\n';
            cout.flush();

            string resp;
            if (!(cin >> resp)) return 0;

            if (resp == "Lose") {
                int v = k + 1;  // unique vertex with Grundy k
                cout << "! " << v << '\n';
                cout.flush();
                string verdict;
                if (!(cin >> verdict)) return 0;
                if (verdict == "Wrong") return 0;
                found = true;
                break;
            } else if (resp == "Win" || resp == "Draw") {
                // Continue searching; Draw shouldn't occur with our DAG
                continue;
            } else {
                // Unexpected response
                return 0;
            }
        }
        if (!found) {
            // Fallback (should not happen)
            cout << "! " << 1 << '\n';
            cout.flush();
            string verdict;
            if (!(cin >> verdict)) return 0;
            if (verdict == "Wrong") return 0;
        }
    }

    return 0;
}