#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>
#include <cstdlib>

using namespace std;

const double PI = acos(-1.0);

struct Square {
    double x, y, a; // center x, y, angle in degrees
};

struct Point {
    double x, y;
};

// Returns the 4 corners of a square given center and angle
vector<Point> get_corners(const Square& s) {
    double rad = s.a * PI / 180.0;
    vector<Point> corners;
    double c = cos(rad), s_val = sin(rad);
    // 4 corners of unit square relative to center: (+-0.5, +-0.5)
    double dx[] = {-0.5, 0.5, 0.5, -0.5};
    double dy[] = {-0.5, -0.5, 0.5, 0.5};
    for (int i = 0; i < 4; ++i) {
        double rx = dx[i] * c - dy[i] * s_val;
        double ry = dx[i] * s_val + dy[i] * c;
        corners.push_back({s.x + rx, s.y + ry});
    }
    return corners;
}

// Check for overlap between two squares using Separating Axis Theorem (approximate penetration depth)
double get_overlap(const Square& s1, const Square& s2) {
    double r1 = s1.a * PI / 180.0;
    double r2 = s2.a * PI / 180.0;
    
    Point axes[4] = {
        {cos(r1), sin(r1)}, { -sin(r1), cos(r1)},
        {cos(r2), sin(r2)}, { -sin(r2), cos(r2)}
    };
    
    auto c1 = get_corners(s1);
    auto c2 = get_corners(s2);
    
    double min_overlap = 1e18;
    
    for (int i = 0; i < 4; ++i) {
        double min1 = 1e18, max1 = -1e18;
        for (const auto& p : c1) {
            double proj = p.x * axes[i].x + p.y * axes[i].y;
            if (proj < min1) min1 = proj;
            if (proj > max1) max1 = proj;
        }
        
        double min2 = 1e18, max2 = -1e18;
        for (const auto& p : c2) {
            double proj = p.x * axes[i].x + p.y * axes[i].y;
            if (proj < min2) min2 = proj;
            if (proj > max2) max2 = proj;
        }
        
        double overlap = max(0.0, min(max1, max2) - max(min1, min2));
        if (overlap < 1e-9) return 0.0; // Separated
        if (overlap < min_overlap) min_overlap = overlap;
    }
    return min_overlap;
}

// Calculate sum of violations where square extends beyond [0, L] x [0, L]
double get_boundary_violation(const Square& s, double L) {
    auto corners = get_corners(s);
    double viol = 0;
    for (const auto& p : corners) {
        if (p.x < 0) viol += -p.x;
        else if (p.x > L) viol += p.x - L;
        if (p.y < 0) viol += -p.y;
        else if (p.y > L) viol += p.y - L;
    }
    return viol;
}

