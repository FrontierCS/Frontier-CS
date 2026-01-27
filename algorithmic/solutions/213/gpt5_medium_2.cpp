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

    vector<tuple<int,int,int>> ops;

    auto apply_left = [&](int l, int x) {
        int r = l + x - 1;
        ops.emplace_back(l, r, 0);
        int tmp = a[l];
        for (int i = l; i < r; ++i) {
            a[i] = a[i+1];
            pos[a[i]] = i;
        }
        a[r] = tmp;
        pos[tmp] = r;
    };

    auto apply_right = [&](int l, int x) {
        int r = l + x - 1;
        ops.emplace_back(l, r, 1);
        int tmp = a[r];
        for (int i = r; i > l; --i) {
            a[i] = a[i-1];
            pos[a[i]] = i;
        }
        a[l] = tmp;
        pos[tmp] = l;
    };

    int x;
    if (n == 1) x = 1;
    else if (n == 2) x = 2;
    else x = min(n - 1, max(2, (int)floor(sqrt((double)n)) + 1));

    if (n == 1) {
        cout << x << "\n";
        cout << 0 << "\n";
        return 0;
    }

    if (n == 2) {
        if (a[1] == 1 && a[2] == 2) {
            cout << x << "\n";
            cout << 0 << "\n";
        } else {
            cout << x << "\n";
            cout << 1 << "\n";
            cout << 1 << " " << 2 << " " << 0 << "\n";
        }
        return 0;
    }

    // Stage 1: Fix positions 1..(n - x - 1)
    int lastStage1 = n - x - 1;
    for (int i = 1; i <= lastStage1; ++i) {
        // Move value i to position i
        while (pos[i] - x >= i) {
            int l1 = pos[i] - x + 1;
            apply_right(l1, x);      // pos[i] -> l1
            apply_left(l1 - 1, x);   // pos[i] -> l1 - 1
        }
        while (pos[i] > i) {
            apply_left(i, x); // shift within [i, i+x-1]
        }
    }

    // Stage 2: Sort block [L..n] where L = n - x
    int L = n - x;
    // Insertion sort within block using only windows W1=[L, L+x-1], W2=[L+1, L+x]
    for (int val = L; val <= n; ++val) {
        while (pos[val] > val) {
            int off = pos[val] - L; // 0..x
            if (off == x) {
                // Use W2 left: [L+1, L+x]
                apply_left(L + 1, x);
            } else {
                // Use W1 left: [L, L+x-1]
                apply_left(L, x);
            }
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &t : ops) {
        int l, r, d;
        tie(l, r, d) = t;
        cout << l << " " << r << " " << d << "\n";
    }
    return 0;
}