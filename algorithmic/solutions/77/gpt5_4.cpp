#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    const double eta = 0.1; // learning rate for randomized weighted majority
    const double beta = exp(-eta);

    vector<long double> w(n, 1.0L);
    std::mt19937 rng(712367821);

    for (int round = 0; round < m; ++round) {
        string s;
        if (!(cin >> s)) return 0;

        long double W0 = 0.0L, W1 = 0.0L;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '1') W1 += w[i];
            else W0 += w[i];
        }

        long double total = W0 + W1;
        double p1;
        if (total > 0.0L) p1 = (double)(W1 / total);
        else p1 = 0.5; // if all weights zero (shouldn't happen), choose uniformly

        // Randomized prediction based on weighted vote
        std::bernoulli_distribution bern(p1);
        int guess = bern(rng) ? 1 : 0;

        cout << guess << "\n";
        cout.flush();

        string actual;
        if (!(cin >> actual)) return 0;
        int y = (actual[0] == '1') ? 1 : 0;

        // Update weights: penalize experts who were wrong
        for (int i = 0; i < n; ++i) {
            int xi = (s[i] == '1') ? 1 : 0;
            if (xi != y) w[i] *= beta;
        }

        // Optional renormalization to prevent underflow (keep scale reasonable)
        // Divide by max weight if it gets too small
        if (round % 256 == 255) {
            long double mx = 0.0L;
            for (int i = 0; i < n; ++i) mx = max(mx, w[i]);
            if (mx > 0 && (mx < 1e-200L || mx > 1e200L)) {
                for (int i = 0; i < n; ++i) w[i] /= mx;
            }
        }
    }

    return 0;
}