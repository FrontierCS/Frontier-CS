#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<double> w(n, 1.0);
    const double eta = 0.3;
    const double decay = 1.0 - eta;
    const double renorm_threshold = 1e-200;

    mt19937_64 rng(712367431234567ULL);
    uniform_real_distribution<double> dist(0.0, 1.0);

    string s;
    for (int t = 0; t < m; ++t) {
        if (!(cin >> s)) return 0;

        double W0 = 0.0, W1 = 0.0;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') W0 += w[i];
            else W1 += w[i];
        }

        int my;
        if (W0 == 0.0 && W1 == 0.0) {
            my = 0;
        } else if (W0 == 0.0) {
            my = 1;
        } else if (W1 == 0.0) {
            my = 0;
        } else {
            double p1 = W1 / (W0 + W1);
            double u = dist(rng);
            my = (u < p1) ? 1 : 0;
        }

        cout << my << endl;
        cout.flush();

        string ystr;
        if (!(cin >> ystr)) return 0;
        int y = (ystr[0] == '1') ? 1 : 0;

        double mx = 0.0;
        for (int i = 0; i < n; ++i) {
            if (((s[i] == '1') ? 1 : 0) != y) w[i] *= decay;
            if (w[i] > mx) mx = w[i];
        }

        if (mx < renorm_threshold) {
            if (mx == 0.0) {
                for (int i = 0; i < n; ++i) w[i] = 1.0;
            } else {
                for (int i = 0; i < n; ++i) w[i] /= mx;
            }
        }
    }

    return 0;
}