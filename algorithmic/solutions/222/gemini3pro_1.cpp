#include <iostream>
#include <vector>
#include <map>
#include <set>
#include <random>
#include <algorithm>

using namespace std;

// Use __int128 to handle large x values and LCM calculations
typedef unsigned __int128 u128;

// Helper to perform query. x is passed as u128 but fits in unsigned long long for output.
long long query(int v, u128 x) {
    // Problem limit is 5 * 10^18, fits in unsigned long long (up to ~1.8 * 10^19)
    cout << "? " << v << " " << (unsigned long long)x << endl;
    long long res;
    cin >> res;
    if (res == -1) exit(0); // Wrong answer or error
    return res;
}

u128 gcd(u128 a, u128 b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

u128 lcm(u128 a, u128 b) {
    if (a == 0 || b == 0) return 0;
    return (a / gcd(a, b)) * b;
}

void solve() {
    int start_node = 1;
    // Establish a reference point 'u' on the cycle (since dist to cycle is at most 1).
    // f(1, 1) is on the cycle.
    long long u = query(start_node, 1);

    // Strategy 1: Check if cycle length L divides M = lcm(1, ..., 42).
    // lcm(1..42) is approx 2.2 * 10^18.
    u128 M = 1;
    for (int i = 1; i <= 42; ++i) {
        M = lcm(M, (u128)i);
    }
    
    // Check if moving M steps from u returns to u.
    // u corresponds to step 1. So we check step 1 + M.
    long long v = query(start_node, (u128)1 + M);
    
    u128 detected_multiple = 0;
    
    if (v == u) {
        // L divides M.
        detected_multiple = M;
    } else {
        // Strategy 2: Birthday attack / Collision finding.
        // L does not divide M, so L likely has a large prime factor.
        // We use random queries to find a collision.
        // Map stores: vertex_index -> x_coordinate
        map<long long, u128> history;
        history[u] = 1;
        history[v] = (u128)1 + M;
        
        set<u128> visited_x;
        visited_x.insert(1);
        visited_x.insert((u128)1 + M);
        
        mt19937_64 rng(1337);
        // We choose x in a range slightly larger than 10^6 to ensure good coverage modulo L.
        // Keeping it relatively small keeps the difference D small, easy to factor.
        uniform_int_distribution<unsigned long long> dist(1, 2000000);
        
        int queries_left = 2490; 
        
        while (queries_left > 0) {
            u128 x = dist(rng);
            if (visited_x.count(x)) continue;
            visited_x.insert(x);
            
            long long res = query(start_node, x);
            queries_left--;
            
            if (history.count(res)) {
                u128 prev_x = history[res];
                // Collision found: f(1, x) == f(1, prev_x) implies L divides |x - prev_x|
                if (x > prev_x) detected_multiple = x - prev_x;
                else detected_multiple = prev_x - x;
                break;
            }
            history[res] = x;
        }
    }
    
    if (detected_multiple == 0) {
        // Fallback if no collision found (unlikely with 2500 queries for L <= 10^6)
        cout << "! 3" << endl;
        int verdict; cin >> verdict;
        return;
    }
    
    // We have a multiple of L. We need to find L.
    // L is the smallest divisor d of detected_multiple such that f(u, d) == u.
    // Equivalently, we start with D and remove prime factors as long as the property holds.
    u128 current_L = detected_multiple;
    
    if (current_L > 3000000000000000000ULL) { 
        // Case 1: Multiple came from M. Prime factors are <= 42.
        vector<int> primes = {2,3,5,7,11,13,17,19,23,29,31,37,41};
        for (int p : primes) {
            while (current_L % p == 0) {
                u128 next_val = current_L / p;
                // Check if L divides next_val
                long long check = query(start_node, (u128)1 + next_val);
                if (check == u) {
                    current_L = next_val;
                } else {
                    break; 
                }
            }
        }
    } else {
        // Case 2: Multiple came from collision. D <= 2*10^6.
        // Factorize by trial division.
        unsigned long long temp = (unsigned long long)current_L;
        vector<unsigned long long> factors;
        for (unsigned long long i = 2; i * i <= temp; ++i) {
            if (temp % i == 0) {
                factors.push_back(i);
                while (temp % i == 0) temp /= i;
            }
        }
        if (temp > 1) factors.push_back(temp);
        
        for (auto p : factors) {
            while (current_L % p == 0) {
                u128 next_val = current_L / p;
                long long check = query(start_node, (u128)1 + next_val);
                if (check == u) {
                    current_L = next_val;
                } else {
                    break;
                }
            }
        }
    }
    
    cout << "! " << (unsigned long long)current_L << endl;
    int verdict; cin >> verdict;
    if (verdict == -1) exit(0);
}

int main() {
    // Interactive problem, flushing is handled by endl.
    int n;
    if (cin >> n) {
        while (n--) {
            solve();
        }
    }
    return 0;
}