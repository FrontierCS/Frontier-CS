#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, x, y;
    if (!(cin >> n >> x >> y)) return 0;

    // If both distances are larger than possible difference, no constraints
    if (x > n - 1 && y > n - 1) {
        cout << n;
        return 0;
    }

    // Exact solution when x == y: only one forbidden distance
    if (x == y) {
        long long d = x;
        if (d > n - 1) {
            cout << n;
            return 0;
        }
        long long q = n / d;
        long long rem = n % d;
        if (q == 0) {
            cout << n;
            return 0;
        }
        auto f = [](long long L) -> long long {
            return (L + 1) / 2;
        };
        long long t = rem;        // residues with length q+1
        long long L1 = q + 1;
        long long L2 = q;
        long long ans = t * f(L1) + (d - t) * f(L2);
        cout << ans;
        return 0;
    }

    const long long MAX_SAMPLE = 25000000LL;
    long long sample_size = n;
    if (sample_size > MAX_SAMPLE) sample_size = MAX_SAMPLE;

    if (sample_size <= 0) {
        cout << 0;
        return 0;
    }

    vector<unsigned char> used(sample_size + 1);

    // Forward greedy
    long long cnt1 = 0;
    fill(used.begin(), used.end(), 0);
    for (long long i = 1; i <= sample_size; ++i) {
        bool ok = true;
        if (i - x >= 1 && used[i - x]) ok = false;
        if (i - y >= 1 && used[i - y]) ok = false;
        if (ok) {
            used[i] = 1;
            ++cnt1;
        }
    }

    // Backward greedy
    long long cnt2 = 0;
    fill(used.begin(), used.end(), 0);
    for (long long i = sample_size; i >= 1; --i) {
        bool ok = true;
        if (i + x <= sample_size && used[i + x]) ok = false;
        if (i + y <= sample_size && used[i + y]) ok = false;
        if (ok) {
            used[i] = 1;
            ++cnt2;
        }
    }

    long double dens1 = (long double)cnt1 / (long double)sample_size;
    long double dens2 = (long double)cnt2 / (long double)sample_size;
    long double best = max(dens1, dens2);

    long double val = best * (long double)n;
    long long est = (long long)(val + 0.5L); // round to nearest
    if (est < 0) est = 0;
    if (est > n) est = n;

    cout << est;
    return 0;
}