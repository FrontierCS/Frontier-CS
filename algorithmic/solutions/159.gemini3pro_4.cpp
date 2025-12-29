#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include <random>
#include <chrono>
#include <cstring>
#include <iomanip>

using namespace std;

// Constants and Globals
int N, M;
double C; // center
struct Point { int x, y; bool operator==(const Point& o) const { return x==o.x && y==o.y; } };
struct Move {
    Point p1; // new
    Point p2, p3, p4; // existing
    double score;
    // For tie-breaking in PQ
    bool operator<(const Move& other) const {
        return score < other.score;
    }
};

// Grid State
bool has_dot[64][64];
bool h_used[64][64]; // (x,y)-(x+1,y)
bool v_used[64][64]; // (x,y)-(x,y+1)
bool d1_used[64][64]; // (x,y)-(x+1,y+1)
bool d2_used[64][64]; // (x,y+1)-(x+1,y)

// Dot lookups for nearest neighbor
vector<int> rows[64];
vector<int> cols[64];
vector<pair<int,int>> diag1[130]; // y-x + N
vector<pair<int,int>> diag2[130]; // y+x

// Precomputed weights
double weight[64][64];

// Utils
inline bool in_bounds(int x, int y) {
    return x >= 0 && x < N && y >= 0 && y < N;
}

inline double get_weight(int x, int y) {
    return weight[x][y];
}

// Check and mark segments
bool is_h_free(int x1, int x2, int y) { // x1 < x2
    for(int x=x1; x<x2; ++x) if(h_used[x][y]) return false;
    return true;
}
bool is_v_free(int y1, int y2, int x) { // y1 < y2
    for(int y=y1; y<y2; ++y) if(v_used[x][y]) return false;
    return true;
}
bool is_d1_free(int x1, int y1, int x2, int y2) { // x1 < x2, y1 < y2
    for(int i=0; i<x2-x1; ++i) if(d1_used[x1+i][y1+i]) return false;
    return true;
}
bool is_d2_free(int x1, int y1, int x2, int y2) { // x1 < x2, y1 > y2
    for(int i=0; i<x2-x1; ++i) if(d2_used[x1+i][y1-1-i]) return false;
    return true;
}

// Mark segments
void set_h(int x1, int x2, int y, bool val) {
    if(x1 > x2) swap(x1, x2);
    for(int x=x1; x<x2; ++x) h_used[x][y] = val;
}
void set_v(int y1, int y2, int x, bool val) {
    if(y1 > y2) swap(y1, y2);
    for(int y=y1; y<y2; ++y) v_used[x][y] = val;
}
void set_d1(int x1, int y1, int x2, int y2, bool val) {
    if(x1 > x2) { swap(x1, x2); swap(y1, y2); }
    for(int i=0; i<x2-x1; ++i) d1_used[x1+i][y1+i] = val;
}
void set_d2(int x1, int y1, int x2, int y2, bool val) {
    if(x1 > x2) { swap(x1, x2); swap(y1, y2); }
    for(int i=0; i<x2-x1; ++i) d2_used[x1+i][y1-1-i] = val;
}

// Check for dots on segment (exclusive of endpoints)
bool is_seg_empty_h(int x1, int x2, int y) {
    if(x1 > x2) swap(x1, x2);
    if(x2 - x1 <= 1) return true;
    // use rows[y]
    auto it = upper_bound(rows[y].begin(), rows[y].end(), x1);
    if(it != rows[y].end() && *it < x2) return false;
    return true;
}
bool is_seg_empty_v(int y1, int y2, int x) {
    if(y1 > y2) swap(y1, y2);
    if(y2 - y1 <= 1) return true;
    auto it = upper_bound(cols[x].begin(), cols[x].end(), y1);
    if(it != cols[x].end() && *it < y2) return false;
    return true;
}
bool is_seg_empty_d1(int x1, int y1, int x2, int y2) {
    if(x1 > x2) { swap(x1, x2); swap(y1, y2); }
    if(x2 - x1 <= 1) return true;
    int idx = y1 - x1 + N;
    // search in diag1[idx]
    // diag1 stores (x, y), sorted by x?
    // Let's assume sorted by x.
    auto it = upper_bound(diag1[idx].begin(), diag1[idx].end(), make_pair(x1, 1000));
    if(it != diag1[idx].end() && it->first < x2) return false;
    return true;
}
bool is_seg_empty_d2(int x1, int y1, int x2, int y2) {
    if(x1 > x2) { swap(x1, x2); swap(y1, y2); }
    if(x2 - x1 <= 1) return true;
    int idx = y1 + x1;
    auto it = upper_bound(diag2[idx].begin(), diag2[idx].end(), make_pair(x1, 1000));
    if(it != diag2[idx].end() && it->first < x2) return false;
    return true;
}