// Base solver for n <= 100
pair<double, vector<Square>> solve_base(int n) {
    // Hardcoded optimal solution for n=5
    if (n == 5) {
        double L = 2.0 + 1.0/sqrt(2.0); // approx 2.70710678
        vector<Square> res;
        res.push_back({0.5, 0.5, 0});
        res.push_back({L-0.5, 0.5, 0});
        res.push_back({0.5, L-0.5, 0});
        res.push_back({L-0.5, L-0.5, 0});
        res.push_back({L/2.0, L/2.0, 45.0});
        return {L, res};
    }
    
    int k = (int)ceil(sqrt(n));
    // Use grid for perfect squares or very small n where optimization is hard/useless
    if (k*k == n || n <= 3) {
        double L = (double)k;
        if (n == 2 || n == 3) L = 2.0; 
        vector<Square> res;
        int count = 0;
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                if (count < n) {
                    res.push_back({0.5 + i, 0.5 + j, 0});
                    count++;
                }
            }
        }
        return {L, res};
    }
    
    // For other small n, try to improve upon grid using Simulated Annealing
    double low = sqrt(n);
    double high = ceil(sqrt(n));
    
    // Initial safe solution (grid)
    vector<Square> best_res;
    int count = 0;
    for(int i=0; i<k; ++i) for(int j=0; j<k; ++j) {
        if(count < n) {
            best_res.push_back({0.5+i, 0.5+j, 0});
            count++;
        }
    }
    double best_L = high;
    
    clock_t start = clock();
    double time_limit = 0.8; // seconds
    
    while ((double)(clock() - start) / CLOCKS_PER_SEC < time_limit) {
        double target_L = (low + high) / 2.0;
        vector<Square> current = best_res;
        
        // Random initialization
        for(auto& sq : current) {
            sq.x = ((double)rand()/RAND_MAX) * (target_L - 1.0) + 0.5;
            sq.y = ((double)rand()/RAND_MAX) * (target_L - 1.0) + 0.5;
            sq.a = ((double)rand()/RAND_MAX) * 90.0;
        }

        bool possible = false;
        double temp = 0.1; 
        double cooling = 0.98;
        int max_iter = 2000;
        
        double current_viol = 0;
        for(int i=0; i<n; ++i) {
            current_viol += get_boundary_violation(current[i], target_L);
            for(int j=i+1; j<n; ++j) current_viol += get_overlap(current[i], current[j]);
        }
        
        for(int iter=0; iter<max_iter; ++iter) {
            if (current_viol < 1e-7) {
                possible = true;
                break;
            }
            
            int idx = rand() % n;
            Square saved = current[idx];
            
            double old_local = get_boundary_violation(saved, target_L);
            for(int j=0; j<n; ++j) if(idx!=j) old_local += get_overlap(saved, current[j]);
            
            double move_scale = temp * 0.5;
            double rot_scale = temp * 45.0;
            
            current[idx].x += ((double)rand()/RAND_MAX - 0.5) * move_scale;
            current[idx].y += ((double)rand()/RAND_MAX - 0.5) * move_scale;
            current[idx].a += ((double)rand()/RAND_MAX - 0.5) * rot_scale;
            while(current[idx].a >= 180) current[idx].a -= 180;
            while(current[idx].a < 0) current[idx].a += 180;
            
            // Heuristic clamp to keep inside
            current[idx].x = max(0.5, min(target_L-0.5, current[idx].x));
            current[idx].y = max(0.5, min(target_L-0.5, current[idx].y));
            
            double new_local = get_boundary_violation(current[idx], target_L);
            for(int j=0; j<n; ++j) if(idx!=j) new_local += get_overlap(current[idx], current[j]);
            
            double delta = new_local - old_local;
            
            if (delta < 0 || ((double)rand()/RAND_MAX) < exp(-delta * 10 / temp)) {
                current_viol += delta;
            } else {
                current[idx] = saved;
            }
            temp *= cooling;
        }
        
        if (possible) {
            best_L = target_L;
            best_res = current;
            high = target_L;
        } else {
            low = target_L;
        }
    }
    
    return {best_L, best_res};
}

// Recursive solver for large n
pair<double, vector<Square>> solve_recursive(int n) {
    if (n <= 100) return solve_base(n);
    
    int sub_n = (n + 3) / 4;
    auto sub_sol = solve_recursive(sub_n);
    double L_sub = sub_sol.first;
    const auto& squares_sub = sub_sol.second;
    
    double L = 2.0 * L_sub;
    vector<Square> res;
    res.reserve(n);
    
    double offsets[4][2] = {
        {0, 0}, {L_sub, 0}, {0, L_sub}, {L_sub, L_sub}
    };
    
    int count = 0;
    for (int k = 0; k < 4 && count < n; ++k) {
        for (const auto& s : squares_sub) {
            if (count >= n) break;
            res.push_back({s.x + offsets[k][0], s.y + offsets[k][1], s.a});
            count++;
        }
    }
    return {L, res};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(42); 
    int n;
    if (cin >> n) {
        auto ans = solve_recursive(n);
        cout << fixed << setprecision(6) << ans.first << endl;
        for (const auto& s : ans.second) {
            cout << s.x << " " << s.y << " " << s.a << endl;
        }
    }
    return 0;
}