#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    long long K = (long long)m + (long long)n * (n - 1) / 2;
    cout << K << '\n';

    // Remove all existing edges
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        cout << "- " << a << ' ' << b << '\n';
    }

    // Add edges: for each a, edges to all b < a
    for (int a = 2; a <= n; ++a) {
        for (int b = 1; b < a; ++b) {
            cout << "+ " << a << ' ' << b << '\n';
        }
    }
    cout.flush();

    // Precompute query sets S[y] so that xor of Grundy values (i-1) over S[y] equals y.
    // We use powers of two as basis: Grundy(i) = i-1, so vertex (1<<k)+1 has Grundy 2^k.
    vector<vector<int>> S(n);
    int maxBit = 0;
    while ((1 << maxBit) < n) ++maxBit; // bits 0..maxBit-1, with (1<<maxBit-1) < n

    for (int y = 0; y < n; ++y) {
        vector<int> vec;
        for (int k = 0; k < maxBit; ++k) {
            if (y & (1 << k)) {
                int v = (1 << k) + 1; // vertex with Grundy 2^k
                if (v <= n) vec.push_back(v);
            }
        }
        S[y] = move(vec);
    }

    string resp;
    for (int round = 0; round < T; ++round) {
        // Issue all n queries for this round
        for (int y = 0; y < n; ++y) {
            auto &vec = S[y];
            cout << "? " << vec.size();
            for (int v : vec) cout << ' ' << v;
            cout << '\n';
        }
        cout.flush();

        int found = -1;
        for (int y = 0; y < n; ++y) {
            if (!(cin >> resp)) return 0;
            if (resp == "Lose") {
                found = y;
            }
        }
        if (found == -1) found = 0; // should not happen

        int guess_vertex = found + 1; // g(v) = v-1
        cout << "! " << guess_vertex << '\n';
        cout.flush();

        if (!(cin >> resp)) return 0;
        if (resp == "Wrong") return 0;
    }

    return 0;
}