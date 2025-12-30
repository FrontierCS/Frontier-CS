#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <cstdlib>

using namespace std;

// Structure to represent a point
struct Point {
    int x, y;
};

// Constants
const int W = 200; // Number of vertical strips
const int MAX_COORD = 100000;
const int STRIP_WIDTH = 500; // 100000 / 200
const int MAX_PERIMETER = 400000;

int N;
vector<Point> mackerels;
vector<Point> sardines;
// Buckets for points in each strip
vector<int> macks_in_strip[W];
vector<int> sards_in_strip[W];

// State variables
int L[W], R[W]; // Bottom and Top y-coordinates for each strip
int global_vertical_perimeter = 0;
long long current_score = 0;

// Count points in a strip i with y-coordinate in [y1, y2]
int count_points(const vector<int>& pts, int y1, int y2) {
    if (y1 > y2) return 0;
    auto it1 = lower_bound(pts.begin(), pts.end(), y1);
    auto it2 = upper_bound(pts.begin(), pts.end(), y2);
    return (int)(it2 - it1);
}

// Calculate score contribution of a strip
int calc_strip_score(int i, int l, int r) {
    int m = count_points(macks_in_strip[i], l, r);
    int s = count_points(sards_in_strip[i], l, r);
    return m - s;
}

int main() {
    // Fast IO not strictly needed but good practice
    // Using scanf/printf for standard IO
    if (scanf("%d", &N) != 1) return 0;
    mackerels.resize(N);
    for(int i=0; i<N; ++i) scanf("%d %d", &mackerels[i].x, &mackerels[i].y);
    sardines.resize(N);
    for(int i=0; i<N; ++i) scanf("%d %d", &sardines[i].x, &sardines[i].y);

    // Distribute points into strips
    for(const auto& p : mackerels) {
        int idx = min(p.x / STRIP_WIDTH, W - 1);
        macks_in_strip[idx].push_back(p.y);
    }
    for(const auto& p : sardines) {
        int idx = min(p.x / STRIP_WIDTH, W - 1);
        sards_in_strip[idx].push_back(p.y);
    }
    // Sort y-coordinates for binary search
    for(int i=0; i<W; ++i) {
        sort(macks_in_strip[i].begin(), macks_in_strip[i].end());
        sort(sards_in_strip[i].begin(), sards_in_strip[i].end());
    }

    // Initialization: bounding box of all mackerels
    int min_y = 100000, max_y = 0;
    bool has_macks = false;
    for(const auto& p : mackerels) {
        min_y = min(min_y, p.y);
        max_y = max(max_y, p.y);
        has_macks = true;
    }
    if (!has_macks) { min_y = 0; max_y = 100000; }
    else {
        min_y = max(0, min_y);
        max_y = min(100000, max_y);
    }

    // Set initial state
    current_score = 0;
    for(int i=0; i<W; ++i) {
        L[i] = min_y;
        R[i] = max_y;
        current_score += calc_strip_score(i, L[i], R[i]);
    }

    // Calculate initial vertical perimeter
    // Horizontal perimeter is fixed at 200000 (100000 bottom + 100000 top)
    global_vertical_perimeter = (R[0] - L[0]) + (R[W-1] - L[W-1]);
    for(int i=0; i<W-1; ++i) {
        global_vertical_perimeter += abs(L[i+1] - L[i]) + abs(R[i+1] - R[i]);
    }

    // Simulated Annealing / Hill Climbing
    double time_limit = 1.95; // seconds
    clock_t start_time = clock();
    
    int iter = 0;
    while(true) {
        iter++;
        if ((iter & 511) == 0) { // Check time every 512 iterations
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            if (elapsed > time_limit) break;
        }

        // Pick a strip and a boundary (L or R) to modify
        int i = rand() % W;
        int type = rand() % 2; // 0 for L, 1 for R
        int old_val = (type == 0 ? L[i] : R[i]);
        int new_val = old_val;

        // Generate a candidate move
        int move_type = rand() % 10;
        if (move_type < 4) { // Small random perturbation
            int delta = (rand() % 2001) - 1000;
            new_val += delta;
        } else if (move_type < 7) { // Align with neighbor
            int neighbor = -1;
            if (i == 0) neighbor = 1;
            else if (i == W-1) neighbor = W-2;
            else neighbor = (rand()%2 ? i-1 : i+1);
            new_val = (type == 0 ? L[neighbor] : R[neighbor]);
        } else { // Snap to a mackerel's y-coordinate
             if (!macks_in_strip[i].empty()) {
                 new_val = macks_in_strip[i][rand() % macks_in_strip[i].size()];
             } else {
                 new_val += (rand() % 101) - 50;
             }
        }
        
        // Clip to valid range
        new_val = max(0, min(MAX_COORD, new_val));
        if (new_val == old_val) continue;

        int l = (type == 0 ? new_val : L[i]);
        int r = (type == 1 ? new_val : R[i]);

        // Constraints check
        if (l >= r) continue; // Ensure strictly positive height
        // Connectivity check with neighbors
        if (i > 0) {
            // max(L) < min(R) ensures overlap
            if (min(R[i-1], r) <= max(L[i-1], l)) continue;
        }
        if (i < W - 1) {
            if (min(R[i+1], r) <= max(L[i+1], l)) continue;
        }

        // Calculate change in perimeter
        int old_p_contrib = 0;
        if (i==0) old_p_contrib += (R[0]-L[0]);
        if (i==W-1) old_p_contrib += (R[W-1]-L[W-1]);
        if (i>0) old_p_contrib += abs(L[i] - L[i-1]) + abs(R[i] - R[i-1]);
        if (i<W-1) old_p_contrib += abs(L[i+1] - L[i]) + abs(R[i+1] - R[i]);

        int new_p_contrib = 0;
        if (i==0) new_p_contrib += (r - l);
        if (i==W-1) new_p_contrib += (r - l);
        if (i>0) new_p_contrib += abs(l - L[i-1]) + abs(r - R[i-1]);
        if (i<W-1) new_p_contrib += abs(L[i+1] - l) + abs(R[i+1] - r);

        int new_total_vert = global_vertical_perimeter - old_p_contrib + new_p_contrib;
        
        // Total perimeter = Horizontal (200000) + Vertical
        if (new_total_vert + 200000 > MAX_PERIMETER) continue;

        // Calculate score change
        int old_score_part = calc_strip_score(i, L[i], R[i]);
        int new_score_part = calc_strip_score(i, l, r);
        int score_diff = new_score_part - old_score_part;

        // Accept or reject logic
        if (score_diff >= 0) {
            // Greedy accept
            if (type == 0) L[i] = new_val; else R[i] = new_val;
            current_score += score_diff;
            global_vertical_perimeter = new_total_vert;
        } else {
            // Probabilistic accept
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            double temp = 10.0 * (1.0 - elapsed / time_limit); 
            if (temp > 1e-9 && exp(score_diff / temp) > (double)rand()/RAND_MAX) {
                if (type == 0) L[i] = new_val; else R[i] = new_val;
                current_score += score_diff;
                global_vertical_perimeter = new_total_vert;
            }
        }
    }

    // Construct vertices for the polygon
    // Bottom boundary: left to right
    vector<pair<int,int>> vertices;
    vertices.push_back({0, L[0]});
    for(int i=0; i<W-1; ++i) {
        vertices.push_back({(i+1)*STRIP_WIDTH, L[i]});
        vertices.push_back({(i+1)*STRIP_WIDTH, L[i+1]});
    }
    vertices.push_back({100000, L[W-1]});
    
    // Top boundary: right to left
    vertices.push_back({100000, R[W-1]});
    for(int i=W-1; i>0; --i) {
        vertices.push_back({i*STRIP_WIDTH, R[i]});
        vertices.push_back({i*STRIP_WIDTH, R[i-1]});
    }
    vertices.push_back({0, R[0]});

    // Remove duplicates and collinear points to reduce vertex count
    vector<pair<int,int>> final_v;
    for(auto p : vertices) {
        if(!final_v.empty() && final_v.back() == p) continue; // Skip duplicates
        if(final_v.size() >= 2) {
            auto p1 = final_v[final_v.size()-2];
            auto p2 = final_v.back();
            // Check if p1, p2, p are collinear
            if ((p1.first == p2.first && p2.first == p.first) || 
                (p1.second == p2.second && p2.second == p.second)) {
                final_v.pop_back(); // Remove middle point
            }
        }
        final_v.push_back(p);
    }
    
    // Check collinearity at loop closure (last -> first)
    if (final_v.size() >= 3) {
        auto p1 = final_v[final_v.size()-2];
        auto p2 = final_v.back();
        auto p0 = final_v[0];
        if ((p1.first == p2.first && p2.first == p0.first) || 
            (p1.second == p2.second && p2.second == p0.second)) {
            final_v.pop_back();
        }
    }

    // Output result
    printf("%d\n", (int)final_v.size());
    for(auto p : final_v) {
        printf("%d %d\n", p.first, p.second);
    }

    return 0;
}