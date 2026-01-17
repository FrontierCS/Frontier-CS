#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n, m;
    cin >> n >> m;

    vector<int> mistakes(n, 0);
    const double eta = 0.5;
    const double beta = exp(-eta);

    vector<double> beta_pow(m + 1);
    beta_pow[0] = 1.0;
    for (int i = 1; i <= m; ++i) {
        beta_pow[i] = beta_pow[i - 1] * beta;
    }

    mt19937 rng(12345);
    uniform_real_distribution<double> dist(0.0, 1.0);

    for (int t = 0; t < m; ++t) {
        string s;
        cin >> s;

        bool has0 = false, has1 = false;
        int M0 = INT_MAX, M1 = INT_MAX;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') {
                has0 = true;
                M0 = min(M0, mistakes[i]);
            } else {
                has1 = true;
                M1 = min(M1, mistakes[i]);
            }
        }

        double sum0 = 0.0, sum1 = 0.0;
        if (has0) {
            for (int i = 0; i < n; ++i) {
                if (s[i] == '0') {
                    sum0 += beta_pow[mistakes[i] - M0];
                }
            }
        }
        if (has1) {
            for (int i = 0; i < n; ++i) {
                if (s[i] == '1') {
                    sum1 += beta_pow[mistakes[i] - M1];
                }
            }
        }

        double w0 = 0.0, w1 = 0.0;
        if (has0 && has1) {
            int M_min = min(M0, M1);
            w0 = beta_pow[M0 - M_min] * sum0;
            w1 = beta_pow[M1 - M_min] * sum1;
        } else if (has0) {
            w0 = sum0;
        } else {
            w1 = sum1;
        }

        double p1;
        if (w0 == 0.0 && w1 == 0.0) {
            p1 = 0.5;
        } else if (w0 == 0.0) {
            p1 = 1.0;
        } else if (w1 == 0.0) {
            p1 = 0.0;
        } else {
            p1 = w1 / (w0 + w1);
        }

        double r = dist(rng);
        char prediction = (r < p1) ? '1' : '0';
        cout << prediction << endl;
        cout.flush();

        char outcome_char;
        cin >> outcome_char;
        int outcome = outcome_char - '0';

        for (int i = 0; i < n; ++i) {
            int pred_i = s[i] - '0';
            if (pred_i != outcome) {
                mistakes[i]++;
            }
        }
    }

    return 0;
}