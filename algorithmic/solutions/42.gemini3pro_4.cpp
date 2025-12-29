#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <map>

using namespace std;

// Constant for PI
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Structure to hold information about a placed square
struct Square {
    double x, y, a;
};

// Structure to hold the solution for a subproblem n
struct Result {
    double L;
    int type; // 0: Grid, 1: Split4, 2: Split5
    vector<int> sub_ns; // sizes of sub problems
    vector<int> perm; // permutation for split4 or split5
};

int N;
map<int, Result> memo;

// Forward declaration
Result solve(int n);

// Baseline: Grid packing
// Packs n squares into ceil(sqrt(n)) * ceil(sqrt(n))
Result solve_grid(int n) {
    Result res;
    res.L = ceil(sqrt(n));
    res.type = 0;
    return res;
}

// Recursive strategy 1: Split n into 4 parts and pack in 2x2
Result solve_split4(int n) {
    Result best;
    best.L = 1e18;
    
    // Balanced split of n into 4 parts
    int k = n / 4;
    int rem = n % 4;
    vector<int> parts(4, k);
    for(int i=0; i<rem; ++i) parts[i]++;
    
    // Recursively solve subproblems
    vector<double> sizes(4);
    for(int i=0; i<4; ++i) {
        if (parts[i] == 0) sizes[i] = 0;
        else sizes[i] = solve(parts[i]).L;
    }
    
    // Try all permutations of placing the 4 parts into TL, TR, BL, BR
    vector<int> p = {0, 1, 2, 3};
    do {
        // Placement mapping: 0:TL, 1:TR, 2:BL, 3:BR
        // Width is max(width of top row, width of bottom row)
        // Height is max(height of left col, height of right col)
        double w = max(sizes[p[0]] + sizes[p[1]], sizes[p[2]] + sizes[p[3]]);
        double h = max(sizes[p[0]] + sizes[p[2]], sizes[p[1]] + sizes[p[3]]);
        double L = max(w, h);
        
        if (L < best.L) {
            best.L = L;
            best.type = 1;
            best.sub_ns = parts;
            best.perm = p;
        }
    } while (next_permutation(p.begin(), p.end()));
    
    return best;
}

// Recursive strategy 2: Split n into 5 parts, place 4 in corners and 1 in center rotated 45 deg
Result solve_split5(int n) {
    Result best;
    best.L = 1e18;
    
    if (n < 5) return best; // Need at least 5 to use this effectively (or logic allows empty, but not useful)
    
    int k = n / 5;
    int rem = n % 5;
    vector<int> parts(5, k);
    for(int i=0; i<rem; ++i) parts[i]++;
    
    vector<double> sizes(5);
    for(int i=0; i<5; ++i) {
        if (parts[i] == 0) sizes[i] = 0;
        else sizes[i] = solve(parts[i]).L;
    }
    
    // Loop over which part is in the center
    // We try all 5 candidates for center. The other 4 go to corners.
    // The permutation vector will store [corner1, corner2, corner3, corner4, center]
    
    for(int c=0; c<5; ++c) {
        double s_center = sizes[c];
        double s_max_corner = 0;
        for(int i=0; i<5; ++i) {
            if (i == c) continue;
            if (sizes[i] > s_max_corner) s_max_corner = sizes[i];
        }
        
        // Calculate required L
        // 1. Corners must fit: 2 * max_corner_size
        double L_corners = 2.0 * s_max_corner;
        
        // 2. Center diamond must fit between corners
        // The center square is rotated 45 degrees.
        // The constraint to avoid overlap with corners (placed at extremes) is:
        double L_with_center = 2.0 * s_max_corner + s_center / sqrt(2.0);
        
        // 3. Center diamond must fit inside container
        // Bounding box of rotated center square is s_center * sqrt(2)
        double L_center_fit = s_center * sqrt(2.0);
        
        double L = max({L_corners, L_with_center, L_center_fit});
        
        if (L < best.L) {
            best.L = L;
            best.type = 2;
            best.sub_ns = parts;
            best.perm.clear();
            for(int i=0; i<5; ++i) if(i != c) best.perm.push_back(i);
            best.perm.push_back(c);
        }
    }
    
    return best;
}

// Main solver with memoization
Result solve(int n) {
    if (n == 0) return {0, 0, {}, {}};
    if (memo.count(n)) return memo[n];
    
    // Default to grid
    Result res = solve_grid(n);
    
    // Try Split 4
    Result r4 = solve_split4(n);
    if (r4.L < res.L - 1e-9) res = r4;
    
    // Try Split 5 if applicable
    if (n >= 5) {
        Result r5 = solve_split5(n);
        if (r5.L < res.L - 1e-9) res = r5;
    }
    
    return memo[n] = res;
}

