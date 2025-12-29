#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>
#include <bitset>
#include <array>

using namespace std;

// Constants
const int MAXN = 65; // N <= 61
const int MAX_COORD = 130; // u, v range up to ~122

// Utilities for bit manipulation
struct Bitset {
    unsigned long long lo, hi;
    Bitset() : lo(0), hi(0) {}
    
    void set(int i) {
        if (i < 64) lo |= (1ULL << i);
        else hi |= (1ULL << (i - 64));
    }
    
    bool test(int i) const {
        if (i < 64) return (lo >> i) & 1;
        else return (hi >> (i - 64)) & 1;
    }
    
    // Check if any bit in range [l, r] is set. Inclusive.
    bool any_in_range(int l, int r) const {
        if (l > r) return false;
        unsigned long long mask_lo = 0, mask_hi = 0;
        
        if (r < 64) {
            mask_lo = (r == 63) ? (~0ULL) : ((1ULL << (r + 1)) - 1);
            mask_lo &= ~((1ULL << l) - 1);
            return (lo & mask_lo) != 0;
        } else if (l >= 64) {
            int lr = l - 64;
            int rr = r - 64;
            mask_hi = (rr == 63) ? (~0ULL) : ((1ULL << (rr + 1)) - 1);
            mask_hi &= ~((1ULL << lr) - 1);
            return (hi & mask_hi) != 0;
        } else {
            // Split across boundary
            mask_lo = ~((1ULL << l) - 1);
            int rr = r - 64;
            mask_hi = (rr == 63) ? (~0ULL) : ((1ULL << (rr + 1)) - 1);
            return (lo & mask_lo) || (hi & mask_hi);
        }
    }
    
    Bitset operator&(const Bitset& other) const {
        Bitset res;
        res.lo = lo & other.lo;
        res.hi = hi & other.hi;
        return res;
    }
    
    Bitset operator^(const Bitset& other) const {
        Bitset res;
        res.lo = lo ^ other.lo;
        res.hi = hi ^ other.hi;
        return res;
    }
    
    bool none() const {
        return lo == 0 && hi == 0;
    }
    
    // Iterate over set bits
    template<typename Func>
    void for_each_set_bit(Func f) const {
        unsigned long long temp = lo;
        while (temp) {
            int i = __builtin_ctzll(temp);
            f(i);
            temp &= ~(1ULL << i);
        }
        temp = hi;
        while (temp) {
            int i = __builtin_ctzll(temp);
            f(i + 64);
            temp &= ~(1ULL << i);
        }
    }
};

struct Point {
    int x, y;
};

struct Move {
    Point p1, p2, p3, p4;
    int weight;
};

int N, M;
int center_coord;

int get_weight(int x, int y) {
    int dx = x - center_coord;
    int dy = y - center_coord;
    return dx * dx + dy * dy + 1;
}

struct State {
    // Dot storage
    // row_dots[y] stores x coordinates
    Bitset row_dots[MAXN];
    // col_dots[x] stores y coordinates
    Bitset col_dots[MAXN];
    // d1_dots[v] stores x coordinates. v = x - y + N. Range [1, 2N-1]
    Bitset d1_dots[MAX_COORD];
    // d2_dots[u] stores x coordinates. u = x + y. Range [0, 2N-2]
    Bitset d2_dots[MAX_COORD];
    
    // Edge storage (segments)
    // h_edges[y] stores x (segment x to x+1)
    Bitset h_edges[MAXN];
    // v_edges[x] stores y (segment y to y+1)
    Bitset v_edges[MAXN];
    // d1_edges[v] stores x (segment on x-y=v-N from x to x+1)
    Bitset d1_edges[MAX_COORD];
    // d2_edges[u] stores x (segment on x+y=u from x to x+1)
    Bitset d2_edges[MAX_COORD];
    
    bool has_dot[MAXN][MAXN];
    long long current_score;
    vector<Move> history;
    
    State() {
        for(int i=0; i<MAXN; ++i) {
            for(int j=0; j<MAXN; ++j) has_dot[i][j] = false;
        }
        current_score = 0;
    }
    
