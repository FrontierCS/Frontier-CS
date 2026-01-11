#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    const double beta = 0.5;
    const double SCALE_THRESHOLD = 1e-100;
    const double SCALE_FACTOR = 1e100;

    vector<double> w(n, 1.0);
    string s;

    for (int t = 0; t < m; ++t) {
        if (!(cin >> s)) return 0;

        double W0 = 0.0, W1 = 0.0;
        double w_max = 0.0;

        for (int i = 0; i < n; ++i) {
            double wi = w[i];
            if (wi > w_max) w_max = wi;
            if (s[i] == '0') W0 += wi;
            else W1 += wi;
        }

        char guess = (W1 > W0) ? '1' : '0';
        cout << guess << '\n';
        cout.flush();

        char res;
        if (!(cin >> res)) return 0;

        w_max = 0.0;
        for (int i = 0; i < n; ++i) {
            if (s[i] != res) w[i] *= beta;
            if (w[i] > w_max) w_max = w[i];
        }

        if (w_max < SCALE_THRESHOLD) {
            for (int i = 0; i < n; ++i) {
                w[i] *= SCALE_FACTOR;
            }
        }
    }

    return 0;
}