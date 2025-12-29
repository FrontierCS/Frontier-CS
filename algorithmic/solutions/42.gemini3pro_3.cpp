#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <map>
#include <random>
#include <chrono>

using namespace std;

// Constants
const double PI = acos(-1.0);
const double EPS = 1e-7;

struct Square {
    double x, y, a; // center x, y, angle in degrees
};

struct Solution {
    double L;
    vector<Square> squares;
};

map<int, Solution> memo;

// Helpers
double deg2rad(double deg) {
    return deg * PI / 180.0;
}

// Geometry for SA evaluation
struct Vec2 { double x, y; };

// Calculate overlap between two squares using Separating Axis Theorem
// Returns a "penetration" metric (approximate)
double get_overlap(const Square& s1, const Square& s2) {
    double r1 = deg2rad(s1.a);
    double r2 = deg2rad(s2.a);
    Vec2 c1 = {s1.x, s1.y};
    Vec2 c2 = {s2.x, s2.y};
    
    // Axes to test: 2 from s1, 2 from s2
    // But since squares are rectangles, only 2 axes per square needed
    Vec2 axes[4] = {
        {cos(r1), sin(r1)}, {-sin(r1), cos(r1)},
        {cos(r2), sin(r2)}, {-sin(r2), cos(r2)}
    };
    
    double min_overlap = 1e18;
    
    for (int i = 0; i < 4; ++i) {
        Vec2 axis = axes[i];
        
        // Project s1
        // Half-width of projection of unit square with angle alpha on axis with angle phi
        // is 0.5 * (|cos(alpha-phi)| + |sin(alpha-phi)|)
        // Here axis is (Ax, Ay). s1 basis (cos r1, sin r1) and (-sin r1, cos r1).
        // Dot products give cos of angle diffs.
        double h1 = 0.5 * (fabs(axis.x * cos(r1) + axis.y * sin(r1)) + fabs(axis.x * (-sin(r1)) + axis.y * cos(r1)));
        double proj_c1 = c1.x * axis.x + c1.y * axis.y;
        double p1_min = proj_c1 - h1;
        double p1_max = proj_c1 + h1;
        
        // Project s2
        double h2 = 0.5 * (fabs(axis.x * cos(r2) + axis.y * sin(r2)) + fabs(axis.x * (-sin(r2)) + axis.y * cos(r2)));
        double proj_c2 = c2.x * axis.x + c2.y * axis.y;
        double p2_min = proj_c2 - h2;
        double p2_max = proj_c2 + h2;
        
        double ov = max(0.0, min(p1_max, p2_max) - max(p1_min, p2_min));
        if (ov < 1e-9) return 0.0; // Separated
        min_overlap = min(min_overlap, ov);
    }
    return min_overlap;
}

// Calculate violation of container boundaries
double get_violation(const Square& s, double L) {
    double r = deg2rad(s.a);
    // Bounding box half-extent
    double ext = 0.5 * (fabs(cos(r)) + fabs(sin(r)));
    
    double min_x = s.x - ext;
    double max_x = s.x + ext;
    double min_y = s.y - ext;
    double max_y = s.y + ext;
    
    double v = 0;
    if (min_x < -1e-7) v += -min_x;
    if (max_x > L + 1e-7) v += max_x - L;
    if (min_y < -1e-7) v += -min_y;
    if (max_y > L + 1e-7) v += max_y - L;
    return v;
}

// Generate standard grid solution
Solution solve_grid(int n) {
    int k = (int)ceil(sqrt(n));
    Solution sol;
    sol.L = (double)k;
    for (int i = 0; i < n; ++i) {
        int r = i / k;
        int c = i % k;
        sol.squares.push_back({c + 0.5, r + 0.5, 0.0});
    }
    return sol;
}

