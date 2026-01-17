#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<pair<int,int>> ops;

    if (n <= 3) {
        int x = 1; // allowed length: 2
        vector<int> pos(n + 1);
        for (int i = 1; i <= n; ++i) pos[a[i]] = i;

        auto apply_rev = [&](int l, int r) {
            ops.emplace_back(l, r);
            while (l < r) {
                swap(a[l], a[r]);
                pos[a[l]] = l;
                pos[a[r]] = r;
                ++l; --r;
            }
        };

        // Simple bubble sort using length-2 reversals
        for (int i = 1; i <= n; ++i) {
            for (int j = n; j > i; --j) {
                if (a[j - 1] > a[j]) apply_rev(j - 1, j);
            }
        }

        cout << x << "\n" << ops.size() << "\n";
        for (auto &op : ops) cout << op.first << " " << op.second << "\n";
        return 0;
    }

    // n >= 4
    int x = 3; // allowed lengths: 2 and 4
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    auto apply_rev = [&](int l, int r) {
        ops.emplace_back(l, r);
        while (l < r) {
            swap(a[l], a[r]);
            pos[a[l]] = l;
            pos[a[r]] = r;
            ++l; --r;
        }
    };

    // Fix positions 1..n-3
    for (int i = 1; i <= n - 3; ++i) {
        int p = pos[i];
        // Move value i left by 3 positions at a time using length-4 reversals
        while (p - i >= 3) {
            int l = p - 3, r = p; // segment length 4, entirely in [i..n]
            apply_rev(l, r);
            p = pos[i];
        }
        // Now p - i is 0, 1, or 2
        if (p == i) continue;
        else if (p == i + 1) {
            // One adjacent swap (length 2)
            apply_rev(i, i + 1);
        } else if (p == i + 2) {
            // Use one length-4 then one length-2 to place i
            apply_rev(i, i + 3);
            apply_rev(i, i + 1);
        }
    }

    // Bubble sort the last 3 elements using length-2 reversals
    for (int i = n - 2; i <= n - 1; ++i) {
        for (int j = n; j > i; --j) {
            if (a[j - 1] > a[j]) apply_rev(j - 1, j);
        }
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) cout << op.first << " " << op.second << "\n";

    return 0;
}