#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

struct Point {
    int x, y;
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

struct Move {
    Point p1; // New dot
    Point p2, p3, p4; // Existing dots: p2 adj, p3 opp, p4 adj
    int weight;
    // For sorting
    bool operator<(const Move& other) const {
        return weight < other.weight;
    }
};

int N, M_init;
vector<Point> initial_dots;
int center_coord;

// State variables
int grid[65][65]; // Stores dot index or -1
bool used_h[65][65]; // (x,y)-(x+1,y)
bool used_v[65][65]; // (x,y)-(x,y+1)
bool used_d1[65][65]; // (x,y)-(x+1,y+1)
bool used_d2[65][65]; // (x,y+1)-(x+1,y)

vector<Point> current_dots;
vector<int> col_dots[65];
vector<int> row_dots[65];
vector<int> d1_dots[130]; // y-x + N
vector<int> d2_dots[130]; // y+x

vector<Move> move_history;
vector<Move> candidates;

// Helper to get weight
int get_weight(int x, int y) {
    int dx = x - center_coord;
    int dy = y - center_coord;
    return dx * dx + dy * dy + 1;
}

// Helper to check boundaries
bool is_valid_pos(int x, int y) {
    return x >= 0 && x < N && y >= 0 && y < N;
}

// Reset state
void reset_state() {
    for (int x = 0; x < N; x++) {
        for (int y = 0; y < N; y++) {
            grid[x][y] = -1;
            used_h[x][y] = false;
            used_v[x][y] = false;
            used_d1[x][y] = false;
            used_d2[x][y] = false;
        }
    }
    for (int i = 0; i < N; i++) {
        col_dots[i].clear();
        row_dots[i].clear();
    }
    for (int i = 0; i < 2 * N; i++) {
        d1_dots[i].clear();
        d2_dots[i].clear();
    }
    current_dots.clear();
    move_history.clear();
    
    for (int i = 0; i < M_init; i++) {
        Point p = initial_dots[i];
        grid[p.x][p.y] = i;
        current_dots.push_back(p);
        col_dots[p.x].push_back(i);
        row_dots[p.y].push_back(i);
        d1_dots[p.y - p.x + N].push_back(i);
        d2_dots[p.y + p.x].push_back(i);
    }
}

// Check if a segment is clear (no overlap, no dots strictly inside)
bool check_segment(Point start, Point end, int& type) {
    int dx = end.x - start.x;
    int dy = end.y - start.y;
    int steps = max(abs(dx), abs(dy));
    if (steps == 0) return false;
    int sx = dx / steps;
    int sy = dy / steps;
    
    if (sx == 1 && sy == 0) type = 0; // Horizontal forward
    else if (sx == -1 && sy == 0) type = 1; // Horizontal backward
    else if (sx == 0 && sy == 1) type = 2; // Vertical up
    else if (sx == 0 && sy == -1) type = 3; // Vertical down
    else if (sx == 1 && sy == 1) type = 4; // D1 up-right
    else if (sx == -1 && sy == -1) type = 5; // D1 down-left
    else if (sx == 1 && sy == -1) type = 6; // D2 down-right
    else if (sx == -1 && sy == 1) type = 7; // D2 up-left
    else return false; 

    int x = start.x;
    int y = start.y;
    for (int k = 0; k < steps; k++) {
        // Check edge usage
        if (type == 0) { if (used_h[x][y]) return false; }
        else if (type == 1) { if (used_h[x-1][y]) return false; }
        else if (type == 2) { if (used_v[x][y]) return false; }
        else if (type == 3) { if (used_v[x][y-1]) return false; }
        else if (type == 4) { if (used_d1[x][y]) return false; }
        else if (type == 5) { if (used_d1[x-1][y-1]) return false; }
        else if (type == 6) { if (used_d2[x][y-1]) return false; }
        else if (type == 7) { if (used_d2[x-1][y]) return false; }

        x += sx;
        y += sy;
        
        // Check for dots, unless it's the end point
        if (k < steps - 1) {
            if (grid[x][y] != -1) return false;
        }
    }
    return true;
}

// Mark edges
void mark_segment(Point start, Point end, int type) {
    int dx = end.x - start.x;
    int dy = end.y - start.y;
    int steps = max(abs(dx), abs(dy));
    int sx = dx / steps;
    int sy = dy / steps;
    int x = start.x;
    int y = start.y;
    for (int k = 0; k < steps; k++) {
        if (type == 0) used_h[x][y] = true;
        else if (type == 1) used_h[x-1][y] = true;
        else if (type == 2) used_v[x][y] = true;
        else if (type == 3) used_v[x][y-1] = true;
        else if (type == 4) used_d1[x][y] = true;
        else if (type == 5) used_d1[x-1][y-1] = true;
        else if (type == 6) used_d2[x][y-1] = true;
        else if (type == 7) used_d2[x-1][y] = true;
        x += sx;
        y += sy;
    }
}

// Validate move fully
bool is_valid_move(const Move& m) {
    if (grid[m.p1.x][m.p1.y] != -1) return false;
    
    int t;
    if (!check_segment(m.p1, m.p2, t)) return false;
    if (!check_segment(m.p2, m.p3, t)) return false;
    if (!check_segment(m.p3, m.p4, t)) return false;
    if (!check_segment(m.p4, m.p1, t)) return false;
    
    return true;
}

void apply_move(const Move& m) {
    int t;
    check_segment(m.p1, m.p2, t); mark_segment(m.p1, m.p2, t);
    check_segment(m.p2, m.p3, t); mark_segment(m.p2, m.p3, t);
    check_segment(m.p3, m.p4, t); mark_segment(m.p3, m.p4, t);
    check_segment(m.p4, m.p1, t); mark_segment(m.p4, m.p1, t);
    
    int idx = current_dots.size();
    grid[m.p1.x][m.p1.y] = idx;
    current_dots.push_back(m.p1);
    
    col_dots[m.p1.x].push_back(idx);
    row_dots[m.p1.y].push_back(idx);
    d1_dots[m.p1.y - m.p1.x + N].push_back(idx);
    d2_dots[m.p1.y + m.p1.x].push_back(idx);
    
    move_history.push_back(m);
}

// Generate candidates involving a specific dot P
void generate_candidates_for(int p_idx, vector<Move>& out) {
    Point P = current_dots[p_idx];
    
    auto add_cand = [&](Point Q, Point A, Point B, Point C) {
        if (!is_valid_pos(Q.x, Q.y)) return;
        if (grid[Q.x][Q.y] != -1) return;
        out.push_back({Q, A, C, B, get_weight(Q.x, Q.y)}); 
    };

    // 1. P is adjacent to A and B. Q is opposite P.
    for (int a_idx : row_dots[P.y]) {
        if (a_idx == p_idx) continue;
        Point A = current_dots[a_idx];
        for (int b_idx : col_dots[P.x]) {
            if (b_idx == p_idx) continue;
            Point B = current_dots[b_idx];
            Point Q = {A.x, B.y}; 
            add_cand(Q, A, P, B);
        }
    }
    
    for (int a_idx : d1_dots[P.y - P.x + N]) {
        if (a_idx == p_idx) continue;
        Point A = current_dots[a_idx];
        for (int b_idx : d2_dots[P.y + P.x]) {
            if (b_idx == p_idx) continue;
            Point B = current_dots[b_idx];
            Point Q = {A.x + B.x - P.x, A.y + B.y - P.y};
            add_cand(Q, A, P, B);
        }
    }

    // 2. P is opposite to some X. Q is a corner.
    for (int x_idx = 0; x_idx < (int)current_dots.size(); x_idx++) {
        if (x_idx == p_idx) continue;
        Point X = current_dots[x_idx];
        
        Point C1 = {P.x, X.y};
        Point C2 = {X.x, P.y};
        if (C1.x == P.x && C1.y == P.y) continue;
        
        int c1_idx = grid[C1.x][C1.y];
        int c2_idx = grid[C2.x][C2.y];
        
        if (c1_idx != -1 && c2_idx == -1) {
            out.push_back({C2, P, C1, X, get_weight(C2.x, C2.y)});
        } else if (c2_idx != -1 && c1_idx == -1) {
            out.push_back({C1, P, C2, X, get_weight(C1.x, C1.y)});
        }
        
        int up = P.x + P.y; int vp = P.x - P.y;
        int ux = X.x + X.y; int vx = X.x - X.y;
        
        if ((up + vx) % 2 == 0) {
            int c1x = (up + vx) / 2;
            int c1y = (up - vx) / 2;
            if (is_valid_pos(c1x, c1y)) {
                int c2x = (ux + vp) / 2;
                int c2y = (ux - vp) / 2;
                if (is_valid_pos(c2x, c2y)) {
                    if (!(c1x == P.x && c1y == P.y)) {
                        int i1 = grid[c1x][c1y];
                        int i2 = grid[c2x][c2y];
                        if (i1 != -1 && i2 == -1) {
                             out.push_back({ {c2x, c2y}, P, {c1x, c1y}, X, get_weight(c2x, c2y) });
                        } else if (i2 != -1 && i1 == -1) {
                             out.push_back({ {c1x, c1y}, P, {c2x, c2y}, X, get_weight(c1x, c1y) });
                        }
                    }
                }
            }
        }
    }
}

vector<Move> best_history;
long long best_score = -1;

void solve(int seed_offset) {
    reset_state();
    
    candidates.clear();
    for (int i = 0; i < M_init; i++) {
        generate_candidates_for(i, candidates);
    }
    
    while (true) {
        sort(candidates.begin(), candidates.end(), [](const Move& a, const Move& b){
            return a.weight > b.weight;
        });
        
        bool found = false;
        Move best_move;
        
        // Lazy invalidation
        vector<Move> next_candidates;
        bool skipped_invalid = false;
        
        for (const auto& m : candidates) {
            if (grid[m.p1.x][m.p1.y] != -1) { skipped_invalid = true; continue; }
            
            if (is_valid_move(m)) {
                best_move = m;
                found = true;
                break;
            } else {
                skipped_invalid = true;
            }
        }
        
        if (!found) break;
        
        apply_move(best_move);
        
        vector<Move> remaining;
        for (const auto& m : candidates) {
            if (m.p1 == best_move.p1 && m.p2 == best_move.p2 && m.p3 == best_move.p3 && m.p4 == best_move.p4) {
                continue;
            }
            if (grid[m.p1.x][m.p1.y] != -1) continue;
            remaining.push_back(m);
        }
        
        vector<Move> new_moves;
        generate_candidates_for(current_dots.size() - 1, new_moves);
        
        candidates = remaining;
        candidates.insert(candidates.end(), new_moves.begin(), new_moves.end());
        
        if (candidates.size() > 40000) {
            nth_element(candidates.begin(), candidates.begin() + 20000, candidates.end(), [](const Move& a, const Move& b){
                return a.weight > b.weight;
            });
            candidates.resize(20000);
        }
    }
    
    long long S = 0;
    for(int x=0; x<N; ++x) for(int y=0; y<N; ++y) S += get_weight(x, y);
    
    long long Q_sum = 0;
    for(const auto& p : current_dots) Q_sum += get_weight(p.x, p.y);
    
    long long current_score = (long long)(1e6 * (double)N * N / M_init * Q_sum / S);
    
    if (current_score > best_score) {
        best_score = current_score;
        best_history = move_history;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M_init)) return 0;
    center_coord = (N - 1) / 2;
    
    initial_dots.resize(M_init);
    for (int i = 0; i < M_init; i++) {
        cin >> initial_dots[i].x >> initial_dots[i].y;
    }
    
    solve(0);

    cout << best_history.size() << "\n";
    for (const auto& m : best_history) {
        cout << m.p1.x << " " << m.p1.y << " " 
             << m.p2.x << " " << m.p2.y << " " 
             << m.p3.x << " " << m.p3.y << " " 
             << m.p4.x << " " << m.p4.y << "\n";
    }
    
    return 0;
}