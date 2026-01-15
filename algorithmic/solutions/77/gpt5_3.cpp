#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937_64 rng(712367218972361ULL);
    auto rand01 = [&]() -> double {
        return (rng() >> 11) * (1.0 / 9007199254740992.0); // [0,1)
    };

    int n, m;
    while ( (cin >> n >> m) ) {
        const double epsilon = 0.25; // tuneable
        const double gamma = 1.0 - epsilon;

        vector<int> mistakes(n, 0);
        vector<double> powGamma(1, 1.0); // gamma^0 = 1

        auto getPow = [&](int d) -> double {
            if (d < (int)powGamma.size()) return powGamma[d];
            int old = powGamma.size();
            powGamma.resize(d + 1);
            for (int k = old; k <= d; ++k) {
                powGamma[k] = powGamma[k - 1] * gamma;
            }
            return powGamma[d];
        };

        for (int t = 0; t < m; ++t) {
            string s;
            do {
                if (!(cin >> s)) return 0;
            } while ((int)s.size() != n);

            // compute s_min
            int s_min = mistakes[0];
            for (int i = 1; i < n; ++i) {
                if (mistakes[i] < s_min) s_min = mistakes[i];
            }

            // compute weighted probability for 1
            double sum1 = 0.0, sum0 = 0.0;
            for (int i = 0; i < n; ++i) {
                int d = mistakes[i] - s_min; // >= 0
                double w = getPow(d);
                if (s[i] == '1') sum1 += w;
                else sum0 += w;
            }
            double total = sum1 + sum0;
            double p1 = (total > 0.0) ? (sum1 / total) : 0.5;

            char guess = (rand01() < p1) ? '1' : '0';
            cout << guess << '\n' << flush;

            string outcome;
            if (!(cin >> outcome)) return 0;
            char y = outcome[0];

            // update mistakes
            for (int i = 0; i < n; ++i) {
                if (s[i] != y) mistakes[i]++;
            }
        }
    }

    return 0;
}