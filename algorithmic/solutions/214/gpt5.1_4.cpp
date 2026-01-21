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

    if (n == 1) {
        cout << 1 << "\n"; // x
        cout << 0 << "\n"; // m
        return 0;
    }

    int x = 3; // allows length 2 (adjacent swap) and 4

    for (int value = 1; value <= n; ++value) {
        int p = pos[value];
        while (p > value) {
            int leftIdx = p - 1;
            int rightIdx = p;
            int valLeft = a[leftIdx];
            int valRight = a[rightIdx];

            // perform reversal of length 2: swap adjacent
            swap(a[leftIdx], a[rightIdx]);
            pos[valRight] = leftIdx;
            pos[valLeft] = rightIdx;

            ops.emplace_back(leftIdx, rightIdx);

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