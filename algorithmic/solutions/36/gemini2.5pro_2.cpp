#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <map>
#include <set>

using namespace std;

using ll = long long;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

map<vector<ll>, ll> query_cache;

ll do_query(const vector<ll>& v) {
    if (v.empty()) {
        return 0;
    }
    vector<ll> sorted_v = v;
    sort(sorted_v.begin(), sorted_v.end());
    if (query_cache.count(sorted_v)) {
        return query_cache[sorted_v];
    }

    cout << "0 " << v.size();
    for (ll x : v) {
        cout << " " << x;
    }
    cout << endl;

    ll collisions;
    cin >> collisions;
    if (collisions == -1) exit(0);
    return query_cache[sorted_v] = collisions;
}

pair<ll, ll> find_any_colliding_pair(const vector<ll>& S);

pair<ll, ll> find_partner(ll p, const vector<ll>& S) {
    if (S.size() == 1) {
        return {p, S[0]};
    }

    vector<ll> S1(S.begin(), S.begin() + S.size() / 2);
    vector<ll> S2(S.begin() + S.size() / 2, S.end());

    vector<ll> q_vec1 = S1;
    q_vec1.push_back(p);

    ll c_s1 = do_query(S1);
    ll c_qs1 = do_query(q_vec1);
    
    if (c_qs1 > c_s1) {
        return find_partner(p, S1);
    } else {
        return find_partner(p, S2);
    }
}

pair<ll, ll> find_cross_pair(const vector<ll>& S1, const vector<ll>& S2) {
    if (S1.size() == 1) {
        return find_partner(S1[0], S2);
    }

    vector<ll> S1a(S1.begin(), S1.begin() + S1.size() / 2);
    vector<ll> S1b(S1.begin() + S1.size() / 2, S1.end());
    
    vector<ll> q_vec = S1a;
    q_vec.insert(q_vec.end(), S2.begin(), S2.end());

    ll c_s1a = do_query(S1a);
    ll c_s2 = do_query(S2);
    ll c_q = do_query(q_vec);

    if (c_q > c_s1a + c_s2) {
        return find_cross_pair(S1a, S2);
    } else {
        return find_cross_pair(S1b, S2);
    }
}

pair<ll, ll> find_any_colliding_pair(const vector<ll>& S) {
    if (S.size() < 2) return {-1, -1};
    
    ll c_s = do_query(S);
    if (c_s == 0) return {-1, -1};
    if (S.size() == 2) return {S[0], S[1]};

    vector<ll> S1(S.begin(), S.begin() + S.size() / 2);
    vector<ll> S2(S.begin() + S.size() / 2, S.end());
    
    auto p1 = find_any_colliding_pair(S1);
    if (p1.first != -1) return p1;

    auto p2 = find_any_colliding_pair(S2);
    if (p2.first != -1) return p2;
    
    return find_cross_pair(S1, S2);
}

ll power(ll base, ll exp, ll mod) {
    ll res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (__int128)res * base % mod;
        base = (__int128)base * base % mod;
        exp /= 2;
    }
    return res;
}

bool miller_rabin(ll n, ll d) {
    ll a = 2 + rng() % (n - 3);
    ll x = power(a, d, n);
    if (x == 1 || x == n - 1) return true;
    while (d != n - 1) {
        x = (__int128)x * x % n;
        d *= 2;
        if (x == 1) return false;
        if (x == n - 1) return true;
    }
    return false;
}

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    ll d = n - 1;
    while (d % 2 == 0) d /= 2;
    for (int i = 0; i < 5; i++) {
        if (!miller_rabin(n, d)) return false;
    }
    return true;
}

ll pollard_rho(ll n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;
    ll x = rng() % (n - 2) + 2;
    ll y = x;
    ll c = rng() % (n - 1) + 1;
    ll d = 1;
    while (d == 1) {
        x = ((__int128)x * x + c) % n;
        y = ((__int128)y * y + c) % n;
        y = ((__int128)y * y + c) % n;
        d = std::gcd(abs(x - y), n);
        if (d == n) return pollard_rho(n);
    }
    return d;
}

void factorize(ll n, map<ll, int>& factors) {
    if (n <= 1) return;
    if (is_prime(n)) {
        factors[n]++;
        return;
    }
    ll d = pollard_rho(n);
    factorize(d, factors);
    factorize(n / d, factors);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int k = 50000;
    vector<ll> R;
    
    pair<ll, ll> p = {-1, -1};
    while(p.first == -1) {
        set<ll> distinct_r;
        while (distinct_r.size() < k) {
            distinct_r.insert(rng());
        }
        R.assign(distinct_r.begin(), distinct_r.end());
        
        p = find_any_colliding_pair(R);
    }

    ll D = abs(p.first - p.second);
    
    map<ll, int> factors;
    factorize(D, factors);

    ll n = 1;
    for (auto const& [p_factor, exponent] : factors) {
        int low = 0, high = exponent;
        int max_e = 0;
        
        while(low <= high) {
            int mid = low + (high-low)/2;
            
            ll M = D;
            bool overflow = false;
            ll temp_p_power = 1;
            for(int i=0; i<mid; ++i){
                 if (__builtin_mul_overflow(temp_p_power, p_factor, &temp_p_power)){
                    overflow = true;
                    break;
                 }
            }
            if(overflow || temp_p_power > D) M = 0;
            else M = D/temp_p_power;

            if (M == 0) { // Should not happen often with D > 0
                high = mid-1; continue;
            }
            
            vector<ll> q_vec = {M, 2 * M};
            if (do_query(q_vec) > 0) { // n divides M
                max_e = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        int b = exponent - max_e;
        for(int i=0; i<b; ++i) n *= p_factor;
    }

    cout << "1 " << n << endl;

    return 0;
}