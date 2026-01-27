#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<pair<int,int>> ops;

    auto apply = [&](int x, int y) {
        // x, y are lengths; x > 0, y > 0, x + y < n
        int m = n - x - y;
        vector<int> q;
        q.reserve(n);
        // C
        for (int i = n - y; i < n; ++i) q.push_back(p[i]);
        // B
        for (int i = x; i < x + m; ++i) q.push_back(p[i]);
        // A
        for (int i = 0; i < x; ++i) q.push_back(p[i]);
        p.swap(q);
        ops.emplace_back(x, y);
    };

    if (n == 3) {
        vector<int> rev = p;
        reverse(rev.begin(), rev.end());
        if (rev < p) {
            apply(1, 1);
        }
    } else {
        int pos1 = -1;
        for (int i = 0; i < n; ++i) if (p[i] == 1) { pos1 = i + 1; break; } // 1-based
        if (pos1 != 1) {
            if (pos1 >= 3) {
                int x = pos1 - 2;
                int y = n - pos1 + 1;
                if (x > 0 && y > 0 && x + y < n) apply(x, y);
            } else if (pos1 == 2) {
                // First move to position >= 3
                if (n >= 4) {
                    apply(1, 2);
                    // Recompute position of 1
                    for (int i = 0; i < n; ++i) if (p[i] == 1) { pos1 = i + 1; break; }
                    if (pos1 >= 3) {
                        int x = pos1 - 2;
                        int y = n - pos1 + 1;
                        if (x > 0 && y > 0 && x + y < n) apply(x, y);
                    }
                }
            }
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}