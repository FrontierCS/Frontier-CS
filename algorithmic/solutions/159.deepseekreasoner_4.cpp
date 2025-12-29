#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
    Point() {}
    Point(int x, int y) : x(x), y(y) {}
};

int N, M;
const int MAX_N = 61;
bool dot[MAX_N][MAX_N];
vector<Point> dots_list;
set<int> row_set[MAX_N];
set<int> col_set[MAX_N];
const int DIAG1_OFFSET = 60;
set<int> diag1_set[2*MAX_N];
set<int> diagm1_set[2*MAX_N];

using Interval = pair<int,int>;
set<Interval> horizontal_intv[MAX_N];
set<Interval> vertical_intv[MAX_N];
set<Interval> diag1_intv[2*MAX_N];
set<Interval> diagm1_intv[2*MAX_N];

int weight[MAX_N][MAX_N];
long long total_weight = 0;

const int MAX_LEN = 10;

bool check_horizontal_no_dots(int y, int x1, int x2) {
    if (x1 > x2) swap(x1, x2);
    auto it = row_set[y].upper_bound(x1);
    return it == row_set[y].end() || *it >= x2;
}

bool check_vertical_no_dots(int x, int y1, int y2) {
    if (y1 > y2) swap(y1, y2);
    auto it = col_set[x].upper_bound(y1);
    return it == col_set[x].end() || *it >= y2;
}

bool check_diag1_no_dots(int c, int x1, int x2) {
    if (x1 > x2) swap(x1, x2);
    auto &s = diag1_set[c + DIAG1_OFFSET];
    auto it = s.upper_bound(x1);
    return it == s.end() || *it >= x2;
}

bool check_diagm1_no_dots(int d, int x1, int x2) {
    if (x1 > x2) swap(x1, x2);
    auto &s = diagm1_set[d];
    auto it = s.upper_bound(x1);
    return it == s.end() || *it >= x2;
}

bool check_edge_no_dots(Point a, Point b) {
    if (a.y == b.y) {
        int y = a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        return check_horizontal_no_dots(y, x1, x2);
    } else if (a.x == b.x) {
        int x = a.x;
        int y1 = min(a.y, b.y), y2 = max(a.y, b.y);
        return check_vertical_no_dots(x, y1, y2);
    } else if (a.x - a.y == b.x - b.y) {
        int c = a.x - a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        return check_diag1_no_dots(c, x1, x2);
    } else if (a.x + a.y == b.x + b.y) {
        int d = a.x + a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        return check_diagm1_no_dots(d, x1, x2);
    }
    return false;
}

bool has_overlap(const set<Interval>& intervals, int a, int b) {
    if (a > b) swap(a, b);
    auto it = intervals.lower_bound({a, a});
    if (it != intervals.end()) {
        if (it->first <= b-1) return true;
    }
    if (it != intervals.begin()) {
        auto it2 = prev(it);
        if (it2->second >= a+1) return true;
    }
    return false;
}

bool check_edge_no_overlap(Point a, Point b) {
    if (a.y == b.y) {
        int y = a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        return !has_overlap(horizontal_intv[y], x1, x2);
    } else if (a.x == b.x) {
        int x = a.x;
        int y1 = min(a.y, b.y), y2 = max(a.y, b.y);
        return !has_overlap(vertical_intv[x], y1, y2);
    } else if (a.x - a.y == b.x - b.y) {
        int c = a.x - a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        return !has_overlap(diag1_intv[c + DIAG1_OFFSET], x1, x2);
    } else if (a.x + a.y == b.x + b.y) {
        int d = a.x + a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        return !has_overlap(diagm1_intv[d], x1, x2);
    }
    return false;
}

