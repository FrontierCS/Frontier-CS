#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to calculate extended GCD
long long extended_gcd(long long a, long long b, long long &x, long long &y) {
    if (a == 0) {
        x = 0;
        y = 1;
        return b;
    }
    long long x1, y1;
    long long d = extended_gcd(b % a, a, x1, y1);
    x = y1 - (b / a) * x1;
    y = x1;
    return d;
}

// Modular inverse
long long modInverse(long long a, long long m) {
    long long x, y;
    long long g = extended_gcd(a, m, x, y);
    // Since X and M are coprime, g should be 1
    return (x % m + m) % m;
}

// Solve linear max independent set for subarray w[start...end-1]
// The problem is finding max weight independent set on a path graph
long long solve_linear_opt(const vector<long long>& w, int start, int end) {
    int len = end - start;
    if (len <= 0) return 0;
    if (len == 1) return w[start];
    
    long long prev2 = w[start];
    long long prev1 = max(w[start], w[start+1]);
    
    for (int i = 2; i < len; ++i) {
        long long curr = max(prev1, prev2 + w[start+i]);
        prev2 = prev1;
        prev1 = curr;
    }
    return prev1;
}

// Solve max weighted independent set on a cycle graph
long long solve_cycle_opt(const vector<long long>& w) {
    int m = w.size();
    if (m == 0) return 0;
    if (m == 1) return w[0];
    
    // Case 1: Vertex 0 is NOT picked. 
    // This reduces to linear problem on vertices 1 to m-1.
    long long ans1 = solve_linear_opt(w, 1, m);
    
    // Case 2: Vertex 0 IS picked.
    // Then neighbors 1 and m-1 cannot be picked.
    // This reduces to linear problem on vertices 2 to m-2, plus weight of 0.
    long long ans2 = w[0];
    if (m > 3) {
        ans2 += solve_linear_opt(w, 2, m-1);
    }
    // If m=2, neighbors are 1. Picking 0 excludes 1. Remainder empty. ans2 = w[0].
    // If m=3, neighbors 1, 2. Picking 0 excludes 1, 2. Remainder empty. ans2 = w[0].
    
    return max(ans1, ans2);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long n, x, y;
    if (!(cin >> n >> x >> y)) return 0;

    // Calculate parameters for the periodic structure
    long long g = std::gcd(x, y);
    long long X = x / g;
    // Period M for each component
    long long M = (x + y) / g;
    
    // Calculate modular inverse of X modulo M. 
    // Since gcd(x/g, (x+y)/g) = gcd(x/g, y/g) = 1, inverse exists.
    long long invX = modInverse(X, M);
    
    long long total_ans = 0;
    vector<long long> w(M);
    
    // The problem decomposes into g independent components based on residue modulo g.
    for (long long i = 0; i < g; ++i) {
        // Check if there are any numbers with residue i modulo g in 1..n
        if (i + 1 > n) break;
        
        // Count of numbers in 1..n congruent to i+1 modulo g
        long long count = (n - (i + 1)) / g + 1;
        
        long long q = count / M;
        long long r = count % M;
        
        // Base weight for all nodes in the cycle is q (full periods)
        std::fill(w.begin(), w.end(), q);
        
        // Add 1 to the weights corresponding to the remainder r
        // The mapping from linear index k to cycle index is pos(k) = (k * invX) % M
        long long curr = 0;
        long long step = invX;
        for (long long k = 0; k < r; ++k) {
            w[curr]++;
            curr += step;
            if (curr >= M) curr -= M;
        }
        
        // Solve the subproblem for this component
        total_ans += solve_cycle_opt(w);
    }
    
    cout << total_ans << endl;

    return 0;
}