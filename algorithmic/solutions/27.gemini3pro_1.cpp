#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

struct Point {
    int r, c;
};

// Strategy 1: All pairs of rows
// This strategy is effective when m is large relative to n^2 (or n is small).
// We try to fill columns with unique pairs of rows.
vector<Point> solve_pairs(int n, int m) {
    vector<Point> ans;
    // Generate all pairs (r1, r2) with 1 <= r1 < r2 <= n
    vector<pair<int, int>> pairs;
    pairs.reserve(min((long long)m, (long long)n * (n - 1) / 2) + 1);
    
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            pairs.push_back({i, j});
            if (pairs.size() > m) goto pairs_generated; // Optimization
        }
    }
    
pairs_generated:
    int used_cols = 0;
    // Fill columns with pairs
    for (const auto& p : pairs) {
        if (used_cols < m) {
            ans.push_back({p.first, used_cols + 1});
            ans.push_back({p.second, used_cols + 1});
            used_cols++;
        } else {
            break;
        }
    }
    
    // Fill remaining columns with a single point (e.g., row 1)
    // Single points do not create rectangles.
    while (used_cols < m) {
        ans.push_back({1, used_cols + 1});
        used_cols++;
    }
    return ans;
}

// Helper for primes
bool is_prime(int x) {
    if (x < 2) return false;
    for (int i = 2; i * i <= x; ++i) {
        if (x % i == 0) return false;
    }
    return true;
}

// Strategy 2: Affine Plane construction
// This constructs a dense C4-free graph based on geometry over finite fields.
// Effective when n and m are comparable or dense.
vector<Point> solve_affine(int n, int m, int p) {
    vector<Point> ans;
    
    // Map 0..n-1 to points (x, y) in the affine plane A(p)
    // We use a box layout to keep points somewhat clustered, which improves density for subgrids.
    int w_pts = ceil(sqrt(n));
    if (w_pts == 0) w_pts = 1;
    vector<pair<int, int>> pts;
    pts.reserve(n);
    for (int i = 0; i < n; ++i) {
        pts.push_back({i % w_pts, i / w_pts});
    }

    // Map 0..m-1 to lines y = mx + c
    // Similarly use box layout for parameters (m, c)
    int w_lines = ceil(sqrt(m));
    if (w_lines == 0) w_lines = 1;
    vector<pair<int, int>> lines;
    lines.reserve(m);
    for (int j = 0; j < m; ++j) {
        lines.push_back({j % w_lines, j / w_lines});
    }

    // Check incidences: Point (x, y) is on Line (M, C) iff y = Mx + C (mod p)
    // Complexity: O(n * m). Since n*m <= 100000, this is very fast.
    for (int j = 0; j < m; ++j) {
        int M_slope = lines[j].first;
        int C_icept = lines[j].second;
        
        for (int i = 0; i < n; ++i) {
            int x = pts[i].first;
            int y = pts[i].second;
            
            if (y == (M_slope * x + C_icept) % p) {
                ans.push_back({i + 1, j + 1});
            }
        }
    }
    return ans;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Ensure n <= m to reduce cases (swapping back at output)
    bool swapped = false;
    if (n > m) {
        swap(n, m);
        swapped = true;
    }

    // Best solution storage
    vector<Point> best_ans;
    
    // 1. Try Pairs strategy
    best_ans = solve_pairs(n, m);

    // 2. Try Affine plane strategy
    // We need a prime p such that p^2 >= m (to have enough distinct lines)
    // Since n <= m, p^2 >= n is also satisfied.
    int start_p = 0;
    for (int p = 2; ; ++p) {
        if (!is_prime(p)) continue;
        if (p * p >= m) {
            start_p = p;
            break;
        }
    }

    // Try a few primes starting from start_p to find the best fit
    int p = start_p;
    int tries = 0;
    while (tries < 5) { // Try 5 primes
        vector<Point> current = solve_affine(n, m, p);
        if (current.size() > best_ans.size()) {
            best_ans = current;
        }
        
        // Find next prime
        p++;
        while (!is_prime(p)) p++;
        tries++;
    }

    // Output result
    cout << best_ans.size() << "\n";
    for (const auto& pt : best_ans) {
        if (swapped) {
            cout << pt.c << " " << pt.r << "\n";
        } else {
            cout << pt.r << " " << pt.c << "\n";
        }
    }

    return 0;
}