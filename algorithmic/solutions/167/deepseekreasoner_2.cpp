#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
    bool is_mackerel;
};

int N;
vector<Point> points;

int eval_rect(int x1, int x2, int y1, int y2) {
    int score = 0;
    for (const Point& p : points) {
        if (p.x >= x1 && p.x <= x2 && p.y >= y1 && p.y <= y2) {
            score += p.is_mackerel ? 1 : -1;
        }
    }
    return score;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> N;
    points.resize(2 * N);
    for (int i = 0; i < N; ++i) {
        cin >> points[i].x >> points[i].y;
        points[i].is_mackerel = true;
    }
    for (int i = 0; i < N; ++i) {
        cin >> points[N + i].x >> points[N + i].y;
        points[N + i].is_mackerel = false;
    }

    const int XMAX = 100000;
    const int YMAX = 100000;
    int best_score = -1e9;
    int best_x1 = 0, best_x2 = 1, best_y1 = 0, best_y2 = 1;

    // -------------------- Candidate from grid --------------------
    const int S = 500;
    const int RX = (XMAX + S - 1) / S; // 200
    const int RY = (YMAX + S - 1) / S; // 200
    vector<vector<int>> grid(RX, vector<int>(RY, 0));
    for (const Point& p : points) {
        int cx = p.x / S;
        int cy = p.y / S;
        if (cx >= RX) cx = RX - 1;
        if (cy >= RY) cy = RY - 1;
        grid[cx][cy] += p.is_mackerel ? 1 : -1;
    }

    // 2D prefix sum
    vector<vector<int>> pref(RX + 1, vector<int>(RY + 1, 0));
    for (int i = 0; i < RX; ++i) {
        for (int j = 0; j < RY; ++j) {
            pref[i + 1][j + 1] = grid[i][j] + pref[i][j + 1] + pref[i + 1][j] - pref[i][j];
        }
    }
    auto subgrid_sum = [&](int r1, int r2, int c1, int c2) {
        return pref[r2 + 1][c2 + 1] - pref[r1][c2 + 1] - pref[r2 + 1][c1] + pref[r1][c1];
    };

    int max_sum = -1e9;
    int br1 = 0, br2 = 0, bc1 = 0, bc2 = 0;
    for (int r1 = 0; r1 < RX; ++r1) {
        for (int r2 = r1; r2 < RX; ++r2) {
            int cur = 0;
            int start_c = 0;
            for (int c = 0; c < RY; ++c) {
                int col_sum = subgrid_sum(r1, r2, c, c);
                cur += col_sum;
                if (cur > max_sum) {
                    max_sum = cur;
                    br1 = r1; br2 = r2; bc1 = start_c; bc2 = c;
                }
                if (cur < 0) {
                    cur = 0;
                    start_c = c + 1;
                }
            }
        }
    }
    if (max_sum > -1e9) {
        int x1 = br1 * S;
        int x2 = (br2 + 1) * S - 1;
        int y1 = bc1 * S;
        int y2 = (bc2 + 1) * S - 1;
        x1 = max(0, min(x1, XMAX));
        x2 = max(0, min(x2, XMAX));
        y1 = max(0, min(y1, YMAX));
        y2 = max(0, min(y2, YMAX));
        if (x1 > x2) swap(x1, x2);
        if (y1 > y2) swap(y1, y2);
        if (x1 < x2 && y1 < y2) {
            int score = eval_rect(x1, x2, y1, y2);
            if (score > best_score) {
                best_score = score;
                best_x1 = x1; best_x2 = x2; best_y1 = y1; best_y2 = y2;
            }
        }
    }

    // -------------------- Random rectangles --------------------
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    for (int i = 0; i < 200; ++i) {
        int x1 = uniform_int_distribution<>(0, XMAX - 1)(rng);
        int x2 = uniform_int_distribution<>(x1 + 1, XMAX)(rng);
        int y1 = uniform_int_distribution<>(0, YMAX - 1)(rng);
        int y2 = uniform_int_distribution<>(y1 + 1, YMAX)(rng);
        int score = eval_rect(x1, x2, y1, y2);
        if (score > best_score) {
            best_score = score;
            best_x1 = x1; best_x2 = x2; best_y1 = y1; best_y2 = y2;
        }
    }

    // -------------------- Around mackerels --------------------
    vector<int> mackerels;
    for (int i = 0; i < 2 * N; ++i) if (points[i].is_mackerel) mackerels.push_back(i);
    shuffle(mackerels.begin(), mackerels.end(), rng);
    int sample_m = min(100, (int)mackerels.size());
    for (int idx = 0; idx < sample_m; ++idx) {
        int i = mackerels[idx];
        int cx = points[i].x, cy = points[i].y;
        for (int sz : {10, 20, 50, 100, 200, 500, 1000, 2000, 5000}) {
            int x1 = max(0, cx - sz / 2);
            int x2 = min(XMAX, cx + sz / 2);
            int y1 = max(0, cy - sz / 2);
            int y2 = min(YMAX, cy + sz / 2);
            if (x2 <= x1 || y2 <= y1) continue;
            int score = eval_rect(x1, x2, y1, y2);
            if (score > best_score) {
                best_score = score;
                best_x1 = x1; best_x2 = x2; best_y1 = y1; best_y2 = y2;
            }
        }
    }

    // -------------------- Local search --------------------
    int cur_x1 = best_x1, cur_x2 = best_x2, cur_y1 = best_y1, cur_y2 = best_y2;
    int cur_score = best_score;
    bool improved = true;
    for (int iter = 0; iter < 20 && improved; ++iter) {
        improved = false;
        // try moves for each edge
        for (int d : {-50, -10, -1, 1, 10, 50}) {
            // left
            int nx1 = cur_x1 + d;
            if (nx1 >= 0 && nx1 < cur_x2) {
                int sc = eval_rect(nx1, cur_x2, cur_y1, cur_y2);
                if (sc > cur_score) {
                    cur_score = sc;
                    cur_x1 = nx1;
                    improved = true;
                }
            }
            // right
            int nx2 = cur_x2 + d;
            if (nx2 > cur_x1 && nx2 <= XMAX) {
                int sc = eval_rect(cur_x1, nx2, cur_y1, cur_y2);
                if (sc > cur_score) {
                    cur_score = sc;
                    cur_x2 = nx2;
                    improved = true;
                }
            }
            // bottom
            int ny1 = cur_y1 + d;
            if (ny1 >= 0 && ny1 < cur_y2) {
                int sc = eval_rect(cur_x1, cur_x2, ny1, cur_y2);
                if (sc > cur_score) {
                    cur_score = sc;
                    cur_y1 = ny1;
                    improved = true;
                }
            }
            // top
            int ny2 = cur_y2 + d;
            if (ny2 > cur_y1 && ny2 <= YMAX) {
                int sc = eval_rect(cur_x1, cur_x2, cur_y1, ny2);
                if (sc > cur_score) {
                    cur_score = sc;
                    cur_y2 = ny2;
                    improved = true;
                }
            }
        }
    }
    if (cur_score > best_score) {
        best_score = cur_score;
        best_x1 = cur_x1; best_x2 = cur_x2; best_y1 = cur_y1; best_y2 = cur_y2;
    }

    // -------------------- Fallback: small safe square --------------------
    if (best_score <= -1) {
        double min_dist = 1e9;
        int best_m = -1;
        for (int i = 0; i < 2 * N; ++i) {
            if (points[i].is_mackerel) {
                int mx = points[i].x, my = points[i].y;
                double dist = 1e9;
                for (int j = 0; j < 2 * N; ++j) {
                    if (!points[j].is_mackerel) {
                        int dx = mx - points[j].x, dy = my - points[j].y;
                        double d = sqrt(dx * dx + dy * dy);
                        if (d < dist) dist = d;
                    }
                }
                if (dist < min_dist) {
                    min_dist = dist;
                    best_m = i;
                }
            }
        }
        if (best_m != -1) {
            int mx = points[best_m].x, my = points[best_m].y;
            int sz = 2;
            int x1 = max(0, mx - sz / 2);
            int x2 = min(XMAX, mx + sz / 2);
            int y1 = max(0, my - sz / 2);
            int y2 = min(YMAX, my + sz / 2);
            if (x2 <= x1) { x1 = max(0, mx - 1); x2 = min(XMAX, mx + 1); }
            if (y2 <= y1) { y1 = max(0, my - 1); y2 = min(YMAX, my + 1); }
            int score = eval_rect(x1, x2, y1, y2);
            if (score > best_score) {
                best_score = score;
                best_x1 = x1; best_x2 = x2; best_y1 = y1; best_y2 = y2;
            }
        }
    }

    // -------------------- Output --------------------
    int m = 4;
    cout << m << '\n';
    cout << best_x1 << ' ' << best_y1 << '\n';
    cout << best_x2 << ' ' << best_y1 << '\n';
    cout << best_x2 << ' ' << best_y2 << '\n';
    cout << best_x1 << ' ' << best_y2 << '\n';

    return 0;
}