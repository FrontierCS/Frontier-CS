#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    // Fixed seed for determinism
    std::mt19937_64 rng(123456789123456789ULL);
    std::uniform_real_distribution<double> dist(0.0, 1.0);

    while (cin >> n >> m) {
        vector<int> mistakes(n, 0);
        int minMist = 0;

        // Parameters for Randomized Weighted Majority
        const double epsilon = 0.2; // factor guarantee ~ (1+epsilon)*b + ln(n)/epsilon
        const double beta = 1.0 - epsilon;

        vector<double> powBeta(m + 2, 1.0);
        for (int i = 1; i <= m + 1; ++i) powBeta[i] = powBeta[i - 1] * beta;

        for (int t = 0; t < m; ++t) {
            string s;
            if (!(cin >> s)) return 0; // safety

            double W1 = 0.0, Wt = 0.0;
            for (int i = 0; i < n; ++i) {
                int d = mistakes[i] - minMist;
                if (d < 0) d = 0;
                if (d > m + 1) d = m + 1;
                double w = powBeta[d];
                Wt += w;
                if (s[i] == '1') W1 += w;
            }
            double p = (Wt > 0) ? (W1 / Wt) : 0.5;

            int guess = (dist(rng) < p) ? 1 : 0;
            cout << guess << '\n';
            // No flush needed in non-interactive environment

            char outcomeChar;
            if (!(cin >> outcomeChar)) return 0;
            int outcome = outcomeChar - '0';

            for (int i = 0; i < n; ++i) {
                if ((s[i] - '0') != outcome) mistakes[i]++;
            }
            int newMin = mistakes[0];
            for (int i = 1; i < n; ++i) newMin = min(newMin, mistakes[i]);
            minMist = newMin;
        }
    }
    return 0;
}