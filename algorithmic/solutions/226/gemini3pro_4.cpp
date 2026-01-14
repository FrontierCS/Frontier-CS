#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    long long n;
    long long x, y;
    if (!(cin >> n >> x >> y)) return 0;
    
    long long g = gcd(x, y);
    long long X = x / g;
    long long Y = y / g;
    long long m = X + Y;
    
    // There are g components in total.
    // n % g components have size n/g + 1
    // g - (n % g) components have size n/g
    long long L1 = n / g;
    long long L2 = L1 + 1;
    long long cnt2 = n % g;
    long long cnt1 = g - cnt2;
    
    long long ans = 0;
    
    if (m % 2 == 0) {
        // Case where X+Y is even: the graph is bipartite.
        // The max independent set of a path of length L is ceil(L/2).
        ans = cnt1 * ((L1 + 1) / 2) + cnt2 * ((L2 + 1) / 2);
    } else {
        // Case where X+Y is odd: the graph contains odd cycles.
        // The structure repeats every m = X+Y.
        // The density of the optimal set is (m-1)/(2m).
        
        // Build the boolean array B representing the optimal pattern on the cycle.
        // The cycle corresponds to indices 0, X, 2X, ... mod m.
        // We pick every second element on this cycle (0, 2, 4, ...).
        vector<int> B(m, 0);
        for (int i = 0; i < m - 1; i += 2) {
            long long res = ((long long)i * X) % m;
            B[res] = 1;
        }
        
        // Helper lambda to find max ones in a window of size r in cyclic B
        auto get_max_rem = [&](long long r) -> long long {
            if (r == 0) return 0;
            // Ensure r is not larger than m (though logic implies r < m)
            if (r >= m) r = m; 
            
            long long cur = 0;
            for (int i = 0; i < r; ++i) cur += B[i];
            long long mx = cur;
            // Slide window
            for (int i = 1; i < m; ++i) {
                cur -= B[i - 1];
                cur += B[(i + r - 1) % m];
                if (cur > mx) mx = cur;
            }
            return mx;
        };
        
        long long K = (m - 1) / 2;
        
        // Calculate answer for length L1
        long long ans1 = (L1 / m) * K + get_max_rem(L1 % m);
        
        // Calculate answer for length L2
        long long ans2 = (L2 / m) * K + get_max_rem(L2 % m);
        
        ans = cnt1 * ans1 + cnt2 * ans2;
    }
    
    cout << ans << endl;
    
    return 0;
}