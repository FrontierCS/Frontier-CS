#include <iostream>
#include <vector>
#include <numeric>
#include <map>
#include <algorithm>
#include <random>

using namespace std;

typedef long long ll;

// Function to interact with the judge
int query(int v, ll x) {
    cout << "? " << v << " " << x << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    // Strategy:
    // 1. Check if the cycle length C is a divisor of a large smooth number (LCM of 1..40).
    //    This handles cases where C is small or "smooth" very efficiently.
    // 2. If not, use a Birthday attack (random sampling) to find a multiple M of C.
    //    We query random positions relative to vertex 1. A collision implies the difference is a multiple of C.
    // 3. Once a multiple M is found, extract all prime factors of M that are <= 10^6.
    //    Since C <= 10^6, C must be formed by these factors.
    // 4. Reduce M to C by attempting to remove prime factors one by one.
    //    We verify if a candidate K is a multiple of C by checking if query(1, 1) == query(1, 1 + K).

    // Calculate LCM of 1..40 safely
    ll LCM = 1;
    for (ll i = 1; i <= 40; ++i) {
        ll g = std::gcd(LCM, i);
        LCM = (LCM / g) * i;
    }
    
    map<ll, int> history;
    // Helper to query with caching
    auto get_query = [&](ll x) {
        if (history.count(x)) return history[x];
        int res = query(1, x);
        history[x] = res;
        return res;
    };

    int u = get_query(1);
    int v = get_query(1 + LCM);
    
    ll multiple = 0;
    
    if (u == v) {
        multiple = LCM;
    } else {
        mt19937_64 rng(1337);
        // Using a large range for random jumps to ensure uniform distribution mod C
        uniform_int_distribution<ll> dist(1, 4000000000000000000LL);
        
        map<int, ll> seen_results;
        seen_results[u] = 1;
        seen_results[v] = 1 + LCM;
        
        int queries_spent = 2;
        // Limit queries to leave some budget for the reduction phase
        // Max queries allowed is 2500. We reserve ~100 for reduction.
        while (queries_spent < 2400) {
            ll x = dist(rng);
            // Ensure distinct queries
            while (history.count(x)) x = dist(rng);
            
            int res = get_query(x);
            queries_spent++;
            
            if (seen_results.count(res)) {
                ll prev_x = seen_results[res];
                multiple = abs(x - prev_x);
                break;
            }
            seen_results[res] = x;
        }
    }
    
    if (multiple == 0) {
        // If no collision found (highly unlikely), exit gracefully
        cout << "! 3" << endl;
        int verdict; cin >> verdict;
        if (verdict == -1) exit(0);
        return;
    }
    
    // Extract factors of 'multiple' that are <= 10^6
    // Since C <= 10^6, only these factors contribute to C.
    ll curr = 1;
    ll temp_m = multiple;
    vector<ll> primes;
    
    for (ll d = 2; d <= 1000000; ++d) {
        if (temp_m % d == 0) {
            primes.push_back(d);
            while (temp_m % d == 0) {
                curr *= d;
                temp_m /= d;
            }
        }
        if (temp_m == 1) break;
    }
    
    // Reduce 'curr' to the smallest multiple of C by removing factors.
    // A number K is a multiple of C if and only if query(1, 1) == query(1, 1 + K).
    // This is because stepping K times along the cycle returns to the start iff K is a multiple of C.
    // Note: We use 1 + K because we compare positions. query(1, 1) is "start+1". query(1, 1+K) is "start+1+K".
    
    ll ans = curr;
    for (ll p : primes) {
        while (ans % p == 0) {
            ll candidate = ans / p;
            int r1 = get_query(1); // This value is cached
            int r2 = get_query(1 + candidate);
            if (r1 == r2) {
                ans = candidate;
            } else {
                break; // Cannot remove this factor p anymore
            }
        }
    }
    
    cout << "! " << ans << endl;
    int verdict;
    cin >> verdict;
    if (verdict == -1) exit(0);
}

int main() {
    // No ios optimization to be safe with interactive IO
    int n;
    if (cin >> n) {
        while(n--) {
            solve();
        }
    }
    return 0;
}