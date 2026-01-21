#include <bits/stdc++.h>
using namespace std;

using i128 = __int128_t;

static string toString(i128 x) {
    if (x == 0) return "0";
    bool neg = x < 0;
    if (neg) x = -x;
    string s;
    while (x > 0) {
        int digit = (int)(x % 10);
        s.push_back(char('0' + digit));
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

static long long ask(int u, int d) {
    cout << "? " << u << " " << d << "\n" << flush;
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;

    int n = (1 << h) - 1;
    int D = 2 * (h - 1);

    vector<int> depth(n + 1, -1);
    vector<i128> sum_q_depth(h, 0);

    vector<int> remaining;
    remaining.reserve(n);
    for (int u = 1; u <= n; u++) remaining.push_back(u);

    i128 totalD = 0;

    // Classify by depth using distances d = (h-1)+t from t=h-1..0
    for (int t = h - 1; t >= 0; t--) {
        int d = (h - 1) + t;
        vector<int> nextRemaining;
        nextRemaining.reserve(remaining.size());

        for (int u : remaining) {
            long long ans = ask(u, d);
            if (d == D) totalD += (i128)ans;

            if (ans != 0 || t == 0) {
                depth[u] = t;
            } else {
                nextRemaining.push_back(u);
            }
        }
        remaining.swap(nextRemaining);
    }

    // Query distance 1 for all nodes and sum by classified depth
    for (int u = 1; u <= n; u++) {
        long long q = ask(u, 1);
        int t = depth[u];
        if (0 <= t && t < h) sum_q_depth[t] += (i128)q;
    }

    vector<i128> W(h, 0);

    // totalD = 2^(h-2) * W[h-1]
    i128 factor = (i128)1 << (h - 2); // h>=2
    W[h - 1] = totalD / factor;

    if (h >= 2) {
        // sum over leaves of dist=1 answers = 2 * W[h-2]
        W[h - 2] = sum_q_depth[h - 1] / 2;

        for (int t = h - 2; t >= 1; t--) {
            // sum_q_depth[t] = 2*W[t-1] + W[t+1]
            W[t - 1] = (sum_q_depth[t] - W[t + 1]) / 2;
        }
    }

    i128 S = 0;
    for (int t = 0; t < h; t++) S += W[t];

    cout << "! " << toString(S) << "\n" << flush;
    return 0;
}