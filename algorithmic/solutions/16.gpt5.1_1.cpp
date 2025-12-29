#include <bits/stdc++.h>
using namespace std;

using ll = long long;

ll n;
int Q_used = 0;
const int Q_LIMIT = 500;

ll dist0(ll u, ll v) {
    ll diff = llabs(u - v);
    return min(diff, n - diff);
}

ll advance_pos(ll v, ll delta) { // 1-based, delta can be negative
    ll r = ((v - 1 + delta) % n + n) % n;
    return r + 1;
}

ll opposite(ll i) {
    ll m = n / 2;
    ll j = i + m;
    if (j > n) j -= n;
    return j;
}

bool is_cycle_neighbor(ll u, ll v) {
    ll diff = llabs(u - v);
    return diff == 1 || diff == n - 1;
}

ll query_dist(ll x, ll y) {
    cout << "? " << x << " " << y << endl;
    cout.flush();
    ll d;
    if (!(cin >> d)) exit(0);
    ++Q_used;
    return d;
}

pair<ll,ll> find_start_pair() {
    ll best_i = -1, best_j = -1;
    ll best_delta = 0;

    int tries = 60;
    for (int t = 0; t < tries && Q_used < Q_LIMIT; ++t) {
        ll i = (1 + ( ( (ll)(t + 1234567) * 1000003LL ) % n ));
        ll j = opposite(i);
        ll d = query_dist(i, j);
        ll d0 = dist0(i, j);
        if (d0 > d) {
            ll delta = d0 - d;
            if (delta > best_delta) {
                best_delta = delta;
                best_i = i;
                best_j = j;
            }
        }
    }
    if (best_delta > 0) return {best_i, best_j};

    // Fallback: systematic small search among first up to 200 vertices
    int K = (int)min(n, 200LL);
    for (int i = 1; i <= K && Q_used < Q_LIMIT; ++i) {
        for (int j = i + 2; j <= K && Q_used < Q_LIMIT; ++j) {
            if (is_cycle_neighbor(i, j)) continue;
            ll d = query_dist(i, j);
            ll d0 = dist0(i, j);
            if (d < d0) {
                return {i, j};
            }
        }
    }

    // As last resort (very unlikely to be needed in proper interactive judge)
    return {1, 3};
}

pair<ll,ll> locate_chord(ll A, ll B, ll D_AB) {
    while (true) {
        if (D_AB == 1) {
            // Since D_AB < dist0(A,B) always when this function is called,
            // A and B cannot be cycle neighbors, hence must be chord endpoints.
            return {A, B};
        }

        ll len0 = dist0(A, B);
        if (len0 <= 1) {
            // Degenerate; shouldn't happen, but just in case
            return {A, B};
        }

        ll cwLen = (B - A + n) % n;
        if (cwLen == 0) cwLen = n;
        ll ccwLen = n - cwLen;

        ll M = -1;
        ll D_AM = -1, D_MB = -1;
        ll len0_AM = -1, len0_MB = -1;

        // First midpoint along clockwise path
        ll M1 = advance_pos(A, cwLen / 2);
        ll x1 = query_dist(A, M1);
        ll y1 = query_dist(M1, B);
        bool ok1 = (x1 + y1 == D_AB);

        if (ok1) {
            M = M1;
            D_AM = x1;
            D_MB = y1;
            len0_AM = dist0(A, M);
            len0_MB = dist0(M, B);
        } else {
            // Second midpoint along counter-clockwise path
            ll M2 = advance_pos(A, -(ccwLen / 2));
            ll x2 = query_dist(A, M2);
            ll y2 = query_dist(M2, B);
            bool ok2 = (x2 + y2 == D_AB);
            if (ok2) {
                M = M2;
                D_AM = x2;
                D_MB = y2;
                len0_AM = dist0(A, M);
                len0_MB = dist0(M, B);
            } else {
                // Fallback: choose the midpoint with smaller x+y as approximate
                ll s1 = x1 + y1;
                ll s2 = x2 + y2;
                if (s1 <= s2) {
                    M = M1;
                    D_AM = x1;
                    D_MB = y1;
                    D_AB = s1;
                } else {
                    M = M2;
                    D_AM = x2;
                    D_MB = y2;
                    D_AB = s2;
                }
                len0_AM = dist0(A, M);
                len0_MB = dist0(M, B);
            }
        }

        // Choose subsegment containing the chord (where distance is shortened)
        if (D_AM < len0_AM) {
            B = M;
            D_AB = D_AM;
        } else if (D_MB < len0_MB) {
            A = M;
            D_AB = D_MB;
        } else {
            // No clear shortening in either half (should not happen theoretically).
            // As a safeguard, shrink by base length halves.
            if (len0_AM <= len0_MB) {
                B = M;
                D_AB = D_AM;
            } else {
                A = M;
                D_AB = D_MB;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        cin >> n;
        Q_used = 0;

        pair<ll,ll> start = find_start_pair();
        ll A = start.first;
        ll B = start.second;
        ll D_AB = query_dist(A, B);
        ll d0_AB = dist0(A, B);
        if (D_AB >= d0_AB) {
            // Our starting pair might not actually benefit from chord (rare fallback).
            // Try once more with another strategy.
            start = find_start_pair();
            A = start.first;
            B = start.second;
            D_AB = query_dist(A, B);
        }

        pair<ll,ll> chord = locate_chord(A, B, D_AB);
        ll u = chord.first;
        ll v = chord.second;

        cout << "! " << u << " " << v << endl;
        cout.flush();

        int r;
        if (!(cin >> r)) return 0;
        if (r == -1) return 0;
    }
    return 0;
}