    virtual void add_initial_dot(int x, int y) {
        if(has_dot[x][y]) return;
        has_dot[x][y] = true;
        current_score += get_weight(x, y);
        
        row_dots[y].set(x);
        col_dots[x].set(y);
        d1_dots[x - y + N].set(x);
        d2_dots[x + y].set(x);
    }
    
    bool is_valid_axis(int x1, int x2, int y1, int y2, int nx, int ny) {
        if (row_dots[y1].any_in_range(x1 + 1, x2 - 1)) return false;
        if (row_dots[y2].any_in_range(x1 + 1, x2 - 1)) return false;
        if (col_dots[x1].any_in_range(y1 + 1, y2 - 1)) return false;
        if (col_dots[x2].any_in_range(y1 + 1, y2 - 1)) return false;
        
        if (h_edges[y2].any_in_range(x1, x2 - 1)) return false;
        if (h_edges[y1].any_in_range(x1, x2 - 1)) return false;
        if (v_edges[x1].any_in_range(y1, y2 - 1)) return false;
        if (v_edges[x2].any_in_range(y1, y2 - 1)) return false;
        
        return true;
    }

    bool is_valid_diag(int u1, int u2, int v1, int v2) {
        int x_u1v1 = (u1 + v1 - N) / 2;
        int x_u2v1 = (u2 + v1 - N) / 2;
        int x_u1v2 = (u1 + v2 - N) / 2;
        int x_u2v2 = (u2 + v2 - N) / 2;
        
        // v=v1 (Diag1 line)
        if (d1_dots[v1].any_in_range(x_u1v1 + 1, x_u2v1 - 1)) return false;
        if (d1_edges[v1].any_in_range(x_u1v1, x_u2v1 - 1)) return false;
        
        // v=v2
        if (d1_dots[v2].any_in_range(x_u1v2 + 1, x_u2v2 - 1)) return false;
        if (d1_edges[v2].any_in_range(x_u1v2, x_u2v2 - 1)) return false;
        
        // u=u1 (Diag2 line)
        if (d2_dots[u1].any_in_range(x_u1v1 + 1, x_u1v2 - 1)) return false;
        if (d2_edges[u1].any_in_range(x_u1v1, x_u1v2 - 1)) return false;
        
        // u=u2
        if (d2_dots[u2].any_in_range(x_u2v1 + 1, x_u2v2 - 1)) return false;
        if (d2_edges[u2].any_in_range(x_u2v1, x_u2v2 - 1)) return false;
        
        return true;
    }
    
    virtual void apply_move(const Move& m) {
        add_initial_dot(m.p1.x, m.p1.y);
        history.push_back(m);
        
        Point pts[4] = {m.p1, m.p2, m.p3, m.p4};
        for(int i=0; i<4; ++i) {
            Point a = pts[i];
            Point b = pts[(i+1)%4];
            
            if (a.y == b.y) { // Horizontal
                int y = a.y;
                int x_min = min(a.x, b.x);
                int x_max = max(a.x, b.x);
                for(int x=x_min; x<x_max; ++x) h_edges[y].set(x);
            } else if (a.x == b.x) { // Vertical
                int x = a.x;
                int y_min = min(a.y, b.y);
                int y_max = max(a.y, b.y);
                for(int y=y_min; y<y_max; ++y) v_edges[x].set(y);
            } else {
                if (a.x - a.y == b.x - b.y) { // Diag1
                    int v = a.x - a.y + N;
                    int x_min = min(a.x, b.x);
                    int x_max = max(a.x, b.x);
                    for(int x=x_min; x<x_max; ++x) d1_edges[v].set(x);
                } else { // Diag2
                    int u = a.x + a.y;
                    int x_min = min(a.x, b.x);
                    int x_max = max(a.x, b.x);
                    for(int x=x_min; x<x_max; ++x) d2_edges[u].set(x);
                }
            }
        }
    }
};

struct StateEnhanced : State {
    Bitset u_dots[MAX_COORD];
    
    void add_initial_dot(int x, int y) override {
        State::add_initial_dot(x, y);
        int u = x + y;
        int v = x - y + N;
        u_dots[u].set(v);
    }
    
    void apply_move(const Move& m) override {
        State::apply_move(m);
        // p1 is the new dot, base apply_move calls add_initial_dot which updates u_dots
    }
};