// Combined Check
bool check_segment(Point a, Point b) {
    if(a.x == b.x) { // Vertical
        if(!is_seg_empty_v(a.y, b.y, a.x)) return false;
        return is_v_free(min(a.y, b.y), max(a.y, b.y), a.x);
    } else if(a.y == b.y) { // Horizontal
        if(!is_seg_empty_h(a.x, b.x, a.y)) return false;
        return is_h_free(min(a.x, b.x), max(a.x, b.x), a.y);
    } else if( (a.y - b.y) == (a.x - b.x) ) { // Diag1
        if(!is_seg_empty_d1(a.x, a.y, b.x, b.y)) return false;
        return is_d1_free(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y));
    } else { // Diag2
        if(!is_seg_empty_d2(a.x, a.y, b.x, b.y)) return false;
        return is_d2_free(min(a.x, b.x), max(a.y, b.y), max(a.x, b.x), min(a.y, b.y));
    }
}

void mark_segment(Point a, Point b, bool val) {
    if(a.x == b.x) set_v(min(a.y, b.y), max(a.y, b.y), a.x, val);
    else if(a.y == b.y) set_h(min(a.x, b.x), max(a.x, b.x), a.y, val);
    else if( (a.y - b.y) == (a.x - b.x) ) set_d1(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y), val);
    else set_d2(min(a.x, b.x), max(a.y, b.y), max(a.x, b.x), min(a.y, b.y), val);
}

// Add/Remove dot
void add_dot(Point p) {
    has_dot[p.x][p.y] = true;
    rows[p.y].insert(upper_bound(rows[p.y].begin(), rows[p.y].end(), p.x), p.x);
    cols[p.x].insert(upper_bound(cols[p.x].begin(), cols[p.x].end(), p.y), p.y);
    diag1[p.y - p.x + N].insert(upper_bound(diag1[p.y - p.x + N].begin(), diag1[p.y - p.x + N].end(), make_pair(p.x, p.y)), make_pair(p.x, p.y));
    diag2[p.y + p.x].insert(upper_bound(diag2[p.y + p.x].begin(), diag2[p.y + p.x].end(), make_pair(p.x, p.y)), make_pair(p.x, p.y));
}

