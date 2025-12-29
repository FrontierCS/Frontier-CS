#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    int x1, y1; // p1 (new dot)
    int x2, y2; // p2
    int x3, y3; // p3
    int x4, y4; // p4
    int weight; // for sorting
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<int> xs(M), ys(M);
    vector<vector<unsigned char>> dot(N, vector<unsigned char>(N, 0)); // dot[y][x]

    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        xs[i] = x;
        ys[i] = y;
        dot[y][x] = 1;
    }

    int c = (N - 1) / 2;

    vector<Candidate> cands;
    cands.reserve(10000);

    // Generate candidates from all triples of initial dots
    for (int i = 0; i < M - 2; i++) {
        int x1 = xs[i], y1 = ys[i];
        for (int j = i + 1; j < M - 1; j++) {
            int x2 = xs[j], y2 = ys[j];

            // Precompute for X to prune early?
            for (int k = j + 1; k < M; k++) {
                int x3 = xs[k], y3 = ys[k];

                // Check there are exactly 2 distinct Xs
                bool atLeastPairX = (x1 == x2) || (x1 == x3) || (x2 == x3);
                bool allEqualX = (x1 == x2) && (x2 == x3);
                if (!(atLeastPairX && !allEqualX)) continue;

                // Check there are exactly 2 distinct Ys
                bool atLeastPairY = (y1 == y2) || (y1 == y3) || (y2 == y3);
                bool allEqualY = (y1 == y2) && (y2 == y3);
                if (!(atLeastPairY && !allEqualY)) continue;

                // Compute min/max for X and Y
                int xlow = x1;
                if (x2 < xlow) xlow = x2;
                if (x3 < xlow) xlow = x3;
                int xhigh = x1;
                if (x2 > xhigh) xhigh = x2;
                if (x3 > xhigh) xhigh = x3;
                int ylow = y1;
                if (y2 < ylow) ylow = y2;
                if (y3 < ylow) ylow = y3;
                int yhigh = y1;
                if (y2 > yhigh) yhigh = y2;
                if (y3 > yhigh) yhigh = y3;

                if (xlow == xhigh || ylow == yhigh) continue; // degenerate

                bool present[4] = {false, false, false, false};
                bool bad = false;

                auto add_point = [&](int x, int y) {
                    int idx = -1;
                    if (x == xlow) {
                        if (y == ylow) idx = 0;        // BL
                        else if (y == yhigh) idx = 1;   // TL
                        else return false;
                    } else if (x == xhigh) {
                        if (y == yhigh) idx = 2;        // TR
                        else if (y == ylow) idx = 3;    // BR
                        else return false;
                    } else {
                        return false;
                    }
                    if (present[idx]) return false;
                    present[idx] = true;
                    return true;
                };

                if (!add_point(x1, y1)) continue;
                if (!add_point(x2, y2)) continue;
                if (!add_point(x3, y3)) continue;

                int missing = -1;
                for (int t = 0; t < 4; t++) {
                    if (!present[t]) {
                        if (missing == -1) missing = t;
                        else { bad = true; break; }
                    }
                }
                if (bad || missing == -1) continue;

                int cx[4] = {xlow, xlow, xhigh, xhigh};
                int cy[4] = {ylow, yhigh, yhigh, ylow};

                int mx = cx[missing];
                int my = cy[missing];

                // The 4th corner must be empty initially
                if (dot[my][mx]) continue;

                Candidate cd;
                cd.x1 = mx;
                cd.y1 = my;
                cd.x2 = cx[(missing + 1) % 4];
                cd.y2 = cy[(missing + 1) % 4];
                cd.x3 = cx[(missing + 2) % 4];
                cd.y3 = cy[(missing + 2) % 4];
                cd.x4 = cx[(missing + 3) % 4];
                cd.y4 = cy[(missing + 3) % 4];

                int dx = cd.x1 - c;
                int dy = cd.y1 - c;
                cd.weight = dx * dx + dy * dy + 1;

                cands.push_back(cd);
            }
        }
    }

    // Sort candidates by weight descending (farther from center preferred)
    sort(cands.begin(), cands.end(), [](const Candidate& a, const Candidate& b) {
        return a.weight > b.weight;
    });

    // Edge usage arrays
    vector<vector<unsigned char>> hor(N, vector<unsigned char>(N - 1, 0)); // hor[y][x] between (x,y)-(x+1,y)
    vector<vector<unsigned char>> ver(N - 1, vector<unsigned char>(N, 0)); // ver[y][x] between (x,y)-(x,y+1)

    vector<Candidate> ops;
    ops.reserve(cands.size());

    for (const auto& cd : cands) {
        int x1 = cd.x1, y1 = cd.y1;
        int x2 = cd.x2, y2 = cd.y2;
        int x3 = cd.x3, y3 = cd.y3;
        int x4 = cd.x4, y4 = cd.y4;

        // Condition 1: p1 must not contain a dot yet
        if (dot[y1][x1]) continue;

        int xmin = min(min(x1, x2), min(x3, x4));
        int xmax = max(max(x1, x2), max(x3, x4));
        int ymin = min(min(y1, y2), min(y3, y4));
        int ymax = max(max(y1, y2), max(y3, y4));

        // Condition 2: no dots on perimeter except at p2,p3,p4
        bool ok = true;
        auto is_p234 = [&](int x, int y) -> bool {
            return (x == x2 && y == y2) || (x == x3 && y == y3) || (x == x4 && y == y4);
        };

        // Bottom and top edges
        for (int x = xmin; x <= xmax && ok; x++) {
            int yb = ymin;
            if (dot[yb][x] && !is_p234(x, yb)) ok = false;

            int yt = ymax;
            if (dot[yt][x] && !is_p234(x, yt)) ok = false;
        }
        // Left and right edges (excluding corners to avoid double-check)
        for (int y = ymin + 1; y <= ymax - 1 && ok; y++) {
            int xl = xmin;
            if (dot[y][xl] && !is_p234(xl, y)) ok = false;

            int xr = xmax;
            if (dot[y][xr] && !is_p234(xr, y)) ok = false;
        }
        if (!ok) continue;

        // Condition 3: no shared segments with existing rectangles
        // First check availability
        for (int x = xmin; x < xmax && ok; x++) {
            if (hor[ymin][x]) ok = false;
            if (hor[ymax][x]) ok = false;
        }
        for (int y = ymin; y < ymax && ok; y++) {
            if (ver[y][xmin]) ok = false;
            if (ver[y][xmax]) ok = false;
        }
        if (!ok) continue;

        // Mark edges as used
        for (int x = xmin; x < xmax; x++) {
            hor[ymin][x] = 1;
            hor[ymax][x] = 1;
        }
        for (int y = ymin; y < ymax; y++) {
            ver[y][xmin] = 1;
            ver[y][xmax] = 1;
        }

        // Place new dot
        dot[y1][x1] = 1;

        ops.push_back(cd);
    }

    // Output
    int K = (int)ops.size();
    cout << K << '\n';
    for (const auto& op : ops) {
        cout << op.x1 << ' ' << op.y1 << ' '
             << op.x2 << ' ' << op.y2 << ' '
             << op.x3 << ' ' << op.y3 << ' '
             << op.x4 << ' ' << op.y4 << '\n';
    }

    return 0;
}