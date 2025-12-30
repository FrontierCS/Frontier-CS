#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// compute gcd for long long
ll mygcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// compute V = k * sum using 128-bit integer
__int128 compute_value(const vector<ll>& seq) {
    ll sum = 0;
    for (ll x : seq) sum += x;
    __int128 res = seq.size();
    res *= sum;
    return res;
}

// sieve for primes up to 1e6
const int MAXP = 1000000;
vector<int> primes;
void sieve() {
    vector<bool> is_prime(MAXP+1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= MAXP; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            if ((ll)i * i <= MAXP) {
                for (int j = i * i; j <= MAXP; j += i)
                    is_prime[j] = false;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    ll n;
    cin >> n;
    
    if (n == 1) {
        cout << "1\n1\n";
        return 0;
    }
    
    // Candidate 1: powers of two
    vector<ll> pow2;
    for (ll x = 1; x <= n; x *= 2) {
        pow2.push_back(x);
    }
    __int128 val1 = compute_value(pow2);
    
    // Candidate 2: prime product sequence
    sieve();
    vector<ll> prime_seq;
    prime_seq.push_back(1);
    if (n >= 2) {
        prime_seq.push_back(2);
        for (size_t i = 1; i < primes.size(); ++i) {
            ll prod = (ll)primes[i-1] * primes[i];
            if (prod <= n) {
                prime_seq.push_back(prod);
            } else {
                break;
            }
        }
    }
    __int128 val2 = compute_value(prime_seq);
    
    // Try to append n to prime_seq if condition holds
    if (prime_seq.back() < n) {
        ll last = prime_seq.back();
        ll prev_gcd = (prime_seq.size() >= 2) ? mygcd(prime_seq[prime_seq.size()-2], last) : 0;
        if (mygcd(last, n) > prev_gcd) {
            vector<ll> prime_seq_ext = prime_seq;
            prime_seq_ext.push_back(n);
            __int128 val2_ext = compute_value(prime_seq_ext);
            if (val2_ext > val2) {
                prime_seq = prime_seq_ext;
                val2 = val2_ext;
            }
        }
    }
    
    // Candidate 3: [1, n]
    vector<ll> simple = {1, n};
    __int128 val3 = compute_value(simple);
    
    // Choose the best
    vector<ll> best;
    __int128 best_val = val1;
    best = pow2;
    if (val2 > best_val) {
        best_val = val2;
        best = prime_seq;
    }
    if (val3 > best_val) {
        best_val = val3;
        best = simple;
    }
    
    // Output
    cout << best.size() << '\n';
    for (size_t i = 0; i < best.size(); ++i) {
        if (i) cout << ' ';
        cout << best[i];
    }
    cout << '\n';
    
    return 0;
}