// Neighbors search
// Dirs: 0:R, 1:U, 2:L, 3:D, 4:UR, 5:UL, 6:DL, 7:DR
Point get_neighbor(Point p, int dir) {
    if(dir == 0) { // +x
        auto it = upper_bound(rows[p.y].begin(), rows[p.y].end(), p.x);
        if(it != rows[p.y].end()) return {*it, p.y};
    } else if(dir == 2) { // -x
        auto it = lower_bound(rows[p.y].begin(), rows[p.y].end(), p.x);
        if(it != rows[p.y].begin()) return {*prev(it), p.y};
    } else if(dir == 1) { // +y
        auto it = upper_bound(cols[p.x].begin(), cols[p.x].end(), p.y);
        if(it != cols[p.x].end()) return {p.x, *it};
    } else if(dir == 3) { // -y
        auto it = lower_bound(cols[p.x].begin(), cols[p.x].end(), p.y);
        if(it != cols[p.x].begin()) return {p.x, *prev(it)};
    } else if(dir == 4) { // +x+y (UR)
        int idx = p.y - p.x + N;
        auto it = upper_bound(diag1[idx].begin(), diag1[idx].end(), make_pair(p.x, p.y));
        if(it != diag1[idx].end()) return {it->first, it->second};
    } else if(dir == 6) { // -x-y (DL)
        int idx = p.y - p.x + N;
        auto it = lower_bound(diag1[idx].begin(), diag1[idx].end(), make_pair(p.x, p.y));
        if(it != diag1[idx].begin()) { auto pit = prev(it); return {pit->first, pit->second}; }
    } else if(dir == 5) { // -x+y (UL)
        int idx = p.y + p.x;
        auto it = lower_bound(diag2[idx].begin(), diag2[idx].end(), make_pair(p.x, p.y));
        if(it != diag2[idx].begin()) { auto pit = prev(it); return {pit->first, pit->second}; }
    } else if(dir == 7) { // +x-y (DR)
        int idx = p.y + p.x;
        auto it = upper_bound(diag2[idx].begin(), diag2[idx].end(), make_pair(p.x, p.y));
        if(it != diag2[idx].end()) return {it->first, it->second};
    }
    return {-1, -1};
}

// Random engine
mt19937 rng(0);
uniform_real_distribution<double> dist_noise(1.0, 1.2);

