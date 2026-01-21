#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<vector<int>> a(n, vector<int>(n));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> a[i][j];

    auto allSolid = [&]() -> bool {
        for (int i = 0; i < n; ++i) {
            for (int x : a[i]) {
                if (x != i + 1) return false;
            }
        }
        return true;
    };

    vector<vector<int>> ops;
    int maxOps = n * (n - 1);

    while (!allSolid() && (int)ops.size() < maxOps) {
        vector<int> move(n);
        // choose card from each player
        for (int i = 0; i < n; ++i) {
            int bestIdx = -1;
            int bestDelta = -1;
            for (int idx = 0; idx < (int)a[i].size(); ++idx) {
                int val = a[i][idx];
                int delta = (val - (i + 1) + n) % n;
                if (delta == 0) continue;  // already correct, prefer wrong cards
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestIdx = idx;
                }
            }
            if (bestIdx == -1) bestIdx = 0; // all correct, must move something
            move[i] = a[i][bestIdx];
            a[i].erase(a[i].begin() + bestIdx);
        }
        // perform simultaneous pass
        vector<int> recv(n);
        for (int i = 0; i < n; ++i)
            recv[(i + 1) % n] = move[i];
        for (int i = 0; i < n; ++i)
            a[i].push_back(recv[i]);
        ops.push_back(move);
    }

    // If still not solid (unlikely with this heuristic), fill remaining operations with arbitrary valid moves
    while (!allSolid() && (int)ops.size() < maxOps) {
        vector<int> move(n);
        for (int i = 0; i < n; ++i) {
            // just move first card
            move[i] = a[i][0];
            a[i].erase(a[i].begin());
        }
        vector<int> recv(n);
        for (int i = 0; i < n; ++i)
            recv[(i + 1) % n] = move[i];
        for (int i = 0; i < n; ++i)
            a[i].push_back(recv[i]);
        ops.push_back(move);
    }

    cout << ops.size() << '\n';
    for (auto &v : ops) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << v[i];
        }
        cout << '\n';
    }

    return 0;
}