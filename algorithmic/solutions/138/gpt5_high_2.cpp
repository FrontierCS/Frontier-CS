#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> s(n), t(n);
    for (int i = 0; i < n; ++i) cin >> s[i];
    for (int i = 0; i < n; ++i) cin >> t[i];
    // Read and ignore presets
    for (int p = 0; p < k; ++p) {
        int np, mp;
        cin >> np >> mp;
        string row;
        for (int i = 0; i < np; ++i) cin >> row;
    }

    // Check if solvable by comparing counts
    vector<int> cntS(256, 0), cntT(256, 0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            cntS[(unsigned char)s[i][j]]++;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            cntT[(unsigned char)t[i][j]]++;

    if (cntS != cntT) {
        cout << -1 << "\n";
        return 0;
    }

    struct Op { int op, x, y; };
    vector<Op> ops;
    ops.reserve(200000);

    auto push_op = [&](int op, int x, int y) {
        ops.push_back({op, x, y});
        if ((int)ops.size() > 400000) {
            cout << -1 << "\n";
            exit(0);
        }
    };

    auto moveRight = [&](int &x, int &y) {
        // swap (x,y) with (x,y+1): op -1 x y, 1-based
        push_op(-1, x + 1, y + 1);
        swap(s[x][y], s[x][y+1]);
        y++;
    };
    auto moveLeft = [&](int &x, int &y) {
        // swap (x,y) with (x,y-1): op -2 x y, 1-based
        push_op(-2, x + 1, y + 1);
        swap(s[x][y], s[x][y-1]);
        y--;
    };
    auto moveUp = [&](int &x, int &y) {
        // swap (x,y) with (x-1,y): op -3 x y, 1-based
        push_op(-3, x + 1, y + 1);
        swap(s[x][y], s[x-1][y]);
        x--;
    };

    for (int idx = 0; idx < n * m; ++idx) {
        int cr = idx / m, cc = idx % m;
        if (s[cr][cc] == t[cr][cc]) continue;

        // Find matching character in the suffix (r > cr or r == cr and c >= cc)
        char need = t[cr][cc];
        int sr = -1, sc = -1;
        bool found = false;
        for (int r = cr; r < n && !found; ++r) {
            int startC = (r == cr ? cc : 0);
            for (int c = startC; c < m; ++c) {
                if (r == cr && c == cc) continue;
                if (s[r][c] == need) {
                    sr = r; sc = c;
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            // Should not happen due to counts, but guard anyway
            cout << -1 << "\n";
            return 0;
        }

        // Move token from (sr, sc) to (cr, cc) using path: right (if sc<cc), up, left
        while (sc < cc) moveRight(sr, sc);
        while (sr > cr) moveUp(sr, sc);
        while (sc > cc) moveLeft(sr, sc);

        // Now s[cr][cc] must be equal to need
        // assert(s[cr][cc] == need);
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.op << " " << op.x << " " << op.y << "\n";
    }
    return 0;
}