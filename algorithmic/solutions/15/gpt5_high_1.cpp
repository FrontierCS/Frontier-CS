#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    int pos1 = -1;
    for (int i = 0; i < n; ++i) if (p[i] == 1) { pos1 = i + 1; break; }

    vector<pair<int,int>> ops;

    if (pos1 == 1) {
        // Do nothing
    } else if (pos1 >= 3) {
        int x = 1;
        int y = n - pos1 + 1;
        if (y > 0 && x + y < n) ops.emplace_back(x, y);
    } else if (pos1 == 2) {
        if (n >= 4) {
            // Two-step to bring 1 to front
            if (2 + 1 < n) ops.emplace_back(2, 1);
            if (1 + 1 < n) ops.emplace_back(1, 1);
        } else if (n == 3) {
            // For n=3, only (1,1) is allowed; use it if it improves
            // Compare original vs operation result
            vector<int> q = {p[2], p[1], p[0]}; // result of (1,1)
            if (q < p) ops.emplace_back(1, 1);
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) cout << op.first << " " << op.second << "\n";
    return 0;
}