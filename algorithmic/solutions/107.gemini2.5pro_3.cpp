#include <iostream>
#include <vector>
#include <numeric>

// Pre-generated groups of primes up to 1000,
// where the product of primes in each group is less than 10^18.
const std::vector<std::vector<int>> prime_groups = {
    {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59},
    {61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113},
    {127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181},
    {191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241},
    {251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311},
    {313, 317, 331, 337, 347, 349, 353, 359, 367, 373},
    {379, 383, 389, 397, 401, 409, 419, 421, 431, 433},
    {439, 443, 449, 457, 461, 463, 467, 479, 487, 491},
    {499, 503, 509, 521, 523, 541, 547, 557, 563, 569},
    {571, 577, 587, 593, 599, 601, 607, 613, 617, 619},
    {631, 641, 643, 647, 653, 659, 661, 673, 677, 683},
    {691, 701, 709, 719, 727, 733, 739, 743, 751, 757},
    {761, 769, 773, 787, 797, 809, 811, 821, 823, 827},
    {829, 839, 853, 857, 859, 863, 877, 881, 883, 887},
    {907, 911, 919, 929, 937, 941, 947, 953, 967, 971},
    {977, 983, 991, 997}
};

void solve() {
    long long d_small = 1;

    std::vector<int> found_primes;
    for (const auto& group : prime_groups) {
        unsigned long long q = 1;
        for (int p : group) {
            q *= p;
        }
        std::cout << "0 " << q << std::endl;
        long long res;
        std::cin >> res;
        for (int p : group) {
            if (res % p == 0) {
                found_primes.push_back(p);
            }
        }
    }

    for (int p : found_primes) {
        long long query_val = 1;
        // Calculate smallest p^k > 10^9
        while (query_val <= 1000000000LL / p) {
            query_val *= p;
        }
        query_val *= p;
        
        std::cout << "0 " << query_val << std::endl;
        long long res;
        std::cin >> res;
        
        int count = 0;
        if (res > 0) {
            while (res % p == 0) {
                res /= p;
                count++;
            }
        }
        d_small *= (count + 1);
    }
    
    std::cout << "1 " << d_small * 2 << std::endl;
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