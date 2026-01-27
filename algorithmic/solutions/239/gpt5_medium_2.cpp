#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    auto ceil_cuberoot = [](long long x) -> int {
        int t = 0;
        while (1LL*(t+1)*(t+1)*(t+1) < x) ++t;
        if (1LL*t*t*t < x) ++t;
        return t;
    };

    int t = ceil_cuberoot(1LL * n + 1);

    struct Edge { int u, c, v; };
    vector<Edge> res;

    auto add_length = [&](int L, int x) {
        if (L <= 0 || x <= 0 || x >= L) return;
        for (int i = 0; i + L <= n; ++i) {
            res.push_back({i, i + x, i + L});
        }
    };

    if (t >= 2) {
        // Small lengths: 2..t-1
        for (int k = 2; k <= t - 1; ++k) add_length(k, k - 1);
        // Length t
        add_length(t, t - 1);
        // Multiples of t: p*t for p=2..t-1
        for (int p = 2; p <= t - 1; ++p) add_length(p * t, (p - 1) * t);
        // Length t^2
        add_length(t * t, (t - 1) * t);
        // Multiples of t^2: p*t^2 for p=2..t-1
        for (int p = 2; p <= t - 1; ++p) add_length(p * t * t, (p - 1) * t * t);
    }

    cout << (int)res.size() << '\n';
    for (auto &e : res) {
        cout << e.u << ' ' << e.c << ' ' << e.v << '\n';
    }
    return 0;
}