#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y, w; // w = +1 for mackerel, -1 for sardine
};

struct Rect {
    int x1, y1, x2, y2;
};

pair<Rect, int> solveWithStep(const vector<Point>& pts, int step) {
    int K = 100000 / step;
    if (K <= 0) K = 1;
    vector<vector<int>> grid(K, vector<int>(K, 0));
    for (const auto& p : pts) {
        int cx = p.x / step;
        int cy = p.y / step;
        if (cx >= K) cx = K - 1;
        if (cy >= K) cy = K - 1;
        grid[cy][cx] += p.w;
    }

    int bestSum = INT_MIN;
    int bestTop = 0, bestBottom = 0, bestLeft = 0, bestRight = 0;
    vector<int> col(K, 0);

    for (int top = 0; top < K; ++top) {
        fill(col.begin(), col.end(), 0);
        for (int bottom = top; bottom < K; ++bottom) {
            for (int c = 0; c < K; ++c) col[c] += grid[bottom][c];
            int curSum = 0, curL = 0;
            int localBest = INT_MIN, localL = 0, localR = 0;
            for (int c = 0; c < K; ++c) {
                if (curSum <= 0) {
                    curSum = col[c];
                    curL = c;
                } else {
                    curSum += col[c];
                }
                if (curSum > localBest) {
                    localBest = curSum;
                    localL = curL;
                    localR = c;
                }
            }
            if (localBest > bestSum) {
                bestSum = localBest;
                bestTop = top;
                bestBottom = bottom;
                bestLeft = localL;
                bestRight = localR;
            }
        }
    }

    // Convert to coordinates
    int x1 = bestLeft * step;
    int x2 = (bestRight == K - 1) ? 100000 : (bestRight + 1) * step - 1;
    int y1 = bestTop * step;
    int y2 = (bestBottom == K - 1) ? 100000 : (bestBottom + 1) * step - 1;

    // Ensure valid rectangle
    if (x1 < 0) x1 = 0;
    if (y1 < 0) y1 = 0;
    if (x2 > 100000) x2 = 100000;
    if (y2 > 100000) y2 = 100000;

    Rect r{x1, y1, x2, y2};

    // Compute actual difference
    int diff = 0;
    for (const auto& p : pts) {
        if (r.x1 <= p.x && p.x <= r.x2 && r.y1 <= p.y && p.y <= r.y2) {
            diff += p.w;
        }
    }

    return {r, diff};
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
        int x, y;
        cin >> x >> y;
        pts.push_back({x, y, +1});
    }
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
        pts.push_back({x, y, -1});
    }

    // Try several grid steps and pick the best rectangle by actual difference
    vector<int> steps = {2000, 1000, 800, 625, 500, 400};
    Rect bestRect{0, 0, 100000, 100000};
    int bestDiff = INT_MIN;

    for (int s : steps) {
        auto [r, diff] = solveWithStep(pts, s);
        if (diff > bestDiff) {
            bestDiff = diff;
            bestRect = r;
        }
    }

    // Fallback to full rectangle if not improving (ensures at least score 1)
    if (bestDiff <= 0) {
        bestRect = {0, 0, 100000, 100000};
    }

    // Ensure rectangle has positive area and within constraints
    if (bestRect.x1 >= bestRect.x2 || bestRect.y1 >= bestRect.y2) {
        bestRect = {0, 0, 100000, 100000};
    }

    cout << 4 << "\n";
    cout << bestRect.x1 << " " << bestRect.y1 << "\n";
    cout << bestRect.x2 << " " << bestRect.y1 << "\n";
    cout << bestRect.x2 << " " << bestRect.y2 << "\n";
    cout << bestRect.x1 << " " << bestRect.y2 << "\n";

    return 0;
}