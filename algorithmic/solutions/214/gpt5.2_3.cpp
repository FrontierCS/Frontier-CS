#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    int x = (n == 1 || n == 2) ? 1 : 3; // use length 2 only for n=2, length 2/4 for n>=3

    vector<pair<int,int>> ops;
    ops.reserve(200 * max(1, n));

    auto revSeg = [&](int l, int r) {
        ops.push_back({l, r});
        while (l < r) {
            swap(a[l], a[r]);
            pos[a[l]] = l;
            pos[a[r]] = r;
            ++l; --r;
        }
    };

    if (n >= 2) {
        // If x==1, only length 2 is useful; if x==3, length 2 and 4 are useful.
        for (int i = 1; i <= n; i++) {
            int p = pos[i];
            if (x == 3) {
                while (p - i >= 3) {
                    revSeg(p - 3, p); // length 4
                    p -= 3;
                }
            }
            while (p > i) {
                revSeg(p - 1, p); // length 2
                p -= 1;
            }
        }
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) cout << op.first << " " << op.second << "\n";
    return 0;
}