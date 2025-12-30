#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Time limit control
const double TIME_LIMIT = 1.95; 

struct Point {
    int x, y;
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
};

struct Rect {
    Point p1, p2, p3, p4;
};

int N, M;
int center_coord;

// Weights
vector<vector<int>> weights;
int get_weight(int x, int y) {
    int dx = x - center_coord;
    int dy = y - center_coord;
    return dx*dx + dy*dy + 1;
}

// Global random engine
mt19937 rng(12345);

// Grid State
struct State {
    vector<vector<bool>> has_dot;
    // Edges
    // 0: Horizontal (y, x) -> (x, x+1)
    // 1: Vertical (x, y) -> (y, y+1)
    // 2: Diag1 (x, y) -> (x+1, y+1)
    // 3: Diag2 (x, y) -> (x+1, y-1)
    vector<vector<bool>> used_h;
    vector<vector<bool>> used_v;
    vector<vector<bool>> used_d1;
    vector<vector<bool>> used_d2;
    
    vector<Rect> history;
    long long current_score;

    State() {
        has_dot.assign(N, vector<bool>(N, false));
        used_h.assign(N, vector<bool>(N, false));
        used_v.assign(N, vector<bool>(N, false));
        used_d1.assign(N, vector<bool>(N, false));
        used_d2.assign(N, vector<bool>(N, false));
        current_score = 0;
    }

    void add_dot(int x, int y) {
        if (!has_dot[x][y]) {
            has_dot[x][y] = true;
        }
    }

    // Check if a segment is clear of dots (excluding endpoints)
    bool is_segment_clear_of_dots(Point a, Point b) const {
        int dx = b.x - a.x;
        int dy = b.y - a.y;
        int steps = max(abs(dx), abs(dy));
        if (steps <= 1) return true;
        
        int sx = dx / steps;
        int sy = dy / steps;
        
        for (int i = 1; i < steps; ++i) {
            if (has_dot[a.x + i * sx][a.y + i * sy]) return false;
        }
        return true;
    }

    // Check if segment is free of used edges
    bool is_segment_free(Point a, Point b) const {
        int dx = b.x - a.x;
        int dy = b.y - a.y;
        int steps = max(abs(dx), abs(dy));
        if (steps == 0) return true;
        
        int sx = dx / steps;
        int sy = dy / steps;
        
        // Determine type
        // H: dy=0, V: dx=0, D1: dx=dy, D2: dx=-dy
        int type = -1;
        if (dy == 0) type = 0;
        else if (dx == 0) type = 1;
        else if (dx == dy) type = 2;
        else if (dx == -dy) type = 3;
        else return false; 

        int cx = a.x;
        int cy = a.y;
        for (int i = 0; i < steps; ++i) {
            int u = cx, v = cy;
            if (type == 0) { // Horizontal
                if (sx < 0) u--; 
                if (used_h[v][u]) return false;
            } else if (type == 1) { // Vertical
                if (sy < 0) v--;
                if (used_v[u][v]) return false;
            } else if (type == 2) { // D1 (1, 1)
                if (sx < 0) { u--; v--; }
                if (used_d1[u][v]) return false;
            } else if (type == 3) { // D2 (1, -1)
                if (sx < 0) { u--; v++; }
                if (used_d2[u][v]) return false;
            }
            cx += sx;
            cy += sy;
        }
        return true;
    }

    void mark_segment(Point a, Point b) {
        int dx = b.x - a.x;
        int dy = b.y - a.y;
        int steps = max(abs(dx), abs(dy));
        int sx = dx / steps;
        int sy = dy / steps;
        
        int type = -1;
        if (dy == 0) type = 0;
        else if (dx == 0) type = 1;
        else if (dx == dy) type = 2;
        else if (dx == -dy) type = 3;

        int cx = a.x;
        int cy = a.y;
        for (int i = 0; i < steps; ++i) {
            int u = cx, v = cy;
            if (type == 0) {
                if (sx < 0) u--;
                used_h[v][u] = true;
            } else if (type == 1) {
                if (sy < 0) v--;
                used_v[u][v] = true;
            } else if (type == 2) {
                if (sx < 0) { u--; v--; }
                used_d1[u][v] = true;
            } else if (type == 3) {
                if (sx < 0) { u--; v++; }
                used_d2[u][v] = true;
            }
            cx += sx;
            cy += sy;
        }
    }
};

// Precompute directions
// 0: E (1,0), 1: N (0,1), 2: W (-1,0), 3: S (0,-1)
// 4: NE (1,1), 5: NW (-1,1), 6: SW (-1,-1), 7: SE (1,-1)
const int DX[8] = {1, 0, -1, 0, 1, -1, -1, 1};
const int DY[8] = {0, 1, 0, -1, 1, 1, -1, -1};
// Orthogonal pairs
const int PAIRS[8][2] = {
    {0, 1}, {1, 2}, {2, 3}, {3, 0},
    {4, 5}, {5, 6}, {6, 7}, {7, 4}
};

