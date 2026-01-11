#include <bits/stdc++.h>
using namespace std;

using ll = long long;

const ll MAX_X = (ll)1e12;      // upper bound for sampled steps (<= 5e18)
const int SAMPLE_LIMIT = 2450;  // max number of sampling queries per graph
const int QUERY_LIMIT = 2500;   // hard limit from statement

mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

ll ask(int v, ll x) {
    cout << "? " << v << " " << x << endl;
    cout.flush();
    ll res;
    if (!(cin >> res)) {
        exit(0);
    }
    if (res == -1) {
        exit(0);
    }
    return res;
}

void solve_one() {
    int queries = 0;

    // First query: get value at step 1 from vertex 1
    ll arr1 = ask(1, 1);
    ++queries;

    unordered_map<ll, ll> firstPos;
    firstPos.reserve(4096);
    firstPos.max_load_factor(0.7f);
    firstPos[arr1] = 1;

    bool collision = false;
    ll D = 0;

    uniform_int_distribution<ll> dist(2, MAX_X);

    // Sampling phase: look for first collision
    while (queries < SAMPLE_LIMIT && !collision) {
        ll x = dist(rng);
        ll y = ask(1, x);
        ++queries;

        auto it = firstPos.find(y);
        if (it == firstPos.end()) {
            firstPos.emplace(y, x);
        } else {
            ll prev = it->second;
            if (prev != x) {
                ll diff = (x > prev ? x - prev : prev - x);
                if (diff > 0) {
                    D = diff;
                    collision = true;
                }
            }
        }
    }

    ll s_est;
    if (!collision) {
        // Extremely unlikely fallback
        s_est = 3;
    } else {
        // Factor D and strip prime factors that are not needed
        ll Dtmp = D;
        vector<pair<ll,int>> fac;
        for (ll p = 2; p * p <= Dtmp; ++p) {
            if (Dtmp % p == 0) {
                int e = 0;
                while (Dtmp % p == 0) {
                    Dtmp /= p;
                    ++e;
                }
                fac.push_back({p, e});
            }
        }
        if (Dtmp > 1) fac.push_back({Dtmp, 1});

        ll cur = D;
        for (auto [p, e] : fac) {
            for (int i = 0; i < e; ++i) {
                if (cur % p != 0) break;
                ll cand = cur / p;
                // Test if s divides cand: arr(1) == arr(1 + cand)
                ll val = ask(1, 1 + cand);
                ++queries;
                if (val == arr1) {
                    cur = cand;
                } else {
                    break;
                }
            }
        }
        s_est = cur;
        if (s_est < 3) s_est = 3;
    }

    cout << "! " << s_est << endl;
    cout.flush();

    int verdict;
    if (!(cin >> verdict)) exit(0);
    if (verdict == -1) exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    for (int i = 0; i < n; ++i) {
        solve_one();
    }
    return 0;
}