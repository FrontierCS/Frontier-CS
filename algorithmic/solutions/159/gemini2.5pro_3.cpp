#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <chrono>

using namespace std;

int N, M;
double C;

bool has_dot[62][62];
bool used_h[62][61];
bool used_v[61][62];
bool used_d1[122][61];
bool used_d2[122][61];

struct Point {
    int x, y;

    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

struct Move {
    Point p1, p2, p3, p4;
    double weight;
};

double get_weight(int x, int y) {
    return (x - C) * (x - C) + (y - C) * (y - C) + 1;
}

bool is_in_grid(int x, int y) {
    return x >= 0 && x < N && y >= 0 && y < N;
}

bool check_validity(const Point& p1, const Point& p_other1, const Point& p_other2, const Point& p_other3) {
    Point rect_pts[4] = {p1, p_other1, p_other2, p_other3};
    long long center_x_4 = 0, center_y_4 = 0;
    for(int i=0; i<4; ++i) {
        center_x_4 += rect_pts[i].x;
        center_y_4 += rect_pts[i].y;
    }

    sort(rect_pts, rect_pts + 4, [&](Point a, Point b) {
        return atan2(a.y * 4 - center_y_4, a.x * 4 - center_x_4) < atan2(b.y * 4 - center_y_4, b.x * 4 - center_x_4);
    });

    for (int i = 0; i < 4; ++i) {
        Point p_start = rect_pts[i];
        Point p_end = rect_pts[(i + 1) % 4];

        int dx = p_end.x - p_start.x;
        int dy = p_end.y - p_start.y;
        if (dx == 0 && dy == 0) continue;
        int g = std::gcd(abs(dx), abs(dy));
        int step_x = dx / g;
        int step_y = dy / g;

        for (int j = 0; j < g; ++j) {
            int cur_x = p_start.x + j * step_x;
            int cur_y = p_start.y + j * step_y;
            
            if (has_dot[cur_x][cur_y]) {
                if (!((cur_x == p_other1.x && cur_y == p_other1.y) ||
                      (cur_x == p_other2.x && cur_y == p_other2.y) ||
                      (cur_x == p_other3.x && cur_y == p_other3.y))) {
                    return false;
                }
            }

            int next_x = cur_x + step_x;
            int next_y = cur_y + step_y;
            if (step_y == 0) { // Horizontal
                if (used_h[cur_y][min(cur_x, next_x)]) return false;
            } else if (step_x == 0) { // Vertical
                if (used_v[min(cur_y, next_y)][cur_x]) return false;
            } else if (step_x * step_y > 0) { // Diagonal /
                if (used_d1[cur_y - cur_x + N - 1][min(cur_x, next_x)]) return false;
            } else { // Diagonal \
                if (used_d2[cur_y + cur_x][min(cur_x, next_x)]) return false;
            }
        }
    }
    return true;
}

void apply_move(const Move& move) {
    has_dot[move.p1.x][move.p1.y] = true;
    Point rect_pts[4] = {move.p1, move.p2, move.p3, move.p4};
    long long center_x_4 = 0, center_y_4 = 0;
    for(int i=0; i<4; ++i) {
        center_x_4 += rect_pts[i].x;
        center_y_4 += rect_pts[i].y;
    }

    sort(rect_pts, rect_pts + 4, [&](Point a, Point b) {
        return atan2(a.y * 4 - center_y_4, a.x * 4 - center_x_4) < atan2(b.y * 4 - center_y_4, b.x * 4 - center_x_4);
    });

    for (int i = 0; i < 4; ++i) {
        Point p_start = rect_pts[i];
        Point p_end = rect_pts[(i + 1) % 4];
        
        int dx = p_end.x - p_start.x;
        int dy = p_end.y - p_start.y;
        if (dx == 0 && dy == 0) continue;
        int g = std::gcd(abs(dx), abs(dy));
        int step_x = dx / g;
        int step_y = dy / g;

        for (int j = 0; j < g; ++j) {
            int cur_x = p_start.x + j * step_x;
            int cur_y = p_start.y + j * step_y;
            int next_x = cur_x + step_x;
            int next_y = cur_y + step_y;
            if (step_y == 0) {
                used_h[cur_y][min(cur_x, next_x)] = true;
            } else if (step_x == 0) {
                used_v[min(cur_y, next_y)][cur_x] = true;
            } else if (step_x * step_y > 0) {
                used_d1[cur_y - cur_x + N - 1][min(cur_x, next_x)] = true;
            } else {
                used_d2[cur_y + cur_x][min(cur_x, next_x)] = true;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    cin >> N >> M;
    C = (N - 1) / 2.0;
    vector<Point> dots(M);
    for (int i = 0; i < M; ++i) {
        cin >> dots[i].x >> dots[i].y;
        has_dot[dots[i].x][dots[i].y] = true;
    }

    vector<Move> applied_moves;

    while (true) {
        auto current_time = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count() > 1950) {
            break;
        }

        Move best_move = {{-1, -1}, {-1, -1}, {-1, -1}, {-1, -1}, -1.0};

        for (size_t i = 0; i < dots.size(); ++i) {
            for (size_t j = i + 1; j < dots.size(); ++j) {
                Point pA = dots[i];
                Point pC = dots[j];
                
                // Axis-aligned
                Point pB_ax = {pA.x, pC.y};
                Point pD_ax = {pC.x, pA.y};
                
                if (is_in_grid(pB_ax.x, pB_ax.y) && has_dot[pB_ax.x][pB_ax.y] &&
                    is_in_grid(pD_ax.x, pD_ax.y) && !has_dot[pD_ax.x][pD_ax.y]) {
                    if (check_validity(pD_ax, pA, pB_ax, pC)) {
                        double w = get_weight(pD_ax.x, pD_ax.y);
                        if (w > best_move.weight) {
                            best_move = {pD_ax, pA, pB_ax, pC, w};
                        }
                    }
                }
                
                if (is_in_grid(pD_ax.x, pD_ax.y) && has_dot[pD_ax.x][pD_ax.y] &&
                    is_in_grid(pB_ax.x, pB_ax.y) && !has_dot[pB_ax.x][pB_ax.y]) {
                     if (check_validity(pB_ax, pA, pD_ax, pC)) {
                        double w = get_weight(pB_ax.x, pB_ax.y);
                        if (w > best_move.weight) {
                            best_move = {pB_ax, pA, pD_ax, pC, w};
                        }
                    }
                }

                // 45-degree tilted
                if (((pA.x + pA.y) % 2) != ((pC.x + pC.y) % 2)) continue;
                
                int uA = pA.x + pA.y, vA = pA.x - pA.y;
                int uC = pC.x + pC.y, vC = pC.x - pC.y;
                
                int uB = uA, vB = vC;
                int uD = uC, vD = vA;

                if (abs(uB + vB) % 2 != 0 || abs(uB - vB) % 2 != 0 || abs(uD + vD) % 2 != 0 || abs(uD - vD) % 2 != 0) continue;
                
                Point pB_d = {(uB + vB) / 2, (uB - vB) / 2};
                Point pD_d = {(uD + vD) / 2, (uD - vD) / 2};

                if (is_in_grid(pB_d.x, pB_d.y) && has_dot[pB_d.x][pB_d.y] &&
                    is_in_grid(pD_d.x, pD_d.y) && !has_dot[pD_d.x][pD_d.y]) {
                    if (check_validity(pD_d, pA, pB_d, pC)) {
                        double w = get_weight(pD_d.x, pD_d.y);
                        if (w > best_move.weight) {
                            best_move = {pD_d, pA, pB_d, pC, w};
                        }
                    }
                }

                if (is_in_grid(pD_d.x, pD_d.y) && has_dot[pD_d.x][pD_d.y] &&
                    is_in_grid(pB_d.x, pB_d.y) && !has_dot[pB_d.x][pB_d.y]) {
                    if (check_validity(pB_d, pA, pD_d, pC)) {
                        double w = get_weight(pB_d.x, pB_d.y);
                        if (w > best_move.weight) {
                            best_move = {pB_d, pA, pD_d, pC, w};
                        }
                    }
                }
            }
        }

        if (best_move.weight < 0) {
            break;
        }

        apply_move(best_move);
        dots.push_back(best_move.p1);
        applied_moves.push_back(best_move);
    }

    cout << applied_moves.size() << "\n";
    for (const auto& move : applied_moves) {
        Point p1 = move.p1;
        Point existing_pts[3] = {move.p2, move.p3, move.p4};
        Point opposite, n1, n2;
        for(int i=0; i<3; ++i) {
            bool is_opp = true;
            for(int j=0; j<3; ++j) {
                if (i==j) continue;
                Point p_i = existing_pts[i];
                Point p_j = existing_pts[j];
                if ((p_i.x - p1.x)*(p_j.x - p1.x) + (p_i.y - p1.y)*(p_j.y - p1.y) == 0) {
                    is_opp = false;
                    break;
                }
            }
            if(is_opp) {
                opposite = existing_pts[i];
                break;
            }
        }
        vector<Point> neighbors;
        for(int i=0; i<3; ++i) {
            if (!(existing_pts[i] == opposite)) {
                neighbors.push_back(existing_pts[i]);
            }
        }
        
        cout << p1.x << " " << p1.y << " "
             << neighbors[0].x << " " << neighbors[0].y << " "
             << opposite.x << " " << opposite.y << " "
             << neighbors[1].x << " " << neighbors[1].y << "\n";
    }

    return 0;
}