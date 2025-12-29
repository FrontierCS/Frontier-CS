#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string line;
    if (!getline(cin, line)) return 0;
    while(line.size() == 0 && getline(cin, line)) {}
    if(line.size() == 0) return 0;
    stringstream ss(line);
    int n, m, k;
    ss >> n >> m >> k;

    vector<string> A(n), B(n);
    for (int i = 0; i < n; ++i) {
        getline(cin, A[i]);
        if (A[i].empty()) { --i; continue; }
    }

    // Skip blank line before target
    while (getline(cin, line)) {
        if (!line.empty()) {
            B[0] = line;
            break;
        }
    }
    for (int i = 1; i < n; ++i) {
        getline(cin, B[i]);
        if (B[i].empty()) { --i; continue; }
    }

    int fullPresetIdx = -1;

    for (int p = 1; p <= k; ++p) {
        // Skip blank line before preset
        while (getline(cin, line)) {
            if (!line.empty()) break;
        }
        if(line.empty()) { // in case of EOF or multiple blanks
            if(!getline(cin, line)) break;
        }
        stringstream ssp(line);
        int np, mp;
        ssp >> np >> mp;
        vector<string> F(np);
        for (int i = 0; i < np; ++i) {
            getline(cin, F[i]);
            if (F[i].empty()) { --i; continue; }
        }
        if (np == n && mp == m) {
            bool same = true;
            for (int i = 0; i < n && same; ++i)
                if (F[i] != B[i]) same = false;
            if (same && fullPresetIdx == -1) fullPresetIdx = p;
        }
    }

    // Count characters
    vector<int> cntA(256, 0), cntB(256, 0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            cntA[(unsigned char)A[i][j]]++, cntB[(unsigned char)B[i][j]]++;

    bool equal = true;
    for (int c = 0; c < 256; ++c)
        if (cntA[c] != cntB[c]) { equal = false; break; }

    if (!equal) {
        if (fullPresetIdx != -1) {
            cout << 1 << '\n';
            cout << fullPresetIdx << " 1 1\n";
        } else {
            cout << -1 << '\n';
        }
        return 0;
    }

    // Use only adjacent swaps to permute A into B
    vector<tuple<int,int,int>> ops;
    auto addOp = [&](int op, int x, int y) {
        ops.emplace_back(op, x, y);
    };

    vector<string> cur = A;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (i == n - 1 && j == m - 1) break; // last cell auto-correct
            if (cur[i][j] == B[i][j]) continue;
            char want = B[i][j];
            int bi = -1, bj = -1;
            for (int ii = i; ii < n && bi == -1; ++ii) {
                int sj = (ii == i ? j : 0);
                for (int jj = sj; jj < m; ++jj) {
                    if (cur[ii][jj] == want) {
                        bi = ii; bj = jj;
                        break;
                    }
                }
            }
            if (bi == -1) {
                cout << -1 << '\n';
                return 0;
            }
            int r = bi, c = bj;
            if (r == i) {
                while (c > j) {
                    // move left: swap (r,c) with (r,c-1) => op -2 at (r,c)
                    addOp(-2, r + 1, c + 1);
                    swap(cur[r][c], cur[r][c - 1]);
                    --c;
                }
            } else {
                if (c < j) {
                    while (c < j) {
                        // move right: swap (r,c) with (r,c+1) => op -1 at (r,c)
                        addOp(-1, r + 1, c + 1);
                        swap(cur[r][c], cur[r][c + 1]);
                        ++c;
                    }
                    while (r > i) {
                        // move up: swap (r,c) with (r-1,c) => op -3 at (r,c)
                        addOp(-3, r + 1, c + 1);
                        swap(cur[r][c], cur[r - 1][c]);
                        --r;
                    }
                } else { // c >= j
                    while (r > i) {
                        addOp(-3, r + 1, c + 1);
                        swap(cur[r][c], cur[r - 1][c]);
                        --r;
                    }
                    while (c > j) {
                        addOp(-2, r + 1, c + 1);
                        swap(cur[r][c], cur[r][c - 1]);
                        --c;
                    }
                }
            }
        }
    }

    // Verify final grid equals target (sanity check)
    if (cur != B) {
        cout << -1 << '\n';
        return 0;
    }

    if ((int)ops.size() > 400000) {
        cout << -1 << '\n';
        return 0;
    }

    cout << ops.size() << '\n';
    for (auto &t : ops) {
        int op, x, y;
        tie(op, x, y) = t;
        cout << op << ' ' << x << ' ' << y << '\n';
    }
    return 0;
}