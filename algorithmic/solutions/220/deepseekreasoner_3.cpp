#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<vector<int>> cnt(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c;
            cin >> c;
            ++cnt[i][c];
        }
    }

    auto is_solid = [&]() -> bool {
        for (int i = 1; i <= n; ++i) {
            if (cnt[i][i] != n) return false;
            for (int j = 1; j <= n; ++j) {
                if (j != i && cnt[i][j] != 0) return false;
            }
        }
        return true;
    };

    vector<vector<int>> ops;
    int max_ops = n * n - n;

    for (int step = 0; step < max_ops; ++step) {
        if (is_solid()) break;

        vector<int> pass(n + 1);
        for (int i = 1; i <= n; ++i) {
            int chosen = -1;
            // try to pass a card with smallest positive distance
            for (int d = 1; d < n; ++d) {
                int j = (i - 1 + d) % n + 1; // j = i+d mod n (1‑based)
                if (cnt[i][j] > 0) {
                    chosen = j;
                    break;
                }
            }
            if (chosen == -1) {
                // only cards of own number remain
                chosen = i;
            }
            pass[i] = chosen;
        }

        vector<int> cur_op;
        for (int i = 1; i <= n; ++i) {
            cur_op.push_back(pass[i]);
            --cnt[i][pass[i]];
        }
        for (int i = 1; i <= n; ++i) {
            int left = (i == 1 ? n : i - 1);
            ++cnt[i][pass[left]];
        }
        ops.push_back(cur_op);
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << op[i];
        }
        cout << '\n';
    }

    return 0;
}