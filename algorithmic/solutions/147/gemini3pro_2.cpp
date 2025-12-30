#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// The grid size is fixed at 10000x10000
const int GRID_SIZE = 10000;

// Representation of a rectangle: [x1, x2) x [y1, y2)
struct Rect {
    int x1, y1, x2, y2;
    int area() const { return (x2 - x1) * (y2 - y1); }
};

// Input request structure
struct Request {
    int id;
    int x, y, r;
};

int n;
vector<Request> requests;
vector<Rect> rects;

// Helper to calculate the satisfaction score for a given area target vs actual
double calc_score_val(int target_area, int current_area) {
    if (current_area == 0) return 0.0;
    double ratio = (double)min(target_area, current_area) / (double)max(target_area, current_area);
    double term = 1.0 - ratio;
    return 1.0 - term * term;
}

// Wrapper to get score for rectangle i
double get_rect_score(int i, const Rect& r) {
    return calc_score_val(requests[i].r, r.area());
}

// Check if a rectangle configuration is valid for company i
bool is_valid(int i, const Rect& r) {
    // Check bounds
    if (r.x1 < 0 || r.y1 < 0 || r.x2 > GRID_SIZE || r.y2 > GRID_SIZE) return false;
    // Check positive area
    if (r.x1 >= r.x2 || r.y1 >= r.y2) return false;
    // Check if it contains the required point (x_i + 0.5, y_i + 0.5)
    // Integer logic: x_i must be in [x1, x2-1], so x1 <= x_i < x2
    if (requests[i].x < r.x1 || requests[i].x >= r.x2) return false;
    if (requests[i].y < r.y1 || requests[i].y >= r.y2) return false;
    return true;
}

// Check if two rectangles overlap
bool check_overlap(const Rect& r1, const Rect& r2) {
    return max(r1.x1, r2.x1) < min(r1.x2, r2.x2) &&
           max(r1.y1, r2.y1) < min(r1.y2, r2.y2);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    requests.resize(n);
    rects.resize(n);
    for (int i = 0; i < n; ++i) {
        requests[i].id = i;
        cin >> requests[i].x >> requests[i].y >> requests[i].r;
        // Initialize with minimal valid 1x1 rectangles
        rects[i] = {requests[i].x, requests[i].y, requests[i].x + 1, requests[i].y + 1};
    }

    auto start_time = chrono::steady_clock::now();
    mt19937 rng(1337);

    // Time management
    // AHC001 usually allows 5 seconds. We use a safe margin.
    double time_limit = 4.85; 
    
    // Simulated Annealing parameters
    double t_start = 0.5;
    double t_end = 1e-7;
    double current_temp = t_start;
    
    long long iterations = 0;
    
    // Temporary storage for moves
    vector<pair<int, Rect>> changes;
    changes.reserve(n);

    while (true) {
        iterations++;
        // Check time every 1024 iterations
        if ((iterations & 1023) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            // Update temperature
            double progress = elapsed / time_limit;
            current_temp = t_start + (t_end - t_start) * progress;
        }

        // 1. Pick a random rectangle
        int i = rng() % n;
        
        // 2. Pick a random edge to modify (0: x1, 1: y1, 2: x2, 3: y2)
        int edge = rng() % 4;
        
        // 3. Determine move size (mix of small and large moves)
        int r_dist = rng() % 100;
        int delta;
        if (r_dist < 60) delta = (rng() % 3) - 1;       // Small tweak: -1, 0, 1
        else if (r_dist < 90) delta = (rng() % 21) - 10;// Medium: [-10, 10]
        else delta = (rng() % 101) - 50;                // Large: [-50, 50]
        
        if (delta == 0) continue;

        Rect new_r = rects[i];
        if (edge == 0) new_r.x1 += delta;
        else if (edge == 1) new_r.y1 += delta;
        else if (edge == 2) new_r.x2 += delta;
        else new_r.y2 += delta;

        // Basic validity check for the modified rectangle
        if (!is_valid(i, new_r)) continue;

        // Check if this move is expanding the rectangle outward
        bool expanding = false;
        if (edge == 0 && delta < 0) expanding = true;      // Left edge moving left
        else if (edge == 1 && delta < 0) expanding = true; // Bottom edge moving down
        else if (edge == 2 && delta > 0) expanding = true; // Right edge moving right
        else if (edge == 3 && delta > 0) expanding = true; // Top edge moving up

        bool possible = true;
        double score_delta = 0;
        
        // Remove old score of i
        score_delta -= get_rect_score(i, rects[i]);
        // Add new score of i
        score_delta += get_rect_score(i, new_r);

        changes.clear();
        changes.push_back({i, new_r});

        if (expanding) {
            // If expanding, check for overlaps
            for (int j = 0; j < n; ++j) {
                if (i == j) continue;
                if (check_overlap(new_r, rects[j])) {
                    // Collision detected. Try to resolve by shrinking j.
                    Rect nj = rects[j];
                    
                    // "Push" logic: align j's boundary to i's new boundary
                    if (edge == 0) nj.x2 = new_r.x1;       // i expanded left, j shrinks right edge
                    else if (edge == 1) nj.y2 = new_r.y1;  // i expanded down, j shrinks top edge
                    else if (edge == 2) nj.x1 = new_r.x2;  // i expanded right, j shrinks left edge
                    else nj.y1 = new_r.y2;                 // i expanded up, j shrinks bottom edge

                    // Check if j remains valid after shrinking
                    if (!is_valid(j, nj)) {
                        possible = false;
                        break;
                    }
                    
                    // Update scores for j
                    score_delta -= get_rect_score(j, rects[j]);
                    score_delta += get_rect_score(j, nj);
                    changes.push_back({j, nj});
                }
            }
        }
        
        if (!possible) continue;

        // SA Acceptance Criteria
        // If score improves, always accept.
        // If score worsens, accept with probability exp(delta / temp).
        if (score_delta >= 0 || bernoulli_distribution(exp(score_delta / current_temp))(rng)) {
            for (const auto& p : changes) {
                rects[p.first] = p.second;
            }
        }
    }

    // Output results
    for (int i = 0; i < n; ++i) {
        cout << rects[i].x1 << " " << rects[i].y1 << " " << rects[i].x2 << " " << rects[i].y2 << "\n";
    }

    return 0;
}