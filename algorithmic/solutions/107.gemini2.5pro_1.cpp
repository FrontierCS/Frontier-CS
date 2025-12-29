#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <map>
#include <algorithm>

// Function to make a query
long long ask(long long q) {
    std::cout << "0 " << q << std::endl;
    long long response;
    std::cin >> response;
    return response;
}

// Function to submit an answer
void answer(long long ans) {
    std::cout << "1 " << ans << std::endl;
}

// Power function for __int128 to avoid overflow
__int128_t power_128(long long base, int exp) {
    __int128_t res = 1;
    for (int i = 0; i < exp; ++i) {
        res *= base;
    }
    return res;
}

void solve() {
    static const std::vector<int> primes = {
        2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 
        101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 
        211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 
        307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 
        401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 
        503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 
        601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 
        701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 
        809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 
        907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997
    };
    
    std::map<int, int> exponents;
    
    for (size_t i = 0; i < primes.size(); i += 2) {
        long long p1 = primes[i];
        long long p2 = (i + 1 < primes.size()) ? primes[i+1] : -1;
        
        __int128_t q = 1;
        
        if (p1 != -1) {
            long long max_a1 = floor(log(1e9) / log(p1));
            q *= power_128(p1, max_a1);
        }
        
        if (p2 != -1) {
            long long max_a2 = floor(log(1e9) / log(p2));
            q *= power_128(p2, max_a2);
        }
        
        if (q == 1) continue;

        long long g = ask(static_cast<long long>(q));
        
        if (p1 != -1) {
            int e1 = 0;
            if (g > 0) {
                while (g % p1 == 0) {
                    e1++;
                    g /= p1;
                }
            }
            exponents[p1] = e1;
        }

        if (p2 != -1) {
            int e2 = 0;
            if (g > 0) {
                 while (g % p2 == 0) {
                    e2++;
                    g /= p2;
                }
            }
            exponents[p2] = e2;
        }
    }
    
    long long d_factored = 1;
    for (auto const& [p, e] : exponents) {
        d_factored *= (e + 1);
    }
    
    answer(2 * d_factored);
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