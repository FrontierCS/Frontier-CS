#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<long double> w(n, 1.0L / n);

    const long double beta = 0.8L;

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&seed);
    try {
        random_device rd;
        seed ^= (uint64_t)rd() << 32;
        seed ^= (uint64_t)rd();
    } catch (...) {
        // ignore
    }
    mt19937_64 rng(seed);
    uniform_real_distribution<long double> uni(0.0L, 1.0L);

    for (int t = 0; t < m; t++) {
        string s;
        if (!(cin >> s)) return 0;

        long double p1 = 0.0L;
        for (int i = 0; i < n; i++) {
            if (s[i] == '1') p1 += w[i];
        }

        int pred = (uni(rng) < p1) ? 1 : 0;
        cout << pred << endl;
        cout.flush();

        string out;
        if (!(cin >> out)) return 0;
        char y = out[0];

        long double sumw = 0.0L;
        for (int i = 0; i < n; i++) {
            if (s[i] != y) w[i] *= beta;
            sumw += w[i];
        }

        if (!(sumw > 0.0L)) {
            long double val = 1.0L / n;
            for (int i = 0; i < n; i++) w[i] = val;
        } else {
            for (int i = 0; i < n; i++) w[i] /= sumw;
        }
    }

    return 0;
}