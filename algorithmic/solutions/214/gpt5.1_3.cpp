#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    vector<pair<int,int>> ops;

    if (n <= 3) {
        int x = 1; // allowed lengths: 0 and 2; we use 2 only
        auto apply = [&](int l, int r) {
            reverse(a.begin() + l, a.begin() + r + 1);
            ops.push_back({l, r});
        };
        // Bubble sort with adjacent swaps (length 2)
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= n - i; j++) {
                if (a[j] > a[j + 1]) {
                    apply(j, j + 1);
                }
            }
        }
        cout << x << "\n" << ops.size() << "\n";
        for (auto &op : ops) {
            cout << op.first << " " << op.second << "\n";
        }
        return 0;
    }

    // n >= 4
    int x = 3; // allowed lengths: 2 and 4
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; i++) pos[a[i]] = i;

    auto apply = [&](int l, int r) {
        reverse(a.begin() + l, a.begin() + r + 1);
        for (int i = l; i <= r; i++) pos[a[i]] = i;
        ops.push_back({l, r});
    };

    // Fix positions 1..n-3
    for (int i = 1; i <= n - 3; i++) {
        int v = i;
        int p = pos[v];
        // Move v left in jumps of 3 positions using length-4 reversals
        while (p >= i + 3) {
            apply(p - 3, p); // length 4
            p -= 3;
        }
        // Now p is i, i+1, or i+2
        if (p == i) {
            continue;
        } else if (p == i + 1) {
            apply(i, i + 1); // length 2
        } else if (p == i + 2) {
            apply(i, i + 3); // length 4, moves v to i+1
            apply(i, i + 1); // length 2, moves v to i
        }
    }

    // Sort last three elements using adjacent swaps (length 2)
    for (int pass = 0; pass < 2; pass++) {
        for (int j = n - 2; j <= n - 1; j++) {
            if (a[j] > a[j + 1]) {
                apply(j, j + 1);
            }
        }
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}