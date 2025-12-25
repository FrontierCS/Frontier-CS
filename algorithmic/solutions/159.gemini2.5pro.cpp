#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <queue>
#include <set>

using namespace std;

const int MAXN = 61;

int N, M;
double C;

struct Pt {
    int x, y;
    bool operator<(const Pt& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
    bool operator==(const Pt& other) const {
        return x == other.x && y == other.y;
    }
};

struct Rect {
    Pt p1, p2, p3, p4;
};

struct Candidate {
    Rect rect;
    long long weight;
    bool operator<(const Candidate& other) const {
        return weight < other.weight;
    }
};

bool has_dot[MAXN][MAXN];
bool used_h[MAXN + 1][MAXN];
bool used_v[MAXN][MAXN + 1];
bool used_d1[MAXN][MAXN];
bool used_d2[MAXN][MAXN];
vector<Pt> dots;
priority_queue<Candidate> pq;

long long get_weight(int x, int y) {
    long long dx = x - C;
    long long dy = y - C;
    return dx * dx + dy * dy + 1;
}

int gcd(int a, int b) {
    return b == 0 ? a : gcd(b, a % b);
}

bool is_valid_point(const Pt& p) {
    return p.x >= 0 && p.x < N && p.y >= 0 && p.y < N;
}

bool check_perimeter(const Rect& r) {
    Pt p[4] = {r.p1, r.p2, r.p3, r.p4};
    for (int i = 0; i < 4; ++i) {
        Pt p_start = p[i];
        Pt p_end = p[(i + 1) % 4];
        if (p_start == p_end) continue;
        int dx = p_end.x - p_start.x;
        int dy = p_end.y - p_start.y;
        int g = gcd(abs(dx), abs(dy));
        if (g == 0) continue;
        int step_x = dx / g;
        int step_y = dy / g;
        for (int j = 1; j < g; ++j) {
            if (has_dot[p_start.x + j * step_x][p_start.y + j * step_y]) {
                return false;
            }
        }
    }
    return true;
}

bool check_segments(const Rect& r) {
    Pt p[4] = {r.p1, r.p2, r.p3, r.p4};
    for (int i = 0; i < 4; ++i) {
        Pt p_start = p[i];
        Pt p_end = p[(i + 1) % 4];
        if (p_start == p_end) continue;
        int dx = p_end.x - p_start.x;
        int dy = p_end.y - p_start.y;
        int g = gcd(abs(dx), abs(dy));
        if (g == 0) continue;
        int step_x = dx / g;
        int step_y = dy / g;
        for (int j = 0; j < g; ++j) {
            int cur_x = p_start.x + j * step_x;
            int cur_y = p_start.y + j * step_y;
            if (step_x == 1 && step_y == 0) { if (used_h[cur_y][cur_x]) return false; }
            else if (step_x == -1 && step_y == 0) { if (used_h[cur_y][cur_x - 1]) return false; }
            else if (step_x == 0 && step_y == 1) { if (used_v[cur_y][cur_x]) return false; }
            else if (step_x == 0 && step_y == -1) { if (used_v[cur_y - 1][cur_x]) return false; }
            else if (step_x == 1 && step_y == 1) { if (used_d1[cur_y][cur_x]) return false; }
            else if (step_x == -1 && step_y == -1) { if (used_d1[cur_y - 1][cur_x - 1]) return false; }
            else if (step_x == 1 && step_y == -1) { if (used_d2[cur_y][cur_x]) return false; }
            else if (step_x == -1 && step_y == 1) { if (used_d2[cur_y-1][cur_x-1]) return false; }
        }
    }
    return true;
}

void apply_move(const Rect& r) {
    Pt p[4] = {r.p1, r.p2, r.p3, r.p4};
    for (int i = 0; i < 4; ++i) {
        Pt p_start = p[i];
        Pt p_end = p[(i + 1) % 4];
        if (p_start == p_end) continue;
        int dx = p_end.x - p_start.x;
        int dy = p_end.y - p_start.y;
        int g = gcd(abs(dx), abs(dy));
        if (g == 0) continue;
        int step_x = dx / g;
        int step_y = dy / g;
        for (int j = 0; j < g; ++j) {
            int cur_x = p_start.x + j * step_x;
            int cur_y = p_start.y + j * step_y;
            if (step_x == 1 && step_y == 0) used_h[cur_y][cur_x] = true;
            else if (step_x == -1 && step_y == 0) used_h[cur_y][cur_x - 1] = true;
            else if (step_x == 0 && step_y == 1) used_v[cur_y][cur_x] = true;
            else if (step_x == 0 && step_y == -1) used_v[cur_y - 1][cur_x] = true;
            else if (step_x == 1 && step_y == 1) used_d1[cur_y][cur_x] = true;
            else if (step_x == -1 && step_y == -1) used_d1[cur_y - 1][cur_x - 1] = true;
            else if (step_x == 1 && step_y == -1) used_d2[cur_y][cur_x] = true;
            else if (step_x == -1 && step_y == 1) used_d2[cur_y-1][cur_x-1] = true;
        }
    }
}

void find_moves(const Pt& p1, const Pt& p2) {
    // Axis-aligned
    Pt p3 = {p1.x, p2.y};
    Pt p4 = {p2.x, p1.y};
    if (is_valid_point(p3) && is_valid_point(p4)) {
        if (has_dot[p3.x][p3.y] && !has_dot[p4.x][p4.y]) {
            Rect r = {p4, p1, p3, p2};
            if (check_perimeter(r) && check_segments(r)) {
                pq.push({r, get_weight(p4.x, p4.y)});
            }
        }
        if (!has_dot[p3.x][p3.y] && has_dot[p4.x][p4.y]) {
            Rect r = {p3, p1, p4, p2};
            if (check_perimeter(r) && check_segments(r)) {
                pq.push({r, get_weight(p3.x, p3.y)});
            }
        }
    }

    // 45-degree
    int dx = p2.x - p1.x;
    int dy = p2.y - p1.y;
    if ((p1.x + p2.x - dy) % 2 != 0 || (p1.y + p2.y + dx) % 2 != 0) return;
    
    Pt p3_t = {(p1.x + p2.x - dy) / 2, (p1.y + p2.y + dx) / 2};
    Pt p4_t = {(p1.x + p2.x + dy) / 2, (p1.y + p2.y - dx) / 2};
    if (is_valid_point(p3_t) && is_valid_point(p4_t)) {
        if (has_dot[p3_t.x][p3_t.y] && !has_dot[p4_t.x][p4_t.y]) {
            Rect r = {p4_t, p1, p3_t, p2};
            if (check_perimeter(r) && check_segments(r)) {
                pq.push({r, get_weight(p4_t.x, p4_t.y)});
            }
        }
        if (!has_dot[p3_t.x][p3_t.y] && has_dot[p4_t.x][p4_t.y]) {
            Rect r = {p3_t, p1, p4_t, p2};
            if (check_perimeter(r) && check_segments(r)) {
                pq.push({r, get_weight(p3_t.x, p3_t.y)});
            }
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    auto start_time = chrono::high_resolution_clock::now();

    cin >> N >> M;
    C = (N - 1.0) / 2.0;

    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        if (!has_dot[x][y]) {
            has_dot[x][y] = true;
            dots.push_back({x, y});
        }
    }

    for (size_t i = 0; i < dots.size(); ++i) {
        for (size_t j = i + 1; j < dots.size(); ++j) {
            find_moves(dots[i], dots[j]);
        }
    }

    vector<Rect> solution;
    while (!pq.empty()) {
        auto now = chrono::high_resolution_clock::now();
        auto duration = chrono::duration_cast<chrono::milliseconds>(now - start_time).count();
        if (duration > 2900) {
            break;
        }

        Candidate cand = pq.top();
        pq.pop();
        Rect r = cand.rect;

        if (has_dot[r.p1.x][r.p1.y]) continue;

        if (check_perimeter(r) && check_segments(r)) {
            solution.push_back(r);
            has_dot[r.p1.x][r.p1.y] = true;
            apply_move(r);
            
            Pt new_dot = r.p1;
            for (const auto& old_dot : dots) {
                find_moves(new_dot, old_dot);
            }
            dots.push_back(new_dot);
        }
    }

    cout << solution.size() << endl;
    for (const auto& r : solution) {
        cout << r.p1.x << " " << r.p1.y << " "
             << r.p2.x << " " << r.p2.y << " "
             << r.p3.x << " " << r.p3.y << " "
             << r.p4.x << " " << r.p4.y << endl;
    }

    return 0;
}