// Reconstruct the solution coordinates
// ox, oy: origin of current container
// base_rot: rotation of current container
void construct(int n, double ox, double oy, double base_rot, vector<Square>& out) {
    if (n == 0) return;
    Result res = solve(n);
    
    if (res.type == 0) {
        // Grid Packing
        int k = ceil(sqrt(n));
        int count = 0;
        double rad = base_rot * M_PI / 180.0;
        double c = cos(rad), s = sin(rad);
        
        for(int i=0; i<k; ++i) {
            for(int j=0; j<k; ++j) {
                if (count >= n) break;
                // Center relative to unrotated BL corner
                double lx = 0.5 + i;
                double ly = 0.5 + j;
                
                // Rotate offset
                double rx = lx * c - ly * s;
                double ry = lx * s + ly * c;
                
                out.push_back({ox + rx, oy + ry, base_rot});
                count++;
            }
        }
    } else if (res.type == 1) {
        // Split 4 Packing
        vector<double> sizes(4);
        for(int i=0; i<4; ++i) sizes[i] = solve(res.sub_ns[i]).L;
        
        double L = res.L;
        
        struct Off { double x, y; int idx; };
        // perm: 0:TL, 1:TR, 2:BL, 3:BR
        // Coordinates of BL corner of each sub-square
        vector<Off> pos(4);
        pos[0] = {0, L - sizes[res.perm[0]], res.perm[0]}; // TL
        pos[1] = {L - sizes[res.perm[1]], L - sizes[res.perm[1]], res.perm[1]}; // TR
        pos[2] = {0, 0, res.perm[2]}; // BL
        pos[3] = {L - sizes[res.perm[3]], 0, res.perm[3]}; // BR
        
        double rad = base_rot * M_PI / 180.0;
        double c = cos(rad), s = sin(rad);
        
        for(int i=0; i<4; ++i) {
            double rx = pos[i].x * c - pos[i].y * s;
            double ry = pos[i].x * s + pos[i].y * c;
            construct(res.sub_ns[pos[i].idx], ox + rx, oy + ry, base_rot, out);
        }
        
    } else if (res.type == 2) {
        // Split 5 Packing
        double L = res.L;
        vector<double> sizes(5);
        for(int i=0; i<5; ++i) sizes[i] = solve(res.sub_ns[i]).L;
        
        double rad = base_rot * M_PI / 180.0;
        double c = cos(rad), s = sin(rad);
        
        // Place 4 corners
        // perm[0..3] are corners
        // We place them tightly in corners of L x L
        struct Off { double x, y; int idx; };
        vector<Off> pos;
        
        // TL
        pos.push_back({0, L - sizes[res.perm[0]], res.perm[0]});
        // TR
        pos.push_back({L - sizes[res.perm[1]], L - sizes[res.perm[1]], res.perm[1]});
        // BL
        pos.push_back({0, 0, res.perm[2]});
        // BR
        pos.push_back({L - sizes[res.perm[3]], 0, res.perm[3]});
        
        for(auto& p : pos) {
            double rx = p.x * c - p.y * s;
            double ry = p.x * s + p.y * c;
            construct(res.sub_ns[p.idx], ox + rx, oy + ry, base_rot, out);
        }
        
        // Place Center (perm[4])
        int c_idx = res.perm[4];
        double Sc = sizes[c_idx];
        
        // Calculate center of the container in world coordinates
        double L_half = L / 2.0;
        double world_cx = ox + (L_half * c - L_half * s);
        double world_cy = oy + (L_half * s + L_half * c);
        
        // New rotation for center square
        double new_rot = base_rot + 45.0;
        double rad_new = new_rot * M_PI / 180.0;
        double cn = cos(rad_new), sn = sin(rad_new);
        
        // Calculate origin of center square such that its center aligns with world_cx, world_cy
        double Sc_half = Sc / 2.0;
        double v_cx = Sc_half * cn - Sc_half * sn;
        double v_cy = Sc_half * sn + Sc_half * cn;
        
        double origin_x = world_cx - v_cx;
        double origin_y = world_cy - v_cy;
        
        construct(res.sub_ns[c_idx], origin_x, origin_y, new_rot, out);
    }
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    Result res = solve(N);
    
    cout << fixed << setprecision(8) << res.L << endl;
    
    vector<Square> squares;
    squares.reserve(N);
    construct(N, 0, 0, 0, squares);
    
    for(const auto& s : squares) {
        double a = fmod(s.a, 360.0);
        while (a < 0) a += 360.0;
        if (a >= 180.0) a -= 180.0;
        cout << s.x << " " << s.y << " " << a << endl;
    }
    
    return 0;
}