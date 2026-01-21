#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    int x = 3; // allows segment lengths 2 and 4; we'll use length 2 (adjacent swaps)

    vector<pair<int,int>> ops;

    // Bubble sort using adjacent swaps (reversal of length 2)
    for (int i = 1; i <= n; ++i) {
        bool changed = false;
        for (int j = n - 1; j >= i; --j) {
            if (a[j] > a[j + 1]) {
                swap(a[j], a[j + 1]);
                ops.emplace_back(j, j + 1);
                changed = true;
            }
        }
        if (!changed) break;
    }

    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}