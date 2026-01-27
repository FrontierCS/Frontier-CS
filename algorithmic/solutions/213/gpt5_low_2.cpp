#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    int x;
    if (n == 1) {
        x = 1;
        cout << x << " " << 0 << "\n";
        return 0;
    } else {
        x = min(n, 50);
        if (x % 2 == 1) {
            if (x > 2) x--;
            else x = 2;
        }
        if (x > n) x = (n % 2 == 0 ? n : n-1);
        if (x < 2) x = 2;
        if (x > n) x = n; // in case n==2
        if (x % 2 == 1 && x > 2) x--; // ensure even if possible
        if (x % 2 == 1 && x == n && n >= 2) x = n-1; // ensure even <= n
        if (x < 2) x = 2;
    }

    struct Op { int l, r, d; };
    vector<Op> ops;

    auto apply_left = [&](int l, int r) {
        int tmp = a[l];
        for (int k = l; k < r; ++k) {
            a[k] = a[k+1];
            pos[a[k]] = k;
        }
        a[r] = tmp;
        pos[tmp] = r;
        ops.push_back({l, r, 0});
    };
    auto apply_right = [&](int l, int r) {
        int tmp = a[r];
        for (int k = r; k > l; --k) {
            a[k] = a[k-1];
            pos[a[k]] = k;
        }
        a[l] = tmp;
        pos[tmp] = l;
        ops.push_back({l, r, 1});
    };

    for (int i = 1; i <= n; ++i) {
        int p = pos[i];
        // Move left in big jumps
        while (p - i >= x - 1) {
            int l = p - x + 1;
            int r = p;
            apply_right(l, r);
            p -= (x - 1);
        }
        // Move right in big jumps
        while (i - p >= x - 1) {
            int l = p;
            int r = p + x - 1;
            apply_left(l, r);
            p += (x - 1);
        }
        // Residual move
        if (p > i) {
            int s = p - i;
            int L = max(1, p - x + 1);
            int R = L + x - 1;
            for (int t = 0; t < s; ++t) {
                apply_left(L, R);
                p--;
            }
        } else if (p < i) {
            int s = i - p;
            int R = min(n, p + x - 1);
            int L = R - x + 1;
            for (int t = 0; t < s; ++t) {
                apply_right(L, R);
                p++;
            }
        }
        // Now pos[i] should be i
    }

    cout << x << " " << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }
    return 0;
}