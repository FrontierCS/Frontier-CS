#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<pair<int,int>> ops;
    ops.reserve(300000);

    auto rev = [&](int l, int r) {
        // assume r-l+1 is 2 or 4
        ops.emplace_back(l, r);
        while (l < r) {
            swap(a[l], a[r]);
            l++; r--;
        }
        // update pos for affected elements
        // l and r were moved; better to recompute for the segment
        // Reconstruct bounds from the stored operation:
        auto [L, R] = ops.back();
        for (int i = L; i <= R; ++i) pos[a[i]] = i;
    };

    // Choose x = 3 -> allowed lengths 2 and 4
    int x = 3;

    for (int i = 1; i <= n; ++i) {
        int v = i;
        while (pos[v] - i >= 3) {
            int p = pos[v];
            rev(p - 3, p); // length 4 reversal moves v left by 3
        }
        int d = pos[v] - i;
        if (d == 2) {
            rev(i + 1, i + 2); // swap positions i+1 and i+2
            rev(i, i + 1);     // swap positions i and i+1
        } else if (d == 1) {
            rev(i, i + 1);     // swap positions i and i+1
        }
        // now a[i] == i
    }

    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}