bool check_conditions_axis(Point p1, Point p2, Point p3, Point p4) {
    if (!check_edge_no_dots(p1, p2)) return false;
    if (!check_edge_no_dots(p2, p3)) return false;
    if (!check_edge_no_dots(p3, p4)) return false;
    if (!check_edge_no_dots(p4, p1)) return false;
    if (!check_edge_no_overlap(p1, p2)) return false;
    if (!check_edge_no_overlap(p2, p3)) return false;
    if (!check_edge_no_overlap(p3, p4)) return false;
    if (!check_edge_no_overlap(p4, p1)) return false;
    return true;
}

bool check_conditions_diag(Point p1, Point p2, Point p3, Point p4) {
    if (!check_edge_no_dots(p1, p2)) return false;
    if (!check_edge_no_dots(p2, p3)) return false;
    if (!check_edge_no_dots(p3, p4)) return false;
    if (!check_edge_no_dots(p4, p1)) return false;
    if (!check_edge_no_overlap(p1, p2)) return false;
    if (!check_edge_no_overlap(p2, p3)) return false;
    if (!check_edge_no_overlap(p3, p4)) return false;
    if (!check_edge_no_overlap(p4, p1)) return false;
    return true;
}

void add_dot(Point p) {
    dot[p.x][p.y] = true;
    dots_list.push_back(p);
    row_set[p.y].insert(p.x);
    col_set[p.x].insert(p.y);
    diag1_set[p.x - p.y + DIAG1_OFFSET].insert(p.x);
    diagm1_set[p.x + p.y].insert(p.x);
}

void add_segment(Point a, Point b) {
    if (a.y == b.y) {
        int y = a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        horizontal_intv[y].insert({x1, x2});
    } else if (a.x == b.x) {
        int x = a.x;
        int y1 = min(a.y, b.y), y2 = max(a.y, b.y);
        vertical_intv[x].insert({y1, y2});
    } else if (a.x - a.y == b.x - b.y) {
        int c = a.x - a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        diag1_intv[c + DIAG1_OFFSET].insert({x1, x2});
    } else if (a.x + a.y == b.x + b.y) {
        int d = a.x + a.y;
        int x1 = min(a.x, b.x), x2 = max(a.x, b.x);
        diagm1_intv[d].insert({x1, x2});
    }
}

void add_rectangle(Point p1, Point p2, Point p3, Point p4) {
    add_dot(p1);
    add_segment(p1, p2);
    add_segment(p2, p3);
    add_segment(p3, p4);
    add_segment(p4, p1);
}

