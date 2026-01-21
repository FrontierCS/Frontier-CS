#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    int x = (n == 1 ? 1 : 2);

    vector<array<int,3>> ops;

    if (n > 1) {
        for (int i = 2; i <= n; ++i) {
            int j = i;
            while (j > 1 && a[j - 1] > a[j]) {
                swap(a[j - 1], a[j]);
                ops.push_back({j - 1, j, 0}); // left shift of length 2 = swap
                --j;
            }
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op[0] << " " << op[1] << " " << op[2] << "\n";
    }

    return 0;
}