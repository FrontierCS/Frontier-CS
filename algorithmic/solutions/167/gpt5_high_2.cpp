#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y, w; // w = +1 for mackerel, -1 for sardine
};

struct Rect {
    int x1, y1, x2, y2;
    int diff;
};

static inline int compute_diff(const vector<Point>& pts, int x1, int y1, int x2, int y2) {
    int diff = 0;
    for (const auto& p : pts) {
        if (p.x >= x1 && p.x <= x2 && p.y >= y1 && p.y <= y2) diff += p.w;
    }
    return diff;
}

static Rect best_rect_grid(const vector<Point>& pts, int NX, int NY) {
    vector<int> Ex(NX + 1), Ey(NY + 1);
    for (int i = 0; i <= NX; i++) Ex[i] = (int)((long long)i * 100000 / NX);
    for (int j = 0; j <= NY; j++) Ey[j] = (int)((long long)j * 100000 / NY);

    vector<vector<int>> grid(NY, vector<int>(NX, 0));
    for (const auto& p : pts) {
        int xi = (int)((long long)p.x * NX / 100000);
        if (xi == NX) xi = NX - 1;
        int yi = (int)((long long)p.y * NY / 100000);
        if (yi == NY) yi = NY - 1;
        grid[yi][xi] += p.w;
    }

    int bestSum = INT_MIN;
    int bestL = 0, bestR = 0, bestT = 0, bestB = 0;

    vector<int> tmp(NY, 0);
    for (int l = 0; l < NX; l++) {
        fill(tmp.begin(), tmp.end(), 0);
        for (int r = l; r < NX; r++) {
            for (int y = 0; y < NY; y++) tmp[y] += grid[y][r];

            int curSum = 0;
            int curStart = 0;
            for (int y = 0; y < NY; y++) {
                if (curSum <= 0) {
                    curSum = tmp[y];
                    curStart = y;
                } else {
                    curSum += tmp[y];
                }
                if (curSum > bestSum) {
                    bestSum = curSum;
                    bestL = l; bestR = r; bestT = curStart; bestB = y;
                }
            }
        }
    }

    int x1 = Ex[bestL];
    int x2 = Ex[bestR + 1];
    int y1 = Ey[bestT];
    int y2 = Ey[bestB + 1];

    if (x1 == x2) {
        if (x2 < 100000) x2++;
        else if (x1 > 0) x1--;
    }
    if (y1 == y2) {
        if (y2 < 100000) y2++;
        else if (y1 > 0) y1--;
    }

    Rect res;
    res.x1 = x1; res.y1 = y1; res.x2 = x2; res.y2 = y2;
    res.diff = compute_diff(pts, x1, y1, x2, y2);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) {
        // Fallback in case input is absent (shouldn't happen in judge)
        cout << 4 << "\n";
        cout << 0 << " " << 0 << "\n";
        cout << 100000 << " " << 0 << "\n";
        cout << 100000 << " " << 100000 << "\n";
        cout << 0 << " " << 100000 << "\n";
        return 0;
    }
    vector<Point> pts;
    pts.reserve(2 * N);
    for (int i = 0; i < 2 * N; i++) {
        int x, y;
        cin >> x >> y;
        pts.push_back({x, y, i < N ? 1 : -1});
    }

    Rect best;
    best.x1 = 0; best.y1 = 0; best.x2 = 100000; best.y2 = 100000;
    best.diff = compute_diff(pts, best.x1, best.y1, best.x2, best.y2); // should be 0

    vector<pair<int,int>> grids = {{64,64}, {96,96}, {128,128}};
    for (auto [NX, NY] : grids) {
        Rect r = best_rect_grid(pts, NX, NY);
        if (r.diff > best.diff) best = r;
    }

    if (best.diff <= 0) {
        best.x1 = 0; best.y1 = 0; best.x2 = 100000; best.y2 = 100000;
    }

    cout << 4 << "\n";
    cout << best.x1 << " " << best.y1 << "\n";
    cout << best.x2 << " " << best.y1 << "\n";
    cout << best.x2 << " " << best.y2 << "\n";
    cout << best.x1 << " " << best.y2 << "\n";
    return 0;
}