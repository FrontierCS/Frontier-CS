#include <bits/stdc++.h>
using namespace std;

struct PathBuilder {
    vector<pair<int,int>> p;
    int x, y;
    PathBuilder(int sx, int sy) {
        x = sx; y = sy;
        p.emplace_back(x, y);
    }
    void right(int targetY) {
        for (int ny = y + 1; ny <= targetY; ++ny) {
            p.emplace_back(x, ny);
        }
        y = targetY;
    }
    void left(int targetY) {
        for (int ny = y - 1; ny >= targetY; --ny) {
            p.emplace_back(x, ny);
        }
        y = targetY;
    }
    void down(int targetX) {
        for (int nx = x + 1; nx <= targetX; ++nx) {
            p.emplace_back(nx, y);
        }
        x = targetX;
    }
    void up(int targetX) {
        for (int nx = x - 1; nx >= targetX; --nx) {
            p.emplace_back(nx, y);
        }
        x = targetX;
    }
};

bool isSubseq(const vector<int>& p, const vector<int>& q) {
    int i = 0, j = 0;
    int n = p.size(), m = q.size();
    while (i < n && j < m) {
        if (p[i] == q[j]) ++j;
        ++i;
    }
    return j == m;
}

// Full grid (L=1,R=m) serpentine from top (row1..n)
vector<pair<int,int>> buildFullGridAsc(int n, int m) {
    PathBuilder pb(1, 1);
    if (m > 1) pb.right(m);
    bool prevR = true;
    for (int r = 2; r <= n; ++r) {
        pb.down(r);
        if (prevR) {
            if (m > 1) pb.left(1);
            prevR = false;
        } else {
            if (m > 1) pb.right(m);
            prevR = true;
        }
    }
    return pb.p;
}

// Full grid serpentine from bottom (row n..1)
vector<pair<int,int>> buildFullGridDesc(int n, int m) {
    PathBuilder pb(n, 1);
    if (m > 1) pb.right(m);
    bool prevR = true;
    for (int r = n - 1; r >= 1; --r) {
        pb.up(r);
        if (prevR) {
            if (m > 1) pb.left(1);
            prevR = false;
        } else {
            if (m > 1) pb.right(m);
            prevR = true;
        }
    }
    return pb.p;
}

// D-region [L,R], w>=2, top-down serpentine (rows 1..n)
vector<pair<int,int>> buildDRegionAscFromTop(int n, int L, int R) {
    PathBuilder pb(1, L);
    if (R > L) pb.right(R);
    bool prevR = true;
    for (int r = 2; r <= n; ++r) {
        pb.down(r);
        if (prevR) {
            pb.left(L);
            prevR = false;
        } else {
            pb.right(R);
            prevR = true;
        }
    }
    return pb.p;
}

// D-region [L,R], w>=2, bottom-up serpentine (rows n..1)
vector<pair<int,int>> buildDRegionDescFromBottom(int n, int L, int R) {
    PathBuilder pb(n, L);
    if (R > L) pb.right(R);
    bool prevR = true;
    for (int r = n - 1; r >= 1; --r) {
        pb.up(r);
        if (prevR) {
            pb.left(L);
            prevR = false;
        } else {
            pb.right(R);
            prevR = true;
        }
    }
    return pb.p;
}

// w == 1, w < m, ASC rotation
vector<pair<int,int>> buildAscWidth1(int n, int m, int L, int Sx, bool hasLeft, bool hasRight) {
    PathBuilder pb(Sx, L);
    if (Sx == 1) {
        for (int r = 2; r <= n; ++r) pb.down(r);
        return pb.p;
    } else {
        // Segment A: Sx..n along D column
        for (int r = Sx + 1; r <= n; ++r) pb.down(r);
        // Bridge from n to 1 via some walkway
        if (hasLeft) {
            if (L > 1) pb.left(1);
            pb.up(1);
            if (L > 1) pb.right(L);
        } else { // must have right
            if (L < m) pb.right(m);
            pb.up(1);
            if (L < m) pb.left(L);
        }
        // Segment C: 1..Sx-1
        for (int r = 2; r <= Sx - 1; ++r) pb.down(r);
        return pb.p;
    }
}