vector<Point> initial_dots;

struct Move {
    Point p1, p2, p3, p4;
    int weight;
};

// Scan from p1 in direction d to find first dot
Point scan(const State& state, Point p1, int d) {
    int x = p1.x + DX[d];
    int y = p1.y + DY[d];
    while (x >= 0 && x < N && y >= 0 && y < N) {
        if (state.has_dot[x][y]) return {x, y};
        x += DX[d];
        y += DY[d];
    }
    return {-1, -1};
}

void solve() {
    cin >> N >> M;
    center_coord = (N - 1) / 2;
    weights.assign(N, vector<int>(N));
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < N; ++y) {
            weights[x][y] = get_weight(x, y);
        }
    }

    State initial_state;
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        initial_state.add_dot(x, y);
        initial_dots.push_back({x, y});
    }
    
    // Sort empty points by weight descending
    vector<Point> all_points;
    for(int x=0; x<N; ++x) {
        for(int y=0; y<N; ++y) {
            all_points.push_back({x, y});
        }
    }
    sort(all_points.begin(), all_points.end(), [&](Point a, Point b){
        return weights[a.x][a.y] > weights[b.x][b.y];
    });

    auto start_time = chrono::high_resolution_clock::now();
    
    State best_state = initial_state;
    long long best_score = 0; 

    while (true) {
        auto curr_time = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(curr_time - start_time).count();
        if (elapsed > TIME_LIMIT) break;

        State current_state = initial_state;
        long long current_added_score = 0;
        
        while (true) {
            vector<Move> candidates;
            int moves_found = 0;
            int points_checked = 0;
            
            for (const auto& p1 : all_points) {
                if (current_state.has_dot[p1.x][p1.y]) continue;
                
                points_checked++;
                if (points_checked > 800 && candidates.size() > 0) break;
                
                for (int i = 0; i < 8; ++i) {
                    int d1 = PAIRS[i][0];
                    int d2 = PAIRS[i][1];
                    
                    Point p2 = scan(current_state, p1, d1);
                    if (p2.x == -1) continue;
                    Point p4 = scan(current_state, p1, d2);
                    if (p4.x == -1) continue;
                    
                    Point p3 = {p2.x + p4.x - p1.x, p2.y + p4.y - p1.y};
                    
                    if (p3.x < 0 || p3.x >= N || p3.y < 0 || p3.y >= N) continue;
                    if (!current_state.has_dot[p3.x][p3.y]) continue;
                    
                    if (!current_state.is_segment_clear_of_dots(p2, p3)) continue;
                    if (!current_state.is_segment_clear_of_dots(p4, p3)) continue;
                    
                    if (!current_state.is_segment_free(p1, p2)) continue;
                    if (!current_state.is_segment_free(p2, p3)) continue;
                    if (!current_state.is_segment_free(p3, p4)) continue;
                    if (!current_state.is_segment_free(p4, p1)) continue;
                    
                    candidates.push_back({p1, p2, p3, p4, weights[p1.x][p1.y]});
                    moves_found++;
                }
                
                if (candidates.size() >= 30) break; 
            }
            
            if (candidates.empty()) break;
            
            sort(candidates.begin(), candidates.end(), [](const Move& a, const Move& b){
                return a.weight > b.weight;
            });
            
            int K = min((int)candidates.size(), 5);
            uniform_int_distribution<int> dist(0, K-1);
            int idx = dist(rng);
            Move chosen = candidates[idx];
            
            current_state.add_dot(chosen.p1.x, chosen.p1.y);
            current_state.mark_segment(chosen.p1, chosen.p2);
            current_state.mark_segment(chosen.p2, chosen.p3);
            current_state.mark_segment(chosen.p3, chosen.p4);
            current_state.mark_segment(chosen.p4, chosen.p1);
            current_state.history.push_back({chosen.p1, chosen.p2, chosen.p3, chosen.p4});
            
            current_added_score += chosen.weight;
        }

        if (current_added_score > best_score) {
            best_score = current_added_score;
            best_state = current_state;
        }
    }
    
    cout << best_state.history.size() << "\n";
    for (const auto& rect : best_state.history) {
        cout << rect.p1.x << " " << rect.p1.y << " " 
             << rect.p2.x << " " << rect.p2.y << " " 
             << rect.p3.x << " " << rect.p3.y << " " 
             << rect.p4.x << " " << rect.p4.y << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}