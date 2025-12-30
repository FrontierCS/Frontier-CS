#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using i128 = __int128_t;

struct Seg {
    ll l, r; // a in [l, r]
    ll f;    // max b for this range (b in [lb, f])
};

i128 get_total(const vector<Seg>& segs, ll lb) {
    i128 tot = 0;
    for (const auto &sg : segs) {
        if (sg.f < lb) continue;
        if (sg.l > sg.r) continue;
        ll w = sg.r - sg.l + 1;
        ll h = sg.f - lb + 1;
        if (w <= 0 || h <= 0) continue;
        tot += (i128)w * h;
    }
    return tot;
}

void normalize(vector<Seg>& segs, ll lb) {
    vector<Seg> ns;
    ns.reserve(segs.size());
    for (auto sg : segs) {
        if (sg.l > sg.r) continue;
        if (sg.f < lb) continue;
        if (!ns.empty() && ns.back().f == sg.f && ns.back().r + 1 == sg.l) {
            ns.back().r = sg.r;
        } else {
            ns.push_back(sg);
        }
    }
    segs.swap(ns);
}

i128 countA_leq(const vector<Seg>& segs, ll lb, ll X) {
    i128 cnt = 0;
    for (const auto &sg : segs) {
        if (sg.l > X) break;
        ll w;
        if (sg.r <= X) {
            w = sg.r - sg.l + 1;
        } else {
            w = X - sg.l + 1;
            if (w <= 0) break;
        }
        ll h = sg.f - lb + 1;
        if (h <= 0) continue;
        cnt += (i128)w * h;
        if (sg.r > X) break;
    }
    return cnt;
}

i128 countB_leq(const vector<Seg>& segs, ll lb, ll Y) {
    if (Y < lb) return 0;
    i128 cnt = 0;
    for (const auto &sg : segs) {
        if (sg.f < lb) continue;
        ll hi = sg.f < Y ? sg.f : Y;
        if (hi < lb) continue;
        ll h = hi - lb + 1;
        ll w = sg.r - sg.l + 1;
        if (w <= 0 || h <= 0) continue;
        cnt += (i128)w * h;
    }
    return cnt;
}

ll choose_x(const vector<Seg>& segs, ll lb, i128 total) {
    ll L = segs.front().l;
    ll R = segs.back().r;
    while (L < R) {
        ll mid = L + (R - L) / 2;
        i128 cnt = countA_leq(segs, lb, mid);
        if (cnt * 2 >= total) R = mid;
        else L = mid + 1;
    }
    return L;
}

ll choose_y(const vector<Seg>& segs, ll lb, i128 total) {
    ll L = lb;
    ll R = segs.front().f; // maximal f due to non-increasing property
    while (L < R) {
        ll mid = L + (R - L) / 2;
        i128 cnt = countB_leq(segs, lb, mid);
        if (cnt * 2 >= total) R = mid;
        else L = mid + 1;
    }
    return L;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll n;
    if (!(cin >> n)) return 0;

    vector<Seg> segs;
    segs.push_back({1, n, n});
    ll lb = 1;

    const int MAX_Q = 10000;

    for (int q = 0; q < MAX_Q; ++q) {
        normalize(segs, lb);
        i128 total = get_total(segs, lb);
        if (total <= 0) {
            return 0; // should not happen
        }

        if (total == 1) {
            ll a0 = -1, b0 = -1;
            bool found = false;
            for (const auto &sg : segs) {
                ll w = sg.r - sg.l + 1;
                ll h = sg.f - lb + 1;
                if (w > 0 && h > 0) {
                    // total == 1 => w == 1 and h == 1
                    a0 = sg.l;
                    b0 = lb;
                    found = true;
                    break;
                }
            }
            if (!found) return 0;
            cout << a0 << " " << b0 << '\n';
            cout.flush();
            ll r;
            if (!(cin >> r)) return 0;
            return 0;
        }

        ll x = choose_x(segs, lb, total);
        ll y = choose_y(segs, lb, total);

        cout << x << " " << y << '\n';
        cout.flush();

        ll res;
        if (!(cin >> res)) return 0;
        if (res == 0) return 0;

        if (res == 1) {
            // a > x
            vector<Seg> ns;
            ns.reserve(segs.size());
            for (auto sg : segs) {
                if (sg.r <= x) continue;
                if (sg.l > x) {
                    ns.push_back(sg);
                } else {
                    // sg.l <= x < sg.r
                    Seg t{ x + 1, sg.r, sg.f };
                    if (t.l <= t.r) ns.push_back(t);
                }
            }
            segs.swap(ns);
        } else if (res == 2) {
            // b > y
            if (y + 1 > lb) lb = y + 1;
            // segs unchanged; normalize will drop invalid ones
        } else if (res == 3) {
            // x > a OR y > b  => keep (a < x) U (b < y)
            vector<Seg> ns;
            ns.reserve(segs.size() * 2);
            for (auto sg : segs) {
                if (sg.r < x) {
                    // Entire segment has a < x, unchanged
                    ns.push_back(sg);
                } else if (sg.l >= x) {
                    // Entire segment has a >= x, enforce b < y
                    ll nf = sg.f;
                    ll ny = y - 1;
                    if (ny < nf) nf = ny;
                    Seg t{ sg.l, sg.r, nf };
                    if (t.l <= t.r) ns.push_back(t);
                } else {
                    // Split at x
                    // Left part: a in [sg.l, x-1], unchanged
                    Seg left{ sg.l, x - 1, sg.f };
                    if (left.l <= left.r) ns.push_back(left);
                    // Right part: a in [x, sg.r], enforce b < y
                    ll nf = sg.f;
                    ll ny = y - 1;
                    if (ny < nf) nf = ny;
                    Seg right{ x, sg.r, nf };
                    if (right.l <= right.r) ns.push_back(right);
                }
            }
            segs.swap(ns);
        } else {
            return 0; // invalid response
        }
    }

    return 0;
}