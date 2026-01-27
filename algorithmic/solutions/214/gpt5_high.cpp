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
    auto do_rev = [&](int l, int r) {
        if (l < 1 || r > n || l >= r) return;
        ops.emplace_back(l, r);
        while (l < r) {
            int u = a[l], v = a[r];
            swap(a[l], a[r]);
            pos[u] = r;
            pos[v] = l;
            ++l; --r;
        }
    };
    
    // Use x = 3, allowed lengths are 2 and 4
    int x = 3;
    
    // Place first n-4 elements using length 4 operations (and only touch indices >= i)
    if (n >= 5) {
        for (int i = 1; i <= n - 4; ++i) {
            int p = pos[i];
            while (p - i >= 3) {
                do_rev(p - 3, p); // move target left by 3
                p = pos[i];
            }
            p = pos[i];
            int delta = p - i;
            if (delta == 2) {
                // +1 then -3
                do_rev(i + 1, i + 4);
                do_rev(i, i + 3);
            } else if (delta == 1) {
                // +1, +1, -3
                do_rev(i, i + 3);
                do_rev(i + 1, i + 4);
                do_rev(i, i + 3);
            }
            // delta == 0: nothing
        }
    }
    
    // Finish the last up to 4 elements using length 2 operations (adjacent swaps)
    int start = max(1, n - 3);
    for (int i = start; i <= n; ++i) {
        int p = pos[i];
        while (p > i) {
            do_rev(p - 1, p);
            --p;
        }
    }
    
    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}