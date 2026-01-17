#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<pair<int,int>> ops;

    auto apply_reverse = [&](int L, int R) {
        ops.push_back({L, R});
        int l = L, r = R;
        while (l < r) {
            swap(a[l], a[r]);
            l++; r--;
        }
        for (int i = L; i <= R; i++) pos[a[i]] = i;
    };

    int x;
    if (n <= 3) {
        x = 1; // only length 2
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j + 1 <= n; j++) {
                if (a[j] > a[j + 1]) apply_reverse(j, j + 1);
            }
        }
    } else {
        x = 3; // lengths 2 and 4
        for (int i = 1; i <= n; i++) {
            while (pos[i] > i) {
                int p = pos[i];
                int d = p - i;
                if (d >= 3) {
                    apply_reverse(p - 3, p); // length 4
                } else if (d == 2) {
                    apply_reverse(p - 1, p);     // length 2
                    apply_reverse(p - 2, p - 1); // length 2
                } else { // d == 1
                    apply_reverse(p - 1, p); // length 2
                }
            }
        }
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) cout << op.first << " " << op.second << "\n";
    return 0;
}