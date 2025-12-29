#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y, w; // w = +1 (mackerel), -1 (sardine)
};

static const int MAXC = 100000;
static const int D = MAXC + 1;

pair<int,int> bestRangeAtLeastTwo(const vector<int>& arr) {
    int n = (int)arr.size();
    vector<int> pref(n + 1, 0);
    for (int i = 0; i < n; ++i) pref[i + 1] = pref[i] + arr[i];
    long long minVal = pref[0];
    int minIdx = 0;
    long long best = LLONG_MIN;
    int bestL = 0, bestR = 1; // ensure length >= 2
    for (int r = 1; r < n; ++r) {
        // allow l <= r-1
        if (pref[r - 1] < minVal) { minVal = pref[r - 1]; minIdx = r - 1; }
        long long sum = (long long)pref[r + 1] - minVal;
        if (sum > best) { best = sum; bestL = minIdx; bestR = r; }
    }
    return {bestL, bestR};
}

long long scoreRect(const vector<Point>& pts, int xl, int xr, int yb, int yt) {
    long long s = 0;
    for (const auto& p : pts) {
        if (xl <= p.x && p.x <= xr && yb <= p.y && p.y <= yt) s += p.w;
    }
    return s;
}

struct Rect {
    int xl, xr, yb, yt;
    long long val;
};

Rect refineFromYRange(const vector<Point>& pts, int yb, int yt) {
    // Refine X given Y, then Y given X, a couple of iterations
    Rect rect;
    rect.yb = yb; rect.yt = yt;
    rect.xl = 0; rect.xr = MAXC;
    rect.val = scoreRect(pts, rect.xl, rect.xr, rect.yb, rect.yt);

    for (int iter = 0; iter < 2; ++iter) {
        // Build arrX for current Y-range
        vector<int> arrX(D, 0);
        for (const auto& p : pts) {
            if (rect.yb <= p.y && p.y <= rect.yt) {
                arrX[p.x] += p.w;
            }
        }
        auto [lx, rx] = bestRangeAtLeastTwo(arrX);
        // compute sum quickly
        static vector<int> prefX;
        prefX.assign(D + 1, 0);
        for (int i = 0; i < D; ++i) prefX[i + 1] = prefX[i] + arrX[i];
        long long sumX = (long long)prefX[rx + 1] - prefX[lx];
        if (sumX >= rect.val) {
            rect.xl = lx; rect.xr = rx; rect.val = sumX;
        }

        // Build arrY for current X-range
        vector<int> arrY(D, 0);
        for (const auto& p : pts) {
            if (rect.xl <= p.x && p.x <= rect.xr) {
                arrY[p.y] += p.w;
            }
        }
        auto [ly, ry] = bestRangeAtLeastTwo(arrY);
        static vector<int> prefY;
        prefY.assign(D + 1, 0);
        for (int i = 0; i < D; ++i) prefY[i + 1] = prefY[i] + arrY[i];
        long long sumY = (long long)prefY[ry + 1] - prefY[ly];
        if (sumY >= rect.val) {
            rect.yb = ly; rect.yt = ry; rect.val = sumY;
        }
    }
    return rect;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) {
        return 0;
    }
    vector<Point> pts;
    pts.reserve(2 * N);
    for (int i = 0; i < N; ++i) {
        int x, y; cin >> x >> y;
        pts.push_back({x, y, +1});
    }
    for (int i = 0; i < N; ++i) {
        int x, y; cin >> x >> y;
        pts.push_back({x, y, -1});
    }

    // Coarse search using grid and 2D Kadane
    int G = 100; // grid size
    long long Dll = D;
    vector<vector<int>> grid(G, vector<int>(G, 0));
    for (const auto& p : pts) {
        int ix = (int)((long long)p.x * G / Dll);
        int iy = (int)((long long)p.y * G / Dll);
        grid[iy][ix] += p.w;
    }
    long long bestSumGrid = LLONG_MIN;
    int bestL = 0, bestR = 0, bestT = 0, bestB = 0;
    vector<int> acc(G);
    for (int top = 0; top < G; ++top) {
        fill(acc.begin(), acc.end(), 0);
        for (int bottom = top; bottom < G; ++bottom) {
            for (int c = 0; c < G; ++c) acc[c] += grid[bottom][c];
            long long cur = LLONG_MIN, bestHere = LLONG_MIN, sum = 0;
            int curL = 0, L = 0, R = 0;
            // Standard Kadane
            sum = 0;
            curL = 0;
            for (int c = 0; c < G; ++c) {
                if (sum <= 0) { sum = acc[c]; curL = c; }
                else { sum += acc[c]; }
                if (sum > bestHere) { bestHere = sum; L = curL; R = c; }
            }
            if (bestHere > bestSumGrid) {
                bestSumGrid = bestHere;
                bestL = L; bestR = R; bestT = top; bestB = bottom;
            }
        }
    }
    auto ceil_div = [](long long a, long long b) -> long long { return (a + b - 1) / b; };
    int coarseXL = (int)ceil_div((long long)bestL * D, G);
    int coarseXR = (int)(((long long)(bestR + 1) * D - 1) / G);
    int coarseYB = (int)ceil_div((long long)bestT * D, G);
    int coarseYT = (int)(((long long)(bestB + 1) * D - 1) / G);
    coarseXL = max(0, min(MAXC, coarseXL));
    coarseXR = max(0, min(MAXC, coarseXR));
    coarseYB = max(0, min(MAXC, coarseYB));
    coarseYT = max(0, min(MAXC, coarseYT));
    if (coarseXR <= coarseXL) coarseXR = min(MAXC, coarseXL + 1);
    if (coarseYT <= coarseYB) coarseYT = min(MAXC, coarseYB + 1);

    // Attempt 1: refine from coarse Y range
    Rect r1 = refineFromYRange(pts, coarseYB, coarseYT);
    // compute exact score (should match r1.val)
    r1.val = scoreRect(pts, r1.xl, r1.xr, r1.yb, r1.yt);

    // Attempt 2: refine from full Y range
    Rect r2 = refineFromYRange(pts, 0, MAXC);
    r2.val = scoreRect(pts, r2.xl, r2.xr, r2.yb, r2.yt);

    Rect best = r1.val >= r2.val ? r1 : r2;

    // Ensure positive width/height
    if (best.xr <= best.xl) best.xr = min(MAXC, best.xl + 1);
    if (best.yt <= best.yb) best.yt = min(MAXC, best.yb + 1);

    // Output rectangle polygon
    cout << 4 << "\n";
    cout << best.xl << " " << best.yb << "\n";
    cout << best.xr << " " << best.yb << "\n";
    cout << best.xr << " " << best.yt << "\n";
    cout << best.xl << " " << best.yt << "\n";
    return 0;
}