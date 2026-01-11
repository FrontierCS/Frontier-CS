#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    int participants = n;
    int extraExperts = 2; // constant 0 and 1
    int experts = participants + extraExperts;

    vector<double> weight(experts, 1.0);
    vector<int> pred(experts);

    const double beta = 0.75;

    for (int t = 0; t < m; ++t) {
        string s;
        if (!(cin >> s)) return 0;

        for (int i = 0; i < participants; ++i) {
            pred[i] = s[i] - '0';
        }
        pred[participants] = 0;
        pred[participants + 1] = 1;

        double sum0 = 0.0, sum1 = 0.0;
        for (int i = 0; i < experts; ++i) {
            if (pred[i] == 0) sum0 += weight[i];
            else sum1 += weight[i];
        }

        int guess = (sum1 >= sum0) ? 1 : 0;
        cout << guess << endl;
        cout.flush();

        char outcome_c;
        if (!(cin >> outcome_c)) return 0;
        int outcome = outcome_c - '0';

        for (int i = 0; i < experts; ++i) {
            if (pred[i] != outcome) {
                weight[i] *= beta;
            }
        }

        double maxw = 0.0;
        for (int i = 0; i < experts; ++i) {
            if (weight[i] > maxw) maxw = weight[i];
        }
        if (maxw > 0 && maxw < 1e-100) {
            for (int i = 0; i < experts; ++i) {
                weight[i] /= maxw;
            }
        }
    }

    return 0;
}