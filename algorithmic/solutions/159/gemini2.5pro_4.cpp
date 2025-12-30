#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>
#include <queue>
#include <chrono>

#pragma GCC optimize("O3,unroll-loops")

using namespace std;

auto start_time = chrono::high_resolution_clock::now();

struct Point {
    int x, y;

    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }

    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

struct Segment {
    Point p1, p2;

    bool operator<(const Segment& other) const {
        if (p1 < other.p1) return true;
        if (other.p1 < p1) return false;
        return p2 < other.p2;
    }
};

Segment make_segment(Point p1, Point p2) {
    if (p2 < p1) swap(p1, p2);
    return {p1, p2};
}

struct Operation {
    Point p1, p2, p3, p4;
};

struct Candidate {
    Point p1, p2, p3, p4;
    long long weight;

    bool operator<(const Candidate& other) const {
        return weight < other.weight;
    }
};

int N, M;
int C;
bool has_dot[62][62];
vector<Point> dots;
set<Segment> drawn_segments;
vector<Operation> history;

long long get_weight(Point p) {
    long long dx = p.x - C;
    long long dy = p.y - C;
    return dx * dx + dy * dy + 1;
}

bool is_in_bounds(Point p) {
    return p.x >= 0 && p.x < N && p.y >= 0 && p.y < N;
}

int gcd(int a, int b) {
    return b == 0 ? a : gcd(b, a % b);
}

bool check_perimeter(Point p1, Point p2, Point p3, Point p4) {
    Point points[] = {p1, p2, p3, p4, p1};
    for (int i = 0; i < 4; ++i) {
        Point pa = points[i];
        Point pb = points[i+1];
        int dx = pb.x - pa.x;
        int dy = pb.y - pa.y;
        int common_divisor = gcd(abs(dx), abs(dy));
        if (common_divisor > 1) {
            for (int j = 1; j < common_divisor; ++j) {
                Point mid = {pa.x + j * dx / common_divisor, pa.y + j * dy / common_divisor};
                if (has_dot[mid.x][mid.y]) {
                    return false;
                }
            }
        }
    }
    return true;
}

bool check_segments(Point p1, Point p2, Point p3, Point p4) {
    if (drawn_segments.count(make_segment(p1, p2))) return false;
    if (drawn_segments.count(make_segment(p2, p3))) return false;
    if (drawn_segments.count(make_segment(p3, p4))) return false;
    if (drawn_segments.count(make_segment(p4, p1))) return false;
    return true;
}

priority_queue<Candidate> pq;

void add_candidate(Point p1, Point d_a, Point d_b, Point d_c) {
    if (!is_in_bounds(p1) || has_dot[p1.x][p1.y]) return;

    Point p2, p3, p4;

    if ((long long)(d_a.x - p1.x) * (d_b.x - p1.x) + (long long)(d_a.y - p1.y) * (d_b.y - p1.y) == 0) {
        Point p3_cand = {d_a.x + d_b.x - p1.x, d_a.y + d_b.y - p1.y};
        if (p3_cand == d_c) {
            p2 = d_a; p3 = d_c; p4 = d_b;
            if (check_perimeter(p1, p2, p3, p4) && check_segments(p1, p2, p3, p4)) {
                pq.push({p1, p2, p3, p4, get_weight(p1)});
            }
            return;
        }
    }
    if ((long long)(d_a.x - p1.x) * (d_c.x - p1.x) + (long long)(d_a.y - p1.y) * (d_c.y - p1.y) == 0) {
        Point p3_cand = {d_a.x + d_c.x - p1.x, d_a.y + d_c.y - p1.y};
        if (p3_cand == d_b) {
            p2 = d_a; p3 = d_b; p4 = d_c;
            if (check_perimeter(p1, p2, p3, p4) && check_segments(p1, p2, p3, p4)) {
                pq.push({p1, p2, p3, p4, get_weight(p1)});
            }
            return;
        }
    }
    if ((long long)(d_b.x - p1.x) * (d_c.x - p1.x) + (long long)(d_b.y - p1.y) * (d_c.y - p1.y) == 0) {
        Point p3_cand = {d_b.x + d_c.x - p1.x, d_b.y + d_c.y - p1.y};
        if (p3_cand == d_a) {
            p2 = d_b; p3 = d_a; p4 = d_c;
            if (check_perimeter(p1, p2, p3, p4) && check_segments(p1, p2, p3, p4)) {
                pq.push({p1, p2, p3, p4, get_weight(p1)});
            }
            return;
        }
    }
}

void find_candidates_from_pair(const Point& d1, const Point& d2) {
    // Axis-aligned, d1, d2 are opposite
    Point p_c = {d1.x, d2.y};
    Point p_d = {d2.x, d1.y};
    if (is_in_bounds(p_c) && has_dot[p_c.x][p_c.y]) add_candidate(p_d, d1, p_c, d2);
    if (is_in_bounds(p_d) && has_dot[p_d.x][p_d.y]) add_candidate(p_c, d1, p_d, d2);

    // 45-degree, d1, d2 are opposite
    int dx = d2.x - d1.x;
    int dy = d2.y - d1.y;
    if (((dx % 2) + 2) % 2 == ((dy % 2) + 2) % 2) {
        Point p_e = {(d1.x + d2.x - dy) / 2, (d1.y + d2.y + dx) / 2};
        Point p_f = {(d1.x + d2.x + dy) / 2, (d1.y + d2.y - dx) / 2};
        if (is_in_bounds(p_e) && has_dot[p_e.x][p_e.y]) add_candidate(p_f, d1, p_e, d2);
        if (is_in_bounds(p_f) && has_dot[p_f.x][p_f.y]) add_candidate(p_e, d1, p_f, d2);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;
    C = (N - 1) / 2;
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        dots.push_back({x, y});
        has_dot[x][y] = true;
    }

    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            find_candidates_from_pair(dots[i], dots[j]);
        }
    }

    int time_limit_ms = 2800 + (N-31)*5;

    while (!pq.empty()) {
        auto elapsed_time = chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - start_time).count();
        if (elapsed_time > time_limit_ms) {
            break;
        }

        Candidate best = pq.top();
        pq.pop();

        if (has_dot[best.p1.x][best.p1.y]) {
            continue;
        }
        
        if (!check_perimeter(best.p1, best.p2, best.p3, best.p4) || !check_segments(best.p1, best.p2, best.p3, best.p4)) {
            continue;
        }

        history.push_back({best.p1, best.p2, best.p3, best.p4});
        Point p_new = best.p1;
        
        has_dot[p_new.x][p_new.y] = true;
        drawn_segments.insert(make_segment(best.p1, best.p2));
        drawn_segments.insert(make_segment(best.p2, best.p3));
        drawn_segments.insert(make_segment(best.p3, best.p4));
        drawn_segments.insert(make_segment(best.p4, best.p1));
        
        for (const auto& p_old : dots) {
            find_candidates_from_pair(p_new, p_old);
        }
        dots.push_back(p_new);
    }

    cout << history.size() << "\n";
    for (const auto& op : history) {
        cout << op.p1.x << " " << op.p1.y << " "
             << op.p2.x << " " << op.p2.y << " "
             << op.p3.x << " " << op.p3.y << " "
             << op.p4.x << " " << op.p4.y << "\n";
    }

    return 0;
}