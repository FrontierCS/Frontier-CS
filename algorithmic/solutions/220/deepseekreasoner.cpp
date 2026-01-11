#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> cnt(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c;
            cin >> c;
            cnt[i][c]++;
        }
    }
    // check if already solid
    bool solid = true;
    for (int i = 1; i <= n; ++i) {
        if (cnt[i][i] != n) {
            solid = false;
            break;
        }
        for (int j = 1; j <= n; ++j) {
            if (j != i && cnt[i][j] != 0) {
                solid = false;
                break;
            }
        }
        if (!solid) break;
    }
    if (solid) {
        cout << 0 << endl;
        return 0;
    }
    vector<vector<int>> ops;
    int max_ops = n * (n - 1);
    for (int t = 0; t < max_ops; ++t) {
        vector<int> pass(n + 1);
        // decide which card each player passes
        for (int i = 1; i <= n; ++i) {
            int r = (i - t) % n;
            if (r <= 0) r += n;   // r in [1, n]
            if (r != i && cnt[i][r] > 0) {
                pass[i] = r;
            } else {
                int chosen = -1;
                for (int j = 1; j <= n; ++j) {
                    if (j != i && cnt[i][j] > 0) {
                        chosen = j;
                        break;
                    }
                }
                if (chosen == -1) chosen = i;
                pass[i] = chosen;
            }
        }
        ops.push_back(vector<int>(pass.begin() + 1, pass.end()));
        // apply the operation: first remove passed cards
        for (int i = 1; i <= n; ++i) {
            cnt[i][pass[i]]--;
        }
        // then add received cards (from left neighbor)
        vector<int> receive(n + 1);
        for (int i = 1; i <= n; ++i) {
            int left = (i == 1) ? n : i - 1;
            receive[i] = pass[left];
        }
        for (int i = 1; i <= n; ++i) {
            cnt[i][receive[i]]++;
        }
        // check if all players are now solid
        solid = true;
        for (int i = 1; i <= n; ++i) {
            if (cnt[i][i] != n) {
                solid = false;
                break;
            }
            for (int j = 1; j <= n; ++j) {
                if (j != i && cnt[i][j] != 0) {
                    solid = false;
                    break;
                }
            }
            if (!solid) break;
        }
        if (solid) break;
    }
    cout << ops.size() << endl;
    for (auto& op : ops) {
        for (int j = 0; j < n; ++j) {
            cout << op[j] << (j + 1 == n ? '\n' : ' ');
        }
    }
    return 0;
}