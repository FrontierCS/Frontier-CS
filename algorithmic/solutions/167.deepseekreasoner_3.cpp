#include <bits/stdc++.h>
using namespace std;

const int N = 5000;
const int TOTAL = 2 * N;
const int MAX_COORD = 100000;
const int G = 500; // grid cell size
const int GRID_SIZE = MAX_COORD / G; // 200

struct Point {
    int x, y, w;
};

vector<Point> points;

int grid[GRID_SIZE][GRID_SIZE];
long long ps[GRID_SIZE + 1][GRID_SIZE + 1];

struct Rect {
    int x1, y1, x2, y2;
    long long score;
};

long long compute_score(const Rect& r) {
    long long s = 0;
    for (const Point& p : points) {
        if (p.x >= r.x1 && p.x <= r.x2 && p.y >= r.y1 && p.y <= r.y2) {
            s += p.w;
        }
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n; // should be 5000
    points.resize(2 * n);
    for (int i = 0; i < 2 * n; ++i) {
        cin >> points[i].x >> points[i].y;
        points[i].w = (i < n) ? 1 : -1;
    }

    // Initialize grid
    memset(grid, 0, sizeof(grid));
    for (const Point& p : points) {
        int i = p.x / G;
        int j = p.y / G;
        if (i >= 0 && i < GRID_SIZE && j >= 0 && j < GRID_SIZE) {
            grid[i][j] += p.w;
        }
    }

    // Compute prefix sums for grid (not used for max submatrix but may be useful)
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            ps[i + 1][j + 1] = grid[i][j] + ps[i][j + 1] + ps[i + 1][j] - ps[i][j];
        }
    }

    // Find maximum sum submatrix in grid
    long long best_grid_sum = -1e18;
    int best_i1 = 0, best_i2 = 0, best_j1 = 0, best_j2 = 0;
    for (int i1 = 0; i1 < GRID_SIZE; ++i1) {
        vector<long long> colsum(GRID_SIZE, 0);
        for (int i2 = i1; i2 < GRID_SIZE; ++i2) {
            for (int j = 0; j < GRID_SIZE; ++j) {
                colsum[j] += grid[i2][j];
            }
            // Kadane on colsum
            long long cur = 0, max_cur = -1e18;
            int start = 0, best_start = 0, best_end = -1;
            for (int j = 0; j < GRID_SIZE; ++j) {
                cur += colsum[j];
                if (cur > max_cur) {
                    max_cur = cur;
                    best_start = start;
                    best_end = j;
                }
                if (cur < 0) {
                    cur = 0;
                    start = j + 1;
                }
            }
            if (max_cur > best_grid_sum) {
                best_grid_sum = max_cur;
                best_i1 = i1;
                best_i2 = i2;
                best_j1 = best_start;
                best_j2 = best_end;
            }
        }
    }

    // Convert cell rectangle to coordinates
    Rect best_rect;
    best_rect.x1 = best_i1 * G;
    best_rect.x2 = (best_i2 + 1) * G; // inclusive
    best_rect.y1 = best_j1 * G;
    best_rect.y2 = (best_j2 + 1) * G;
    // Clamp to [0, MAX_COORD]
    if (best_rect.x1 < 0) best_rect.x1 = 0;
    if (best_rect.x2 > MAX_COORD) best_rect.x2 = MAX_COORD;
    if (best_rect.y1 < 0) best_rect.y1 = 0;
    if (best_rect.y2 > MAX_COORD) best_rect.y2 = MAX_COORD;
    // Ensure at least some size
    if (best_rect.x1 >= best_rect.x2) best_rect.x2 = best_rect.x1 + 1;
    if (best_rect.y1 >= best_rect.y2) best_rect.y2 = best_rect.y1 + 1;

    best_rect.score = compute_score(best_rect);

    // Whole grid rectangle
    Rect whole = {0, 0, MAX_COORD, MAX_COORD, 0};
    whole.score = compute_score(whole);

    // Start with the better of whole and best from grid
    if (whole.score > best_rect.score) {
        best_rect = whole;
    }

    // Local search
    bool improved = true;
    while (improved) {
        improved = false;
        // Try moving left boundary
        for (int dx = -100; dx <= 100; ++dx) {
            int new_x1 = best_rect.x1 + dx;
            if (new_x1 < 0 || new_x1 >= best_rect.x2) continue;
            Rect r = best_rect;
            r.x1 = new_x1;
            long long s = compute_score(r);
            if (s > best_rect.score) {
                best_rect.score = s;
                best_rect.x1 = new_x1;
                improved = true;
                break;
            }
        }
        if (improved) continue;
        // Try moving right boundary
        for (int dx = -100; dx <= 100; ++dx) {
            int new_x2 = best_rect.x2 + dx;
            if (new_x2 <= best_rect.x1 || new_x2 > MAX_COORD) continue;
            Rect r = best_rect;
            r.x2 = new_x2;
            long long s = compute_score(r);
            if (s > best_rect.score) {
                best_rect.score = s;
                best_rect.x2 = new_x2;
                improved = true;
                break;
            }
        }
        if (improved) continue;
        // Try moving bottom boundary
        for (int dy = -100; dy <= 100; ++dy) {
            int new_y1 = best_rect.y1 + dy;
            if (new_y1 < 0 || new_y1 >= best_rect.y2) continue;
            Rect r = best_rect;
            r.y1 = new_y1;
            long long s = compute_score(r);
            if (s > best_rect.score) {
                best_rect.score = s;
                best_rect.y1 = new_y1;
                improved = true;
                break;
            }
        }
        if (improved) continue;
        // Try moving top boundary
        for (int dy = -100; dy <= 100; ++dy) {
            int new_y2 = best_rect.y2 + dy;
            if (new_y2 <= best_rect.y1 || new_y2 > MAX_COORD) continue;
            Rect r = best_rect;
            r.y2 = new_y2;
            long long s = compute_score(r);
            if (s > best_rect.score) {
                best_rect.score = s;
                best_rect.y2 = new_y2;
                improved = true;
                break;
            }
        }
    }

    // If best score is negative, output whole grid (score 0 gives score 1)
    if (best_rect.score < 0) {
        best_rect = whole;
    }

    // Output polygon (rectangle)
    int x1 = best_rect.x1, y1 = best_rect.y1, x2 = best_rect.x2, y2 = best_rect.y2;
    cout << 4 << "\n";
    cout << x1 << " " << y1 << "\n";
    cout << x2 << " " << y1 << "\n";
    cout << x2 << " " << y2 << "\n";
    cout << x1 << " " << y2 << "\n";

    return 0;
}