void get_moves(const StateEnhanced& s, vector<Move>& moves) {
    // 1. Axis-Aligned
    for(int x1=0; x1<N-1; ++x1) {
        if(s.col_dots[x1].none()) continue;
        for(int x2=x1+1; x2<N; ++x2) {
            if(s.col_dots[x2].none()) continue;
            
            Bitset common = s.col_dots[x1] & s.col_dots[x2];
            if(common.none()) continue;
            Bitset one = s.col_dots[x1] ^ s.col_dots[x2];
            if(one.none()) continue;
            
            common.for_each_set_bit([&](int yc) {
                one.for_each_set_bit([&](int yt) {
                    int nx = s.has_dot[x1][yt] ? x2 : x1;
                    int ny = yt;
                    
                    int y_min = min(yc, yt);
                    int y_max = max(yc, yt);
                    
                    if(((State&)s).is_valid_axis(x1, x2, y_min, y_max, nx, ny)) {
                         int ox = (nx == x1) ? x2 : x1;
                         Move m;
                         m.p1 = {nx, ny};
                         m.p2 = {nx, yc};
                         m.p3 = {ox, yc};
                         m.p4 = {ox, ny};
                         m.weight = get_weight(nx, ny);
                         moves.push_back(m);
                    }
                });
            });
        }
    }
    
    // 2. Diag-Aligned
    int max_u = 2*N - 2;
    for(int u1=0; u1<max_u; ++u1) {
        if(s.u_dots[u1].none()) continue;
        // Same parity u required for sharing a v
        for(int u2=u1+2; u2<=max_u; u2+=2) { 
            if(s.u_dots[u2].none()) continue;
            
            Bitset common = s.u_dots[u1] & s.u_dots[u2];
            if(common.none()) continue;
            Bitset one = s.u_dots[u1] ^ s.u_dots[u2];
            if(one.none()) continue;
            
            common.for_each_set_bit([&](int vc) {
                one.for_each_set_bit([&](int vt) {
                    int u_target = s.u_dots[u1].test(vt) ? u2 : u1;
                    
                    auto to_pt = [&](int u, int v) {
                        return Point{(u + v - N) / 2, (u - v + N) / 2};
                    };
                    
                    Point p1 = to_pt(u_target, vt);
                    
                    if(((State&)s).is_valid_diag(u1, u2, min(vc, vt), max(vc, vt))) {
                        int u_other = (u_target == u1) ? u2 : u1;
                        Move m;
                        m.p1 = p1;
                        m.p2 = to_pt(u_target, vc);
                        m.p3 = to_pt(u_other, vc);
                        m.p4 = to_pt(u_other, vt);
                        m.weight = get_weight(p1.x, p1.y);
                        moves.push_back(m);
                    }
                });
            });
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    cin >> N >> M;
    center_coord = (N - 1) / 2;
    
    StateEnhanced initial_state;
    for(int i=0; i<M; ++i) {
        int x, y;
        cin >> x >> y;
        initial_state.add_initial_dot(x, y);
    }
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 4.8; 
    
    StateEnhanced best_state = initial_state;
    long long best_score = -1;
    
    mt19937 rng(12345);
    
    int trials = 0;
    while(true) {
        auto curr_time = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(curr_time - start_time).count();
        if(elapsed > time_limit) break;
        
        trials++;
        StateEnhanced current = initial_state;
        
        while(true) {
            vector<Move> moves;
            get_moves(current, moves);
            
            if(moves.empty()) break;
            
            shuffle(moves.begin(), moves.end(), rng);
            sort(moves.begin(), moves.end(), [](const Move& a, const Move& b){
                return a.weight > b.weight;
            });
            
            int K = min((int)moves.size(), 3);
            int idx = uniform_int_distribution<int>(0, K-1)(rng);
            current.apply_move(moves[idx]);
        }
        
        if(current.current_score > best_score) {
            best_score = current.current_score;
            best_state = current;
        }
    }
    
    cout << best_state.history.size() << "\n";
    for(const auto& m : best_state.history) {
        cout << m.p1.x << " " << m.p1.y << " " 
             << m.p2.x << " " << m.p2.y << " "
             << m.p3.x << " " << m.p3.y << " "
             << m.p4.x << " " << m.p4.y << "\n";
    }
    
    return 0;
}