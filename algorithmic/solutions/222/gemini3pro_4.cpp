#include <iostream>
#include <vector>
#include <map>
#include <numeric>
#include <random>
#include <chrono>
#include <cmath>
#include <algorithm>
#include <set>
#include <cstdlib>
#include <ctime>

using namespace std;

typedef long long ll;

int query_count = 0;
const int MAX_QUERIES = 2500;

// Function to perform query
// Returns the vertex index
int ask(int v, ll x) {
    if (query_count >= MAX_QUERIES) {
        return -1;
    }
    cout << "? " << v << " " << x << endl;
    query_count++;
    int res;
    cin >> res;
    return res;
}

// Modular multiplication to avoid overflow using __int128
ll mul_mod(ll a, ll b, ll m) {
    return (__int128)a * b % m;
}

// Modular exponentiation
ll power(ll base, ll exp, ll mod) {
    ll res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = mul_mod(res, base, mod);
        base = mul_mod(base, base, mod);
        exp /= 2;
    }
    return res;
}

// Miller-Rabin primality test
bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;
    
    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) {
        d /= 2;
        s++;
    }
    
    static const vector<ll> bases = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (ll a : bases) {
        if (n <= a) break;
        ll x = power(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; r++) {
            x = mul_mod(x, x, n);
            if (x == n - 1) {
                composite = false;
                break;
            }
        }
        if (composite) return false;
    }
    return true;
}

// GCD function
ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Pollard's Rho for integer factorization
ll pollard_rho(ll n) {
    if (n == 1) return 1;
    if (n % 2 == 0) return 2;
    ll x = 2, y = 2, d = 1, c = 1;
    auto f = [&](ll x) { return (mul_mod(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = gcd(abs(x - y), n);
        if (d == n) { // failure, retry with different params
             x = rand() % (n - 2) + 2;
             y = x;
             c = rand() % (n - 1) + 1;
             d = 1;
        }
    }
    return d;
}

// Get all prime factors of n
void get_factors(ll n, vector<ll>& factors) {
    if (n == 1) return;
    if (is_prime(n)) {
        factors.push_back(n);
        return;
    }
    ll d = pollard_rho(n);
    get_factors(d, factors);
    get_factors(n / d, factors);
}

void solve() {
    query_count = 0;
    
    // Step 1: Get a vertex on the cycle
    // We are guaranteed that after 1 step we are on the cycle.
    int u = ask(1, 1);
    if (u == -1) return;

    // Step 2: Random sampling to find a collision
    map<int, ll> history;
    history[u] = 0;
    
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    // We use a large range for random steps. 
    // The probability of collision on a cycle of length L after K queries is roughly 1 - exp(-K^2 / 2L).
    // For L=10^6 and K=2300, K^2/2L approx 2.6, so collision is very likely.
    uniform_int_distribution<ll> dist(1, 4000000000000000000LL); 
    
    ll cycle_multiple = 0;
    
    // We try until we find a collision or come close to query limit.
    // We leave some budget for the reduction step.
    while (query_count < 2350) {
        ll x = dist(rng);
        int v = ask(u, x);
        
        if (history.count(v)) {
            ll prev_x = history[v];
            ll diff = abs(x - prev_x);
            if (diff != 0) {
                cycle_multiple = diff;
                break;
            }
        } else {
            history[v] = x;
        }
    }
    
    if (cycle_multiple == 0) {
        // If we fail to find a collision (extremely unlikely), we can't solve it.
        // Output a dummy value.
        cout << "! " << 3 << endl;
        int verdict; cin >> verdict;
        if (verdict == -1) exit(0);
        return;
    }
    
    // Step 3: Reduce cycle_multiple to the true cycle length L
    // We find prime factors of M and try to divide M by them.
    vector<ll> factors;
    get_factors(cycle_multiple, factors);
    sort(factors.begin(), factors.end());
    
    ll current_L = cycle_multiple;
    
    for (ll p : factors) {
        if (current_L % p == 0) {
            ll temp = current_L / p;
            // Check if temp is a multiple of L:
            // ask(u, temp) should land on u if L divides temp.
            if (query_count >= MAX_QUERIES) break;
            
            int res = ask(u, temp);
            if (res == u) {
                current_L = temp;
            }
        }
    }
    
    cout << "! " << current_L << endl;
    int verdict;
    cin >> verdict;
    if (verdict == -1) exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));
    
    int n;
    if (cin >> n) {
        while (n--) {
            solve();
        }
    }
    return 0;
}