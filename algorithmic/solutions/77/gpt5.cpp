#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    while ( (cin >> n >> m) ) {
        vector<double> w(n, 1.0 / n);
        const double beta = 0.7;

        for (int t = 0; t < m; ++t) {
            string s;
            if (!(cin >> s)) return 0;

            double sum1 = 0.0, sum0 = 0.0;
            for (int i = 0; i < n; ++i) {
                if (s[i] == '1') sum1 += w[i];
                else sum0 += w[i];
            }

            char guess = (sum1 > sum0) ? '1' : '0';
            cout << guess << '\n';
            cout.flush();

            char actual;
            if (!(cin >> actual)) return 0;

            // Update weights
            double sumw = 0.0;
            for (int i = 0; i < n; ++i) {
                if (s[i] != actual) w[i] *= beta;
                sumw += w[i];
            }

            // Renormalize to prevent underflow/overflow
            if (sumw <= 0) {
                // In the extremely unlikely event of numerical underflow, reset to uniform
                fill(w.begin(), w.end(), 1.0 / n);
            } else {
                for (int i = 0; i < n; ++i) w[i] /= sumw;
            }
        }
    }

    return 0;
}