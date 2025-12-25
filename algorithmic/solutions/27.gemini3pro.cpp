#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>

using namespace std;

struct Pt {
    int r, c;
};

int N, M;
vector<Pt> best_sol;

void update(const vector<Pt>& sol, bool swapped) {
    if (sol.size() > best_sol.size()) {
        if (!swapped) {
            best_sol = sol;
        } else {
            best_sol.clear();
            best_sol.reserve(sol.size());
            for (const auto& p : sol) {
                best_sol.push_back({p.c, p.r});
            }
        }
    }
}

// Generates solution using All-Pairs construction
// Assumes n <= m
vector<Pt> solve_all_pairs(int n, int m) {
    vector<Pt> sol;
    // Max pairs
    long long pairs = (long long)n * (n - 1) / 2;
    // We can use at most m columns for pairs
    int cols_for_pairs = 0;
    if (m > 0) cols_for_pairs = (int)min((long long)m, pairs);
    
    // Generate pairs
    int count = 0;
    int col_idx = 1;
    for (int i = 1; i <= n && count < cols_for_pairs; ++i) {
        for (int j = i + 1; j <= n && count < cols_for_pairs; ++j) {
            sol.push_back({i, col_idx});
            sol.push_back({j, col_idx});
            col_idx++;
            count++;
        }
    }
    
    // Remaining columns: fill with 1 point at row 1
    for (; col_idx <= m; ++col_idx) {
        sol.push_back({1, col_idx});
    }
    return sol;
}

// Generates solution using Affine Plane AG(2, p)
// defined over F_p
vector<Pt> solve_affine(int n, int m, int p) {
    vector<Pt> sol;
    sol.reserve(n * (int)sqrt(m) + m); 
    
    int max_r = min(n, p * p);
    
    vector<bool> col_occupied(m, false);

    for (int r = 0; r < max_r; ++r) {
        int u1 = r / p;
        int u2 = r % p;
        
        // Slope lines
        for (int a = 0; a < p; ++a) {
            int term = (a * u1) % p;
            int b = (u2 - term + p) % p;
            int c = a * p + b;
            if (c < m) {
                sol.push_back({r + 1, c + 1});
                col_occupied[c] = true;
            }
        }
        
        // Vertical lines
        int c_vert = p * p + u1;
        if (c_vert < m) {
            sol.push_back({r + 1, c_vert + 1});
            col_occupied[c_vert] = true;
        }
    }
    
    // Fill empty columns
    for (int c = 0; c < m; ++c) {
        if (!col_occupied[c]) {
            sol.push_back({1, c + 1});
        }
    }
    
    return sol;
}

bool is_prime(int x) {
    if (x < 2) return false;
    for (int i = 2; i * i <= x; ++i) if (x % i == 0) return false;
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    // Strategy 1: All Pairs
    if (N <= M) {
        update(solve_all_pairs(N, M), false);
    } else {
        update(solve_all_pairs(M, N), true);
    }
    
    // Strategy 2: Affine Planes
    set<int> candidates;
    
    auto add_candidates_near = [&](int target) {
        // Find closest prime <= target
        for (int p = target; p >= 2; --p) {
            if (is_prime(p)) {
                candidates.insert(p);
                break;
            }
        }
        // Find closest prime >= target
        for (int p = target; p <= 2000; ++p) {
            if (is_prime(p)) {
                candidates.insert(p);
                break;
            }
        }
    };
    
    // Primes around sqrt(N) and sqrt(M)
    add_candidates_near(max(2, (int)sqrt(N)));
    add_candidates_near(max(2, (int)sqrt(M)));
    
    for (int p : candidates) {
        update(solve_affine(N, M, p), false);
        update(solve_affine(M, N, p), true);
    }
    
    cout << best_sol.size() << "\n";
    for (const auto& p : best_sol) {
        cout << p.r << " " << p.c << "\n";
    }
    
    return 0;
}