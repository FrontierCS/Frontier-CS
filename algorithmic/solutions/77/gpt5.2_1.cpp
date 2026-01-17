#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    while (cin >> n >> m) {
        const double eps = 0.30;
        const double beta = max(1e-12, 1.0 - eps / 2.0);
        const double logbeta = log(beta);

        vector<double> logw(n, 0.0);

        for (int t = 0; t < m; t++) {
            string s;
            cin >> s;

            double maxLog = logw[0];
            for (int i = 1; i < n; i++) maxLog = max(maxLog, logw[i]);

            double sum0 = 0.0, sum1 = 0.0;
            for (int i = 0; i < n; i++) {
                double w = exp(logw[i] - maxLog);
                if (s[i] == '0') sum0 += w;
                else sum1 += w;
            }

            char guess = (sum1 >= sum0) ? '1' : '0';
            cout << guess << '\n' << flush;

            string outcome;
            if (!(cin >> outcome)) return 0;
            char y = outcome[0];

            if (beta != 1.0) {
                for (int i = 0; i < n; i++) {
                    if (s[i] != y) logw[i] += logbeta;
                }
            }
        }
    }

    return 0;
}