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
            ++cnt[i][c];
        }
    }

    // check if already solid
    bool solid = true;
    for (int i = 1; i <= n; ++i) {
        if (cnt[i][i] != n) {
            solid = false;
            break;
        }
    }
    if (solid) {
        cout << 0 << endl;
        return 0;
    }

    int limit = n * n - n;
    vector<vector<int>> operations;

    for (int step = 0; step < limit; ++step) {
        vector<int> pass(n + 1);
        // decide which card each player passes
        for (int i = 1; i <= n; ++i) {
            int nxt = (i % n) + 1;
            if (cnt[i][nxt] > 0) {
                pass[i] = nxt;
            } else {
                int other = -1;
                for (int j = 1; j <= n; ++j) {
                    if (j != i && cnt[i][j] > 0) {
                        other = j;
                        break;
                    }
                }
                if (other == -1) {
                    pass[i] = i;  // all cards are i
                } else {
                    pass[i] = other;
                }
            }
        }

        // apply the passes simultaneously
        vector<int> recv(n + 1);
        for (int i = 1; i <= n; ++i) {
            int left = (i == 1) ? n : i - 1;
            recv[i] = pass[left];
        }
        for (int i = 1; i <= n; ++i) {
            --cnt[i][pass[i]];
            ++cnt[i][recv[i]];
        }
        operations.push_back(pass);

        // check if solid now
        solid = true;
        for (int i = 1; i <= n; ++i) {
            if (cnt[i][i] != n) {
                solid = false;
                break;
            }
        }
        if (solid) break;
    }

    cout << operations.size() << endl;
    for (auto &op : operations) {
        for (int i = 1; i <= n; ++i) {
            cout << op[i] << " ";
        }
        cout << endl;
    }

    return 0;
}