// w == 1, w < m, DESC rotation
vector<pair<int,int>> buildDescWidth1(int n, int m, int L, int Sx, bool hasLeft, bool hasRight) {
    PathBuilder pb(Sx, L);
    if (Sx == n) {
        for (int r = n - 1; r >= 1; --r) pb.up(r);
        return pb.p;
    } else {
        // Segment A: Sx..1
        for (int r = Sx - 1; r >= 1; --r) pb.up(r);
        // Bridge from 1 to n
        if (hasLeft) {
            if (L > 1) pb.left(1);
            pb.down(n);
            if (L > 1) pb.right(L);
        } else { // right
            if (L < m) pb.right(m);
            pb.down(n);
            if (L < m) pb.left(L);
        }
        // Segment C: n-1..Sx+1
        for (int r = n - 1; r >= Sx + 1; --r) pb.up(r);
        return pb.p;
    }
}

// w >= 2, w < m, ASC rotation (general Sx)
vector<pair<int,int>> buildAscGeneral(int n, int m, int L, int R, int Sx, bool hasLeft, bool hasRight) {
    if (Sx == 1) {
        return buildDRegionAscFromTop(n, L, R);
    }
    PathBuilder pb(Sx, L);
    // Segment A: rows Sx..n serpentine
    if (R > L) pb.right(R);
    bool prevR = true; // after row Sx
    for (int r = Sx + 1; r <= n; ++r) {
        pb.down(r);
        if (prevR) {
            pb.left(L);
            prevR = false;
        } else {
            pb.right(R);
            prevR = true;
        }
    }
    int exit_col = pb.y; // L or R
    // Segment B: bridge n -> 1 using side matching exit_col
    if (exit_col == L) {
        // use left walkway
        if (L > 1) pb.left(1);
        pb.up(1);
        if (L > 1) pb.right(L);
    } else { // exit_col == R
        // use right walkway
        if (R < m) pb.right(m);
        pb.up(1);
        if (R < m) pb.left(R);
    }
    // Now at row1, col = L (if left) or R (if right)
    // Segment C: rows 1..Sx-1
    if (Sx > 1) {
        bool sideRight; // whether last cell in current row is at R
        if (pb.y == L) {
            if (R > L) pb.right(R); // row1 L->R
            sideRight = (R > L);
            if (L == R) sideRight = true;
        } else { // pb.y == R
            pb.left(L); // row1 R->L
            sideRight = false;
        }
        for (int r = 2; r <= Sx - 1; ++r) {
            pb.down(r);
            if (sideRight) {
                pb.left(L);
                sideRight = false;
            } else {
                pb.right(R);
                sideRight = true;
            }
        }
    }
    return pb.p;
}

