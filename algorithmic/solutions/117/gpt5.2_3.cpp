#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ld = long double;

static constexpr ld AFF_EPS = 1e-6L;
static constexpr ld COL_EPS = 1e-8L;
static constexpr ld KINK_EPS = 1e-7L;

static ld ask_point(ld x, ld y) {
    cout.setf(std::ios::fixed); 
    cout << setprecision(20);
    cout << "? " << (double)x << " " << (double)y << "\n";
    cout.flush();
    ld ans;
    if (!(cin >> ans)) exit(0);
    return ans;
}

struct KinkItem {
    ll t;         // breakpoint y = a*x + b at this scan x
    int abs_a;    // |a|
    ld w;         // 1/sqrt(a^2+1)
};

static int abs_a_from_w(ld w) {
    if (w <= 0) return 0;
    ld inv = 1.0L / w;
    ld val = inv * inv - 1.0L;
    if (val < 0) val = 0;
    ld root = sqrt(val);
    ll k0 = llround(root);

    int best = 0;
    ld bestErr = 1e100L;

    auto check = [&](ll k) {
        if (k < 0) k = 0;
        if (k > 10000) k = 10000;
        ld ww = 1.0L / sqrt((ld)k * (ld)k + 1.0L);
        ld err = fabsl(ww - w);
        if (err < bestErr) {
            bestErr = err;
            best = (int)k;
        }
    };

    for (ll dk = -3; dk <= 3; ++dk) check(k0 + dk);

    // Fallback brute force if something is off (still cheap for N<=100)
    if (bestErr > 1e-6L) {
        best = 0;
        bestErr = 1e100L;
        for (int k = 0; k <= 10000; ++k) {
            ld ww = 1.0L / sqrt((ld)k * (ld)k + 1.0L);
            ld err = fabsl(ww - w);
            if (err < bestErr) {
                bestErr = err;
                best = k;
            }
        }
    }
    return best;
}

struct VerticalScan {
    ll x;
    unordered_map<ll, ld> cache;

    explicit VerticalScan(ll x_) : x(x_) {
        cache.reserve(1 << 14);
    }

    ld get(ll y) {
        auto it = cache.find(y);
        if (it != cache.end()) return it->second;
        ld v = ask_point((ld)x, (ld)y);
        cache.emplace(y, v);
        return v;
    }

    bool is_affine(ll L, ll M, ll R) {
        ld fL = get(L), fM = get(M), fR = get(R);
        ld t = (ld)(M - L) / (ld)(R - L);
        ld expected = fL + (fR - fL) * t;
        return fabsl(fM - expected) <= AFF_EPS;
    }

    void sample(ll L, ll R) {
        get(L); get(R);
        if (R - L <= 1) return;
        ll M = L + (R - L) / 2;
        get(M);
        if (is_affine(L, M, R)) return;
        sample(L, M);
        sample(M, R);
    }

    vector<pair<ll, ld>> reduced_points(vector<pair<ll, ld>> pts) {
        sort(pts.begin(), pts.end(), [](auto &a, auto &b){ return a.first < b.first; });
        vector<pair<ll, ld>> st;
        st.reserve(pts.size());
        for (auto &p : pts) {
            if (!st.empty() && st.back().first == p.first) continue;
            st.push_back(p);
            while (st.size() >= 3) {
                auto [x0, y0] = st[st.size() - 3];
                auto [x1, y1] = st[st.size() - 2];
                auto [x2, y2] = st[st.size() - 1];
                ld lhs = (y1 - y0) * (ld)(x2 - x1);
                ld rhs = (y2 - y1) * (ld)(x1 - x0);
                if (fabsl(lhs - rhs) <= COL_EPS * (1.0L + fabsl(lhs) + fabsl(rhs))) {
                    st.erase(st.end() - 2);
                } else break;
            }
        }
        return st;
    }

