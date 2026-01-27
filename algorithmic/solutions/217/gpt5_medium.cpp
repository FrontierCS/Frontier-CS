#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> vals;
    long long x;
    while (cin >> x) vals.push_back(x);
    if (vals.size() < 2) return 0;
    int N = (int)vals[0];
    int M = (int)vals[1];
    long long L = 1LL * N * M;

    auto print_groups_consecutive = [&]() {
        for (int t = 0; t < M; ++t) {
            for (int j = 0; j < N; ++j) {
                if (j) cout << ' ';
                cout << (t * N + j + 1);
            }
            cout << '\n';
        }
    };

    if ((long long)vals.size() >= 2 + L) {
        // Offline version with colors provided
        vector<vector<int>> byColor(N + 1);
        for (long long i = 0; i < L; ++i) {
            int c = (int)vals[2 + i];
            if (1 <= c && c <= N) byColor[c].push_back((int)i + 1);
        }
        bool ok = true;
        for (int c = 1; c <= N; ++c) {
            if ((int)byColor[c].size() != M) { ok = false; break; }
        }
        if (!ok) {
            // Fallback: cannot trust colors; print consecutive grouping
            print_groups_consecutive();
            return 0;
        }
        for (int t = 0; t < M; ++t) {
            for (int c = 1; c <= N; ++c) {
                if (c > 1) cout << ' ';
                cout << byColor[c][t];
            }
            cout << '\n';
        }
    } else {
        // No colors available; fallback to consecutive grouping
        print_groups_consecutive();
    }

    return 0;
}