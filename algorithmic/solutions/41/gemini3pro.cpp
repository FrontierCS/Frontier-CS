#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Manual GCD function to ensure compatibility with older C++ standards
long long my_gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

int main() {
    // Optimize I/O operations for speed
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long n;
    if (!(std::cin >> n)) return 0;

    // Base case for n=1
    if (n == 1) {
        std::cout << "1\n1\n";
        return 0;
    }

    // g stores the sequence of GCDs
    // g[0] corresponds to g_1 (the gcd between a_2 and a_1)
    std::vector<long long> g;
    g.reserve(2000000);
    g.push_back(1); // g_1 = 1
    g.push_back(2); // g_2 = 2

    // a stores the Brilliant Sequence of Umbrellas
    std::vector<long long> a;
    a.reserve(2000000);
    a.push_back(1); // a_1 = 1
    a.push_back(2); // a_2 = g_1 * g_2 = 1 * 2 = 2

    // Generate the sequence greedily
    // We want a dense sequence of g_i such that gcd(g_i, g_{i-1}) = 1 and gcd(g_i, g_{i-2}) = 1
    // This allows a_i = g_{i-1} * g_i with gcd(a_i, a_{i-1}) = g_{i-1}
    long long next_g = 3;
    while (true) {
        long long last = g.back();
        long long second_last = g[g.size() - 2];
        
        // Find next valid g_i
        while (my_gcd(next_g, last) != 1 || my_gcd(next_g, second_last) != 1) {
            next_g++;
        }
        
        // Calculate next a_i candidate
        // a_k = g_{k-1} * g_k (using 1-based indexing for g)
        // In 0-based vector: new a corresponds to g.back() * next_g
        long long next_a = last * next_g;
        
        if (next_a > n) {
            break;
        }
        
        g.push_back(next_g);
        a.push_back(next_a);
        next_g++;
    }

    // Optimization: Try to increase the last element a_k to maximize the sum.
    // a_k must be a multiple of g_{k-1}.
    // If a.size() >= 3, we have constraints from g_{k-2}.
    // gcd(a_k, a_{k-1}) must equal g_{k-1}.
    // Since a_{k-1} = g_{k-1} * g_{k-2}, we need gcd(a_k, g_{k-1} * g_{k-2}) = g_{k-1}.
    // Let a_k = V * g_{k-1}. Then gcd(V * g_{k-1}, g_{k-1} * g_{k-2}) = g_{k-1} * gcd(V, g_{k-2}).
    // Thus we need gcd(V, g_{k-2}) = 1.
    
    if (a.size() >= 3) {
        long long prev_g = g[g.size()-2]; // g_{k-1}
        long long prev_prev_g = g[g.size()-3]; // g_{k-2}
        long long current_val = g.back(); // g_k used currently
        
        long long max_v = n / prev_g;
        
        // Search downwards from the largest possible multiple
        for (long long v = max_v; v > current_val; --v) {
            if (my_gcd(v, prev_prev_g) == 1) {
                a.back() = prev_g * v;
                break;
            }
        }
    } else if (a.size() == 2) {
        // Only a_1, a_2. a_1 = 1, a_2 = 2.
        // We can increase a_2 up to n.
        // a_2 must be > a_1 (1 < n is true for n >= 2).
        a.back() = n;
    } else {
        // Case k=1, a_1 = 1.
        a[0] = n;
    }

    // Output results
    std::cout << a.size() << "\n";
    for (size_t i = 0; i < a.size(); ++i) {
        std::cout << a[i] << (i == a.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}