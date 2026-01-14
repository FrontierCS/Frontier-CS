#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();

    // Prefix sum of ones
    vector<int> P(n + 1, 0);
    for (int i = 1; i <= n; ++i) P[i] = P[i - 1] + (s[i - 1] == '1');

    // Positions of ones (1-based indices in string)
    vector<int> pos;
    pos.reserve(P[n]);
    for (int i = 0; i < n; ++i) if (s[i] == '1') pos.push_back(i + 1);
    int m = (int)pos.size();

    // If no ones, no valid non-empty substrings satisfy zeros = ones^2
    if (m == 0) {
        cout << 0 << '\n';
        return 0;
    }

    // Compute LZ (zeros before each 1) and RZ (zeros after each 1), and gaps between ones
    vector<int> LZ(m + 1, 0), RZ(m + 1, 0), gap(m + 2, 0);
    // pos is 0-based here, adapt indices
    // pos_i (1-based) corresponds to pos[i-1]
    // LZ[1] = pos1 - 1, LZ[t] = pos[t] - pos[t-1] - 1
    LZ[1] = pos[0] - 1;
    for (int t = 2; t <= m; ++t) {
        LZ[t] = pos[t - 1] - pos[t - 2] - 1;
    }
    // RZ[t] = pos[t+1] - pos[t] - 1, with RZ[m] = n - pos[m]
    for (int t = 1; t <= m - 1; ++t) {
        RZ[t] = pos[t] - pos[t - 1] - 1;
        gap[t] = RZ[t];
    }
    RZ[m] = n - pos[m - 1];
    gap[m] = 0; // padding

    // Kmax based on length constraint L = k(k+1) <= n
    long double disc = (long double)1 + (long double)4 * (long double)n;
    long long Kmax_all = (long long)floor((sqrtl(disc) - 1.0L) / 2.0L);
    int Kmax = (int)min<long long>(Kmax_all, m);

    long long ans = 0;

    // Dynamic budgets
    const long long smallOpsBudget = 120000000LL;  // budget for small-k block processing (m * K_small)
    const long long windowsBudget = 80000000LL;    // budget for large-k window scans (sum of (n - L + 1))

    // Determine large-k range [K_big..Kmax]
    int K_big = Kmax + 1; // default: no large-k if budget exceeded immediately
    {
        long long acc = 0;
        for (int k = Kmax; k >= 1; --k) {
            long long L = 1LL * k * (k + 1);
            if (L > n) continue;
            long long w = (long long)n - L + 1;
            if (acc + w > windowsBudget) { K_big = k + 1; break; }
            acc += w;
        }
        if (K_big == Kmax + 1) {
            // All k fit in budget
            K_big = 1;
        }
    }

    // Determine small-k range [1..K_small]
    int K_small = 0;
    if (m > 0) {
        long long candidate = smallOpsBudget / (long long)m;
        if (candidate > Kmax) candidate = Kmax;
        K_small = (int)candidate;
        if (K_big <= Kmax) {
            // avoid overlap
            if (K_small >= K_big) K_small = K_big - 1;
        }
    }

    // Small-k exact using ones-block method
    if (K_small >= 1) {
        long long baseInner = 0; // sum of first (k-1) gaps for current k
        for (int k = 1; k <= K_small && k <= m; ++k) {
            long long k2 = 1LL * k * k;
            int limit = m - k + 1;
            long long innerSum = (k >= 2 ? baseInner : 0);
            int u = k;
            if (k == 1) {
                for (int t = 1; t <= limit; ++t, ++u) {
                    int A = LZ[t];
                    int B = RZ[u];
                    long long sneed = 1; // k^2 - innerZeros = 1 - 0
                    long long sumAB = (long long)A + (long long)B;
                    if (sneed <= sumAB) {
                        long long lower = sneed - B; if (lower < 0) lower = 0;
                        long long upper = sneed; if (upper > A) upper = A;
                        if (upper >= lower) ans += (upper - lower + 1);
                    }
                }
            } else {
                for (int t = 1; t <= limit; ++t, ++u) {
                    int A = LZ[t];
                    int B = RZ[u];
                    long long sneed = k2 - innerSum;
                    if (sneed >= 0) {
                        long long sumAB = (long long)A + (long long)B;
                        if (sneed <= sumAB) {
                            long long lower = sneed - B; if (lower < 0) lower = 0;
                            long long upper = sneed; if (upper > A) upper = A;
                            if (upper >= lower) ans += (upper - lower + 1);
                        }
                    }
                    if (t < limit) {
                        // innerSum for next t: remove gap[t], add gap[t + k - 1]
                        innerSum += (long long)gap[t + k - 1] - (long long)gap[t];
                    }
                }
                if (k < m) baseInner += (long long)gap[k];
            }
        }
    }

    // Large-k exact using window sliding
    if (K_big <= Kmax) {
        for (int k = K_big; k <= Kmax; ++k) {
            long long L = 1LL * k * (k + 1);
            if (L > n) continue;
            int Li = (int)L;
            int lim = n - Li;
            const int* p = P.data();
            long long c = 0;
            for (int i = 0; i <= lim; ++i) {
                int val = p[i + Li] - p[i];
                if (val == k) ++c;
            }
            ans += c;
        }
    }

    cout << ans << '\n';
    return 0;
}