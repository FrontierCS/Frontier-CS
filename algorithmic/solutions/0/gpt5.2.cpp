#include <bits/stdc++.h>
using namespace std;

struct Transform {
    int w, h;
    long long minx, miny;
    int r, f;
};

static int ceil_sqrt_ll(long long x) {
    if (x <= 0) return 0;
    long long r = (long long)floor(sqrt((long double)x));
    while (r * r < x) ++r;
    while ((r - 1) > 0 && (r - 1) * (r - 1) >= x) --r;
    return (int)r;
}

static inline pair<long long,long long> rot(long long x, long long y, int r) {
    switch (r & 3) {
        case 0: return {x, y};
        case 1: return {y, -x};
        case 2: return {-x, -y};
        default: return {-y, x};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<array<Transform, 8>> trs(n);

    long long totalCells = 0;
    long long sumMinBBoxArea = 0;
    int globalMaxMinW = 1;

    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        totalCells += k;
        vector<pair<long long,long long>> pts;
        pts.reserve(k);
        for (int j = 0; j < k; j++) {
            long long x, y;
            cin >> x >> y;
            pts.push_back({x, y});
        }

        int idx = 0;
        for (int f = 0; f <= 1; f++) {
            for (int r = 0; r < 4; r++) {
                long long minx = (1LL<<62), miny = (1LL<<62);
                long long maxx = -(1LL<<62), maxy = -(1LL<<62);
                for (auto [x0, y0] : pts) {
                    long long x = x0, y = y0;
                    if (f) x = -x;
                    auto [rx, ry] = rot(x, y, r);
                    minx = min(minx, rx);
                    miny = min(miny, ry);
                    maxx = max(maxx, rx);
                    maxy = max(maxy, ry);
                }
                int w = (int)(maxx - minx + 1);
                int h = (int)(maxy - miny + 1);
                trs[i][idx++] = Transform{w, h, minx, miny, r, f};
            }
        }

        int minW = INT_MAX;
        int minArea = INT_MAX;
        for (int t = 0; t < 8; t++) {
            minW = min(minW, trs[i][t].w);
            minArea = min(minArea, trs[i][t].w * trs[i][t].h);
        }
        globalMaxMinW = max(globalMaxMinW, minW);
        sumMinBBoxArea += minArea;
    }

    int baseBBox = max(globalMaxMinW, ceil_sqrt_ll(sumMinBBoxArea));
    int baseCells = max(globalMaxMinW, ceil_sqrt_ll(totalCells));

    set<int> candSet;
    auto addCand = [&](int w) {
        if (w < globalMaxMinW) return;
        if (w <= 0) return;
        if (w > 100000) return;
        candSet.insert(w);
    };

    int L1 = max(globalMaxMinW, baseBBox - 30);
    int R1 = baseBBox + 120;
    for (int w = L1; w <= R1; w++) addCand(w);

    // A few additional larger widths (coarse), in case shelf packing benefits.
    for (int w = baseBBox + 140; w <= baseBBox + 800; w += 20) addCand(w);

    // Optionally include some around sqrt(totalCells) if much smaller than bbox bound.
    if (baseCells + 40 < baseBBox) {
        for (int w = max(globalMaxMinW, baseCells - 20); w <= baseCells + 120; w += 5) addCand(w);
    }

    // Ensure some small widths exist (at least min feasible).
    for (int w = globalMaxMinW; w <= globalMaxMinW + 20; w++) addCand(w);

    vector<int> cands(candSet.begin(), candSet.end());

    vector<int> selT(n), selW(n), selH(n), ord(n);
    vector<int> tmpX(n), tmpY(n);
    vector<int> bestT(n), bestX(n), bestY(n);

    long long bestSide = (1LL<<62);
    int bestPackW = -1;
    int bestPackH = -1;

    for (int W : cands) {
        if ((long long)W >= bestSide) continue;

        bool ok = true;
        for (int i = 0; i < n; i++) {
            long long bestScore = (1LL<<62);
            int bestIdx = -1;
            int besth = 0, bestw = 0;
            for (int t = 0; t < 8; t++) {
                const auto &tr = trs[i][t];
                if (tr.w > W) continue;
                long long score = 1LL * tr.h * W + tr.w; // heuristic
                if (score < bestScore ||
                    (score == bestScore && (tr.h < besth || (tr.h == besth && tr.w < bestw)))) {
                    bestScore = score;
                    bestIdx = t;
                    besth = tr.h;
                    bestw = tr.w;
                }
            }
            if (bestIdx < 0) { ok = false; break; }
            selT[i] = bestIdx;
            selW[i] = trs[i][bestIdx].w;
            selH[i] = trs[i][bestIdx].h;
        }
        if (!ok) continue;

        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (selH[a] != selH[b]) return selH[a] > selH[b];
            if (selW[a] != selW[b]) return selW[a] > selW[b];
            return a < b;
        });

        int x = 0, y = 0, rowH = 0;
        int maxH = 0;
        ok = true;

        for (int id : ord) {
            int pw = selW[id], ph = selH[id];
            if (pw > W) { ok = false; break; }

            if (x + pw > W) {
                y += rowH;
                if ((long long)y >= bestSide) { ok = false; break; }
                x = 0;
                rowH = 0;
            }

            tmpX[id] = x;
            tmpY[id] = y;

            x += pw;
            rowH = max(rowH, ph);
            maxH = max(maxH, y + rowH);

            if ((long long)max(maxH, W) >= bestSide) {
                // can't beat current best
                ok = false;
                break;
            }
        }
        if (!ok) continue;

        int H = y + rowH;
        long long side = max<long long>(W, H);

        if (side < bestSide || (side == bestSide && (W < bestPackW || (W == bestPackW && H < bestPackH)))) {
            bestSide = side;
            bestPackW = W;
            bestPackH = H;
            bestT = selT;
            bestX = tmpX;
            bestY = tmpY;
        }
    }

    // Fallback: should never happen, but just in case.
    if (bestPackW < 0) {
        int W = max(globalMaxMinW, ceil_sqrt_ll(sumMinBBoxArea));
        iota(ord.begin(), ord.end(), 0);
        for (int i = 0; i < n; i++) {
            int bestIdx = 0;
            long long bestScore = (1LL<<62);
            for (int t = 0; t < 8; t++) {
                const auto &tr = trs[i][t];
                if (tr.w > W) continue;
                long long score = 1LL * tr.h * W + tr.w;
                if (score < bestScore) { bestScore = score; bestIdx = t; }
            }
            bestT[i] = bestIdx;
            selW[i] = trs[i][bestIdx].w;
            selH[i] = trs[i][bestIdx].h;
        }
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (selH[a] != selH[b]) return selH[a] > selH[b];
            if (selW[a] != selW[b]) return selW[a] > selW[b];
            return a < b;
        });
        int x = 0, y = 0, rowH = 0;
        for (int id : ord) {
            int pw = selW[id], ph = selH[id];
            if (x + pw > W) { y += rowH; x = 0; rowH = 0; }
            bestX[id] = x;
            bestY[id] = y;
            x += pw;
            rowH = max(rowH, ph);
        }
        int H = y + rowH;
        bestSide = max<long long>(W, H);
    }

    // Output as square (safe even if rectangle allowed).
    long long S = bestSide;
    cout << S << " " << S << "\n";
    for (int i = 0; i < n; i++) {
        const auto &tr = trs[i][bestT[i]];
        long long X = (long long)bestX[i] - tr.minx;
        long long Y = (long long)bestY[i] - tr.miny;
        cout << X << " " << Y << " " << tr.r << " " << tr.f << "\n";
    }

    return 0;
}