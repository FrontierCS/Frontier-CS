#include <iostream>
#include <vector>
#include <numeric>

// Function to calculate gcd
long long gcd(long long a, long long b) {
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

    // Handle small n edge cases
    if (n == 1) {
        std::cout << "1\n1\n";
        return 0;
    }
    if (n == 2) {
        std::cout << "2\n1 2\n";
        return 0;
    }

    // x stores the sequence of GCDs (x_2, x_3, ...)
    // a stores the sequence of umbrellas (a_1, a_2, ...)
    // Note: indices in vectors are 0-based.
    // x[0] corresponds to x_2, x[1] to x_3, etc.
    std::vector<long long> x;
    std::vector<long long> a;

    // We start with a base sequence.
    // x_2 = 1, x_3 = 2 implies a_1 = 1, a_2 = lcm(1, 2) = 2.
    // This is a valid start for strictly increasing x and a.
    x.push_back(1);
    x.push_back(2);
    a.push_back(1);
    a.push_back(2);

    // Try to extend the sequence greedily
    long long next_x = 3;

    while (true) {
        // We want to append a new GCD value w = next_x
        // The last two GCDs were u = x_{k-1} and v = x_k
        // We are forming a_k = lcm(v, w).
        // The condition gcd(a_k, a_{k-1}) = x_k = v requires:
        // gcd( w/gcd(v,w), u/gcd(u,v) ) == 1
        
        long long u = x[x.size() - 2];
        long long v = x.back();
        long long w = next_x;

        // Optimization: if w is very large, lcm(v, w) will likely exceed n.
        // lcm(v, w) >= w. So if w > n, we can stop.
        if (w > n) break;

        long long g_uv = gcd(u, v);
        long long g_vw = gcd(v, w);

        long long part_u = u / g_uv;
        long long part_w = w / g_vw;

        // Check the coprime condition imposed by strict GCD increasing property
        if (gcd(part_u, part_w) == 1) {
            // Calculate potential next umbrella value
            // Use 128-bit integer for intermediate calculation to avoid overflow, 
            // though with w, v ~ 10^6 and n ~ 10^12 it fits in long long usually,
            // but w*v can exceed 2^63-1 if not careful (though we break before that).
            // Safe way: v / g_vw * w
            unsigned __int128 temp = (unsigned __int128)(v / g_vw) * w;
            
            if (temp > n) {
                // If the smallest valid next umbrella exceeds n, we stop.
                // Since w is increasing, further candidates will also likely exceed n.
                break;
            }

            long long next_a_val = (long long)temp;

            // Ensure strictly increasing umbrella sizes
            if (next_a_val > a.back()) {
                x.push_back(w);
                a.push_back(next_a_val);
                // Increment next_x and continue to next iteration
                next_x++;
                continue;
            }
        }
        
        // Try next integer for w
        next_x++;
    }

    // Scale the sequence to maximize the sum
    // Multiply all elements by M = floor(n / max_element)
    long long k = a.size();
    long long M = n / a.back();

    std::cout << k << "\n";
    for (int i = 0; i < k; ++i) {
        std::cout << a[i] * M << (i == k - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}