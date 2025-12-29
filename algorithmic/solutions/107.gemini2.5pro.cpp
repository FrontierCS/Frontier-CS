#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

long long query(long long q) {
    std::cout << "0 " << q << std::endl;
    long long response;
    std::cin >> response;
    return response;
}

void answer(long long ans) {
    std::cout << "1 " << ans << std::endl;
}

void solve() {
    std::vector<int> primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53};
    long long d = 1;

    for (int p : primes) {
        long long q = p;
        __int128 p_power = p;
        while (p_power * p <= 1000000000) {
            p_power *= p;
        }
        q = (long long)p_power;

        long long g = query(q);
        
        int count = 0;
        if (g > 0) {
            while (g % p == 0) {
                count++;
                g /= p;
            }
        }
        d *= (count + 1);
    }
    
    if (d > 1) {
        answer(d * 2);
    } else {
        answer(4);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}