// w >= 2, w < m, DESC rotation (general Sx)
vector<pair<int,int>> buildDescGeneral(int n, int m, int L, int R, int Sx, bool hasLeft, bool hasRight) {
    if (Sx == n) {
        return buildDRegionDescFromBottom(n, L, R);
    }
    PathBuilder pb(Sx, L);
    // Segment A: rows Sx..1 serpentine upwards
    if (R > L) pb.right(R);
    bool prevR = true;
    for (int r = Sx - 1; r >= 1; --r) {
        pb.up(r);
        if (prevR) {
            pb.left(L);
            prevR = false;
        } else {
            pb.right(R);
            prevR = true;
        }
    }
    int exit_col = pb.y; // col at row1
    // Segment B: bridge 1 -> n
    if (exit_col == L) {
        if (L > 1) pb.left(1);
        pb.down(n);
        if (L > 1) pb.right(L);
    } else { // R
        if (R < m) pb.right(m);
        pb.down(n);
        if (R < m) pb.left(R);
    }
    // Now at row n, col L or R
    // Segment C: rows n-1..Sx+1
    if (Sx + 1 <= n - 1) {
        bool sideRight;
        if (pb.y == L) {
            if (R > L) pb.right(R); // row n L->R
            sideRight = (R > L);
            if (L == R) sideRight = true;
        } else { // at R
            pb.left(L); // row n R->L
            sideRight = false;
        }
        for (int r = n - 1; r >= Sx + 1; --r) {
            pb.up(r);
            if (sideRight) {
                pb.left(L);
                sideRight = false;
            } else {
                pb.right(R);
                sideRight = true;
            }
        }
    }
    return pb.p;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s_param;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s_param)) {
        return 0;
    }
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    // Validate q range
    for (int x : q) {
        if (x < 1 || x > n) {
            cout << "NO\n";
            return 0;
        }
    }

    int w = R - L + 1;
    bool hasLeft = (L > 1);
    bool hasRight = (R < m);

    vector<pair<int,int>> path;
    bool ok = false;

    // Case 1: D is entire grid (no walkway)
    if (w == m) {
        // Only possible if Sx at boundary 1 or n
        if (Sx == 1) {
            vector<int> pAsc(n);
            for (int i = 0; i < n; ++i) pAsc[i] = i + 1;
            if (isSubseq(pAsc, q)) {
                path = buildFullGridAsc(n, m);
                ok = true;
            }
        }
        if (!ok && Sx == n) {
            vector<int> pDesc(n);
            for (int i = 0; i < n; ++i) pDesc[i] = n - i;
            if (isSubseq(pDesc, q)) {
                path = buildFullGridDesc(n, m);
                ok = true;
            }
        }
        if (!ok) {
            cout << "NO\n";
            return 0;
        }
        cout << "YES\n";
        cout << path.size() << "\n";
        for (auto &pt : path) cout << pt.first << " " << pt.second << "\n";
        return 0;
    }

    // Case 2: walkway exists (w < m)
    // Build candidate row orders: asc and desc rotations starting at Sx
    vector<int> pAsc(n), pDesc(n);
    for (int i = 0; i < n; ++i) {
        pAsc[i] = ( (Sx - 1 + i) % n ) + 1;
        int idx = (Sx - 1 - i) % n;
        if (idx < 0) idx += n;
        pDesc[i] = idx + 1;
    }

    bool ascSub = isSubseq(pAsc, q);
    bool descSub = isSubseq(pDesc, q);

    bool ascGeom = false, descGeom = false;

    if (w == 1) {
        // width 1 but walkway exists (m > 1)
        if (Sx == 1) ascGeom = true;
        else ascGeom = (hasLeft || hasRight);
        if (Sx == n) descGeom = true;
        else descGeom = (hasLeft || hasRight);
    } else {
        // w >= 2
        if (Sx == 1) ascGeom = true;
        else {
            if (hasLeft || hasRight) {
                int parity_n = (n - Sx) & 1;
                int exit_col = (parity_n == 0 ? R : L);
                if ((exit_col == L && hasLeft) || (exit_col == R && hasRight)) ascGeom = true;
            }
        }

        if (Sx == n) descGeom = true;
        else {
            if (hasLeft || hasRight) {
                int parity1 = (Sx - 1) & 1;
                int exit_col1 = (parity1 == 0 ? R : L);
                if ((exit_col1 == L && hasLeft) || (exit_col1 == R && hasRight)) descGeom = true;
            }
        }
    }

    // Try ASC orientation first if feasible and subsequence ok
    if (ascSub && ascGeom) {
        if (w == 1) {
            path = buildAscWidth1(n, m, L, Sx, hasLeft, hasRight);
        } else {
            path = buildAscGeneral(n, m, L, R, Sx, hasLeft, hasRight);
        }
        ok = true;
    } else if (descSub && descGeom) {
        if (w == 1) {
            path = buildDescWidth1(n, m, L, Sx, hasLeft, hasRight);
        } else {
            path = buildDescGeneral(n, m, L, R, Sx, hasLeft, hasRight);
        }
        ok = true;
    }

    if (!ok) {
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n";
    cout << path.size() << "\n";
    for (auto &pt : path) {
        cout << pt.first << " " << pt.second << "\n";
    }
    return 0;
}