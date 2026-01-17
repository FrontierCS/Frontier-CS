#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<Op> ops;
    ops.reserve(n * n / 2);

    int x = 2; // segment length

    // Insertion sort using adjacent swaps (len=2 rotations)
    for (int i = 2; i <= n; ++i) {
        int j = i;
        while (j > 1 && a[j - 1] > a[j]) {
            swap(a[j - 1], a[j]);
            ops.push_back({j - 1, j, 0}); // 0 = left shift, same as swap for length 2
            --j;
        }
    }

    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }

    return 0;
}