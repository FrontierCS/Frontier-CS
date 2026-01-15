#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    bool feasible = false;
    vector<int> order;
    vector<pair<int,int>> path;
};

int n, m, L, R, Sx, Sy, Lq;
long long sparam;
vector<int> qseq;

bool isSubsequence(const vector<int>& p, const vector<int>& q) {
    size_t i = 0, j = 0;
    while (i < p.size() && j < q.size()) {
        if (p[i] == q[j]) ++j;
        ++i;
    }
    return j == q.size();
}

struct PathBuilder {
    int n, m, L, R, Sx;
    bool hasLeft, hasRight;
    int w;
    vector<pair<int,int>> path;
    int cx, cy;

    PathBuilder(int n_, int m_, int L_, int R_, int Sx_)
        : n(n_), m(m_), L(L_), R(R_), Sx(Sx_) {
        hasLeft = (L > 1);
        hasRight = (R < m);
        w = R - L + 1;
        path.clear();
        cx = Sx;
        cy = L;
    }

    void resetStart() {
        path.clear();
        cx = Sx;
        cy = L;
        path.emplace_back(cx, cy);
    }

    void moveHoriz(int targetY) {
        int dir = (targetY > cy) ? 1 : -1;
        while (cy != targetY) {
            cy += dir;
            path.emplace_back(cx, cy);
        }
    }

    void moveVert(int targetX) {
        int dir = (targetX > cx) ? 1 : -1;
        while (cx != targetX) {
            cx += dir;
            path.emplace_back(cx, cy);
        }
    }

    // Serpentine from start row to end row inclusive, step dr = +1 (down) or -1 (up),
    // starting at current (cx,cy). Assumes we are at start row and in segment [L,R].
    void serpentineRows(int startRow, int endRow, int dr) {
        int r = startRow;
        while (true) {
            if (cy == L) moveHoriz(R);
            else moveHoriz(L);
            if (r == endRow) break;
            moveVert(r + dr);
            r += dr;
        }
    }

    // Candidate 0: Down-first to n, then (if Sx>1) go outside along end side to row 1,
    // enter row 1 and serpentine down to row Sx-1 inside D.
    Candidate buildDownTopInc() {
        Candidate cand;
        cand.order.clear();
        // Order of rows first visited:
        for (int i = Sx; i <= n; ++i) cand.order.push_back(i);
        for (int i = 1; i <= Sx - 1; ++i) cand.order.push_back(i);

        resetStart();
        // Stage 1: serp down Sx..n
        serpentineRows(Sx, n, +1);
        int endSide = (cy == L ? 0 : 1); // 0 left, 1 right

        if (Sx > 1) {
            // Need to go outside from (n, cy) at side endSide
            if (w >= 2) {
                if (endSide == 0 && !hasLeft) return cand; // infeasible
                if (endSide == 1 && !hasRight) return cand; // infeasible
            } else {
                // w == 1, we can choose a side if current side not available
                if (!(hasLeft || hasRight)) return cand; // no outside at all
                if (endSide == 0 && !hasLeft) endSide = 1;
                if (endSide == 1 && !hasRight) endSide = 0;
            }
            int outsideY = (endSide == 0 ? L - 1 : R + 1);
            moveHoriz(outsideY);
            moveVert(1); // go to top along outside
            int entryY = (outsideY == L - 1 ? L : R);
            moveHoriz(entryY); // enter row 1
            // Serpentine inside from row 1 down to Sx-1
            if (Sx - 1 >= 1)
                serpentineRows(1, Sx - 1, +1);
        }
        cand.feasible = true;
        cand.path = path;
        return cand;
    }

    // Candidate 1: Up-first to 1, then (if Sx<n) go outside along end side to row n,
    // enter row n and serpentine up to row Sx+1 inside D.
    Candidate buildUpBottomInc() {
        Candidate cand;
        cand.order.clear();
        for (int i = Sx; i >= 1; --i) cand.order.push_back(i);
        for (int i = n; i >= Sx + 1; --i) cand.order.push_back(i);

        resetStart();
        // Stage 1: serp up Sx..1
        serpentineRows(Sx, 1, -1);
        int endSide = (cy == L ? 0 : 1); // 0 left, 1 right

        if (Sx < n) {
            if (w >= 2) {
                if (endSide == 0 && !hasLeft) return cand; // infeasible
                if (endSide == 1 && !hasRight) return cand; // infeasible
            } else {
                if (!(hasLeft || hasRight)) return cand;
                if (endSide == 0 && !hasLeft) endSide = 1;
                if (endSide == 1 && !hasRight) endSide = 0;
            }
            int outsideY = (endSide == 0 ? L - 1 : R + 1);
            moveHoriz(outsideY);
            moveVert(n); // go to bottom along outside
            int entryY = (outsideY == L - 1 ? L : R);
            moveHoriz(entryY); // enter row n
            // Serpentine inside from row n up to Sx+1
            if (Sx + 1 <= n)
                serpentineRows(n, Sx + 1, -1);
        }
        cand.feasible = true;
        cand.path = path;
        return cand;
    }