int main() {
    cin >> N >> M;
    int c = (N-1)/2;
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < N; ++y) {
            int dx = x - c;
            int dy = y - c;
            weight[x][y] = dx*dx + dy*dy + 1;
            total_weight += weight[x][y];
        }
    }
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        Point p(x,y);
        add_dot(p);
    }
    vector<tuple<Point,Point,Point,Point>> operations;
    while (true) {
        Point best_p1, best_p2, best_p3, best_p4;
        int best_weight = -1;
        for (int x = 0; x < N; ++x) {
            const set<int>& col_y = col_set[x];
            if (col_y.size() < 2) continue;
            for (auto it1 = col_y.begin(); it1 != col_y.end(); ++it1) {
                int y1 = *it1;
                auto it2 = next(it1);
                for (; it2 != col_y.end(); ++it2) {
                    int y2 = *it2;
                    if (abs(y2 - y1) > MAX_LEN) continue;
                    for (int x2 : row_set[y2]) {
                        if (x2 == x) continue;
                        Point p1(x2, y1);
                        if (dot[p1.x][p1.y]) continue;
                        Point p2(x, y1);
                        Point p3(x, y2);
                        Point p4(x2, y2);
                        if (check_conditions_axis(p1, p2, p3, p4)) {
                            int w = weight[p1.x][p1.y];
                            if (w > best_weight) {
                                best_weight = w;
                                best_p1 = p1; best_p2 = p2; best_p3 = p3; best_p4 = p4;
                            }
                        }
                    }
                    for (int x2 : row_set[y1]) {
                        if (x2 == x) continue;
                        Point p1(x2, y2);
                        if (dot[p1.x][p1.y]) continue;
                        Point p2(x, y2);
                        Point p3(x, y1);
                        Point p4(x2, y1);
                        if (check_conditions_axis(p1, p2, p3, p4)) {
                            int w = weight[p1.x][p1.y];
                            if (w > best_weight) {
                                best_weight = w;
                                best_p1 = p1; best_p2 = p2; best_p3 = p3; best_p4 = p4;
                            }
                        }
                    }
                }
            }
        }
        for (int y = 0; y < N; ++y) {
            const set<int>& row_x = row_set[y];
            if (row_x.size() < 2) continue;
            for (auto it1 = row_x.begin(); it1 != row_x.end(); ++it1) {
                int x1 = *it1;
                auto it2 = next(it1);
                for (; it2 != row_x.end(); ++it2) {
                    int x2 = *it2;
                    if (abs(x2 - x1) > MAX_LEN) continue;
                    for (int y2 : col_set[x2]) {
                        if (y2 == y) continue;
                        Point p1(x1, y2);
                        if (dot[p1.x][p1.y]) continue;
                        Point p2(x1, y);
                        Point p3(x2, y);
                        Point p4(x2, y2);
                        if (check_conditions_axis(p1, p2, p3, p4)) {
                            int w = weight[p1.x][p1.y];
                            if (w > best_weight) {
                                best_weight = w;
                                best_p1 = p1; best_p2 = p2; best_p3 = p3; best_p4 = p4;
                            }
                        }
                    }
                    for (int y2 : col_set[x1]) {
                        if (y2 == y) continue;
                        Point p1(x2, y2);
                        if (dot[p1.x][p1.y]) continue;
                        Point p2(x2, y);
                        Point p3(x1, y);
                        Point p4(x1, y2);
                        if (check_conditions_axis(p1, p2, p3, p4)) {
                            int w = weight[p1.x][p1.y];
                            if (w > best_weight) {
                                best_weight = w;
                                best_p1 = p1; best_p2 = p2; best_p3 = p3; best_p4 = p4;
                            }
                        }
                    }
                }
            }
        }
        int D = dots_list.size();
        for (int i = 0; i < D; ++i) {
            Point p2 = dots_list[i];
            for (int j = 0; j < D; ++j) {
                if (i == j) continue;
                Point p4 = dots_list[j];
                int A = p2.x + p2.y;
                int B = p4.y - p4.x;
                if ((A + B) % 2 != 0) continue;
                int y3 = (A + B) / 2;
                int x3 = (A - B) / 2;
                if (x3 < 0 || x3 >= N || y3 < 0 || y3 >= N) continue;
                if (!dot[x3][y3]) continue;
                int a = x3 - p4.x;
                int b = x3 - p2.x;
                if (abs(a) > MAX_LEN || abs(b) > MAX_LEN) continue;
                if (a == 0 || b == 0) continue;
                int x1 = p2.x - a;
                int y1 = p2.y - a;
                if (x1 < 0 || x1 >= N || y1 < 0 || y1 >= N) continue;
                if (dot[x1][y1]) continue;
                Point p1(x1, y1);
                Point p3(x3, y3);
                if (check_conditions_diag(p1, p2, p3, p4)) {
                    int w = weight[p1.x][p1.y];
                    if (w > best_weight) {
                        best_weight = w;
                        best_p1 = p1; best_p2 = p2; best_p3 = p3; best_p4 = p4;
                    }
                }
            }
        }
        if (best_weight == -1) break;
        add_rectangle(best_p1, best_p2, best_p3, best_p4);
        operations.push_back({best_p1, best_p2, best_p3, best_p4});
    }
    cout << operations.size() << endl;
    for (auto& op : operations) {
        Point p1, p2, p3, p4;
        tie(p1, p2, p3, p4) = op;
        cout << p1.x << " " << p1.y << " "
             << p2.x << " " << p2.y << " "
             << p3.x << " " << p3.y << " "
             << p4.x << " " << p4.y << endl;
    }
    return 0;
}