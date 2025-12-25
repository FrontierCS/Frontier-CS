#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

int query(ll x, ll y, ll n) {
    if (x == y) return 0;
    cout << "? " << x << " " << y << endl;
    cout.flush();
    int d;
    cin >> d;
    return d;
}

ll get_cw(ll start, ll d, ll nn) {
    return ((start - 1 + d) % nn + nn) % nn + 1;
}

ll get_ccw(ll start, ll d, ll nn) {
    return ((start - 1 - d + nn) % nn + nn) % nn + 1;
}

ll cycle_dist(ll u, ll v, ll n) {
    ll dif = abs(u - v);
    return min(dif, n - dif);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        ll n;
        cin >> n;
        ll K = n / 2;
        ll L = n - K;
        ll r = 1;
        ll s = -1;
        ll m = -1;
        int shifts = 0;
        while (s == K && shifts < 10) {
            m = get_cw(r, K, n);
            s = query(r, m, n);
            if (s == K) {
                r = get_cw(r, 1, n);
                ++shifts;
            }
        }
        // Now s < K or shifts max, but assume found
        bool found = false;
        ll u, v;
        // Sum search on short arc (cw from r to m, length K)
        {
            auto cond = [&](int i) -> bool {
                if (i == 0 || i == K) return true;
                ll pp = get_cw(r, i, n);
                int d1 = query(r, pp, n);
                int d2 = query(pp, m, n);
                return d1 + d2 == s;
            };
            int lo = 0, hi = K - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                if (cond(mid)) lo = mid;
                else hi = mid - 1;
            }
            int maxi = (cond(lo) ? lo : -1);
            if (maxi >= 1) {
                ll pp = get_cw(r, maxi, n);
                int drp = query(r, pp, n);
                ll dd = s - drp - 1;
                if (dd >= 0 && dd < L) {
                    ll qq = get_cw(m, dd, n);
                    int dc = query(pp, qq, n);
                    ll cyc = cycle_dist(pp, qq, n);
                    if (dc == 1 && cyc >= 2) {
                        u = min(pp, qq);
                        v = max(pp, qq);
                        found = true;
                    }
                }
            }
        }
        if (!found) {
            // Sum search on long arc (ccw from r to m, length L)
            {
                auto cond = [&](int j) -> bool {
                    if (j == 0 || j == L) return true;
                    ll qq = get_ccw(r, j, n);
                    int d1 = query(r, qq, n);
                    int d2 = query(qq, m, n);
                    return d1 + d2 == s;
                };
                int lo = 0, hi = L - 1;
                while (lo < hi) {
                    int mid = (lo + hi + 1) / 2;
                    if (cond(mid)) lo = mid;
                    else hi = mid - 1;
                }
                int maxj = (cond(lo) ? lo : -1);
                if (maxj >= 1) {
                    ll qq = get_ccw(r, maxj, n);
                    int drq = query(r, qq, n);
                    ll dd = s - drq - 1;
                    if (dd >= 0 && dd < K) {
                        ll pp = get_ccw(m, dd, n);
                        int dc = query(pp, qq, n);
                        ll cyc = cycle_dist(pp, qq, n);
                        if (dc == 1 && cyc >= 2) {
                            u = min(pp, qq);
                            v = max(pp, qq);
                            found = true;
                        }
                    }
                }
            }
        }
        if (!found) {
            // Check if on short
            ll near_m_short = get_cw(r, K - 1, n);
            int ds_near = query(r, near_m_short, n);
            int exp_s_near = K - 1;
            if (ds_near < exp_s_near) {
                // Drop search on short cw
                int low = 1, hi = K;
                while (low < hi) {
                    int mid = (low + hi) / 2;
                    ll xx = get_cw(r, mid, n);
                    int dx = query(r, xx, n);
                    if (dx < mid) {
                        hi = mid;
                    } else {
                        low = mid + 1;
                    }
                }
                ll bpos = get_cw(r, low, n);
                int db = query(r, bpos, n);
                int expb = low;
                if (db < expb) {
                    int da = db - 1;
                    if (da >= 0 && da < low) {
                        ll apos = get_cw(r, da, n);
                        int dc = query(apos, bpos, n);
                        ll cyc = cycle_dist(apos, bpos, n);
                        if (dc == 1 && cyc >= 2) {
                            u = min(apos, bpos);
                            v = max(apos, bpos);
                            found = true;
                        }
                    }
                }
            } else {
                // On long ccw
                int low = 1, hi = L;
                while (low < hi) {
                    int mid = (low + hi) / 2;
                    ll xx = get_ccw(r, mid, n);
                    int dx = query(r, xx, n);
                    if (dx < mid) {
                        hi = mid;
                    } else {
                        low = mid + 1;
                    }
                }
                ll bpos = get_ccw(r, low, n);
                int db = query(r, bpos, n);
                int expb = low;
                if (db < expb) {
                    int da = db - 1;
                    if (da >= 0 && da < low) {
                        ll apos = get_ccw(r, da, n);
                        int dc = query(apos, bpos, n);
                        ll cyc = cycle_dist(apos, bpos, n);
                        if (dc == 1 && cyc >= 2) {
                            u = min(apos, bpos);
                            v = max(apos, bpos);
                            found = true;
                        }
                    }
                }
            }
        }
        // Now output
        cout << "! " << u << " " << v << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == -1) {
            return 0;
        }
    }
}