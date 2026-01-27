#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> S(n), T(n);
    for (int i = 0; i < n; ++i) cin >> S[i];
    for (int i = 0; i < n; ++i) cin >> T[i];
    // Read presets but ignore content
    for (int t = 0; t < k; ++t) {
        int np, mp;
        cin >> np >> mp;
        string tmp;
        for (int i = 0; i < np; ++i) cin >> tmp;
    }

    // Check counts
    vector<int> cntS(256, 0), cntT(256, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            cntS[(unsigned char)S[i][j]]++;
            cntT[(unsigned char)T[i][j]]++;
        }
    }
    for (int c = 0; c < 256; ++c) {
        if (cntS[c] != cntT[c]) {
            cout << -1 << "\n";
            return 0;
        }
    }

    vector<array<int,3>> ops;
    auto add_op = [&](int op, int x, int y) {
        // x,y are 0-based; convert to 1-based for output
        ops.push_back({op, x + 1, y + 1});
    };
    auto swap_cells = [&](int x1, int y1, int x2, int y2) {
        // assume adjacent
        if (x1 == x2) {
            if (y2 == y1 + 1) {
                // swap right neighbor
                add_op(-1, x1, y1);
            } else if (y2 + 1 == y1) {
                // swap left neighbor
                add_op(-2, x1, y1);
            } else {
                // not adjacent horizontally
                return;
            }
        } else if (y1 == y2) {
            if (x2 == x1 + 1) {
                // swap down
                add_op(-4, x1, y1);
            } else if (x2 + 1 == x1) {
                // swap up
                add_op(-3, x1, y1);
            } else {
                // not adjacent vertically
                return;
            }
        } else {
            return;
        }
        swap(S[x1][y1], S[x2][y2]);
    };

    auto move_left = [&](int &r, int &c) {
        swap_cells(r, c, r, c - 1);
        --c;
    };
    auto move_right = [&](int &r, int &c) {
        swap_cells(r, c, r, c + 1);
        ++c;
    };
    auto move_up = [&](int &r, int &c) {
        swap_cells(r, c, r - 1, c);
        --r;
    };

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (S[i][j] == T[i][j]) continue;
            char need = T[i][j];
            int rr = -1, cc = -1;
            // search in allowed region: (i, j+1..m-1), then rows i+1..n-1 any col
            for (int r = i; r < n && rr == -1; ++r) {
                int cstart = (r == i ? j + 1 : 0);
                for (int c = cstart; c < m; ++c) {
                    if (S[r][c] == need) {
                        rr = r; cc = c;
                        break;
                    }
                }
            }
            if (rr == -1) {
                // Should not happen if counts match and prior positions are correct
                cout << -1 << "\n";
                return 0;
            }
            // Move horizontally in row rr to column j
            while (cc > j) {
                move_left(rr, cc);
                if (ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            while (cc < j) {
                // Only allowed if rr > i; if rr == i, this would cross fixed cells
                if (rr == i) { cout << -1 << "\n"; return 0; }
                move_right(rr, cc);
                if (ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            // Move up to row i
            while (rr > i) {
                move_up(rr, cc);
                if (ops.size() > 400000) { cout << -1 << "\n"; return 0; }
            }
            // Now S[i][j] == need
        }
    }

    if (ops.size() > 400000) {
        cout << -1 << "\n";
        return 0;
    }
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op[0] << " " << op[1] << " " << op[2] << "\n";
    }
    return 0;
}