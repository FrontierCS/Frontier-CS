#include <bits/stdc++.h>
using namespace std;
using ll = long long;

const int MAXQ = 500;

ll N;               // current n
int queriesUsed;    // per test case

ll ask(ll x, ll y) {
    cout << "? " << x << " " << y << endl;
    cout.flush();
    ll d;
    if (!(cin >> d)) exit(0);
    if (d == -1) exit(0); // safety
    ++queriesUsed;
    return d;
}

inline ll cycleDist(ll u, ll v) {
    ll diff = llabs(u - v);
    return min(diff, N - diff);
}

inline bool isAdjacent(ll u, ll v) {
    ll diff = llabs(u - v);
    return diff == 1 || diff == N - 1;
}

ll dist_plus(ll u, ll v, int a, int b) {
    if (u == v) return 0;
    ll direct = cycleDist(u, v);
    ll via_ab = cycleDist(u, a) + 1 + cycleDist(b, v);
    ll via_ba = cycleDist(u, b) + 1 + cycleDist(a, v);
    return min(direct, min(via_ab, via_ba));
}

// For large N: find one chord endpoint from "start" side of pair (start, other)
pair<bool, ll> find_endpoint_side(ll start, ll other, ll D) {
    if (D <= 1) return {false, -1};

    ll cw = (start == N ? 1 : start + 1);
    ll ccw = (start == 1 ? N : start - 1);

    bool cwOn = false, ccwOn = false;

    ll d_cw_other = ask(cw, other);
    if (1 + d_cw_other == D) cwOn = true;

    ll d_ccw_other = ask(ccw, other);
    if (1 + d_ccw_other == D) ccwOn = true;

    if (!cwOn && !ccwOn) return {false, -1};

    int sign = cwOn ? +1 : -1;

    auto move = [&](ll k) -> ll {
        if (sign == +1) {
            return ((start - 1 + k) % N) + 1;
        } else {
            ll kk = k % N;
            return ((start - 1 - kk + N) % N) + 1;
        }
    };

    auto Pprefix = [&](ll k) -> bool {
        ll v = move(k);
        ll dxv;
        if (k == 1) dxv = 1;
        else dxv = ask(start, v);

        ll dvy;
        if (v == other) dvy = 0;
        else dvy = ask(v, other);

        return (dxv == k && dxv + dvy == D);
    };

    ll maxK = D - 1; // first segment along cycle before chord
    ll lo = 1;
    // Pprefix(1) is guaranteed true (by construction of direction)
    ll hi = 2;
    while (hi <= maxK) {
        if (!Pprefix(hi)) break;
        lo = hi;
        hi <<= 1;
    }

    ll s;
    if (hi > maxK) {
        // Pprefix(k) is true for all k in [1, maxK]
        s = maxK;
    } else {
        // We know Pprefix(lo) == true, Pprefix(hi) == false
        ll L = lo, R = hi - 1;
        while (L < R) {
            ll mid = (L + R + 1) / 2;
            if (Pprefix(mid)) L = mid;
            else R = mid - 1;
        }
        s = L;
    }

    ll endpoint = move(s);
    return {true, endpoint};
}

// Deterministic solution for small N (N <= 250)
void solve_small() {
    int root1 = 1;
    int root2 = (int)(N / 2) + 1;
    if (root2 == root1) root2 = (root1 % (int)N) + 1;

    vector<ll> d1(N + 1), d2(N + 1);

    for (int i = 1; i <= (int)N; ++i) {
        if (i == root1) d1[i] = 0;
        else d1[i] = ask(root1, i);
    }
    for (int i = 1; i <= (int)N; ++i) {
        if (i == root2) d2[i] = 0;
        else d2[i] = ask(root2, i);
    }

    vector<pair<int,int>> candidates;

    for (int a = 1; a <= (int)N; ++a) {
        for (int b = a + 1; b <= (int)N; ++b) {
            ll diff = b - a;
            if (diff == 1 || diff == N - 1) continue; // adjacent; not chord

            bool ok = true;
            for (int x = 1; x <= (int)N && ok; ++x) {
                ll dp = dist_plus(root1, x, a, b);
                if (dp != d1[x]) ok = false;
            }
            if (!ok) continue;

            for (int x = 1; x <= (int)N && ok; ++x) {
                ll dp = dist_plus(root2, x, a, b);
                if (dp != d2[x]) ok = false;
            }
            if (ok) candidates.push_back({a, b});
        }
    }

    int ca, cb;
    if (candidates.empty()) {
        ca = 1;
        cb = 3 % (int)N + 1;
        if (cb == 2 || cb == N) cb = (cb % (int)N) + 1;
    } else {
        ca = candidates[0].first;
        cb = candidates[0].second;
    }

    // Optional verification (1 extra query, still within limit)
    ask(ca, cb); // should be 1 in correct case

    cout << "! " << ca << " " << cb << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
}

// Randomized + geometric solution for large N
void solve_large(mt19937_64 &rng) {
    const int RESERVED_QUERIES = 260;
    int max_rand_queries = MAXQ - RESERVED_QUERIES; // 240
    if (max_rand_queries < 0) max_rand_queries = 0;

    struct GoodPair {
        ll u, v, d;
    } good;
    bool found = false;

    for (int t = 0; t < max_rand_queries && !found; ++t) {
        ll x = (ll)(rng() % N) + 1;
        ll y = (ll)(rng() % (N - 1)) + 1;
        if (y >= x) ++y;

        ll d = ask(x, y);
        ll cyc = cycleDist(x, y);

        if (d < cyc) {
            if (d == 1 && !isAdjacent(x, y)) {
                // Directly the chord
                cout << "! " << x << " " << y << endl;
                cout.flush();
                int r;
                if (!(cin >> r)) exit(0);
                if (r == -1) exit(0);
                return;
            } else {
                good = {x, y, d};
                found = true;
                break;
            }
        }
    }

    if (!found) {
        // Extremely unlikely fallback: guess something (may be wrong in theory)
        ll a = 1, b = 3;
        if (b > N) b = 2;
        cout << "! " << a << " " << b << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
        return;
    }

    ll u = good.u, v = good.v, D = good.d;

    auto res1 = find_endpoint_side(u, v, D);
    auto res2 = find_endpoint_side(v, u, D);

    ll a = -1, b = -1;

    if (res1.first && res2.first) {
        a = res1.second;
        b = res2.second;
    } else if (res1.first && !res2.first) {
        a = res1.second;
        b = v;
    } else if (!res1.first && res2.first) {
        a = u;
        b = res2.second;
    } else {
        // Very unlikely; fallback to good pair itself
        a = u;
        b = v;
    }

    if (a == b) {
        // Fallback safeguard
        a = 1;
        b = 3;
        if (b > N) b = 2;
    }

    ll dab = ask(a, b); // verification
    if (dab != 1 || isAdjacent(a, b)) {
        // Fallback in degenerate case
        a = 1;
        b = 3;
        if (b > N) b = 2;
    }

    cout << "! " << a << " " << b << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    while (T--) {
        cin >> N;
        queriesUsed = 0;

        if (N <= 250) {
            solve_small();
        } else {
            solve_large(rng);
        }
    }

    return 0;
}