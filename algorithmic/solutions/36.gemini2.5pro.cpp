#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <map>
#include <set>

using namespace std;

typedef long long ll;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

map<vector<ll>, ll> query_cache;

ll do_query(const vector<ll>& q_vec) {
    if (q_vec.empty()) {
        return 0;
    }
    vector<ll> sorted_q = q_vec;
    sort(sorted_q.begin(), sorted_q.end());
    if (query_cache.count(sorted_q)) {
        return query_cache[sorted_q];
    }

    cout << "0 " << q_vec.size();
    for (ll x : q_vec) {
        cout << " " << x;
    }
    cout << endl;

    ll collisions;
    cin >> collisions;
    return query_cache[sorted_q] = collisions;
}

ll get_collisions(const vector<ll>& q_vec) {
    return do_query(q_vec);
}

ll get_internal_collisions(const vector<ll>& q_vec) {
    return get_collisions(q_vec);
}

ll get_cross_collisions(const vector<ll>& v1, const vector<ll>& v2, ll c1, ll c2) {
    if (v1.empty() || v2.empty()) return 0;
    vector<ll> combined = v1;
    combined.insert(combined.end(), v2.begin(), v2.end());
    ll c_combined = get_collisions(combined);
    return c_combined - c1 - c2;
}

// Miller-Rabin primality test
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

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) {
        d /= 2;
        s++;
    }
    ll bases[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (ll a : bases) {
        if (n == a) return true;
        ll x = power(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; ++r) {
            x = (__int128)x * x % n;
            if (x == n - 1) {
                composite = false;
                break;
            }
        }
        if (composite) return false;
    }
    return true;
}

// Pollard's rho algorithm
ll pollard(ll n) {
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
        d = __gcd(abs(x - y), n);
        if (d == n) return pollard(n);
    }
    return d;
}

void factorize(ll n, map<ll, int>& factors) {
    if (n <= 1) return;
    if (is_prime(n)) {
        factors[n]++;
        return;
    }
    ll f = pollard(n);
    factorize(f, factors);
    factorize(n / f, factors);
}

vector<ll> fixed_randoms;
void generate_fixed_randoms() {
    uniform_int_distribution<ll> dist(1e17, 5e17);
    for(int i = 0; i < 100; ++i) {
        fixed_randoms.push_back(dist(rng));
    }
}

bool check_divisor(ll m) {
    if (m == 1) return true;
    vector<ll> q;
    for(ll r : fixed_randoms) {
        q.push_back(m * r);
    }
    return get_collisions(q) == 4950;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    generate_fixed_randoms();

    const int K = 10000;
    vector<ll> A, B;
    ll c_A, c_B;

    uniform_int_distribution<ll> dist(1, 1e18);
    
    while(true) {
        A.clear(); B.clear();
        query_cache.clear();
        set<ll> used_nums;
        for(int i=0; i<K; ++i) {
            ll val;
            do { val = dist(rng); } while(used_nums.count(val));
            A.push_back(val);
            used_nums.insert(val);
        }
        for(int i=0; i<K; ++i) {
            ll val;
            do { val = dist(rng); } while(used_nums.count(val));
            B.push_back(val);
            used_nums.insert(val);
        }

        c_A = get_internal_collisions(A);
        c_B = get_internal_collisions(B);
        if(get_cross_collisions(A, B, c_A, c_B) > 0) {
            break;
        }
    }
    
    map<pair<int, int>, ll> precomputed_A, precomputed_B;

    for (int len = K / 2; len >= 1; len /= 2) {
        for (int i = 0; i < K; i += len) {
            vector<ll> sub_A(A.begin() + i, A.begin() + i + len);
            precomputed_A[{i, len}] = get_internal_collisions(sub_A);
            vector<ll> sub_B(B.begin() + i, B.begin() + i + len);
            precomputed_B[{i, len}] = get_internal_collisions(sub_B);
        }
    }

    int a_idx = 0, a_len = K;
    while(a_len > 1) {
        int mid_len = a_len / 2;
        vector<ll> A1(A.begin() + a_idx, A.begin() + a_idx + mid_len);
        ll c_A1 = precomputed_A[{a_idx, mid_len}];
        if (get_cross_collisions(A1, B, c_A1, c_B) > 0) {
            a_len = mid_len;
        } else {
            a_idx += mid_len;
            a_len -= mid_len;
        }
    }
    ll found_a = A[a_idx];

    int b_idx = 0, b_len = K;
    while(b_len > 1) {
        int mid_len = b_len / 2;
        vector<ll> B1(B.begin() + b_idx, B.begin() + b_idx + mid_len);
        ll c_B1 = precomputed_B[{b_idx, mid_len}];
        vector<ll> q = B1;
        q.push_back(found_a);
        if (get_collisions(q) - c_B1 > 0) {
            b_len = mid_len;
        } else {
            b_idx += mid_len;
            b_len -= mid_len;
        }
    }
    ll found_b = B[b_idx];

    ll D = abs(found_a - found_b);
    
    ll n = 1;

    int v2 = 0;
    int low = 0, high = 60;
    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (mid == 0) {
             low = mid + 1;
             continue;
        }
        if (check_divisor(1LL << mid)) {
            v2 = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    n *= (1LL << v2);
    
    while(D > 0 && D % 2 == 0) D /= 2;

    map<ll, int> prime_factors;
    if(D > 1) factorize(D, prime_factors);

    for(auto const& [p, e] : prime_factors) {
        if (p > 1e9 + 7 && !is_prime(p)) continue;
        int vp = 0;
        low = 0, high = e;
        while(low <= high) {
            int mid = low + (high-low)/2;
            if(mid == 0) {
                low = mid + 1;
                continue;
            }
            ll p_power = 1;
            for(int i=0; i<mid; ++i) p_power *= p;
            if (check_divisor(n * p_power)) {
                vp = mid;
                low = mid + 1;
            } else {
                high = mid-1;
            }
        }
        for(int i=0; i<vp; ++i) n *= p;
    }

    cout << "1 " << n << endl;

    return 0;
}