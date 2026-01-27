#include <bits/stdc++.h>
using namespace std;

pair<long long, int> query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    long long x;
    int f;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    if (!(cin >> f)) exit(0);
    if (f == -1) exit(0);
    return {x, f};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> ans(n + 1, 0);

    int i = 1;
    while (i <= n) {
        int L = i;
        int lo = L - 1, hi = n;
        long long val = -1;
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            auto [x, f] = query(L, mid);
            if (f == mid - L + 1) {
                val = x;
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        int R = lo;
        for (int j = L; j <= R; ++j) ans[j] = val;
        i = R + 1;
    }

    cout << "! ";
    for (int j = 1; j <= n; ++j) {
        if (j > 1) cout << ' ';
        cout << ans[j];
    }
    cout << endl;
    cout.flush();

    return 0;
}