vector<Move> candidates;
void find_moves(Point p, priority_queue<Move>& pq) {
    // Check L-shapes centered at p
    // Orthogonal pairs of directions
    // (0,1), (1,2), (2,3), (3,0) for axis
    // (4,5), (5,6), (6,7), (7,4) for diag
    
    int pairs[8][2] = {{0,1}, {1,2}, {2,3}, {3,0}, {4,5}, {5,6}, {6,7}, {7,4}};
    
    for(int i=0; i<8; ++i) {
        int d1 = pairs[i][0];
        int d2 = pairs[i][1];
        Point a = get_neighbor(p, d1);
        if(a.x == -1) continue;
        Point b = get_neighbor(p, d2);
        if(b.x == -1) continue;
        
        // p is center, a and b are neighbors
        // Check segments pa and pb
        if(!check_segment(p, a)) continue;
        if(!check_segment(p, b)) continue;
        
        Point c = {a.x + b.x - p.x, a.y + b.y - p.y};
        if(!in_bounds(c.x, c.y) || has_dot[c.x][c.y]) continue;
        
        // Check segments ac and bc
        if(!check_segment(a, c)) continue;
        if(!check_segment(b, c)) continue;
        
        // Valid Move: Rect p-a-c-b. new is c.
        // Output order: c, a, p, b
        Move m = {c, a, p, b, (i<4?0:1), get_weight(c.x, c.y) * dist_noise(rng)};
        pq.push(m);
    }
    
    // Check L-shapes where p is leaf
    // p-a-b, new is c.
    // iterate all 8 dirs for a
    for(int d1=0; d1<8; ++d1) {
        Point a = get_neighbor(p, d1);
        if(a.x == -1) continue;
        if(!check_segment(p, a)) continue;
        
        // At a, iterate perpendiculars
        // If d1 is 0 (+x), perps are 1 (+y) and 3 (-y).
        // General: axis: (d1+1)%4, (d1+3)%4.
        // diag: 4 (UR) -> perps 5 (UL), 7 (DR). (d1 is 4..7)
        // map d1 to index in 0..7.
        vector<int> perp_dirs;
        if(d1 < 4) {
            perp_dirs.push_back((d1+1)%4);
            perp_dirs.push_back((d1+3)%4);
        } else {
            // 4: UR perps 5, 7.
            // 5: UL perps 4, 6.
            // 6: DL perps 5, 7.
            // 7: DR perps 4, 6.
            if(d1==4 || d1==6) { perp_dirs.push_back(5); perp_dirs.push_back(7); }
            else { perp_dirs.push_back(4); perp_dirs.push_back(6); }
        }
        
        for(int d2 : perp_dirs) {
            Point b = get_neighbor(a, d2);
            if(b.x == -1) continue;
            if(!check_segment(a, b)) continue;
            
            // Rect p-a-b-c
            Point c = {p.x + b.x - a.x, p.y + b.y - a.y};
            if(!in_bounds(c.x, c.y) || has_dot[c.x][c.y]) continue;
            
            if(!check_segment(b, c)) continue;
            if(!check_segment(c, p)) continue;
            
            // Output order: c, p, a, b
            Move m = {c, p, a, b, (d1<4?0:1), get_weight(c.x, c.y) * dist_noise(rng)};
            pq.push(m);
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::high_resolution_clock::now();
    
    cin >> N >> M;
    C = (N - 1) / 2.0;
    
    vector<Point> initial_dots(M);
    for(int i=0; i<M; ++i) {
        cin >> initial_dots[i].x >> initial_dots[i].y;
    }
    
    // Precompute weights
    for(int x=0; x<N; ++x) {
        for(int y=0; y<N; ++y) {
            weight[x][y] = (x - C)*(x - C) + (y - C)*(y - C) + 1.0;
        }
    }
    
    vector<Move> best_history;
    double max_total_weight = -1.0;
    
    // Restarts
    int restarts = 0;
    while(true) {
        auto curr_time = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(curr_time - start_time).count();
        if(elapsed > 4.8) break;
        restarts++;
        
        // Reset
        memset(has_dot, 0, sizeof(has_dot));
        memset(h_used, 0, sizeof(h_used));
        memset(v_used, 0, sizeof(v_used));
        memset(d1_used, 0, sizeof(d1_used));
        memset(d2_used, 0, sizeof(d2_used));
        for(int i=0; i<N; ++i) { rows[i].clear(); cols[i].clear(); }
        for(int i=0; i<130; ++i) { diag1[i].clear(); diag2[i].clear(); }
        
        priority_queue<Move> pq;
        
        // Initialize
        for(const auto& p : initial_dots) {
            add_dot(p);
        }
        
        // Initial Moves
        for(const auto& p : initial_dots) {
            find_moves(p, pq);
        }
        
        vector<Move> history;
        double current_score = 0;
        
        while(!pq.empty()) {
            Move m = pq.top();
            pq.pop();
            
            // Re-validate
            if(has_dot[m.p1.x][m.p1.y]) continue;
            // The segments to be drawn must be valid
            if(!check_segment(m.p1, m.p2)) continue;
            if(!check_segment(m.p2, m.p3)) continue;
            if(!check_segment(m.p3, m.p4)) continue;
            if(!check_segment(m.p4, m.p1)) continue;
            
            // Apply
            add_dot(m.p1);
            mark_segment(m.p1, m.p2, true);
            mark_segment(m.p2, m.p3, true);
            mark_segment(m.p3, m.p4, true);
            mark_segment(m.p4, m.p1, true);
            
            history.push_back(m);
            current_score += weight[m.p1.x][m.p1.y]; // Just track raw weight sum
            
            find_moves(m.p1, pq);
        }
        
        // Check global score
        // Score calculation from problem: just sum of weights of final dots.
        // We want to maximize added weight.
        double total_w = 0;
        for(int x=0; x<N; ++x) 
            for(int y=0; y<N; ++y) 
                if(has_dot[x][y]) total_w += weight[x][y];
        
        if(total_w > max_total_weight) {
            max_total_weight = total_w;
            best_history = history;
        }
        
        // Optional: break early if small N to avoid overhead? N is small enough.
    }
    
    cout << best_history.size() << "\n";
    for(const auto& m : best_history) {
        cout << m.p1.x << " " << m.p1.y << " " 
             << m.p2.x << " " << m.p2.y << " " 
             << m.p3.x << " " << m.p3.y << " " 
             << m.p4.x << " " << m.p4.y << "\n";
    }
    
    return 0;
}