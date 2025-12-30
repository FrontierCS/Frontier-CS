#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

static int64 isqrtll(int64 x) {
    long double d = sqrtl((long double)x);
    int64 r = (int64)d;
    while ((r + 1) > 0 && (r + 1) * (r + 1) <= x) ++r;
    while (r * r > x) --r;
    return r;
}

static i128 objective(const vector<int64>& v) {
    i128 sum = 0;
    for (int64 x : v) sum += (i128)x;
    return (i128)v.size() * sum;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int64 n;
    if (!(cin >> n)) return 0;

    vector<int64> best, candA, candB;

    // Candidate A: powers of 2 from 1
    {
        uint64_t p = 1;
        while (p <= (uint64_t)n) {
            candA.push_back((int64)p);
            if (p > (uint64_t)n / 2) break;
            p <<= 1;
        }
    }

    best = candA;
    i128 bestV = objective(best);

    // Candidate B: odd-gcd construction, valid for n >= 9
    if (n >= 9) {
        int64 t = isqrtll(n);
        int64 k = (t + 3) / 2; // ensures (2k-3)^2 <= n
        if (k >= 3) {
            candB.reserve((size_t)k);
            candB.push_back(1);
            for (int64 i = 2; i <= k - 1; ++i) {
                int64 x = 2 * i - 3;
                int64 y = 2 * i - 1;
                candB.push_back(x * y);
            }
            int64 x = 2 * k - 3;
            candB.push_back(x * x);

            i128 vB = objective(candB);
            if (vB > bestV) {
                bestV = vB;
                best.swap(candB);
            }
        }
    }

    cout << best.size() << "\n";
    for (size_t i = 0; i < best.size(); ++i) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << "\n";
    return 0;
}