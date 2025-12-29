#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <queue>
#include <chrono>
#include <set>
#include <array>

using namespace std;

int N, M;
int center_x, center_y;

struct Point {
    int x, y;

    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

struct Rect {
    Point p1, p2, p3, p4;
};

long long weight(const Point& p) {
    long long dx = p.x - center_x;
    long long dy = p.y - center_y;
    return dx * dx + dy * dy + 1;
}

struct Move {
    Rect r;
    long long w;

    bool operator>(const Move& other) const {
        return w < other.w;
    }
};

bool has_dot[62][62];
vector<Point> dots;
vector<Rect> result_rects;

bool h_edge[62][61];
bool v_edge[61][62];
bool d1_edge[123][61]; // y-x+N-1, x
bool d2_edge[123][61]; // y+x, x

set<int> row_dots[62];
set<int> col_dots[62];
set<int> diag1_dots[123]; // y-x+N-1, stores x
set<int> diag2_dots[123]; // y+x, stores x

priority_queue<Move, vector<Move>, greater<Move>> pq;

auto start_time = chrono::high_resolution_clock::now();

bool is_out_of_bounds(const Point& p) {
    return p.x < 0 || p.x >= N || p.y < 0 || p.y >= N;
}

bool check_perimeter_dots(const Point& p1, const Point& p2, const Point& p3, const Point& p4) {
    const array<Point, 5> points = {p1, p2, p3, p4, p1};
    for (int i = 0; i < 4; ++i) {
        Point A = points[i];
        Point B = points[i + 1];
        if (A.y == B.y) {
            auto it = row_dots[A.y].upper_bound(min(A.x, B.x));
            if (it != row_dots[A.y].end() && *it < max(A.x, B.x)) return false;
        } else if (A.x == B.x) {
            auto it = col_dots[A.x].upper_bound(min(A.y, B.y));
            if (it != col_dots[A.x].end() && *it < max(A.y, B.y)) return false;
        } else if (A.y - A.x == B.y - B.x) {
            auto it = diag1_dots[A.y - A.x + N - 1].upper_bound(min(A.x, B.x));
            if (it != diag1_dots[A.y - A.x + N - 1].end() && *it < max(A.x, B.x)) return false;
        } else {
            auto it = diag2_dots[A.y + A.x].upper_bound(min(A.x, B.x));
            if (it != diag2_dots[A.y + A.x].end() && *it < max(A.x, B.x)) return false;
        }
    }
    return true;
}

bool check_perimeter_edges(const Point& p1, const Point& p2, const Point& p3, const Point& p4) {
    const array<Point, 5> points = {p1, p2, p3, p4, p1};
    for (int i = 0; i < 4; ++i) {
        Point A = points[i];
        Point B = points[i + 1];
        int dx = B.x - A.x;
        int dy = B.y - A.y;
        int g = std::gcd(abs(dx), abs(dy));
        int ux = dx / g;
        int uy = dy / g;
        for (int j = 0; j < g; ++j) {
            Point start = {A.x + j * ux, A.y + j * uy};
            Point end = {start.x + ux, start.y + uy};
            if (ux == 1 && uy == 0) { if (h_edge[start.y][start.x]) return false;
            } else if (ux == -1 && uy == 0) { if (h_edge[end.y][end.x]) return false;
            } else if (ux == 0 && uy == 1) { if (v_edge[start.y][start.x]) return false;
            } else if (ux == 0 && uy == -1) { if (v_edge[end.y][end.x]) return false;
            } else if (ux == 1 && uy == 1) { if (d1_edge[start.y-start.x+N-1][start.x]) return false;
            } else if (ux == -1 && uy == -1) { if (d1_edge[end.y-end.x+N-1][end.x]) return false;
            } else if (ux == 1 && uy == -1) { if (d2_edge[start.y+start.x][start.x]) return false;
            } else { if (d2_edge[end.y+end.x][end.x]) return false; }
        }
    }
    return true;
}

void add_rectangle_edges(const Point& p1, const Point& p2, const Point& p3, const Point& p4) {
    const array<Point, 5> points = {p1, p2, p3, p4, p1};
    for (int i = 0; i < 4; ++i) {
        Point A = points[i];
        Point B = points[i + 1];
        int dx = B.x - A.x;
        int dy = B.y - A.y;
        int g = std::gcd(abs(dx), abs(dy));
        int ux = dx / g;
        int uy = dy / g;
        for (int j = 0; j < g; ++j) {
            Point start = {A.x + j * ux, A.y + j * uy};
            Point end = {start.x + ux, start.y + uy};
            if (ux == 1 && uy == 0) { h_edge[start.y][start.x] = true;
            } else if (ux == -1 && uy == 0) { h_edge[end.y][end.x] = true;
            } else if (ux == 0 && uy == 1) { v_edge[start.y][start.x] = true;
            } else if (ux == 0 && uy == -1) { v_edge[end.y][end.x] = true;
            } else if (ux == 1 && uy == 1) { d1_edge[start.y-start.x+N-1][start.x] = true;
            } else if (ux == -1 && uy == -1) { d1_edge[end.y-end.x+N-1][end.x] = true;
            } else if (ux == 1 && uy == -1) { d2_edge[start.y+start.x][start.x] = true;
            } else { d2_edge[end.y+end.x][end.x] = true; }
        }
    }
}

void validate_and_push(Point p1, Point p2, Point p3, Point p4) {
    if (is_out_of_bounds(p1) || has_dot[p1.y][p1.x]) return;
    
    Point p_ord[4];
    p_ord[0] = p1;
    if ((long long)(p2.x-p1.x)*(p4.x-p1.x) + (long long)(p2.y-p1.y)*(p4.y-p1.y) == 0) {
        p_ord[1] = p2; p_ord[2] = p3; p_ord[3] = p4;
    } else {
        p_ord[1] = p4; p_ord[2] = p3; p_ord[3] = p2;
    }

    if (!check_perimeter_dots(p_ord[0], p_ord[1], p_ord[2], p_ord[3])) return;
    if (!check_perimeter_edges(p_ord[0], p_ord[1], p_ord[2], p_ord[3])) return;
    
    pq.push({{p1, p2, p3, p4}, weight(p1)});
}


void find_candidates_from_pair(const Point& A, const Point& B) {
    // Axis-aligned, A and B diagonal
    Point C1 = {A.x, B.y};
    Point D1 = {B.x, A.y};
    if (!is_out_of_bounds(C1) && !is_out_of_bounds(D1)) {
        if (has_dot[C1.y][C1.x] && !has_dot[D1.y][D1.x]) {
            validate_and_push(D1, A, C1, B);
        }
        if (has_dot[D1.y][D1.x] && !has_dot[C1.y][C1.x]) {
            validate_and_push(C1, A, D1, B);
        }
    }

    // Tilted, A and B diagonal
    if ((abs(A.x - B.x) % 2) == (abs(A.y - B.y) % 2)) {
        int dx = A.x - B.x;
        int dy = A.y - B.y;
        Point C2 = {(A.x + B.x - dy) / 2, (A.y + B.y + dx) / 2};
        Point D2 = {(A.x + B.x + dy) / 2, (A.y + B.y - dx) / 2};
        if (!is_out_of_bounds(C2) && !is_out_of_bounds(D2)) {
            if (has_dot[C2.y][C2.x] && !has_dot[D2.y][D2.x]) {
                validate_and_push(D2, A, C2, B);
            }
            if (has_dot[D2.y][D2.x] && !has_dot[C2.y][C2.x]) {
                validate_and_push(C2, A, D2, B);
            }
        }
    }
}

void add_dot(const Point& p) {
    has_dot[p.y][p.x] = true;
    dots.push_back(p);
    row_dots[p.y].insert(p.x);
    col_dots[p.x].insert(p.y);
    diag1_dots[p.y - p.x + N - 1].insert(p.x);
    diag2_dots[p.y + p.x].insert(p.x);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_time = chrono::high_resolution_clock::now();

    cin >> N >> M;
    center_x = (N - 1) / 2;
    center_y = (N - 1) / 2;

    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        add_dot({x, y});
    }

    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            find_candidates_from_pair(dots[i], dots[j]);
        }
    }
    
    while (!pq.empty()) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 2800) {
            break;
        }

        Move m = pq.top();
        pq.pop();

        Point p1 = m.r.p1;
        if (has_dot[p1.y][p1.x]) continue;

        Point p2 = m.r.p2, p3 = m.r.p3, p4 = m.r.p4;
        
        Point p_ord[4];
        p_ord[0] = p1;
        if ((long long)(p2.x-p1.x)*(p4.x-p1.x) + (long long)(p2.y-p1.y)*(p4.y-p1.y) == 0) {
            p_ord[1] = p2; p_ord[2] = p3; p_ord[3] = p4;
        } else {
            p_ord[1] = p4; p_ord[2] = p3; p_ord[3] = p2;
        }
        
        if (!check_perimeter_dots(p_ord[0], p_ord[1], p_ord[2], p_ord[3])) continue;
        if (!check_perimeter_edges(p_ord[0], p_ord[1], p_ord[2], p_ord[3])) continue;
        
        result_rects.push_back({p_ord[0], p_ord[1], p_ord[2], p_ord[3]});
        add_rectangle_edges(p_ord[0], p_ord[1], p_ord[2], p_ord[3]);
        
        Point new_dot = p1;
        int old_dots_size = dots.size();
        add_dot(new_dot);
        
        for (int i = 0; i < old_dots_size; ++i) {
            find_candidates_from_pair(new_dot, dots[i]);
        }
    }

    cout << result_rects.size() << "\n";
    for (const auto& r : result_rects) {
        cout << r.p1.x << " " << r.p1.y << " "
             << r.p2.x << " " << r.p2.y << " "
             << r.p3.x << " " << r.p3.y << " "
             << r.p4.x << " " << r.p4.y << "\n";
    }

    return 0;
}