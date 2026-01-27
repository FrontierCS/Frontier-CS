#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<double> w(n, 1.0 / n);
    const double eta = 0.3;
    const double alpha = exp(-eta);

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    std::uniform_real_distribution<double> dist(0.0, 1.0);

    for (int round = 0; round < m; ++round) {
        string s;
        if (!(cin >> s)) return 0;

        double S1 = 0.0;
        for (int i = 0; i < n; ++i) if (s[i] == '1') S1 += w[i];
        double S0 = 1.0 - S1;

        double p1 = (S0 + S1 > 0) ? (S1 / (S0 + S1)) : 0.5;
        char ans = (dist(rng) < p1) ? '1' : '0';

        cout << ans << '\n' << flush;

        string y;
        if (!(cin >> y)) return 0;
        char yy = y[0];

        double sumw = 0.0;
        for (int i = 0; i < n; ++i) {
            if (s[i] != yy) w[i] *= alpha;
            sumw += w[i];
        }
        if (sumw == 0.0) {
            double inv = 1.0 / n;
            for (int i = 0; i < n; ++i) w[i] = inv;
        } else {
            double inv = 1.0 / sumw;
            for (int i = 0; i < n; ++i) w[i] *= inv;
        }
    }
    return 0;
}