#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    while (cin >> n >> m) {
        vector<long double> w(n, 1.0L);
        const long double beta = 0.5L;

        for (int round = 0; round < m; ++round) {
            string s;
            if (!(cin >> s)) return 0;

            long double sum1 = 0.0L, sum0 = 0.0L;
            for (int i = 0; i < n; ++i) {
                if (s[i] == '1') sum1 += w[i];
                else sum0 += w[i];
            }

            char ans = (sum1 >= sum0) ? '1' : '0';
            cout << ans << endl;

            string outcome;
            if (!(cin >> outcome)) return 0;
            char y = outcome[0];

            long double maxw = 0.0L;
            for (int i = 0; i < n; ++i) {
                if (s[i] != y) w[i] *= beta;
                if (w[i] > maxw) maxw = w[i];
            }

            if (maxw == 0.0L) {
                for (int i = 0; i < n; ++i) w[i] = 1.0L;
            } else {
                for (int i = 0; i < n; ++i) w[i] /= maxw;
            }
        }
    }

    return 0;
}