// Simulated Annealing for small n
Solution solve_sa(int n, double target_L, double time_limit_sec) {
    Solution sol;
    sol.L = target_L;
    sol.squares.resize(n);
    
    mt19937 rng(1337 + n); // Seed depends on n
    uniform_real_distribution<double> dist_pos(0.5, target_L - 0.5);
    uniform_real_distribution<double> dist_angle(0, 90);
    
    for (int i = 0; i < n; ++i) {
        sol.squares[i] = {dist_pos(rng), dist_pos(rng), dist_angle(rng)};
    }
    
    auto calc_energy = [&](const vector<Square>& sqs) {
        double e = 0;
        for (int i = 0; i < n; ++i) {
            e += get_violation(sqs[i], target_L) * 10.0;
            for (int j = i + 1; j < n; ++j) {
                double ov = get_overlap(sqs[i], sqs[j]);
                if (ov > 0) e += ov * ov;
            }
        }
        return e;
    };
    
    double cur_e = calc_energy(sol.squares);
    double temp = 1.0;
    double cooling = 0.95;
    
    auto start_t = chrono::steady_clock::now();
    int iter = 0;
    
    // Only run limited iterations or time
    while (true) {
        if (iter % 100 == 0) {
             auto now = chrono::steady_clock::now();
             if (chrono::duration<double>(now - start_t).count() > time_limit_sec) break;
             if (cur_e < 1e-8) break;
        }
        iter++;
        
        int idx = rng() % n;
        vector<Square> next_sqs = sol.squares;
        
        double move_scale = temp * target_L * 0.2;
        double rot_scale = temp * 30.0;
        
        uniform_real_distribution<double> m_dist(-move_scale, move_scale);
        uniform_real_distribution<double> r_dist(-rot_scale, rot_scale);
        
        next_sqs[idx].x += m_dist(rng);
        next_sqs[idx].y += m_dist(rng);
        next_sqs[idx].a += r_dist(rng);
        
        // Normalize angle
        while (next_sqs[idx].a >= 90) next_sqs[idx].a -= 90;
        while (next_sqs[idx].a < 0) next_sqs[idx].a += 90;

        // Keep inside loosely to guide
        next_sqs[idx].x = max(0.0, min(target_L, next_sqs[idx].x));
        next_sqs[idx].y = max(0.0, min(target_L, next_sqs[idx].y));
        
        double next_e = calc_energy(next_sqs);
        
        if (next_e < cur_e) {
            sol.squares = next_sqs;
            cur_e = next_e;
        } else {
             if (bernoulli_distribution(exp(-(next_e - cur_e) / (temp * 0.001)))(rng)) {
                 sol.squares = next_sqs;
                 cur_e = next_e;
             }
        }
        
        temp *= cooling;
        if (temp < 1e-4) temp = 1e-4; // sustain low temp noise
    }
    
    if (cur_e < 1e-7) return sol;
    return { -1.0, {} };
}

Solution solve(int n) {
    if (memo.count(n)) return memo[n];
    
    // Strategy 1: Grid
    Solution best_sol = solve_grid(n);
    
    // Strategy 2: Recursive (divide into 4)
    if (n > 1) {
        int sub_n = (n + 3) / 4;
        Solution sub = solve(sub_n);
        Solution rec_sol;
        rec_sol.L = sub.L * 2.0;
        
        double shift[4][2] = {
            {0, 0}, {sub.L, 0}, {0, sub.L}, {sub.L, sub.L}
        };
        
        int count = 0;
        for (int k = 0; k < 4; ++k) {
            for (const auto& s : sub.squares) {
                if (count >= n) break;
                rec_sol.squares.push_back({s.x + shift[k][0], s.y + shift[k][1], s.a});
                count++;
            }
            if (count >= n) break;
        }
        
        if (rec_sol.L < best_sol.L - 1e-9) {
            best_sol = rec_sol;
        }
    }
    
    // Strategy 3: Specialized / SA for small n
    if (n <= 5) {
        if (n == 5) {
            double L = 2.0 + 1.0/sqrt(2.0);
            if (L < best_sol.L) {
                best_sol.L = L;
                best_sol.squares.clear();
                best_sol.squares.push_back({0.5, 0.5, 0});
                best_sol.squares.push_back({L-0.5, 0.5, 0});
                best_sol.squares.push_back({0.5, L-0.5, 0});
                best_sol.squares.push_back({L-0.5, L-0.5, 0});
                best_sol.squares.push_back({L/2.0, L/2.0, 45.0});
            }
        }
    } else if (n <= 25) { // SA limit
        double current_L = best_sol.L;
        double lb = sqrt(n);
        // Try a few target sizes
        for (int k = 1; k <= 8; ++k) {
            double target = lb + (current_L - lb) * (1.0 - k/9.0);
            if (target >= current_L - 1e-4) continue;
            Solution sa = solve_sa(n, target, 0.03); // ~30ms per try
            if (sa.L > 0) {
                best_sol = sa;
                current_L = target;
            }
        }
    }
    
    memo[n] = best_sol;
    return best_sol;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (cin >> n) {
        Solution sol = solve(n);
        
        cout << fixed << setprecision(8) << sol.L << "\n";
        for (const auto& s : sol.squares) {
            double a = s.a;
            // Normalize for output 0 <= a < 180
            while (a >= 180.0) a -= 180.0;
            while (a < 0.0) a += 180.0;
            cout << s.x << " " << s.y << " " << a << "\n";
        }
    }
    return 0;
}