    vector<KinkItem> extract_kinks(int n) {
        ll ax = llabs(x);
        ll max_t = 10000LL * ax + 10000LL;
        ll L = -max_t - 50;
        ll R =  max_t + 50;

        sample(L, R);

        vector<pair<ll, ld>> pts;
        pts.reserve(cache.size());
        for (auto &kv : cache) pts.push_back({kv.first, kv.second});
        pts = reduced_points(std::move(pts));

        if (pts.size() < 2) return {};

        int m = (int)pts.size();
        vector<ld> segSlope;
        segSlope.reserve(max(0, m - 1));
        for (int i = 0; i + 1 < m; ++i) {
            ll dx = pts[i + 1].first - pts[i].first;
            ld dy = pts[i + 1].second - pts[i].second;
            segSlope.push_back(dy / (ld)dx);
        }

        vector<KinkItem> items;
        items.reserve(n);
        for (int i = 1; i + 1 < m; ++i) {
            ld delta = segSlope[i] - segSlope[i - 1]; // should be 2w at kink
            if (delta > KINK_EPS) {
                ld w = delta / 2.0L;
                int abs_a = abs_a_from_w(w);
                items.push_back({pts[i].first, abs_a, w});
            }
        }

        // If numerical issues cause missing, try with smaller threshold
        if ((int)items.size() != n) {
            items.clear();
            for (int i = 1; i + 1 < m; ++i) {
                ld delta = segSlope[i] - segSlope[i - 1];
                if (delta > 1e-9L) {
                    ld w = delta / 2.0L;
                    int abs_a = abs_a_from_w(w);
                    items.push_back({pts[i].first, abs_a, w});
                }
            }
        }

        return items;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    const ll X1 = 20001;
    const ll X2 = 20002;

    VerticalScan scan1(X1), scan2(X2);

    auto k1 = scan1.extract_kinks(n);
    auto k2 = scan2.extract_kinks(n);

    // Group t2 by abs_a
    unordered_map<int, vector<ll>> t2_by_abs;
    t2_by_abs.reserve(512);
    for (auto &it : k2) t2_by_abs[it.abs_a].push_back(it.t);

    vector<int> a(n), b(n);
    int idx = 0;

    for (auto &it : k1) {
        int k = it.abs_a;
        auto &v = t2_by_abs[k];

        ll cand1 = it.t + (ll)k;
        ll cand2 = it.t - (ll)k;

        int pos = -1;
        for (int i = 0; i < (int)v.size(); ++i) {
            if (v[i] == cand1 || v[i] == cand2) { pos = i; break; }
        }
        if (pos == -1) {
            // Fallback: if something is slightly off, search any within [-10000,10000] and consistent abs
            for (int i = 0; i < (int)v.size(); ++i) {
                ll diff = v[i] - it.t;
                if (llabs(diff) == k && llabs(diff) <= 10000) { pos = i; break; }
            }
        }
        if (pos == -1) {
            // As last resort, brute over all remaining abs groups
            bool found = false;
            for (auto &kv : t2_by_abs) {
                auto &vv = kv.second;
                for (int i = 0; i < (int)vv.size(); ++i) {
                    ll diff = vv[i] - it.t;
                    if (llabs(diff) <= 10000) {
                        int aa = (int)diff;
                        int absa = abs(aa);
                        if (absa == it.abs_a) {
                            k = absa;
                            v = vv; // not actually used
                            pos = i;
                            found = true;
                            break;
                        }
                    }
                }
                if (found) break;
            }
            if (!found) pos = -1;
        }

        if (pos == -1) {
            // Cannot proceed; output dummy to terminate.
            cout << "! ";
            for (int i = 0; i < n; ++i) cout << 0 << (i + 1 == n ? ' ' : ' ');
            for (int i = 0; i < n; ++i) cout << 0 << (i + 1 == n ? '\n' : ' ');
            cout.flush();
            return 0;
        }

        ll t2 = v[pos];
        v[pos] = v.back();
        v.pop_back();

        ll aa = t2 - it.t;
        ll bb = it.t - aa * X1;

        a[idx] = (int)aa;
        b[idx] = (int)bb;
        idx++;
    }

    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << a[i] << (i + 1 == n ? ' ' : ' ');
    }
    for (int i = 0; i < n; ++i) {
        cout << b[i] << (i + 1 == n ? '\n' : ' ');
    }
    cout.flush();
    return 0;
}