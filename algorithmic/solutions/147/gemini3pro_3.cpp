#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <random>

using namespace std;

// Constants
const int W = 10000;
const int H = 10000;
const double TIME_LIMIT = 4.95; // seconds; slightly less than 5s to be safe

struct Rect {
    int a, b, c, d; // [a, c) x [b, d)
    int area() const { return (c - a) * (d - b); }
};

struct Request {
    int id;
    int x, y, r;
};

int N;
vector<Request> reqs;
vector<Rect> rects;
vector<double> scores; 
double total_score = 0.0;

// Fast random number generator (Xorshift128)
uint32_t xorshift128() {
    static uint32_t x = 123456789;
    static uint32_t y = 362436069;
    static uint32_t z = 521288629;
    static uint32_t w = 88675123;
    uint32_t t = x ^ (x << 11);
    x = y; y = z; z = w;
    w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    return w;
}

double get_rand() {
    return (double)xorshift128() / 0xFFFFFFFF;
}

int get_rand_int(int max_val) { 
    return xorshift128() % max_val;
}

double calc_satisfaction(int r, int s) {
    if (s == 0) return 0.0;
    double v = 1.0 - (double)min(r, s) / max(r, s);
    return 1.0 - v * v;
}

bool is_overlap(const Rect& r1, const Rect& r2) {
    return max(r1.a, r2.a) < min(r1.c, r2.c) && max(r1.b, r2.b) < min(r1.d, r2.d);
}

// Check if point (x+0.5, y+0.5) is inside rect
// Since coords are integers, point (x+0.5, y+0.5) is inside [a, c) x [b, d) if a <= x < c and b <= y < d
bool contains_point(const Rect& r, int x, int y) {
    return r.a <= x && x < r.c && r.b <= y && y < r.d;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::high_resolution_clock::now();
    
    if (!(cin >> N)) return 0;
    
    reqs.resize(N);
    rects.resize(N);
    scores.resize(N);
    
    for (int i = 0; i < N; ++i) {
        reqs[i].id = i;
        cin >> reqs[i].x >> reqs[i].y >> reqs[i].r;
        
        // Initial solution: 1x1 rectangle at (x, y)
        rects[i] = {reqs[i].x, reqs[i].y, reqs[i].x + 1, reqs[i].y + 1};
        scores[i] = calc_satisfaction(reqs[i].r, 1);
        total_score += scores[i];
    }
    
    int iter = 0;
    // Simulated Annealing parameters
    double temp_start = 0.01; // Start temperature
    double temp_end = 0.000001; // End temperature
    double current_temp = temp_start;
    
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> diff = now - start_time;
            double elapsed = diff.count();
            if (elapsed > TIME_LIMIT) break;
            
            double ratio = elapsed / TIME_LIMIT;
            current_temp = temp_start * pow(temp_end / temp_start, ratio);
        }
        
        // Pick a random rectangle
        int i = get_rand_int(N);
        // Pick action: 0 = Shrink, 1 = Expand/Push
        int action_type = get_rand_int(2); 
        // Pick a side: 0:Left(a), 1:Top(b), 2:Right(c), 3:Bottom(d)
        int side = get_rand_int(4); 
        
        Rect old_ri = rects[i];
        Rect new_ri = old_ri;
        
        if (action_type == 0) { // Shrink
             // Move boundary inward
             if (side == 0) new_ri.a++;
             else if (side == 1) new_ri.b++;
             else if (side == 2) new_ri.c--;
             else if (side == 3) new_ri.d--;
             
             // Checks
             if (!contains_point(new_ri, reqs[i].x, reqs[i].y)) continue;
             if (new_ri.a >= new_ri.c || new_ri.b >= new_ri.d) continue;
             
             double old_s = scores[i];
             double new_s = calc_satisfaction(reqs[i].r, new_ri.area());
             double score_diff = new_s - old_s;
             
             // Metropolis acceptance
             if (score_diff >= 0 || get_rand() < exp(score_diff / current_temp)) {
                 rects[i] = new_ri;
                 scores[i] = new_s;
                 total_score += score_diff;
             }
        } 
        else { // Expand
             // Move boundary outward
             if (side == 0) new_ri.a--;
             else if (side == 1) new_ri.b--;
             else if (side == 2) new_ri.c++;
             else if (side == 3) new_ri.d++;
             
             // Bounds check
             if (new_ri.a < 0 || new_ri.b < 0 || new_ri.c > W || new_ri.d > H) continue;
             
             // Overlap check
             vector<int> overlaps;
             bool possible = true;
             for (int j = 0; j < N; ++j) {
                 if (i == j) continue;
                 if (is_overlap(new_ri, rects[j])) {
                     overlaps.push_back(j);
                 }
             }
             
             double score_diff = 0;
             double old_si = scores[i];
             double new_si = calc_satisfaction(reqs[i].r, new_ri.area());
             score_diff += (new_si - old_si);
             
             vector<Rect> new_neighbors;
             vector<double> new_neighbor_scores;
             new_neighbors.reserve(overlaps.size());
             new_neighbor_scores.reserve(overlaps.size());
             
             // Try to resolve overlaps by shrinking neighbors
             for (int j : overlaps) {
                 Rect rj = rects[j];
                 Rect next_rj = rj;
                 
                 // If i expanded Right (c++), j must shrink Left (a++)
                 if (side == 0) next_rj.c--; 
                 else if (side == 1) next_rj.d--;
                 else if (side == 2) next_rj.a++;
                 else if (side == 3) next_rj.b++;
                 
                 // Check validity for j
                 if (!contains_point(next_rj, reqs[j].x, reqs[j].y) || 
                     next_rj.a >= next_rj.c || next_rj.b >= next_rj.d) {
                     possible = false;
                     break;
                 }
                 
                 new_neighbors.push_back(next_rj);
                 double ns = calc_satisfaction(reqs[j].r, next_rj.area());
                 new_neighbor_scores.push_back(ns);
                 score_diff += (ns - scores[j]);
             }
             
             if (possible) {
                 if (score_diff >= 0 || get_rand() < exp(score_diff / current_temp)) {
                     rects[i] = new_ri;
                     scores[i] = new_si;
                     for (size_t k = 0; k < overlaps.size(); ++k) {
                         int idx = overlaps[k];
                         rects[idx] = new_neighbors[k];
                         scores[idx] = new_neighbor_scores[k];
                     }
                     total_score += score_diff;
                 }
             }
        }
    }
    
    for (int i = 0; i < N; ++i) {
        cout << rects[i].a << " " << rects[i].b << " " << rects[i].c << " " << rects[i].d << "\n";
    }
    
    return 0;
}