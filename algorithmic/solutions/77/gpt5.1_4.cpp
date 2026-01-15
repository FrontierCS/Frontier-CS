#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<int> errors(n, 0);
    int izzyErrors = 0;

    const double eta = 0.3; // learning rate
    vector<double> wDiff(m + 1);
    for (int d = 0; d <= m; ++d) {
        wDiff[d] = exp(-eta * d);
    }

    for (int round = 0; round < m; ++round) {
        string s;
        if (!(cin >> s)) return 0;
        if ((int)s.size() != n) return 0;

        int minErr = errors[0];
        for (int i = 1; i < n; ++i) {
            if (errors[i] < minErr) minErr = errors[i];
        }

        double sum0 = 0.0, sum1 = 0.0;
        for (int i = 0; i < n; ++i) {
            int diff = errors[i] - minErr;
            if (diff < 0) diff = 0;
            if (diff > m) diff = m;
            double w = wDiff[diff];
            if (s[i] == '1') sum1 += w;
            else sum0 += w;
        }

        char guess = (sum1 >= sum0 ? '1' : '0');
        cout << guess << endl;
        cout.flush();

        char actual;
        if (!(cin >> actual)) return 0;

        if (guess != actual) ++izzyErrors;

        for (int i = 0; i < n; ++i) {
            if (s[i] != actual) ++errors[i];
        }
    }

    return 0;
}