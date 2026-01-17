#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    vector<pair<int,int>> ops;

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    // Use x = 3, so allowed lengths are 2 and 4; we only use length 2 (adjacent swaps).
    for (int i = 0; i < n; ++i) {
        int target = i + 1;
        int j = i;
        while (j < n && a[j] != target) ++j;
        while (j > i) {
            swap(a[j], a[j - 1]);
            ops.emplace_back(j, j + 1); // 1-based indices, length = 2
            --j;
        }
    }

    int x = 3;
    cout << x << "\n" << ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}