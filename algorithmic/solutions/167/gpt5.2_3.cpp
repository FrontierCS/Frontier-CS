#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    static uint64_t splitmix64(uint64_t &v) {
        uint64_t z = (v += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t nextU64() { return splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
};

struct P {
    int x, y, w;
};

static inline bool normalizeRect(int &x1, int &x2, int &y1, int &y2) {
    if (x1 > x2) swap(x1, x2);
    if (y1 > y2) swap(y1, y2);
    x1 = max(0, min(100000, x1));
    x2 = max(0, min(100000, x2));
    y1 = max(0, min(100000, y1));
    y2 = max(0, min(100000, y2));
    if (x1 == x2) {
        if (x1 > 0) --x1;
        else if (x2 < 100000) ++x2;
        else return false;
    }
    if (y1 == y2) {
        if (y1 > 0) --y1;
        else if (y2 < 100000) ++y2;
        else return false;
    }
    if (x1 > x2 || y1 > y2) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    int M = 2 * N;
    vector<P> pts(M);
    uint64_t seed = 1469598103934665603ULL; // FNV offset basis
    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        int w = (i < N) ? 1 : -1;
        pts[i] = {x, y, w};
        seed ^= (uint64_t)(x + 1) * 1000003ULL;
        seed *= 1099511628211ULL;
        seed ^= (uint64_t)(y + 7) * 9176ULL;
        seed *= 1099511628211ULL;
        seed ^= (uint64_t)(w + 3);
        seed *= 1099511628211ULL;
    }

    SplitMix64 rng(seed);

    // Baseline: whole field
    int bestSum = 0;
    int bestX1 = 0, bestY1 = 0, bestX2 = 100000, bestY2 = 100000;

    auto evalRect = [&](int x1, int x2, int y1, int y2) -> int {
        int s = 0;
        for (const auto &p : pts) {
            if (x1 <= p.x && p.x <= x2 && y1 <= p.y && p.y <= y2) s += p.w;
        }
        return s;
    };

    auto tryRect = [&](int x1, int x2, int y1, int y2) {
        if (!normalizeRect(x1, x2, y1, y2)) return;
        int s = evalRect(x1, x2, y1, y2);
        if (s > bestSum) {
            bestSum = s;
            bestX1 = x1; bestX2 = x2; bestY1 = y1; bestY2 = y2;
        }
    };

    // Candidate widths (half-widths)
    const vector<int> widthsSmall = {150, 300, 600, 1200, 2500, 5000, 10000, 20000, 35000};
    const vector<int> widthsMed = {400, 800, 1600, 3200, 6400, 12800, 25600, 51200};

    // Sample some mackerels, try centered squares/rectangles
    int samples = 320;
    for (int t = 0; t < samples; t++) {
        int i = (int)((uint64_t)t * (uint64_t)N / (uint64_t)samples);
        int cx = pts[i].x, cy = pts[i].y;
        for (int w : widthsSmall) {
            tryRect(cx - w, cx + w, cy - w, cy + w);
            int wx = w, wy = widthsSmall[(t + w) % widthsSmall.size()];
            tryRect(cx - wx, cx + wx, cy - wy, cy + wy);
        }
        // Some thin rectangles
        for (int w : widthsMed) {
            int h = widthsSmall[(t + w) % widthsSmall.size()];
            tryRect(cx - w, cx + w, cy - h, cy + h);
            tryRect(cx - h, cx + h, cy - w, cy + w);
        }
    }

    // Rectangles defined by pairs of mackerels (with margin)
    int pairTrials = 280;
    for (int it = 0; it < pairTrials; it++) {
        int a = rng.nextInt(0, N - 1);
        int b = rng.nextInt(0, N - 1);
        int margin = rng.nextInt(0, 1200);
        int x1 = min(pts[a].x, pts[b].x) - margin;
        int x2 = max(pts[a].x, pts[b].x) + margin;
        int y1 = min(pts[a].y, pts[b].y) - margin;
        int y2 = max(pts[a].y, pts[b].y) + margin;
        tryRect(x1, x2, y1, y2);
    }

    // Random rectangles around mackerels with asymmetric half-widths
    int randTrials = 2400;
    for (int it = 0; it < randTrials; it++) {
        int idx = rng.nextInt(0, N - 1);
        int cx = pts[idx].x, cy = pts[idx].y;
        int wx = widthsMed[rng.nextInt(0, (int)widthsMed.size() - 1)];
        int wy = widthsMed[rng.nextInt(0, (int)widthsMed.size() - 1)];

        int lx = rng.nextInt(0, wx);
        int rx = wx - lx;
        int ly = rng.nextInt(0, wy);
        int ry = wy - ly;

        int x1 = cx - lx;
        int x2 = cx + rx;
        int y1 = cy - ly;
        int y2 = cy + ry;

        // occasional jitter
        if ((rng.nextU32() & 3u) == 0u) {
            int jx = rng.nextInt(-1500, 1500);
            int jy = rng.nextInt(-1500, 1500);
            x1 += jx; x2 += jx;
            y1 += jy; y2 += jy;
        }

        tryRect(x1, x2, y1, y2);
    }

    // Also try some rectangles based on a sardine to avoid them: center on mackerel, but exclude nearby sardine by shifting
    int avoidTrials = 600;
    for (int it = 0; it < avoidTrials; it++) {
        int mi = rng.nextInt(0, N - 1);
        int si = rng.nextInt(N, 2 * N - 1);
        int cx = pts[mi].x, cy = pts[mi].y;
        int sx = pts[si].x, sy = pts[si].y;
        int wx = widthsSmall[rng.nextInt(0, (int)widthsSmall.size() - 1)];
        int wy = widthsSmall[rng.nextInt(0, (int)widthsSmall.size() - 1)];

        int x1 = cx - wx, x2 = cx + wx;
        int y1 = cy - wy, y2 = cy + wy;

        // If sardine lies inside, shift rectangle away along the dominant axis
        if (x1 <= sx && sx <= x2 && y1 <= sy && sy <= y2) {
            int dx = (sx < cx) ? (cx - sx) : (sx - cx);
            int dy = (sy < cy) ? (cy - sy) : (sy - cy);
            int shift = 1 + rng.nextInt(0, 2000);
            if (dx >= dy) {
                if (sx < cx) { x1 += shift; x2 += shift; }
                else { x1 -= shift; x2 -= shift; }
            } else {
                if (sy < cy) { y1 += shift; y2 += shift; }
                else { y1 -= shift; y2 -= shift; }
            }
        }
        tryRect(x1, x2, y1, y2);
    }

    // Output best rectangle
    int x1 = bestX1, x2 = bestX2, y1 = bestY1, y2 = bestY2;
    normalizeRect(x1, x2, y1, y2);

    cout << 4 << "\n";
    cout << x1 << " " << y1 << "\n";
    cout << x2 << " " << y1 << "\n";
    cout << x2 << " " << y2 << "\n";
    cout << x1 << " " << y2 << "\n";
    return 0;
}