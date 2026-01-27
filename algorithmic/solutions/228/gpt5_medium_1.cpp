#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    if (!getline(cin, s)) return 0;
    int n = (int)s.size();

    // Build gap array g: size m+1 where m is number of ones.
    vector<int> g;
    g.reserve(n + 1);
    int cnt0 = 0;
    int m = 0;
    bool seenOne = false;
    for (char c : s) {
        if (c == '1') {
            if (!seenOne) {
                g.push_back(cnt0); // leading zeros
                seenOne = true;
            } else {
                g.push_back(cnt0); // inner gap between ones
            }
            cnt0 = 0;
            ++m;
        } else {
            ++cnt0;
        }
    }
    if (!seenOne) {
        cout << 0 << '\n';
        return 0;
    }
    g.push_back(cnt0); // trailing zeros, g size = m+1

    // Precompute prefix and suffix max over g for bounds
    vector<int> prefMax(m + 1), suffMax(m + 1);
    prefMax[0] = g[0];
    for (int i = 1; i <= m; ++i) prefMax[i] = max(prefMax[i - 1], g[i]);
    suffMax[m] = g[m];
    for (int i = m - 1; i >= 0; --i) suffMax[i] = max(suffMax[i + 1], g[i]);

    // Max inner gap
    int innerMax = 0;
    if (m >= 2) {
        for (int i = 1; i <= m - 1; ++i) innerMax = max(innerMax, g[i]);
    }

    // Compute K limit by length: L = k(k+1) <= n -> k <= floor((sqrt(1+4n)-1)/2)
    long long disc = 1LL + 4LL * n;
    long long sq = (long long)floor(sqrt((long double)disc));
    while ((sq + 1) * (sq + 1) <= disc) ++sq;
    while (sq * sq > disc) --sq;
    int KmaxLen = (int)((sq - 1) / 2);
    int Klimit = min(KmaxLen, m);

    long long ans = 0;

    const int *gp = g.data();

    for (int k = 1; k <= Klimit; ++k) {
        int k2 = k * k;

        // Upper bound: for any i, S_i <= (k-1)*innerMax, gl+gr <= pref[m-k] + suff[k]
        int U1 = prefMax[m - k] + suffMax[k];
        long long bound = (long long)(k - 1) * (long long)innerMax + (long long)U1;
        if ((long long)k2 > bound) continue;

        long long ssum = 0;
        // initial sum of inner gaps g[1..k-1]
        for (int t = 1; t <= k - 1; ++t) ssum += gp[t];

        int limit = m - k + 1;
        for (int i = 1; i <= limit; ++i) {
            int gl = gp[i - 1];
            int gr = gp[i + k - 1];
            long long T = (long long)k2 - ssum;
            if (T >= 0) {
                long long sumgrgl = (long long)gl + (long long)gr;
                if (T <= sumgrgl) {
                    long long lo = T - gr; if (lo < 0) lo = 0;
                    long long hi = T < gl ? T : gl;
                    if (lo <= hi) ans += (hi - lo + 1);
                }
            }
            if (i < limit) ssum += - (long long)gp[i] + (long long)gp[i + k - 1];
        }
    }

    cout << ans << '\n';
    return 0;
}