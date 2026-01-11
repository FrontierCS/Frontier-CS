#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Add two dummy experts: always 0 and always 1
    int total_experts = n + 2;
    int dummy0 = n;
    int dummy1 = n + 1;

    vector<double> w(total_experts, 1.0);

    // Randomized Weighted Majority parameters
    const double eta = 0.3;                 // learning rate
    const double beta = exp(-eta);          // multiplicative factor for mistakes

    // Deterministic RNG (xorshift* 64-bit)
    uint64_t seed = 0x9E3779B97F4A7C15ULL;
    auto rng01 = [&]() -> double {
        seed ^= seed >> 12;
        seed ^= seed << 25;
        seed ^= seed >> 27;
        uint64_t res = seed * 2685821657736338717ULL;
        // convert to [0,1)
        return (res >> 11) * (1.0 / (double)(1ULL << 53));
    };

    for (int t = 0; t < m; ++t) {
        string s;
        cin >> s;
        if ((int)s.size() != n) {
            // Robustly handle any stray whitespace/newlines
            while ((int)s.size() < n) {
                string more;
                cin >> more;
                s += more;
                if (!cin) break;
            }
            s.resize(n);
        }

        // Compute weighted probability for predicting 1
        double sum1 = w[dummy1]; // always-1 expert
        double sum0 = w[dummy0]; // always-0 expert
        for (int i = 0; i < n; ++i) {
            if (s[i] == '1') sum1 += w[i];
            else sum0 += w[i];
        }
        double W = sum0 + sum1;
        double p1 = (W > 0) ? (sum1 / W) : 0.5;

        char guess;
        if (p1 <= 1e-12) guess = '0';
        else if (p1 >= 1.0 - 1e-12) guess = '1';
        else guess = (rng01() < p1 ? '1' : '0');

        cout << guess << '\n';
        // No flush needed in offline environment

        string r;
        cin >> r;
        char outcome = r[0];

        // Update weights: penalize experts that were wrong
        for (int i = 0; i < n; ++i) {
            if (s[i] != outcome) w[i] *= beta;
        }
        if (outcome == '1') w[dummy0] *= beta;
        else w[dummy1] *= beta;

        // Renormalize to avoid underflow/overflow
        double maxw = 0.0;
        for (int i = 0; i < total_experts; ++i) {
            if (w[i] > maxw) maxw = w[i];
        }
        if (maxw == 0.0) {
            for (int i = 0; i < total_experts; ++i) w[i] = 1.0;
        } else {
            for (int i = 0; i < total_experts; ++i) w[i] /= maxw;
        }
    }

    return 0;
}