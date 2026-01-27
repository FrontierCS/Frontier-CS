#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, c, v;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n <= 1) {
        cout << 0 << '\n';
        return 0;
    }

    int B = (int)std::sqrt(n);
    if (1LL * B * B < n) ++B;

    vector<Edge> res;
    res.reserve(400000);

    int maxSmallLen = min(B, n);

    // Build edges for lengths 2..B
    for (int L = 2; L <= maxSmallLen; ++L) {
        for (int i = 0; i + L <= n; ++i) {
            int u = i;
            int c = i + L - 1;
            int v = i + L;
            res.push_back({u, c, v});
        }
    }

    int M = n / B;

    // Build edges for lengths k*B, k = 2..M
    for (int k = 2; k <= M; ++k) {
        int L = k * B;
        if (L > n) break;
        int a = (k - 1) * B;
        for (int i = 0; i + L <= n; ++i) {
            int u = i;
            int c = i + a;
            int v = i + L;
            res.push_back({u, c, v});
        }
    }

    cout << res.size() << '\n';
    for (const auto &e : res) {
        cout << e.u << ' ' << e.c << ' ' << e.v << '\n';
    }

    return 0;
}