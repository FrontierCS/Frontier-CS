#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    const double beta = 0.85;
    const double logBeta = log(beta);

    vector<double> logw(n, 0.0);

    std::random_device rd;
    uint64_t seed = (uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ ((uint64_t)rd() << 1);
    mt19937_64 rng(seed);
    uniform_real_distribution<double> unif(0.0, 1.0);

    for (int t = 0; t < m; t++) {
        string s;
        if (!(cin >> s)) break;

        double mx = logw[0];
        for (int i = 1; i < n; i++) mx = max(mx, logw[i]);

        double w0 = 0.0, w1 = 0.0;
        for (int i = 0; i < n; i++) {
            double w = exp(logw[i] - mx);
            if (s[i] == '0') w0 += w;
            else w1 += w;
        }

        int guess;
        if (w0 == 0.0) guess = 1;
        else if (w1 == 0.0) guess = 0;
        else {
            double p1 = w1 / (w0 + w1);
            guess = (unif(rng) < p1) ? 1 : 0;
        }

        cout << guess << '\n';
        cout.flush();

        string outcome;
        if (!(cin >> outcome)) break;
        char y = outcome[0];

        for (int i = 0; i < n; i++) {
            if (s[i] != y) logw[i] += logBeta;
        }
    }

    return 0;
}