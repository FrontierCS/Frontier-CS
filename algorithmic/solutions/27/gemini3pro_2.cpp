#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>

using namespace std;

struct Point {
    int r, c;
};

// Generate Comb solution: Full first row and Full first column
vector<Point> solve_comb(int n, int m) {
    vector<Point> pts;
    pts.reserve(n + m - 1);
    for (int c = 1; c <= m; ++c) pts.push_back({1, c});
    for (int r = 2; r <= n; ++r) pts.push_back({r, 1});
    return pts;
}

// Check if a number is prime
bool is_prime(int x) {
    if (x < 2) return false;
    for (int i = 2; i * i <= x; ++i) {
        if (x % i == 0) return false;
    }
    return true;
}

// Solve using Projective Plane PG(2, p)
// We map grid rows to points (or lines) and grid cols to lines (or points)
// Attempt to select best subset of rows/cols
vector<Point> solve_pg(int n, int m, int p) {
    long long N_long = 1LL * p * p + p + 1;
    if (N_long > 200000) return {}; // Safety limit
    int N = (int)N_long;

    // Generate incidences of PG(2, p)
    // Points are 0..N-1
    // We implicitly iterate lines. Each line is a set of points.
    
    // We want to select 'n' rows and 'm' columns from the N x N incidence matrix
    // to maximize 1s.
    // Let's assume Rows -> Points, Cols -> Lines.
    // We initially select rows 0..n-1 (clamped to N).
    // Then select best m lines.
    // Then select best n points for those lines.
    
    int n_eff = min(n, N);
    int m_eff = min(m, N);
    
    vector<bool> in_row_set(N, false);
    for(int i=0; i<n_eff; ++i) in_row_set[i] = true;
    
    // Weights for lines (columns)
    vector<int> col_weights(N, 0);

    // Helper to process a line defined by [A, B, C]
    // Ax + By + Cz = 0
    auto process_lines = [&](bool update_cols, const vector<bool>& current_rows, vector<int>& weights) {
        // Enumerate all lines
        // Type 1: [0, 0, 1] -> z=0. Points: (1, y, 0), (0, 1, 0).
        // Type 2: [0, 1, C] -> y + Cz = 0.
        // Type 3: [1, B, C] -> x + By + Cz = 0.
        
        int line_idx = 0;
        
        // Line [0, 0, 1]
        {
            int w = 0;
            vector<int> points_on_line;
            // (0, 1, 0) -> index 1
            points_on_line.push_back(1);
            // (1, y, 0) -> indices p+1 + y*p (wait, mapping is tricky)
            // Let's standardize point mapping
            // Point 0: (0,0,1)
            // Points 1..p: (0,1,z) for z in 0..p-1
            // Points p+1..p^2+p: (1,y,z) for y,z in 0..p-1 => index = p + 1 + y*p + z
            
            // For line [0, 0, 1] (z=0):
            // (0, 1, 0) is index 1 + 0 = 1.
            // (1, y, 0) is index p + 1 + y*p.
            for (int y = 0; y < p; ++y) points_on_line.push_back(p + 1 + y * p);
            
            if (update_cols) {
                int c = 0;
                for (int u : points_on_line) if (u < N && current_rows[u]) c++;
                weights[line_idx] = c;
            } else { // update rows from chosen cols
                 if (current_rows[line_idx]) { // here current_rows acts as "is col chosen"
                     for (int u : points_on_line) if (u < N) weights[u]++;
                 }
            }
            line_idx++;
        }
        
        // Lines [0, 1, C] for C in 0..p-1
        // Eq: y + Cz = 0
        for (int C = 0; C < p; ++C) {
            vector<int> points_on_line;
            // (0, 0, 1) -> y=0, z=1 => 0 + C = C. If C=0?
            // Wait, (0,0,1) has y=0, z=1. Eq: 0 + C*1 = C. So only on line C=0.
            if (C == 0) points_on_line.push_back(0);
            
            // (1, y, z): y + Cz = 0 => y = -Cz.
            // For each z, y is determined.
            for (int z = 0; z < p; ++z) {
                int y = (p - (C * z) % p) % p;
                points_on_line.push_back(p + 1 + y * p + z);
            }
            
            if (update_cols) {
                int c = 0;
                for (int u : points_on_line) if (u < N && current_rows[u]) c++;
                weights[line_idx] = c;
            } else {
                 if (current_rows[line_idx]) {
                     for (int u : points_on_line) if (u < N) weights[u]++;
                 }
            }
            line_idx++;
        }

        // Lines [1, B, C] for B, C in 0..p-1
        // Eq: x + By + Cz = 0
        for (int B = 0; B < p; ++B) {
            for (int C = 0; C < p; ++C) {
                vector<int> points_on_line;
                // (0, 0, 1) -> C=0?
                if (C == 0) points_on_line.push_back(0);
                
                // (0, 1, z) -> B + Cz = 0.
                if (C != 0) {
                    // z = -B * inv(C)
                    // Compute inv(C) naive
                    int invC = 1;
                    for(; invC<p; ++invC) if((C*invC)%p == 1) break;
                    int z = (p - B) % p;
                    z = (z * invC) % p;
                    points_on_line.push_back(1 + z);
                } else if (B == 0) {
                    // B=0, C=0. Eq: 0=0. All points (0,1,z).
                    // But lines in PG(2,p) have p+1 points. 
                    // [1,0,0] => x=0. 
                    // Points (0,1,z) satisfy x=0. There are p such points.
                    // Also (0,0,1). Total p+1.
                    for(int z=0; z<p; ++z) points_on_line.push_back(1 + z);
                }
                
                // (1, y, z) -> 1 + By + Cz = 0
                if (B != 0) {
                    // y = -(1 + Cz)/B
                    int invB = 1;
                    for(; invB<p; ++invB) if((B*invB)%p == 1) break;
                    for (int z = 0; z < p; ++z) {
                        int val = (1 + C * z) % p;
                        int y = (p - val) % p;
                        y = (y * invB) % p;
                        points_on_line.push_back(p + 1 + y * p + z);
                    }
                } else {
                    // B=0. 1 + Cz = 0.
                    if (C != 0) {
                        // z fixed. y arbitrary.
                        int invC = 1;
                        for(; invC<p; ++invC) if((C*invC)%p == 1) break;
                        int z = (p - 1); // -1 mod p
                        z = (z * invC) % p;
                        for (int y = 0; y < p; ++y) {
                            points_on_line.push_back(p + 1 + y * p + z);
                        }
                    }
                    // B=0, C=0 -> 1=0 impossible.
                }
                
                if (update_cols) {
                    int c = 0;
                    for (int u : points_on_line) if (u < N && current_rows[u]) c++;
                    weights[line_idx] = c;
                } else {
                     if (current_rows[line_idx]) {
                         for (int u : points_on_line) if (u < N) weights[u]++;
                     }
                }
                line_idx++;
            }
        }
    };

    // Pass 1: Calc col weights based on initial rows
    process_lines(true, in_row_set, col_weights);
    
    // Select best m lines
    vector<pair<int, int>> sorted_cols(N);
    for(int i=0; i<N; ++i) sorted_cols[i] = {col_weights[i], i};
    sort(sorted_cols.rbegin(), sorted_cols.rend());
    
    vector<bool> in_col_set(N, false);
    for(int i=0; i<m_eff; ++i) in_col_set[sorted_cols[i].second] = true;
    
    // Pass 2: Calc row weights based on selected cols
    vector<int> row_weights(N, 0);
    process_lines(false, in_col_set, row_weights); // false -> update weights (which are rows), in_col_set passed as current
    
    // Select best n rows
    vector<pair<int, int>> sorted_rows(N);
    for(int i=0; i<N; ++i) sorted_rows[i] = {row_weights[i], i};
    sort(sorted_rows.rbegin(), sorted_rows.rend());
    
    vector<int> final_rows;
    vector<int> row_map(N, -1);
    for(int i=0; i<n_eff; ++i) {
        final_rows.push_back(sorted_rows[i].second);
        row_map[sorted_rows[i].second] = i + 1; // 1-based coord
    }
    
    vector<int> final_cols;
    vector<int> col_map(N, -1);
    for(int i=0; i<m_eff; ++i) {
        final_cols.push_back(sorted_cols[i].second);
        col_map[sorted_cols[i].second] = i + 1; // 1-based coord
    }
    
    // Collect points
    vector<Point> pts;
    // We need to iterate again to find intersections between final_rows and final_cols
    // Or just check incidences one last time
    // To be fast, we can just iterate lines in in_col_set
    
    // Re-run line generation restricted to selected cols
    auto collect_points = [&](const vector<bool>& selected_cols, const vector<int>& r_map, const vector<int>& c_map) {
         int line_idx = 0;
         auto handle_line = [&](const vector<int>& points) {
             if (selected_cols[line_idx]) {
                 int c_coord = c_map[line_idx];
                 for (int u : points) {
                     if (u < N && r_map[u] != -1) {
                         pts.push_back({r_map[u], c_coord});
                     }
                 }
             }
             line_idx++;
         };
         
         // Same generation logic...
         // [0,0,1]
         {
             vector<int> p_list; p_list.push_back(1);
             for(int y=0; y<p; ++y) p_list.push_back(p+1+y*p);
             handle_line(p_list);
         }
         // [0,1,C]
         for (int C=0; C<p; ++C) {
             vector<int> p_list;
             if(C==0) p_list.push_back(0);
             for(int z=0; z<p; ++z) {
                 int y = (p - (C*z)%p)%p;
                 p_list.push_back(p+1+y*p+z);
             }
             handle_line(p_list);
         }
         // [1,B,C]
         for(int B=0; B<p; ++B) {
             for(int C=0; C<p; ++C) {
                 vector<int> p_list;
                 if(C==0) p_list.push_back(0);
                 if(C!=0) {
                     int invC=1; while((C*invC)%p!=1) invC++;
                     int z=(p-B)%p; z=(z*invC)%p;
                     p_list.push_back(1+z);
                 } else if(B==0) {
                     for(int z=0; z<p; ++z) p_list.push_back(1+z);
                 }
                 if(B!=0) {
                     int invB=1; while((B*invB)%p!=1) invB++;
                     for(int z=0; z<p; ++z) {
                         int val=(1+C*z)%p; int y=(p-val)%p; y=(y*invB)%p;
                         p_list.push_back(p+1+y*p+z);
                     }
                 } else if (C!=0) {
                     int invC=1; while((C*invC)%p!=1) invC++;
                     int z=(p-1); z=(z*invC)%p;
                     for(int y=0; y<p; ++y) p_list.push_back(p+1+y*p+z);
                 }
                 handle_line(p_list);
             }
         }
    };
    
    collect_points(in_col_set, row_map, col_map);
    return pts;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    // Case n=1 or m=1
    if (n == 1) {
        cout << m << "\n";
        for (int i = 1; i <= m; ++i) cout << "1 " << i << "\n";
        return 0;
    }
    if (m == 1) {
        cout << n << "\n";
        for (int i = 1; i <= n; ++i) cout << i << " 1\n";
        return 0;
    }

    // Try Comb
    vector<Point> best_pts = solve_comb(n, m);
    
    // Try Transposed Comb (Row 1 full, Col 1 full vs Col 1 full, Row 1 full is same score n+m-1)
    
    // Try PG(2, p)
    // We try a few primes such that N_p >= max(n, m) or close to it.
    int target = max(n, m);
    // Find primes
    vector<int> candidates;
    for (int p = 2; p <= 350; ++p) {
        if (!is_prime(p)) continue;
        long long N = 1LL * p * p + p + 1;
        if (N >= target) {
            candidates.push_back(p);
            if (candidates.size() >= 2) break; // Take 2 closest upper bounds
        }
    }
    // Also try largest prime such that N <= target
    for (int p = 350; p >= 2; --p) {
        if (!is_prime(p)) continue;
        long long N = 1LL * p * p + p + 1;
        if (N <= target) {
            candidates.push_back(p);
            break;
        }
    }
    
    // Try both orientations for each prime
    for (int p : candidates) {
        // Normal
        {
            vector<Point> pts = solve_pg(n, m, p);
            if (pts.size() > best_pts.size()) best_pts = pts;
        }
        // Transposed logic (swap n, m, solve, swap coords back)
        {
            vector<Point> pts = solve_pg(m, n, p);
            for (auto& pt : pts) swap(pt.r, pt.c);
            if (pts.size() > best_pts.size()) best_pts = pts;
        }
    }
    
    cout << best_pts.size() << "\n";
    for (const auto& pt : best_pts) {
        cout << pt.r << " " << pt.c << "\n";
    }
    
    return 0;
}