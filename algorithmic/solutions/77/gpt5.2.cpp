#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    const double eps = 0.3;
    const double beta = 1.0 / (1.0 + eps);

    int N = 2 * n + 2;                 // originals, opposites, const0, const1
    int idxConst0 = 2 * n;
    int idxConst1 = 2 * n + 1;

    vector<double> w(N, 1.0);

    for (int round = 0; round < m; round++) {
        string s;
        cin >> s;

        double W0 = w[idxConst0];
        double W1 = w[idxConst1];

        for (int i = 0; i < n; i++) {
            if (s[i] == '0') {
                W0 += w[i];
                W1 += w[i + n];
            } else {
                W1 += w[i];
                W0 += w[i + n];
            }
        }

        char guess = (W1 >= W0) ? '1' : '0';
        cout << guess << '\n' << flush;

        string out;
        cin >> out;
        char y = out[0];

        // Update weights: penalize experts that predicted incorrectly
        for (int i = 0; i < n; i++) {
            if (s[i] == y) w[i + n] *= beta; // opposite wrong
            else w[i] *= beta;               // original wrong
        }
        if (y == '1') w[idxConst0] *= beta;
        else w[idxConst1] *= beta;

        // Normalize to avoid underflow/denormals
        double mx = 0.0;
        for (double val : w) mx = max(mx, val);
        if (mx == 0.0) {
            fill(w.begin(), w.end(), 1.0);
        } else {
            double inv = 1.0 / mx;
            for (double &val : w) val *= inv;
        }
    }

    return 0;
}