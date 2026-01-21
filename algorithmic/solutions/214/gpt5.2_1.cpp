#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    int x = (n <= 2 ? 1 : 3); // x=3 => lengths 2 and 4; x=1 => length 2 only
    vector<pair<int,int>> ops;
    ops.reserve(200000);

    auto do_rev = [&](int l, int r) {
        while (l < r) {
            int vl = a[l], vr = a[r];
            swap(a[l], a[r]);
            pos[vl] = r;
            pos[vr] = l;
            l++; r--;
        }
    };

    if (x == 1) {
        // Only n<=2 here; adjacent swaps suffice.
        for (int i = 1; i <= n; i++) {
            while (pos[i] > i) {
                int p = pos[i];
                ops.push_back({p - 1, p});
                do_rev(p - 1, p);
            }
        }
    } else {
        // x==3: allowed lengths 2 and 4
        for (int i = 1; i <= n; i++) {
            while (pos[i] >= i + 3) {
                int p = pos[i];
                ops.push_back({p - 3, p}); // length 4
                do_rev(p - 3, p);
            }
            while (pos[i] > i) {
                int p = pos[i];
                ops.push_back({p - 1, p}); // length 2
                do_rev(p - 1, p);
            }
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &pr : ops) {
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}