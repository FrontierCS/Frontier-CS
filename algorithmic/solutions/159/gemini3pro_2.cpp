#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

const int MAXN = 65;

struct Point {
    int x, y;
    bool operator==(const Point& other) const { return x == other.x && y == other.y; }
};

struct Move {
    Point p1, p2, p3, p4;
    int score;
};

int N, M;
int center_coord;
bool has_dot[MAXN][MAXN];

// Directions
// Axis: 0:R, 1:U, 2:L, 3:D
int dx_axis[4] = {1, 0, -1, 0};
int dy_axis[4] = {0, 1, 0, -1};
// Diag: 0:UR, 1:UL, 2:DL, 3:DR
int dx_diag[4] = {1, -1, -1, 1};
int dy_diag[4] = {1, 1, -1, -1};

int get_weight(int x, int y) {
    int dx = x - center_coord;
    int dy = y - center_coord;
    return dx*dx + dy*dy + 1;
}

bool is_in(int x, int y) {
    return x >= 0 && x < N && y >= 0 && y < N;
}

// Check if segment has dots strictly inside
bool segment_has_dots(int x1, int y1, int x2, int y2, const bool cur_has_dot[MAXN][MAXN]) {
    int dx = x2 - x1;
    int dy = y2 - y1;
    int steps = max(abs(dx), abs(dy));
    if (steps <= 1) return false;
    int sdx = dx / steps;
    int sdy = dy / steps;
    for (int i = 1; i < steps; ++i) {
        if (cur_has_dot[x1 + i * sdx][y1 + i * sdy]) return true;
    }
    return false;
}

// Mark or check edges occupancy
bool check_edges(Point p1, Point p2, Point p3, Point p4, bool check_only, 
                 bool (&uh)[MAXN][MAXN], bool (&uv)[MAXN][MAXN], 
                 bool (&ud1)[MAXN][MAXN], bool (&ud2)[MAXN][MAXN]) {
    Point pts[4] = {p1, p2, p3, p4};
    for (int i = 0; i < 4; ++i) {
        Point u = pts[i];
        Point v = pts[(i+1)%4];
        int dx = v.x - u.x;
        int dy = v.y - u.y;
        int len = max(abs(dx), abs(dy));
        int sx = dx / len;
        int sy = dy / len;
        int cx = u.x;
        int cy = u.y;
        for (int k = 0; k < len; ++k) {
            if (sx == 1 && sy == 0) { // H Right
                if (check_only && uh[cy][cx]) return false;
                if (!check_only) uh[cy][cx] = true;
            } else if (sx == -1 && sy == 0) { // H Left
                if (check_only && uh[cy][cx-1]) return false;
                if (!check_only) uh[cy][cx-1] = true;
            } else if (sx == 0 && sy == 1) { // V Up
                if (check_only && uv[cx][cy]) return false;
                if (!check_only) uv[cx][cy] = true;
            } else if (sx == 0 && sy == -1) { // V Down
                if (check_only && uv[cx][cy-1]) return false;
                if (!check_only) uv[cx][cy-1] = true;
            } else if (sx == 1 && sy == 1) { // D2 UR
                if (check_only && ud2[cx][cy]) return false;
                if (!check_only) ud2[cx][cy] = true;
            } else if (sx == -1 && sy == -1) { // D2 DL
                if (check_only && ud2[cx-1][cy-1]) return false;
                if (!check_only) ud2[cx-1][cy-1] = true;
            } else if (sx == 1 && sy == -1) { // D1 DR
                if (check_only && ud1[cx][cy]) return false;
                if (!check_only) ud1[cx][cy] = true;
            } else if (sx == -1 && sy == 1) { // D1 UL
                if (check_only && ud1[cx-1][cy+1]) return false;
                if (!check_only) ud1[cx-1][cy+1] = true;
            }
            cx += sx;
            cy += sy;
        }
    }
    return true;
}

struct State {
    vector<Point> dots;
    vector<Move> history;
    bool local_has_dot[MAXN][MAXN];
    bool local_used_h[MAXN][MAXN];
    bool local_used_v[MAXN][MAXN];
    bool local_used_d1[MAXN][MAXN];
    bool local_used_d2[MAXN][MAXN];
};

vector<Move> best_history;
long long best_score_total = -1;

