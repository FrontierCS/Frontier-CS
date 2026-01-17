#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if(!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) {
        return 0;
    }
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    auto isSubseq = [&](const vector<int>& order)->bool{
        int j = 0;
        for (int x : order) {
            if (j < Lq && x == q[j]) ++j;
        }
        return j == Lq;
    };

    bool leftExists = (L > 1);
    bool rightExists = (R < m);

    // Build possible orders
    vector<int> orderDown, orderUp;
    // Down-first order: Sx..n, 1..Sx-1
    for (int r = Sx; r <= n; ++r) orderDown.push_back(r);
    for (int r = 1; r <= Sx - 1; ++r) orderDown.push_back(r);
    // Up-first order: Sx..1, n..Sx+1
    for (int r = Sx; r >= 1; --r) orderUp.push_back(r);
    for (int r = n; r >= Sx + 1; --r) orderUp.push_back(r);

    auto downPossible = [&]()->bool{
        if (Sx > 1) {
            int y_end = ((n - Sx) % 2 == 0) ? R : L;
            if (y_end == L && !leftExists) return false;
            if (y_end == R && !rightExists) return false;
        }
        return true;
    }();

    auto upPossible = [&]()->bool{
        if (Sx < n) {
            int y_end = ((Sx - 1) % 2 == 0) ? R : L;
            if (y_end == L && !leftExists) return false;
            if (y_end == R && !rightExists) return false;
        }
        return true;
    }();

    bool pickDown = false, pickUp = false;
    if (downPossible && isSubseq(orderDown)) pickDown = true;
    if (upPossible && isSubseq(orderUp)) pickUp = true;

    // If both possible, prefer the one with no outside move (if Sx at boundary),
    // otherwise prefer down by default.
    if (!pickDown && !pickUp) {
        cout << "NO\n";
        return 0;
    }
    bool useDown;
    if (pickDown && pickUp) {
        // Prefer option that doesn't require outside, else default to down
        bool downNoOutside = (Sx <= 1);
        bool upNoOutside = (Sx >= n);
        if (downNoOutside && !upNoOutside) useDown = true;
        else if (!downNoOutside && upNoOutside) useDown = false;
        else useDown = true;
    } else if (pickDown) useDown = true;
    else useDown = false;

    vector<pair<int,int>> path;
    auto pushH = [&](int x, int yFrom, int yTo){
        if (yFrom < yTo) {
            for (int y = yFrom + 1; y <= yTo; ++y) path.push_back({x, y});
        } else {
            for (int y = yFrom - 1; y >= yTo; --y) path.push_back({x, y});
        }
    };
    auto pushV = [&](int xFrom, int xTo, int y){
        if (xFrom < xTo) {
            for (int x = xFrom + 1; x <= xTo; ++x) path.push_back({x, y});
        } else {
            for (int x = xFrom - 1; x >= xTo; --x) path.push_back({x, y});
        }
    };

    // Build path
    path.push_back({Sx, L});
    // Immediately traverse row Sx from L to R
    if (L != R) pushH(Sx, L, R);
    int curx = Sx, cury = R;

    if (useDown) {
        // Stage A: go down to n inside D
        for (int r = Sx + 1; r <= n; ++r) {
            // move vertically to (r, cury)
            pushV(curx, r, cury);
            curx = r;
            // traverse row r to other endpoint
            int other = L + R - cury;
            if (cury != other) pushH(curx, cury, other);
            cury = other;
        }
        // If there are rows above, use outside to reach row 1 then go down inside to Sx-1
        if (Sx > 1) {
            int outsideCol;
            if (cury == L) outsideCol = L - 1; else outsideCol = R + 1;
            // step to outside
            path.push_back({curx, outsideCol});
            // move along outside to row 1
            for (int x = curx - 1; x >= 1; --x) path.push_back({x, outsideCol});
            // enter row 1 at endpoint adjacent to outside
            int enterY = (outsideCol == L - 1 ? L : R);
            path.push_back({1, enterY});
            curx = 1; cury = enterY;
            // traverse row 1 across its segment
            int other = L + R - cury;
            if (cury != other) pushH(curx, cury, other);
            cury = other;
            // Now go down inside to Sx-1
            for (int r = 2; r <= Sx - 1; ++r) {
                pushV(curx, r, cury);
                curx = r;
                int other2 = L + R - cury;
                if (cury != other2) pushH(curx, cury, other2);
                cury = other2;
            }
        }
    } else {
        // useUp: Stage A go up to 1 inside D
        for (int r = Sx - 1; r >= 1; --r) {
            pushV(curx, r, cury);
            curx = r;
            int other = L + R - cury;
            if (cury != other) pushH(curx, cury, other);
            cury = other;
        }
        // If there are rows below, use outside to reach row n then go up inside to Sx+1
        if (Sx < n) {
            int outsideCol;
            if (cury == L) outsideCol = L - 1; else outsideCol = R + 1;
            path.push_back({curx, outsideCol});
            for (int x = curx + 1; x <= n; ++x) path.push_back({x, outsideCol});
            int enterY = (outsideCol == L - 1 ? L : R);
            path.push_back({n, enterY});
            curx = n; cury = enterY;
            int other = L + R - cury;
            if (cury != other) pushH(curx, cury, other);
            cury = other;
            for (int r = n - 1; r >= Sx + 1; --r) {
                pushV(curx, r, cury);
                curx = r;
                int other2 = L + R - cury;
                if (cury != other2) pushH(curx, cury, other2);
                cury = other2;
            }
        }
    }

    cout << "YES\n";
    cout << (int)path.size() << "\n";
    for (auto &p : path) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}