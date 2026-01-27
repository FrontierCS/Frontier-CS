#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    vector<array<int,3>> ops;
    if (n == 0) {
        cout << 0 << "\n";
        return 0;
    }

    auto add_length_with_split = [&](long long L, long long P) {
        if (L <= 1) return; // We do not add length 1 (already present)
        if (L > n) return;
        for (long long i = 0; i + L <= n; ++i) {
            long long u = i;
            long long c = i + P;
            long long v = i + L;
            ops.push_back({(int)u, (int)c, (int)v});
        }
    };

    // Choose t = ceil(cuberoot(n+1)) so that any d <= n can be written as x*t^2 + y*t + z with 0<=x,y,z<t
    long long t = 1;
    while (t * t * t < n + 1) ++t;

    // A1: lengths 2..t-1 (build sequentially using d=(d-1)+1)
    for (long long d = 2; d <= n && d <= t - 1; ++d) {
        add_length_with_split(d, d - 1);
    }

    // A2: lengths k*t for k=1..t-1
    if (t <= n) {
        // First k=1: t = (t-1) + 1
        add_length_with_split(t, t - 1);
        for (long long k = 2; k <= t - 1; ++k) {
            long long L = k * t;
            if (L > n) break;
            // L = (k-1)*t + t
            add_length_with_split(L, (k - 1) * t);
        }
    }

    // A3: lengths k*t^2 for k=1..t-1
    if (t * t <= n) {
        // First k=1: t^2 = (t-1)*t + t
        add_length_with_split(t * t, (t - 1) * t);
        for (long long k = 2; k <= t - 1; ++k) {
            long long L = k * t * t;
            if (L > n) break;
            // L = (k-1)*t^2 + t^2
            add_length_with_split(L, (k - 1) * t * t);
        }
    }

    cout << ops.size() << "\n";
    for (auto &e : ops) {
        cout << e[0] << " " << e[1] << " " << e[2] << "\n";
    }
    return 0;
}