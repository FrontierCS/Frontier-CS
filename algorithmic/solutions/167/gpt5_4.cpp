#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<pair<int,int>> pts(2*N);
    for (int i = 0; i < 2*N; i++) cin >> pts[i].first >> pts[i].second;

    vector<int> w(2*N, 1);
    for (int i = N; i < 2*N; i++) w[i] = -1;

    auto compute_diff = [&](int xl, int yl, int xr, int yr) -> long long {
        long long diff = 0;
        for (int i = 0; i < 2*N; i++) {
            int x = pts[i].first, y = pts[i].second;
            if (xl <= x && x <= xr && yl <= y && y <= yr) diff += w[i];
        }
        return diff;
    };

    const int M2 = 100001; // for mapping 0..100000 inclusive
    vector<int> Blist = {60, 80, 100, 120, 150};
    long long bestDiff = LLONG_MIN;
    int best_xl = 0, best_yl = 0, best_xr = 1, best_yr = 1;

    for (int B : Blist) {
        vector<vector<int>> grid(B, vector<int>(B, 0));
        for (int i = 0; i < 2*N; i++) {
            int xi = (long long)pts[i].first * B / M2;
            int yi = (long long)pts[i].second * B / M2;
            if (xi < 0) xi = 0; if (xi >= B) xi = B-1;
            if (yi < 0) yi = 0; if (yi >= B) yi = B-1;
            grid[xi][yi] += w[i];
        }
        int bestSum = -1e9, bestL = 0, bestR = 0, bestT = 0, bestB = 0;
        vector<int> col(B, 0);
        for (int top = 0; top < B; top++) {
            fill(col.begin(), col.end(), 0);
            for (int bot = top; bot < B; bot++) {
                for (int x = 0; x < B; x++) col[x] += grid[x][bot];
                int sum = 0, ltemp = 0;
                int curBest = -1e9, curL = 0, curR = 0;
                for (int x = 0; x < B; x++) {
                    sum += col[x];
                    if (sum > curBest) { curBest = sum; curL = ltemp; curR = x; }
                    if (sum < 0) { sum = 0; ltemp = x + 1; }
                }
                if (curBest > bestSum) {
                    bestSum = curBest;
                    bestL = curL; bestR = curR; bestT = top; bestB = bot;
                }
            }
        }
        auto coord_from_idx_left = [&](int idx) -> int {
            return (int)((long long)idx * M2 / B);
        };
        auto coord_from_idx_right = [&](int idx) -> int {
            long long r = (long long)(idx + 1) * M2 / B - 1;
            if (r > 100000) r = 100000;
            if (r < 0) r = 0;
            return (int)r;
        };
        int xl = coord_from_idx_left(bestL);
        int xr = coord_from_idx_right(bestR);
        int yl = coord_from_idx_left(bestT);
        int yr = coord_from_idx_right(bestB);
        if (xl == xr) {
            if (xr < 100000) xr++;
            else if (xl > 0) xl--;
        }
        if (yl == yr) {
            if (yr < 100000) yr++;
            else if (yl > 0) yl--;
        }
        if (xl < 0) xl = 0; if (xr > 100000) xr = 100000;
        if (yl < 0) yl = 0; if (yr > 100000) yr = 100000;
        if (xl == xr) { if (xr < 100000) xr++; else if (xl > 0) xl--; }
        if (yl == yr) { if (yr < 100000) yr++; else if (yl > 0) yl--; }

        long long diff = compute_diff(xl, yl, xr, yr);
        if (diff > bestDiff) {
            bestDiff = diff;
            best_xl = xl; best_xr = xr; best_yl = yl; best_yr = yr;
        }
    }

    // Fallback to ensure non-negative score if bestDiff <= 0: choose empty rectangle
    if (bestDiff <= 0) {
        const int MAXC = 100000;
        vector<char> usedX(MAXC+1, 0), usedY(MAXC+1, 0);
        for (int i = 0; i < 2*N; i++) {
            usedX[pts[i].first] = 1;
            usedY[pts[i].second] = 1;
        }
        bool foundX = false, foundY = false;
        int x0 = 0, y0 = 0;
        for (int i = 0; i < MAXC; i++) {
            if (!usedX[i] && !usedX[i+1]) { foundX = true; x0 = i; break; }
        }
        for (int i = 0; i < MAXC; i++) {
            if (!usedY[i] && !usedY[i+1]) { foundY = true; y0 = i; break; }
        }
        if (foundX) {
            best_xl = x0; best_xr = x0 + 1;
            best_yl = 0; best_yr = 1;
        } else if (foundY) {
            best_yl = y0; best_yr = y0 + 1;
            best_xl = 0; best_xr = 1;
        } else {
            // Extremely unlikely; try random small rectangles until empty
            std::mt19937 rng(712367);
            uniform_int_distribution<int> dist(0, MAXC-1);
            bool ok = false;
            for (int tries = 0; tries < 2000 && !ok; tries++) {
                int xl = dist(rng), yl = dist(rng);
                int xr = min(MAXC, xl + 1);
                int yr = min(MAXC, yl + 1);
                long long diff = compute_diff(xl, yl, xr, yr);
                if (diff == 0) {
                    best_xl = xl; best_xr = xr; best_yl = yl; best_yr = yr;
                    ok = true;
                    break;
                }
            }
            if (!ok) {
                // As a last resort, choose a tiny rectangle at (0,0)-(1,1)
                best_xl = 0; best_xr = 1; best_yl = 0; best_yr = 1;
            }
        }
    }

    // Ensure positive width and height and constraints
    if (best_xl == best_xr) {
        if (best_xr < 100000) best_xr++;
        else if (best_xl > 0) best_xl--;
    }
    if (best_yl == best_yr) {
        if (best_yr < 100000) best_yr++;
        else if (best_yl > 0) best_yl--;
    }
    best_xl = max(0, min(100000, best_xl));
    best_xr = max(0, min(100000, best_xr));
    best_yl = max(0, min(100000, best_yl));
    best_yr = max(0, min(100000, best_yr));
    if (best_xl == best_xr) { if (best_xr < 100000) best_xr++; else best_xl--; }
    if (best_yl == best_yr) { if (best_yr < 100000) best_yr++; else best_yl--; }

    cout << 4 << "\n";
    cout << best_xl << " " << best_yl << "\n";
    cout << best_xr << " " << best_yl << "\n";
    cout << best_xr << " " << best_yr << "\n";
    cout << best_xl << " " << best_yr << "\n";

    return 0;
}