    // Candidate 2: Down-first to n, then alternate outside sides (requires both sides),
    // visiting rows n-1..1 in decreasing order.
    Candidate buildDownAltDec() {
        Candidate cand;
        cand.order.clear();
        for (int i = Sx; i <= n; ++i) cand.order.push_back(i);
        for (int i = n - 1; i >= 1; --i) cand.order.push_back(i);

        if (!(hasLeft && hasRight)) return cand;
        resetStart();
        // Stage 1
        serpentineRows(Sx, n, +1);
        int endSide = (cy == L ? 0 : 1);
        // Must exit at that side (both sides exist anyway)
        int outsideY = (endSide == 0 ? L - 1 : R + 1);
        moveHoriz(outsideY);
        // Stage 2: for r = n-1 down to 1
        int currentOutsideY = outsideY;
        for (int r = n - 1; r >= 1; --r) {
            moveVert(r); // move along current outside to row r
            int entryY = (currentOutsideY == L - 1 ? L : R);
            moveHoriz(entryY); // enter D at side
            // traverse across to other side
            int otherY = (entryY == L ? R : L);
            moveHoriz(otherY);
            // step to other outside
            int otherOutsideY = (otherY == L ? L - 1 : R + 1);
            moveHoriz(otherOutsideY);
            currentOutsideY = otherOutsideY;
        }
        cand.feasible = true;
        cand.path = path;
        return cand;
    }

    // Candidate 3: Up-first to 1, then alternate outside sides (requires both sides),
    // visiting rows 2..n in increasing order.
    Candidate buildUpAltInc() {
        Candidate cand;
        cand.order.clear();
        for (int i = Sx; i >= 1; --i) cand.order.push_back(i);
        for (int i = 2; i <= n; ++i) cand.order.push_back(i);

        if (!(hasLeft && hasRight)) return cand;
        resetStart();
        // Stage 1
        serpentineRows(Sx, 1, -1);
        int endSide = (cy == L ? 0 : 1);
        int outsideY = (endSide == 0 ? L - 1 : R + 1);
        moveHoriz(outsideY);
        // Stage 2: for r = 2 up to n
        int currentOutsideY = outsideY;
        for (int r = 2; r <= n; ++r) {
            moveVert(r); // move along current outside to row r
            int entryY = (currentOutsideY == L - 1 ? L : R);
            moveHoriz(entryY); // enter D at side
            // traverse across to other side
            int otherY = (entryY == L ? R : L);
            moveHoriz(otherY);
            // step to other outside
            int otherOutsideY = (otherY == L ? L - 1 : R + 1);
            moveHoriz(otherOutsideY);
            currentOutsideY = otherOutsideY;
        }
        cand.feasible = true;
        cand.path = path;
        return cand;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> sparam)) {
        return 0;
    }
    qseq.resize(Lq);
    for (int i = 0; i < Lq; ++i) cin >> qseq[i];

    // Validate q elements are within [1..n]
    for (int x : qseq) {
        if (x < 1 || x > n) {
            cout << "NO\n";
            return 0;
        }
    }

    PathBuilder builder(n, m, L, R, Sx);

    vector<Candidate> candidates;

    // Build candidates
    candidates.push_back(builder.buildDownTopInc());
    PathBuilder builder2(n, m, L, R, Sx);
    candidates.push_back(builder2.buildUpBottomInc());
    PathBuilder builder3(n, m, L, R, Sx);
    candidates.push_back(builder3.buildDownAltDec());
    PathBuilder builder4(n, m, L, R, Sx);
    candidates.push_back(builder4.buildUpAltInc());

    // Filter feasible and q subsequence
    int bestIdx = -1;
    size_t bestLen = SIZE_MAX;
    for (int i = 0; i < (int)candidates.size(); ++i) {
        if (!candidates[i].feasible) continue;
        if (!isSubsequence(candidates[i].order, qseq)) continue;
        if (candidates[i].path.size() < bestLen) {
            bestLen = candidates[i].path.size();
            bestIdx = i;
        }
    }

    if (bestIdx == -1) {
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n";
    cout << candidates[bestIdx].path.size() << "\n";
    for (auto &p : candidates[bestIdx].path) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}