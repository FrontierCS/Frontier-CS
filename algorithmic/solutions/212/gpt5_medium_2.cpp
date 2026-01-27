#include <bits/stdc++.h>
using namespace std;

int n, m, Lc, Rc, Sx, Sy, Lq;
long long sParam;

bool inRange(int x, int y) {
    return 1 <= x && x <= n && 1 <= y && y <= m;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> m >> Lc >> Rc >> Sx >> Sy >> Lq >> sParam)) {
        return 0;
    }
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    // Basic validity checks
    if (Sy != Lc) {
        cout << "NO\n";
        return 0;
    }
    vector<int> posInQ(n + 1, -1);
    for (int i = 0; i < Lq; ++i) {
        if (q[i] < 1 || q[i] > n) {
            cout << "NO\n";
            return 0;
        }
        posInQ[q[i]] = i;
    }
    if (posInQ[Sx] != -1 && q[0] != Sx) {
        cout << "NO\n";
        return 0;
    }

    auto respects_q = [&](const vector<int>& order) -> bool {
        vector<int> filtered;
        filtered.reserve(Lq);
        for (int r : order) {
            if (posInQ[r] != -1) filtered.push_back(r);
        }
        if ((int)filtered.size() != Lq) return false;
        for (int i = 0; i < Lq; ++i) if (filtered[i] != q[i]) return false;
        return true;
    };

    auto build_order = [&](bool upFirst) -> vector<int> {
        vector<int> ord;
        ord.reserve(n);
        if (!upFirst) { // down then up
            for (int i = Sx; i <= n; ++i) ord.push_back(i);
            for (int i = 1; i <= Sx - 1; ++i) ord.push_back(i);
        } else { // up then down
            for (int i = Sx; i >= 1; --i) ord.push_back(i);
            for (int i = n; i >= Sx + 1; --i) ord.push_back(i);
        }
        return ord;
    };

    auto try_construct = [&](bool upFirst, vector<pair<int,int>>& outPath) -> bool {
        outPath.clear();
        vector<vector<char>> vis(n + 1, vector<char>(m + 1, 0));
        auto push = [&](int x, int y)->bool{
            if (!inRange(x,y)) return false;
            if (vis[x][y]) return false;
            vis[x][y] = 1;
            outPath.emplace_back(x,y);
            return true;
        };
        auto process_row = [&](int row, int start_col, int& end_col)->bool{
            if (start_col != Lc && start_col != Rc) return false;
            if (!inRange(row, start_col)) return false;
            // We assume current position is already at (row, start_col)
            if (start_col == Lc) {
                for (int y = Lc + 1; y <= Rc; ++y) {
                    if (!push(row, y)) return false;
                }
                end_col = Rc;
            } else {
                for (int y = Rc - 1; y >= Lc; --y) {
                    if (!push(row, y)) return false;
                }
                end_col = Lc;
            }
            return true;
        };

        // Initial position
        if (!push(Sx, Lc)) return false;

        int dir1 = upFirst ? -1 : +1;
        int bound1 = upFirst ? 1 : n;

        int curRow = Sx;
        int curCol = Lc;
        int endCol = curCol;

        // Phase 1
        while (true) {
            if (!process_row(curRow, curCol, endCol)) return false;
            if (curRow == bound1) break;
            int nextRow = curRow + dir1;
            if (!push(nextRow, endCol)) return false; // move vertically inside segment to next row
            curRow = nextRow;
            curCol = endCol;
        }

        bool remain = upFirst ? (Sx < n) : (Sx > 1);
        if (!remain) {
            return true; // all rows processed in one phase
        }

        // Need corridor to switch sides
        if (endCol == Rc && Rc == m) return false;
        if (endCol == Lc && Lc == 1) return false;

        int outsideCol = (endCol == Rc) ? Rc + 1 : Lc - 1;
        int targetRow = upFirst ? n : 1;

        // Step to outside
        if (!push(curRow, outsideCol)) return false;

        // Move along outside to targetRow
        if (curRow != targetRow) {
            int step = (targetRow > curRow) ? +1 : -1;
            for (int r = curRow + step; r != targetRow + step; r += step) {
                if (!push(r, outsideCol)) return false;
            }
        }

        // Step into required area at targetRow on endCol side
        if (!push(targetRow, endCol)) return false;

        // Phase 2
        int dir2 = upFirst ? -1 : +1;
        int bound2 = upFirst ? (Sx + 1) : (Sx - 1);

        curRow = targetRow;
        curCol = endCol;
        while (true) {
            if (!process_row(curRow, curCol, endCol)) return false;
            if (curRow == bound2) break;
            int nextRow = curRow + dir2;
            if (!push(nextRow, endCol)) return false; // move to next row inside segment
            curRow = nextRow;
            curCol = endCol;
        }

        return true;
    };

    // Try both options
    vector<int> orderA = build_order(false);
    vector<int> orderB = build_order(true);

    vector<pair<int,int>> path;

    bool done = false;
    if (respects_q(orderA)) {
        if (try_construct(false, path)) done = true;
    }
    if (!done && respects_q(orderB)) {
        if (try_construct(true, path)) done = true;
    }

    if (!done) {
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n";
    cout << path.size() << "\n";
    for (auto &p : path) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}