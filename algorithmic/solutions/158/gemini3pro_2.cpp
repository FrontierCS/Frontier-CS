#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <iomanip>

using namespace std;

// Constants defined in the problem
const int MAX_COORD = 1000000000;
const int CAKE_RADIUS = 10000;
const double PI = acos(-1.0);

struct Point {
    int x, y;
};

struct Line {
    long long px, py, qx, qy;
};

// Global variables for problem input
int N, K;
vector<int> a(11);
vector<Point> strawberries;

// Fast Random Number Generator (Xorshift)
struct Xorshift {
    uint64_t x = 88172645463325252ULL;
    inline uint64_t next() {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        return x;
    }
    // Returns random integer in [0, range-1]
    inline int next_int(int range) {
        return next() % range;
    }
    // Returns random double in [0, 1)
    inline double next_double() {
        return (next() & 0xFFFFFFFFFFFFF) * (1.0 / 4503599627370496.0);
    }
} rng;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read Input
    if (!(cin >> N >> K)) return 0;
    for (int i = 1; i <= 10; ++i) cin >> a[i];
    strawberries.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> strawberries[i].x >> strawberries[i].y;
    }

    // Start timer
    auto start_time = chrono::steady_clock::now();

    // Variables to store the best solution found so far
    int max_score_numerator = -1;
    vector<Line> best_lines;

    // Buffers for calculation to avoid re-allocation
    vector<uint64_t> keys;
    keys.reserve(N);
    int b[12]; // b[d] stores count of pieces with d strawberries

    // Perform random search until time limit approaches
    // AHC012 typically has a 3-second time limit. We stop safely before that.
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::duration<double>>(curr_time - start_time).count();
        if (elapsed > 2.8) break;

        // --- Generate Random Grid Parameters ---
        // 1. Rotation angle theta
        double theta = rng.next_double() * PI;
        double cos_t = cos(theta);
        double sin_t = sin(theta);

        // 2. Grid spacings (wx, wy)
        // Heuristic: try spacings that create cells containing few strawberries.
        // Range [200, 2000] covers various densities.
        int wx = 200 + rng.next_int(1800);
        int wy = 200 + rng.next_int(1800);

        // 3. Grid offsets (ox, oy)
        int ox = rng.next_int(wx);
        int oy = rng.next_int(wy);

        // --- Determine Grid Lines ---
        // We only generate lines that intersect or touch the cake (radius 10000).
        // Rotated coord range is approx [-10000, 10000].
        // x' = k * wx + ox. Constraint: -CAKE_RADIUS <= x' <= CAKE_RADIUS
        
        int min_kx = ceil((-CAKE_RADIUS - ox) / (double)wx);
        int max_kx = floor((CAKE_RADIUS - ox) / (double)wx);
        
        int min_ky = ceil((-CAKE_RADIUS - oy) / (double)wy);
        int max_ky = floor((CAKE_RADIUS - oy) / (double)wy);
        
        int lines_x = max(0, max_kx - min_kx + 1);
        int lines_y = max(0, max_ky - min_ky + 1);
        
        // Check constraints
        if (lines_x + lines_y > K) continue; // Too many lines
        if (lines_x + lines_y == 0) continue; // Empty cut (unlikely to be optimal but valid)

        // --- Evaluate Solution ---
        keys.clear();
        // Use a large offset to ensure cell indices are positive for bitwise key generation
        const long long OFFSET_IDX = 2000; 
        
        for (int i = 0; i < N; ++i) {
            // Rotate point
            double rx = strawberries[i].x * cos_t - strawberries[i].y * sin_t;
            double ry = strawberries[i].x * sin_t + strawberries[i].y * cos_t;
            
            // Determine cell index
            long long kx = floor((rx - ox) / wx);
            long long ky = floor((ry - oy) / wy);
            
            // Create a unique key for the cell (kx, ky)
            // Indices are roughly in [-50, 50], so offset makes them safe for uint32
            uint64_t key = ((uint64_t)(kx + OFFSET_IDX) << 32) | (uint32_t)(ky + OFFSET_IDX);
            keys.push_back(key);
        }
        
        // Sort keys to group strawberries in the same cell
        sort(keys.begin(), keys.end());
        
        // Count distribution of piece sizes
        for(int i = 0; i <= 10; ++i) b[i] = 0;
        
        if (!keys.empty()) {
            int current_run = 1;
            for (size_t i = 1; i < keys.size(); ++i) {
                if (keys[i] == keys[i-1]) {
                    current_run++;
                } else {
                    if (current_run <= 10) b[current_run]++;
                    current_run = 1;
                }
            }
            if (current_run <= 10) b[current_run]++;
        }
        
        // Calculate score numerator sum(min(a_d, b_d))
        int current_score = 0;
        for (int d = 1; d <= 10; ++d) {
            current_score += min(a[d], b[d]);
        }
        
        // Update best solution
        if (current_score > max_score_numerator) {
            max_score_numerator = current_score;
            best_lines.clear();
            
            // Length for defining line points (must be large enough to be robust)
            double L = 4.0e8; 

            // Generate X-lines corresponding to x' = C
            // Equation: x cos(theta) - y sin(theta) = C
            // Point on line closest to origin: P0 = (C cos, -C sin)
            // Direction vector: (sin, cos)
            for (int k = min_kx; k <= max_kx; ++k) {
                double C = k * (double)wx + ox;
                double p0x = C * cos_t;
                double p0y = -C * sin_t;
                
                Line l;
                l.px = round(p0x + L * sin_t);
                l.py = round(p0y + L * cos_t);
                l.qx = round(p0x - L * sin_t);
                l.qy = round(p0y - L * cos_t);
                best_lines.push_back(l);
            }
            
            // Generate Y-lines corresponding to y' = C
            // Equation: x sin(theta) + y cos(theta) = C
            // Point on line closest to origin: P0 = (C sin, C cos)
            // Direction vector: (cos, -sin)
            for (int k = min_ky; k <= max_ky; ++k) {
                double C = k * (double)wy + oy;
                double p0x = C * sin_t;
                double p0y = C * cos_t;
                
                Line l;
                l.px = round(p0x + L * cos_t);
                l.py = round(p0y - L * sin_t);
                l.qx = round(p0x - L * cos_t);
                l.qy = round(p0y + L * sin_t);
                best_lines.push_back(l);
            }
        }
    }

    // Output Result
    cout << best_lines.size() << "\n";
    for (const auto& l : best_lines) {
        cout << l.px << " " << l.py << " " << l.qx << " " << l.qy << "\n";
    }

    return 0;
}