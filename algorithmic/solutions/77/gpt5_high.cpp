#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Parameters for multiplicative weights
    const double decay = 0.75; // multiply weight by decay on mistake

    // Meta-experts:
    // 0: always 0
    // 1: always 1
    // 2: last outcome (or 0 for first round)
    // 3: opposite of last outcome (or 1 for first round)
    // 4: majority of participants this round (tie -> 1)
    // 5: anti-majority (tie -> 0)
    const int K = 6;

    int tot = n + K;
    vector<double> w(tot, 1.0);

    bool haveLast = false;
    int last = 0;

    for (int round = 0; round < m; ++round) {
        string s;
        if (!(cin >> s)) return 0;

        vector<unsigned char> pred(tot, 0);
        int ones = 0;
        for (int i = 0; i < n; ++i) {
            pred[i] = (s[i] == '1');
            if (pred[i]) ++ones;
        }
        int zeros = n - ones;

        int idx = n;
        pred[idx++] = 0; // always 0
        pred[idx++] = 1; // always 1
        pred[idx++] = haveLast ? (unsigned char)last : (unsigned char)0; // last
        pred[idx++] = haveLast ? (unsigned char)(1 - last) : (unsigned char)1; // anti-last
        int maj = (ones >= zeros) ? 1 : 0; // tie -> 1
        pred[idx++] = (unsigned char)maj; // majority
        pred[idx++] = (unsigned char)(1 - maj); // anti-majority

        double sum1 = 0.0, sum0 = 0.0;
        for (int i = 0; i < tot; ++i) {
            if (pred[i]) sum1 += w[i];
            else sum0 += w[i];
        }

        int guess = (sum1 >= sum0) ? 1 : 0;
        cout << guess << "\n";
        cout.flush();

        string tstr;
        if (!(cin >> tstr)) return 0;
        int t = (tstr[0] == '1') ? 1 : 0;

        for (int i = 0; i < tot; ++i) {
            if ((int)pred[i] != t) w[i] *= decay;
        }
        double wmax = 0.0;
        for (int i = 0; i < tot; ++i) wmax = max(wmax, w[i]);
        if (wmax <= 0.0) {
            for (int i = 0; i < tot; ++i) w[i] = 1.0;
        } else {
            for (int i = 0; i < tot; ++i) w[i] /= wmax;
        }

        haveLast = true;
        last = t;
    }
    return 0;
}