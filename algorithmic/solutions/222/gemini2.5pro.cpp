#include <iostream>
#include <vector>
#include <numeric>
#include <chrono>
#include <random>
#include <map>
#include <algorithm>
#include <cmath>
#include <string>

using namespace std;

// Function to handle queries to the interactor
long long ask(long long v, unsigned __int128 x) {
    cout << "? " << v << " ";
    string s = "";
    if (x == 0) s = "0";
    else {
        unsigned __int128 temp = x;
        while(temp > 0) {
            s += (temp % 10) + '0';
            temp /= 10;
        }
        reverse(s.begin(), s.end());
    }
    cout << s << endl;

    long long result;
    cin >> result;
    if (result == -1) exit(0);
    return result;
}

// Function to submit the final answer
void answer(long long s) {
    cout << "! " << s << endl;
    int result;
    cin >> result;
    if (result == -1) {
        exit(0);
    }
}

// Utility functions for 128-bit integers
unsigned __int128 gcd_u128(unsigned __int128 a, unsigned __int128 b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

unsigned __int128 abs_diff(unsigned __int128 a, unsigned __int128 b) {
    return (a > b) ? a - b : b - a;
}

// Global random number generator
mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

// Modular exponentiation for 128-bit integers
unsigned __int128 power(unsigned __int128 base, unsigned __int128 exp, unsigned __int128 mod) {
    unsigned __int128 res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (unsigned __int128)res * base % mod;
        base = (unsigned __int128)base * base % mod;
        exp /= 2;
    }
    return res;
}

// Miller-Rabin primality test
bool miller_rabin(unsigned __int128 n, unsigned __int128 d) {
    uniform_int_distribution<unsigned __int128> dist(2, n - 2);
    unsigned __int128 a = dist(rng);
    unsigned __int128 x = power(a, d, n);
    if (x == 1 || x == n - 1) return true;
    while (d != n - 1) {
        x = (unsigned __int128)x * x % n;
        d *= 2;
        if (x == 1) return false;
        if (x == n - 1) return true;
    }
    return false;
}

bool is_prime(unsigned __int128 n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    unsigned __int128 d = n - 1;
    while (d % 2 == 0) d /= 2;
    for (int i = 0; i < 5; i++) {
        if (!miller_rabin(n, d)) return false;
    }
    return true;
}

// Pollard's rho algorithm for integer factorization
unsigned __int128 pollard_rho(unsigned __int128 n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;

    uniform_int_distribution<unsigned __int128> dist(1, n - 1);
    unsigned __int128 x = dist(rng);
    unsigned __int128 y = x;
    unsigned __int128 c = dist(rng);
    unsigned __int128 d = 1;

    while (d == 1) {
        x = (power(x, 2, n) + c + n) % n;
        y = (power(y, 2, n) + c + n) % n;
        y = (power(y, 2, n) + c + n) % n;
        d = gcd_u128(abs_diff(x, y), n);
        if (d == n) return pollard_rho(n);
    }
    return d;
}

void factorize(unsigned __int128 n, map<unsigned __int128, int>& factors) {
    if (n <= 1) return;
    if (n < 1000000) { 
        long long num = (long long)n;
        for(long long i = 2; i * i <= num; ++i) {
            while(num % i == 0) {
                factors[i]++;
                num /= i;
            }
        }
        if (num > 1) factors[num]++;
        return;
    }

    if (is_prime(n)) {
        factors[n]++;
        return;
    }
    unsigned __int128 d = pollard_rho(n);
    factorize(d, factors);
    factorize(n / d, factors);
}

// Recursive function to generate all divisors
void get_divs_recursive(const vector<pair<unsigned __int128, int>>& pf, int idx, unsigned __int128 current_d, vector<long long>& divs) {
    if (idx == pf.size()) {
        if (current_d <= 1000000) {
            divs.push_back((long long)current_d);
        }
        return;
    }
    
    unsigned __int128 p = pf[idx].first;
    int count = pf[idx].second;
    unsigned __int128 term = 1;
    for (int i = 0; i <= count; ++i) {
        if ( (unsigned __int128)2000000 / term < current_d) break;
        get_divs_recursive(pf, idx + 1, current_d * term, divs);
        if (i < count) term *= p;
    }
}

void solve() {
    uniform_int_distribution<long long> v_dist(1, 1000000);
    uniform_int_distribution<unsigned __int128> x_dist(1, 5000000000000000000ULL);
    
    long long c = ask(v_dist(rng), 1000001);

    map<long long, vector<unsigned __int128>> history;
    unsigned __int128 g = 0;
    unsigned __int128 current_S = 0;
    history[c].push_back(0);
    
    int query_count = 0;
    int query_limit_phase1 = 480;
    for (int i = 0; i < query_limit_phase1; ++i) {
        unsigned __int128 x = x_dist(rng);
        current_S += x;
        
        long long p = ask(c, current_S);
        query_count++;
        
        if (history.count(p)) {
            for (unsigned __int128 prev_S : history[p]) {
                unsigned __int128 diff = abs_diff(current_S, prev_S);
                if (g == 0) {
                    g = diff;
                } else {
                    g = gcd_u128(g, diff);
                }
            }
        }
        history[p].push_back(current_S);
    }
    
    if (g == 0) {
        int query_limit_phase2 = 2450 - query_count;
        for (int i = 0; i < query_limit_phase2; ++i) {
            unsigned __int128 x = x_dist(rng);
            current_S += x;
            long long p = ask(c, current_S);
            if (history.count(p)) {
                for (unsigned __int128 prev_S : history[p]) {
                    unsigned __int128 diff = abs_diff(current_S, prev_S);
                    if (g == 0) g = diff;
                    else g = gcd_u128(g, diff);
                }
            }
            history[p].push_back(current_S);
            if(g!=0 && g <= 1000000) break;
        }
    }
    
    if (g == 0) {
      // Fallback for extremely unlucky cases
      for(long long s = 3; s <= 1000000; ++s){
          if(ask(c, s) == c){
              answer(s);
              return;
          }
      }
    }

    map<unsigned __int128, int> prime_factors;
    factorize(g, prime_factors);
    
    vector<pair<unsigned __int128, int>> pf_vec;
    for(auto const& [p, count] : prime_factors) pf_vec.push_back({p,count});

    vector<long long> divisors;
    get_divs_recursive(pf_vec, 0, 1, divisors);
    sort(divisors.begin(), divisors.end());
    divisors.erase(unique(divisors.begin(), divisors.end()), divisors.end());

    for (long long d : divisors) {
        if (d >= 3) {
            if (ask(c, d) == c) {
                answer(d);
                return;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    while (n--) {
        solve();
    }
    return 0;
}