#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
    bool is_mack;
};

pair<int,int> evaluate_rect(int x1, int x2, int y1, int y2, const vector<Point>& points) {
    int a = 0, b = 0;
    for (const auto& p : points) {
        if (p.x >= x1 && p.x <= x2 && p.y >= y1 && p.y <= y2) {
            if (p.is_mack) a++;
            else b++;
        }
    }
    return {a, b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<Point> points(2*N);
    for (int i = 0; i < N; i++) {
        cin >> points[i].x >> points[i].y;
        points[i].is_mack = true;
    }
    for (int i = 0; i < N; i++) {
        cin >> points[N+i].x >> points[N+i].y;
        points[N+i].is_mack = false;
    }

    const int G = 200;
    const int CELL = 500; // 100000 / 200
    const int MAX_COORD = 100000;

    vector<vector<int>> grid(G, vector<int>(G, 0));
    for (const auto& p : points) {
        int i = min(p.x / CELL, G-1);
        int j = min(p.y / CELL, G-1);
        if (p.is_mack) grid[i][j]++;
        else grid[i][j]--;
    }

    vector<vector<int>> pref(G+1, vector<int>(G+1, 0));
    for (int i = 0; i < G; i++) {
        for (int j = 0; j < G; j++) {
            pref[i+1][j+1] = grid[i][j] + pref[i][j+1] + pref[i+1][j] - pref[i][j];
        }
    }

    int best_sum_grid = -1e9;
    int best_r1 = 0, best_r2 = 0, best_c1 = 0, best_c2 = 0;

    for (int r1 = 0; r1 < G; r1++) {
        for (int r2 = r1; r2 < G; r2++) {
            vector<int> col_sum(G);
            for (int c = 0; c < G; c++) {
                col_sum[c] = pref[r2+1][c+1] - pref[r1][c+1] - pref[r2+1][c] + pref[r1][c];
            }
            int cur = 0, max_here = -1e9;
            int start = 0, best_start = 0, best_end = 0;
            for (int i = 0; i < G; i++) {
                if (cur <= 0) {
                    cur = col_sum[i];
                    start = i;
                } else {
                    cur += col_sum[i];
                }
                if (cur > max_here) {
                    max_here = cur;
                    best_start = start;
                    best_end = i;
                }
            }
            if (max_here > best_sum_grid) {
                best_sum_grid = max_here;
                best_r1 = r1;
                best_r2 = r2;
                best_c1 = best_start;
                best_c2 = best_end;
            }
        }
    }

    if (best_sum_grid <= -1) {
        int x1 = 0, y1 = 0, x2 = 1, y2 = 1;
        bool found = false;
        for (int d = 1; d <= 10; d++) {
            auto [a1,b1] = evaluate_rect(0, d, 0, d, points);
            if (a1 == 0 && b1 == 0) {
                x1 = 0; y1 = 0; x2 = d; y2 = d;
                found = true;
                break;
            }
            auto [a2,b2] = evaluate_rect(MAX_COORD-d, MAX_COORD, MAX_COORD-d, MAX_COORD, points);
            if (a2 == 0 && b2 == 0) {
                x1 = MAX_COORD-d; y1 = MAX_COORD-d; x2 = MAX_COORD; y2 = MAX_COORD;
                found = true;
                break;
            }
        }
        if (!found) {
            x1 = 0; y1 = 0; x2 = 1; y2 = 1;
        }
        cout << 4 << "\n";
        cout << x1 << " " << y1 << "\n";
        cout << x2 << " " << y1 << "\n";
        cout << x2 << " " << y2 << "\n";
        cout << x1 << " " << y2 << "\n";
        return 0;
    }

    int x1_grid = best_c1 * CELL;
    int x2_grid = (best_c2+1) * CELL;
    int y1_grid = best_r1 * CELL;
    int y2_grid = (best_r2+1) * CELL;

    vector<Point> points_in_rect;
    for (const auto& p : points) {
        if (p.x >= x1_grid && p.x <= x2_grid && p.y >= y1_grid && p.y <= y2_grid) {
            points_in_rect.push_back(p);
        }
    }

    set<int> X_set, Y_set;
    X_set.insert(x1_grid);
    X_set.insert(x2_grid);
    Y_set.insert(y1_grid);
    Y_set.insert(y2_grid);
    for (const auto& p : points_in_rect) {
        X_set.insert(p.x);
        Y_set.insert(p.y);
    }
    vector<int> X(X_set.begin(), X_set.end());
    vector<int> Y(Y_set.begin(), Y_set.end());

    const int MAX_DIM = 200;
    if (X.size() > MAX_DIM) {
        vector<int> X2;
        int step = max(1, (int)X.size() / MAX_DIM);
        for (size_t i = 0; i < X.size(); i += step) X2.push_back(X[i]);
        if (X2.back() != X.back()) X2.push_back(X.back());
        X = X2;
    }
    if (Y.size() > MAX_DIM) {
        vector<int> Y2;
        int step = max(1, (int)Y.size() / MAX_DIM);
        for (size_t i = 0; i < Y.size(); i += step) Y2.push_back(Y[i]);
        if (Y2.back() != Y.back()) Y2.push_back(Y.back());
        Y = Y2;
    }

    unordered_map<int, int> x_to_idx, y_to_idx;
    for (size_t i = 0; i < X.size(); i++) x_to_idx[X[i]] = i;
    for (size_t i = 0; i < Y.size(); i++) y_to_idx[Y[i]] = i;

    int rows = X.size(), cols = Y.size();
    vector<vector<int>> D(rows, vector<int>(cols, 0));
    for (const auto& p : points_in_rect) {
        int xi = x_to_idx[p.x];
        int yi = y_to_idx[p.y];
        if (p.is_mack) D[xi][yi] += 1;
        else D[xi][yi] -= 1;
    }

    vector<vector<int>> prefD(rows+1, vector<int>(cols+1, 0));
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            prefD[i+1][j+1] = D[i][j] + prefD[i][j+1] + prefD[i+1][j] - prefD[i][j];
        }
    }

    int best_sum = -1e9;
    int best_i1 = 0, best_i2 = 0, best_j1 = 0, best_j2 = 0;

    for (int i1 = 0; i1 < rows; i1++) {
        for (int i2 = i1; i2 < rows; i2++) {
            vector<int> col_sum(cols);
            for (int j = 0; j < cols; j++) {
                col_sum[j] = prefD[i2+1][j+1] - prefD[i1][j+1] - prefD[i2+1][j] + prefD[i1][j];
            }
            int cur = 0, max_here = -1e9;
            int start = 0, best_start = 0, best_end = 0;
            for (int i = 0; i < cols; i++) {
                if (cur <= 0) {
                    cur = col_sum[i];
                    start = i;
                } else {
                    cur += col_sum[i];
                }
                if (cur > max_here) {
                    max_here = cur;
                    best_start = start;
                    best_end = i;
                }
            }
            if (max_here > best_sum) {
                best_sum = max_here;
                best_i1 = i1;
                best_i2 = i2;
                best_j1 = best_start;
                best_j2 = best_end;
            }
        }
    }

    if (best_sum <= -1) {
        int x1 = 0, y1 = 0, x2 = 1, y2 = 1;
        bool found = false;
        for (int d = 1; d <= 10; d++) {
            auto [a1,b1] = evaluate_rect(0, d, 0, d, points);
            if (a1 == 0 && b1 == 0) {
                x1 = 0; y1 = 0; x2 = d; y2 = d;
                found = true;
                break;
            }
            auto [a2,b2] = evaluate_rect(MAX_COORD-d, MAX_COORD, MAX_COORD-d, MAX_COORD, points);
            if (a2 == 0 && b2 == 0) {
                x1 = MAX_COORD-d; y1 = MAX_COORD-d; x2 = MAX_COORD; y2 = MAX_COORD;
                found = true;
                break;
            }
        }
        if (!found) {
            x1 = 0; y1 = 0; x2 = 1; y2 = 1;
        }
        cout << 4 << "\n";
        cout << x1 << " " << y1 << "\n";
        cout << x2 << " " << y1 << "\n";
        cout << x2 << " " << y2 << "\n";
        cout << x1 << " " << y2 << "\n";
        return 0;
    }

    int rect_x1 = X[best_i1];
    int rect_x2 = X[best_i2];
    int rect_y1 = Y[best_j1];
    int rect_y2 = Y[best_j2];

    if (rect_x1 == rect_x2) rect_x2++;
    if (rect_y1 == rect_y2) rect_y2++;

    cout << 4 << "\n";
    cout << rect_x1 << " " << rect_y1 << "\n";
    cout << rect_x2 << " " << rect_y1 << "\n";
    cout << rect_x2 << " " << rect_y2 << "\n";
    cout << rect_x1 << " " << rect_y2 << "\n";

    return 0;
}