void solve() {
    State st;
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) {
        st.local_has_dot[i][j] = has_dot[i][j];
        st.local_used_h[i][j] = false;
        st.local_used_v[i][j] = false;
        st.local_used_d1[i][j] = false;
        st.local_used_d2[i][j] = false;
        if(has_dot[i][j]) st.dots.push_back({i, j});
    }

    while(true) {
        vector<Move> candidates;
        for (const auto& p3 : st.dots) {
            // Check Axis Neighbors
            Point neighbors[4];
            bool has_n[4] = {false};
            for(int d=0; d<4; ++d) {
                int k = 1;
                while(true) {
                    int nx = p3.x + k*dx_axis[d];
                    int ny = p3.y + k*dy_axis[d];
                    if (!is_in(nx, ny)) break;
                    if (st.local_has_dot[nx][ny]) {
                        neighbors[d] = {nx, ny};
                        has_n[d] = true;
                        break;
                    }
                    k++;
                }
            }
            // Axis Pairs: (R, U), (U, L), (L, D), (D, R) -> (0,1), (1,2), (2,3), (3,0)
            int axis_pairs[4][2] = {{0, 1}, {1, 2}, {2, 3}, {3, 0}};
            for(int i=0; i<4; ++i) {
                int d1 = axis_pairs[i][0];
                int d2 = axis_pairs[i][1];
                if (has_n[d1] && has_n[d2]) {
                    Point p2 = neighbors[d1];
                    Point p4 = neighbors[d2];
                    Point p1 = {p2.x + p4.x - p3.x, p2.y + p4.y - p3.y};
                    if (is_in(p1.x, p1.y) && !st.local_has_dot[p1.x][p1.y]) {
                        // Check empty segments
                        if (!segment_has_dots(p1.x, p1.y, p2.x, p2.y, st.local_has_dot) &&
                            !segment_has_dots(p1.x, p1.y, p4.x, p4.y, st.local_has_dot)) {
                            // Check edges not intersecting existing
                            if (check_edges(p1, p2, p3, p4, true, st.local_used_h, st.local_used_v, st.local_used_d1, st.local_used_d2)) {
                                candidates.push_back({p1, p2, p3, p4, get_weight(p1.x, p1.y)});
                            }
                        }
                    }
                }
            }
            
            // Check Diag Neighbors
            Point d_neighbors[4];
            bool has_dn[4] = {false};
            for(int d=0; d<4; ++d) {
                int k = 1;
                while(true) {
                    int nx = p3.x + k*dx_diag[d];
                    int ny = p3.y + k*dy_diag[d];
                    if (!is_in(nx, ny)) break;
                    if (st.local_has_dot[nx][ny]) {
                        d_neighbors[d] = {nx, ny};
                        has_dn[d] = true;
                        break;
                    }
                    k++;
                }
            }
            // Diag Pairs: (UR, UL), (UL, DL), (DL, DR), (DR, UR) -> (0,1), (1,2), (2,3), (3,0)
            int diag_pairs[4][2] = {{0, 1}, {1, 2}, {2, 3}, {3, 0}};
            for(int i=0; i<4; ++i) {
                int d1 = diag_pairs[i][0];
                int d2 = diag_pairs[i][1];
                if (has_dn[d1] && has_dn[d2]) {
                    Point p2 = d_neighbors[d1];
                    Point p4 = d_neighbors[d2];
                    Point p1 = {p2.x + p4.x - p3.x, p2.y + p4.y - p3.y};
                    if (is_in(p1.x, p1.y) && !st.local_has_dot[p1.x][p1.y]) {
                        if (!segment_has_dots(p1.x, p1.y, p2.x, p2.y, st.local_has_dot) &&
                            !segment_has_dots(p1.x, p1.y, p4.x, p4.y, st.local_has_dot)) {
                             if (check_edges(p1, p2, p3, p4, true, st.local_used_h, st.local_used_v, st.local_used_d1, st.local_used_d2)) {
                                candidates.push_back({p1, p2, p3, p4, get_weight(p1.x, p1.y)});
                            }
                        }
                    }
                }
            }
        }
        
        if (candidates.empty()) break;
        
        // Randomized greedy
        for(auto& mv : candidates) {
            double rnd = (double)rand() / RAND_MAX;
            mv.score = (int)(mv.score * (1.0 + rnd * 0.2)); 
        }
        
        sort(candidates.begin(), candidates.end(), [](const Move& a, const Move& b){
            return a.score > b.score;
        });
        
        Move best = candidates[0];
        
        st.history.push_back(best);
        st.local_has_dot[best.p1.x][best.p1.y] = true;
        st.dots.push_back(best.p1);
        check_edges(best.p1, best.p2, best.p3, best.p4, false, st.local_used_h, st.local_used_v, st.local_used_d1, st.local_used_d2);
    }
    
    long long sum_w = 0;
    for(const auto& p : st.dots) sum_w += get_weight(p.x, p.y);
    
    if (sum_w > best_score_total) {
        best_score_total = sum_w;
        best_history = st.history;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(0);
    
    if (!(cin >> N >> M)) return 0;
    center_coord = (N - 1) / 2;
    
    for(int i=0; i<M; ++i) {
        int x, y;
        cin >> x >> y;
        has_dot[x][y] = true;
    }
    
    clock_t start_time = clock();
    double time_limit = 1.8;
    
    while(true) {
        solve();
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > time_limit) break;
    }
    
    cout << best_history.size() << "\n";
    for(const auto& mv : best_history) {
        cout << mv.p1.x << " " << mv.p1.y << " " 
             << mv.p2.x << " " << mv.p2.y << " " 
             << mv.p3.x << " " << mv.p3.y << " " 
             << mv.p4.x << " " << mv.p4.y << "\n";
    }
    
    return 0;
}