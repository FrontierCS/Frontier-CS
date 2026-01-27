#include <bits/stdc++.h>
using namespace std;

struct Op {
    int op, x, y;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> A(n), B(n);
    for (int i = 0; i < n; ++i) cin >> A[i];
    for (int i = 0; i < n; ++i) cin >> B[i];
    // Read and discard presets (not used)
    for (int p = 0; p < k; ++p) {
        int np, mp;
        cin >> np >> mp;
        string tmp;
        for (int i = 0; i < np; ++i) cin >> tmp;
    }

    // Check multiset equality
    array<int, 256> cntA{}, cntB{};
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            cntA[(unsigned char)A[i][j]]++;
            cntB[(unsigned char)B[i][j]]++;
        }
    }
    for (int c = 0; c < 256; ++c) {
        if (cntA[c] != cntB[c]) {
            cout << -1 << "\n";
            return 0;
        }
    }

    vector<Op> ops;
    auto apply_swap = [&](int op, int x, int y) {
        // x,y are 0-based internally, output 1-based
        ops.push_back({op, x + 1, y + 1});
    };
    auto swap_cells = [&](int x1, int y1, int x2, int y2) {
        // Adjacent cells swap; update A and record op accordingly
        if (x1 == x2 && y1 + 1 == y2) {
            // right neighbor: swap (x1,y1) with (x1,y1+1)
            apply_swap(-1, x1, y1);
        } else if (x1 == x2 && y2 + 1 == y1) {
            // left neighbor
            apply_swap(-2, x1, y1);
        } else if (y1 == y2 && x1 + 1 == x2) {
            // down neighbor
            apply_swap(-4, x1, y1);
        } else if (y1 == y2 && x2 + 1 == x1) {
            // up neighbor
            apply_swap(-3, x1, y1);
        } else {
            // not adjacent - should not happen
            return;
        }
        swap(A[x1][y1], A[x2][y2]);
    };

    // Transform A into B using adjacent swaps
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (A[i][j] == B[i][j]) continue;
            char target = B[i][j];
            int sr = -1, sc = -1;
            // Find target in suffix (row-major), ensuring we don't pick earlier positions
            for (int r = i; r < n; ++r) {
                int cstart = (r == i ? j + 1 : 0);
                for (int c = cstart; c < m; ++c) {
                    if (A[r][c] == target) {
                        sr = r; sc = c;
                        goto found;
                    }
                }
            }
        found:
            if (sr == -1) {
                // Should not happen due to matching counts
                cout << -1 << "\n";
                return 0;
            }
            // Move horizontally to column j if sr > i
            if (sr > i) {
                while (sc > j) {
                    swap_cells(sr, sc, sr, sc - 1);
                    sc--;
                }
                while (sc < j) {
                    swap_cells(sr, sc, sr, sc + 1);
                    sc++;
                }
                // Move up to row i along column j
                while (sr > i) {
                    swap_cells(sr, j, sr - 1, j);
                    sr--;
                }
            } else {
                // sr == i; sc must be > j
                while (sc > j) {
                    swap_cells(sr, sc, sr, sc - 1);
                    sc--;
                }
            }
            // Now A[i][j] == target
        }
    }

    // Output
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.op << " " << op.x << " " << op.y << "\n";
    }
    return 0;
}