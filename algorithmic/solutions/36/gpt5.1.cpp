#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

int64 query(const vector<int64> &a) {
    cout << 0 << " " << a.size();
    for (int64 x : a) cout << " " << x;
    cout << endl << flush;
    int64 c;
    if (!(cin >> c)) exit(0);
    return c;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int K = 1000000;
    vector<int64> a(K);
    for (int i = 0; i < K; ++i) a[i] = i + 1;  // 1..K

    int64 c1 = query(a);
    int64 n;

    if (c1 > 0) {
        int64 k = K;
        n = -1;
        for (int64 q = 1; q * 2 <= k; ++q) {
            int64 num = 2 * (q * k - c1);
            int64 den = q * (q + 1);
            if (num <= 0) continue;
            if (num % den) continue;
            int64 cand = num / den;
            if (cand < 2 || cand > 1000000000LL) continue;
            int64 r = k - q * cand;
            if (r < 0 || r >= cand) continue;
            i128 cc = (i128)q * r + (i128)q * cand * (q - 1) / 2;
            if (cc == c1) {
                n = cand;
                break;
            }
        }
        if (n == -1) n = 2;  // fallback
    } else {
        // c1 == 0: n >= K, possibly n == K or n > K
        vector<int64> b = {1, 1LL + K};
        int64 c2 = query(b);
        if (c2 == 1) {
            n = K;
        } else {
            n = 1000000000LL;  // fallback guess
        }
    }

    cout << 1 << " " << n << endl << flush;
    return 0;
}