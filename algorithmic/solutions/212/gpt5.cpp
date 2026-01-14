#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m, L, R, Sx, Sy, Lq;
    long long s_param;
    vector<int> q;

    vector<pair<int,int>> path;
    vector<vector<char>> vis;
    int curx, cury;

    bool hasLeftCorr() const { return L > 1; }
    bool hasRightCorr() const { return R < m; }

    void add(int x, int y) {
        // Assume inputs valid; path construction guarantees no revisits.
        if (x < 1 || x > n || y < 1 || y > m) return; // safety
        if (!vis[x][y]) {
            vis[x][y] = 1;
            path.emplace_back(x, y);
            curx = x; cury = y;
        } else {
            // Should not happen in correct construction; ignore in release.
            curx = x; cury = y;
        }
    }

    void stepRight(){ add(curx, cury + 1); }
    void stepLeft(){ add(curx, cury - 1); }
    void stepUp(){ add(curx - 1, cury); }
    void stepDown(){ add(curx + 1, cury); }

    void moveHorizontalTo(int y2) {
        while (cury < y2) stepRight();
        while (cury > y2) stepLeft();
    }
    void moveVerticalTo(int x2) {
        while (curx < x2) stepDown();
        while (curx > x2) stepUp();
    }

    void sweepRow(int row, bool startAtL) {
        // Precondition: currently at (row, start end)
        if (startAtL) {
            for (int y = L + 1; y <= R; ++y) stepRight();
        } else {
            for (int y = R - 1; y >= L; --y) stepLeft();
        }
    }

    vector<int> buildPUp() {
        vector<int> p;
        // p = Sx, Sx-1, ..., 1, Sx+1, ..., n
        for (int r = Sx; r >= 1; --r) p.push_back(r);
        for (int r = Sx + 1; r <= n; ++r) p.push_back(r);
        return p;
    }
    vector<int> buildPDown() {
        vector<int> p;
        // p = Sx, Sx+1, ..., n, Sx-1, ..., 1
        for (int r = Sx; r <= n; ++r) p.push_back(r);
        for (int r = Sx - 1; r >= 1; --r) p.push_back(r);
        return p;
    }

    bool isSubseq(const vector<int>& P, const vector<int>& Q) {
        int i = 0, j = 0;
        while (i < (int)P.size() && j < (int)Q.size()) {
            if (P[i] == Q[j]) { ++i; ++j; }
            else ++i;
        }
        return j == (int)Q.size();
    }

    vector<pair<int,int>> buildUp() {
        path.clear();
        vis.assign(n+1, vector<char>(m+1, 0));
        // Start
        curx = Sx; cury = Sy;
        add(curx, cury); // (Sx, L)
        // Stage A: Sx -> 1 via inside
        // Row Sx: L -> R
        sweepRow(Sx, true); // starting at L
        for (int r = Sx - 1; r >= 1; --r) {
            stepUp(); // to (r, R or L depending current cury)
            bool startAtL = (cury == L);
            // We entered at cury, sweep from that end
            sweepRow(r, startAtL);
        }
        // Now at row 1, end side depends on parity; cury is current end
        if (Sx == 1) {
            // Continue downwards via inside: rows 2..n
            for (int r = 2; r <= n; ++r) {
                stepDown();
                bool startAtL = (cury == L);
                sweepRow(r, startAtL);
            }
            return path;
        } else {
            // Need corridor at current end side
            int corridorCol = (cury == L ? L - 1 : R + 1);
            moveHorizontalTo(corridorCol);
            // Move down corridor to row Sx+1
            moveVerticalTo(Sx + 1);
            // Enter row Sx+1 at corridor-adjacent end (same as current cury opposite by 1 step)
            moveHorizontalTo(corridorCol == L - 1 ? L : R);
            bool startAtL = (cury == L);
            sweepRow(Sx + 1, startAtL);
            // Now for rows Sx+2..n via inside
            for (int r = Sx + 2; r <= n; ++r) {
                stepDown();
                startAtL = (cury == L);
                sweepRow(r, startAtL);
            }
            return path;
        }
    }

    vector<pair<int,int>> buildDown() {
        path.clear();
        vis.assign(n+1, vector<char>(m+1, 0));
        // Start
        curx = Sx; cury = Sy;
        add(curx, cury); // (Sx, L)
        // Stage A: Sx -> n via inside
        // Row Sx: L -> R
        sweepRow(Sx, true);
        for (int r = Sx + 1; r <= n; ++r) {
            stepDown();
            bool startAtL = (cury == L);
            sweepRow(r, startAtL);
        }
        if (Sx == n) {
            // Continue upwards via inside: rows n-1..1
            for (int r = n - 1; r >= 1; --r) {
                stepUp();
                bool startAtL = (cury == L);
                sweepRow(r, startAtL);
            }
            return path;
        } else {
            // Need corridor at current end side
            int corridorCol = (cury == L ? L - 1 : R + 1);
            moveHorizontalTo(corridorCol);
            // Move up corridor to row Sx-1
            moveVerticalTo(Sx - 1);
            // Enter row Sx-1
            moveHorizontalTo(corridorCol == L - 1 ? L : R);
            bool startAtL = (cury == L);
            sweepRow(Sx - 1, startAtL);
            // Now for rows Sx-2..1 via inside
            for (int r = Sx - 2; r >= 1; --r) {
                stepUp();
                startAtL = (cury == L);
                sweepRow(r, startAtL);
            }
            return path;
        }
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s_param)) {
            return;
        }
        q.resize(Lq);
        for (int i = 0; i < Lq; ++i) cin >> q[i];

        // Validate q range
        for (int x : q) {
            if (x < 1 || x > n) {
                cout << "NO\n";
                return;
            }
        }

        // Determine feasibility of patterns
        bool upEndIsR = ((Sx - 1) % 2 == 0);
        bool downEndIsR = ((n - Sx) % 2 == 0);
        bool feasibleUp = (Sx == 1) || (upEndIsR ? hasRightCorr() : hasLeftCorr());
        bool feasibleDown = (Sx == n) || (downEndIsR ? hasRightCorr() : hasLeftCorr());

        vector<int> pUp = buildPUp();
        vector<int> pDown = buildPDown();

        bool upOK = feasibleUp && isSubseq(pUp, q);
        bool downOK = feasibleDown && isSubseq(pDown, q);

        if (!upOK && !downOK) {
            cout << "NO\n";
            return;
        }

        bool chooseUp = false;
        if (upOK && !downOK) chooseUp = true;
        else if (!upOK && downOK) chooseUp = false;
        else {
            // both OK: choose shorter corridor (fewer extra cells)
            int corrUp = (Sx == 1 ? 0 : Sx); // approximate, sufficient for comparison
            int corrDown = (Sx == n ? 0 : (n - Sx));
            chooseUp = (corrUp <= corrDown);
        }

        vector<pair<int,int>> res = chooseUp ? buildUp() : buildDown();

        // Output
        cout << "YES\n";
        cout << (int)res.size() << "\n";
        for (auto &pr : res) {
            cout << pr.first << " " << pr.second << "\n";
        }
    }
};

int main() {
    Solver solver;
    solver.solve();
    return 0;
}