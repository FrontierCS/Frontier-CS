#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();

    int onesTotal = 0, zerosTotal = 0;
    for (char c : s) {
        if (c == '1') ++onesTotal;
        else ++zerosTotal;
    }

    // No substring can satisfy zeros = ones^2 if there are no ones or no zeros.
    if (onesTotal == 0 || zerosTotal == 0) {
        cout << 0 << '\n';
        return 0;
    }

    // Build positions of '1's and zero-run lengths zrun[0..m]
    vector<int> pos;
    pos.reserve(onesTotal);
    vector<int> zrun;
    zrun.reserve(onesTotal + 1);

    int cntZero = 0;
    for (int i = 0; i < n; ++i) {
        if (s[i] == '0') {
            ++cntZero;
        } else {
            zrun.push_back(cntZero);
            cntZero = 0;
            pos.push_back(i + 1); // 1-based position of '1'
        }
    }
    zrun.push_back(cntZero); // zeros after last '1'

    int m = (int)pos.size();
    if (m == 0) {
        cout << 0 << '\n';
        return 0;
    }

    // Bound on number of ones in a valid substring: t^2 <= zerosTotal
    int T_global = (int)sqrt((double)zerosTotal);
    if (T_global > m) T_global = m;
    if (T_global == 0) {
        cout << 0 << '\n';
        return 0;
    }

    // Max zero-run length
    int maxZ = 0;
    for (int v : zrun) if (v > maxZ) maxZ = v;

    // Suffix sums of interior zeros: suffixInner[i] = sum_{k=i}^{m-1} zrun[k]
    vector<int> suffixInner(m + 1);
    suffixInner[m] = 0;
    for (int k = m - 1; k >= 0; --k) {
        suffixInner[k] = suffixInner[k + 1] + zrun[k];
    }

    // Precompute t^2
    vector<int> t2(T_global + 1);
    for (int t = 1; t <= T_global; ++t) t2[t] = t * t;

    long long ans = 0;
    long long T2 = 1LL * T_global * T_global;

    for (int i = 1; i <= m; ++i) { // i: index of first '1' in window (1-based)
        int leftZ = zrun[i - 1];
        int maxInner = suffixInner[i]; // max possible interior zeros for any j >= i
        long long sumBound = (long long)leftZ + maxZ + maxInner;

        int limitT;
        if (T2 <= sumBound) {
            limitT = T_global;
        } else {
            double sd = sqrt((double)sumBound);
            int r = (int)sd;
            while ((long long)(r + 1) * (r + 1) <= sumBound) ++r;
            while ((long long)r * r > sumBound) --r;
            if (r > T_global) r = T_global;
            limitT = r;
        }

        int maxTbyOnes = m - i + 1;
        if (limitT > maxTbyOnes) limitT = maxTbyOnes;
        if (limitT <= 0) continue;

        int curInnerZ = 0; // interior zeros between current i and j
        for (int t = 1; t <= limitT; ++t) {
            int j = i + t - 1; // index of last '1' in window
            if (t > 1) curInnerZ += zrun[j - 1];

            int needSum = t2[t] - curInnerZ; // S = t^2 - innerZeros
            if (needSum < 0) continue;

            int rightZ = zrun[j];
            int sumLR = leftZ + rightZ;
            if (needSum > sumLR) continue;

            int lo = needSum - rightZ;
            if (lo < 0) lo = 0;
            int hi = needSum < leftZ ? needSum : leftZ;
            if (hi >= lo) ans += (long long)(hi - lo + 1);
        }
    }

    cout << ans << '\n';
    return 0;
}