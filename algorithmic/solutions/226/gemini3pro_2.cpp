#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

// Helper function to calculate GCD
long long gcd_func(long long a, long long b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Solves Max Weight Independent Set on a linear chain with weights w
long long solve_linear(const vector<long long>& w) {
    if (w.empty()) return 0;
    int n = w.size();
    if (n == 1) return w[0];
    
    // dp0: max weight for prefix ending at i-1 where w[i-1] is NOT selected
    // dp1: max weight for prefix ending at i-1 where w[i-1] IS selected
    // Initial state for index 0
    long long dp0 = 0;
    long long dp1 = w[0];
    
    for (int i = 1; i < n; ++i) {
        long long new_dp0 = max(dp0, dp1);
        long long new_dp1 = dp0 + w[i];
        dp0 = new_dp0;
        dp1 = new_dp1;
    }
    return max(dp0, dp1);
}

// Solves Max Weight Independent Set on a cycle with weights w
long long solve_cycle(const vector<long long>& w) {
    int n = w.size();
    if (n == 0) return 0;
    if (n == 1) return w[0];
    if (n == 2) return max(w[0], w[1]); 
    if (n == 3) return max({w[0], w[1], w[2]}); 

    // Case 1: Node 0 is NOT selected.
    // The problem reduces to a linear chain from 1 to n-1
    vector<long long> linear1;
    linear1.reserve(n - 1);
    for (int i = 1; i < n; ++i) linear1.push_back(w[i]);
    long long res1 = solve_linear(linear1);

    // Case 2: Node 0 IS selected.
    // Then neighbors 1 and n-1 cannot be selected.
    // The problem reduces to a linear chain from 2 to n-2, plus w[0]
    vector<long long> linear2;
    if (n > 3) {
        linear2.reserve(n - 3);
        for (int i = 2; i < n - 1; ++i) linear2.push_back(w[i]);
    }
    long long res2 = w[0] + solve_linear(linear2);

    return max(res1, res2);
}

// Solves the problem for a specific component size M
// This reduces to finding MWIS on a cycle of length L_prime
long long solve_subproblem(long long M, long long x_prime, long long L_prime) {
    if (M == 0) return 0;
    
    // Determine the frequency of each residue class modulo L_prime
    // in the range [1, M].
    // k in 1..M maps to (k % L_prime).
    // Note: range 1..M covers full cycles Q times.
    // The remainder R covers 1..R.
    // Residue 0 corresponds to L_prime (or multiple of L_prime).
    
    long long Q = M / L_prime;
    long long R = M % L_prime;
    
    // Construct weights for the cycle graph C_{L'}
    // Vertices of cycle are 0..L'-1
    // Vertex j in cycle corresponds to residue (j * x_prime) % L_prime
    vector<long long> w(L_prime);
    long long current_val = 0; // Starts at 0 * x_prime
    
    for (int j = 0; j < L_prime; ++j) {
        // Calculate count for residue `current_val`
        // Residues 1..R appear Q+1 times
        // Residues R+1..L'-1 and 0 appear Q times
        long long count = Q;
        if (current_val != 0 && current_val <= R) {
            count++;
        }
        w[j] = count;
        
        // Move to next vertex in the cycle defined by step x_prime
        current_val += x_prime;
        if (current_val >= L_prime) current_val -= L_prime;
    }
    
    return solve_cycle(w);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    long long n, x, y;
    if (cin >> n >> x >> y) {
        long long g = gcd_func(x, y);
        // Reduce the problem to coprime steps x' and y'
        long long x_prime = x / g;
        long long y_prime = y / g; 
        long long L_prime = x_prime + y_prime;
        
        // The original graph decomposes into g components based on i % g
        // r components have size n/g + 1
        // g-r components have size n/g
        long long q = n / g;
        long long r = n % g;
        
        long long ans = 0;
        
        // Solve for the two types of component sizes
        if (r > 0) {
            long long res1 = solve_subproblem(q + 1, x_prime, L_prime);
            ans += r * res1;
        }
        
        if (g - r > 0) {
            long long res2 = solve_subproblem(q, x_prime, L_prime);
            ans += (g - r) * res2;
        }
        
        cout << ans << endl;
    }
    return 0;
}