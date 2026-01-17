#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    const double eps = 0.1;
    vector<double> w(n, 1.0);
    string s, outcome;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist(0.0, 1.0);

    for (int round = 0; round < m; ++round) {
        if (!(cin >> s)) return 0;

        double sum0 = 0.0, sum1 = 0.0;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') sum0 += w[i];
            else sum1 += w[i];
        }

        double total = sum0 + sum1;
        char guess = '0';
        if (total > 0.0) {
            double u = dist(rng);
            double p1 = sum1 / total;
            guess = (u < p1 ? '1' : '0');
        }

        cout << guess << endl;
        cout.flush();

        if (!(cin >> outcome)) return 0;
        char truth = outcome[0];

        double maxw = 0.0;
        for (int i = 0; i < n; ++i) {
            if (s[i] != truth) {
                w[i] *= (1.0 - eps);
            }
            if (w[i] > maxw) maxw = w[i];
        }

        if (maxw < 1e-200) {
            if (maxw <= 0.0) {
                fill(w.begin(), w.end(), 1.0);
            } else {
                for (int i = 0; i < n; ++i) w[i] /= maxw;
            }
        }
    }

    return 0;
}