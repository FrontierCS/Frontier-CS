#include <bits/stdc++.h>
using namespace std;

struct Op {
    int x1, y1, x2, y2, x3, y3, x4, y4;
};

static inline uint64_t betweenMask(int a, int b) {
    int l = min(a, b) + 1;
    int r = max(a, b) - 1;
    if (l > r) return 0ULL;
    return ((1ULL << (r + 1)) - 1ULL) ^ ((1ULL << l) - 1ULL);
}

static inline uint64_t edgeMask(int a, int b) {
    int l = min(a, b);
    int r = max(a, b);
    if (l == r) return 0ULL;
    return ((1ULL << r) - 1ULL) ^ ((1ULL << l) - 1ULL);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<vector<uint8_t>> dot(N, vector<uint8_t>(N, 0));
    vector<uint64_t> rowMask(N, 0ULL), colMask(N, 0ULL);
    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        if (!dot[x][y]) {
            dot[x][y] = 1;
            rowMask[y] |= (1ULL << x);
            colMask[x] |= (1ULL << y);
        }
    }

    // used edges for condition 3 (axis-aligned only)
    vector<uint64_t> hEdge(N, 0ULL); // bit x: edge (x,y)-(x+1,y)
    vector<uint64_t> vEdge(N, 0ULL); // bit y: edge (x,y)-(x,y+1)

    int c = (N - 1) / 2;
    struct P { int x, y, w; };
    vector<P> points;
    points.reserve(N * N);
    for (int y = 0; y < N; y++) for (int x = 0; x < N; x++) {
        int dx = x - c, dy = y - c;
        int w = dx * dx + dy * dy + 1;
        points.push_back({x, y, w});
    }
    sort(points.begin(), points.end(), [](const P& a, const P& b) {
        if (a.w != b.w) return a.w > b.w;
        if (a.x != b.x) return a.x < b.x;
        return a.y < b.y;
    });

    auto canAdd = [&](int x1, int y1, int x2, int y2) -> bool {
        if (x1 == x2 || y1 == y2) return false;
        if (x1 < 0 || x1 >= N || y1 < 0 || y1 >= N) return false;
        if (x2 < 0 || x2 >= N || y2 < 0 || y2 >= N) return false;
        if (dot[x1][y1]) return false;
        if (!dot[x2][y1] || !dot[x2][y2] || !dot[x1][y2]) return false;

        // condition 2: no other dots on perimeter
        uint64_t xm = betweenMask(x1, x2);
        uint64_t ym = betweenMask(y1, y2);

        if (rowMask[y1] & xm) return false;
        if (rowMask[y2] & xm) return false;
        if (colMask[x1] & ym) return false;
        if (colMask[x2] & ym) return false;

        // condition 3: no shared segment with existing perimeters (unit-edge reuse)
        uint64_t emx = edgeMask(x1, x2);
        uint64_t emy = edgeMask(y1, y2);
        if (hEdge[y1] & emx) return false;
        if (hEdge[y2] & emx) return false;
        if (vEdge[x1] & emy) return false;
        if (vEdge[x2] & emy) return false;

        return true;
    };

    auto applyAdd = [&](int x1, int y1, int x2, int y2, vector<Op>& ops) {
        ops.push_back({x1, y1, x2, y1, x2, y2, x1, y2});

        dot[x1][y1] = 1;
        rowMask[y1] |= (1ULL << x1);
        colMask[x1] |= (1ULL << y1);

        uint64_t emx = edgeMask(x1, x2);
        uint64_t emy = edgeMask(y1, y2);
        hEdge[y1] |= emx;
        hEdge[y2] |= emx;
        vEdge[x1] |= emy;
        vEdge[x2] |= emy;
    };

    vector<Op> ops;
    ops.reserve(N * N);

    auto start = chrono::steady_clock::now();
    const double TL = 1.85; // seconds

    auto timeExceeded = [&]() -> bool {
        auto now = chrono::steady_clock::now();
        double sec = chrono::duration<double>(now - start).count();
        return sec > TL;
    };

    while (true) {
        if (timeExceeded()) break;
        bool progress = false;

        for (const auto& p : points) {
            if (timeExceeded()) break;
            int x1 = p.x, y1 = p.y;
            if (dot[x1][y1]) continue;

            int bestPer = INT_MAX;
            int bestX2 = -1, bestY2 = -1;

            uint64_t xs = rowMask[y1];
            while (xs) {
                int x2 = __builtin_ctzll(xs);
                xs &= xs - 1;
                if (x2 == x1) continue;

                uint64_t inter = colMask[x1] & colMask[x2];
                while (inter) {
                    int y2 = __builtin_ctzll(inter);
                    inter &= inter - 1;
                    if (y2 == y1) continue;

                    int per = abs(x2 - x1) + abs(y2 - y1);
                    if (per >= bestPer) continue;
                    if (!canAdd(x1, y1, x2, y2)) continue;

                    bestPer = per;
                    bestX2 = x2;
                    bestY2 = y2;
                }
            }

            if (bestX2 != -1) {
                applyAdd(x1, y1, bestX2, bestY2, ops);
                progress = true;
            }
        }

        if (!progress) break;
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.x1 << " " << op.y1 << " "
             << op.x2 << " " << op.y2 << " "
             << op.x3 << " " << op.y3 << " "
             << op.x4 << " " << op.y4 << "\n";
    }

    return 0;
}