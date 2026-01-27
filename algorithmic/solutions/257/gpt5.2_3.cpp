#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> known(n + 2, LLONG_MIN);
    vector<long long> ans(n + 1, 0);

    auto query = [&](int l, int r) -> pair<long long, long long> {
        cout << "? " << l << " " << r << '\n';
        cout.flush();

        long long x;
        if (!(cin >> x)) die();
        if (x == -1) die();
        long long f;
        if (!(cin >> f)) die();
        return {x, f};
    };

    function<long long(int)> getValue = [&](int idx) -> long long {
        if (known[idx] != LLONG_MIN) return known[idx];
        auto [x, f] = query(idx, idx);
        known[idx] = x;
        return x;
    };

    function<int(int, long long)> findEnd = [&](int s, long long v) -> int {
        int lo = s;
        long long step = 1;
        int hi = n + 1;

        while (true) {
            long long idxll = (long long)s + step;
            if (idxll > n) {
                hi = n + 1;
                break;
            }
            int idx = (int)idxll;
            long long vv = getValue(idx);
            if (vv == v) {
                lo = idx;
                step <<= 1;
            } else {
                hi = idx;
                break;
            }
        }

        if (hi == n + 1) return n;

        int L = lo + 1, R = hi - 1;
        int res = lo;
        while (L <= R) {
            int mid = L + (R - L) / 2;
            long long vv = getValue(mid);
            if (vv == v) {
                res = mid;
                L = mid + 1;
            } else {
                R = mid - 1;
            }
        }
        return res;
    };

    int pos = 1;
    while (pos <= n) {
        long long v = getValue(pos);
        int end = findEnd(pos, v);
        for (int i = pos; i <= end; i++) ans[i] = v;
        pos = end + 1;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << ' ' << ans[i];
    cout << '\n';
    cout.flush();
    return 0;
}