#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

ll n_global;
int Q_USED;
const int Q_LIMIT = 500;

ll baseDist(ll x, ll y, ll n) {
    ll diff = llabs(x - y);
    return min(diff, n - diff);
}

ll cwDist(ll x, ll y, ll n) {
    if (y >= x) return y - x;
    return n - (x - y);
}

bool adjacent(ll x, ll y, ll n) {
    ll d = llabs(x - y);
    return d == 1 || d == n - 1;
}

ll ask(ll x, ll y) {
    if (Q_USED >= Q_LIMIT) {
        // Should not happen; but just in case, guess and exit
        cout << "! " << 1 << " " << 3 << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        exit(0);
    }
    cout << "? " << x << " " << y << endl;
    cout.flush();
    ++Q_USED;
    ll d;
    if (!(cin >> d)) exit(0);
    if (d == -1) exit(0);
    return d;
}

void give_answer(ll u, ll v) {
    cout << "! " << u << " " << v << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
}

struct GP {
    ll x, y;
    ll d, d0;
};

ll seg_total_len(const vector<pair<ll,ll>>& segs) {
    ll s = 0;
    for (auto &p : segs) {
        s += (p.second - p.first + 1);
    }
    return s;
}

vector<pair<ll,ll>> intersect_sets(const vector<pair<ll,ll>>& A, const vector<pair<ll,ll>>& B) {
    vector<pair<ll,ll>> R;
    for (auto &a : A) {
        for (auto &b : B) {
            ll l = max(a.first, b.first);
            ll r = min(a.second, b.second);
            if (l <= r) R.push_back({l, r});
        }
    }
    if (R.empty()) return R;
    sort(R.begin(), R.end());
    vector<pair<ll,ll>> M;
    M.push_back(R[0]);
    for (size_t i = 1; i < R.size(); ++i) {
        if (R[i].first <= M.back().second + 1) {
            M.back().second = max(M.back().second, R[i].second);
        } else {
            M.push_back(R[i]);
        }
    }
    return M;
}

void apply_constraint(vector<pair<ll,ll>>& segs, ll start_v1, ll s, ll arcLen, ll n) {
    ll st = start_v1 - 1; // 0-based
    ll maxOff = s - arcLen;
    if (maxOff < 0) return;
    ll p = (st + maxOff) % n;
    vector<pair<ll,ll>> C;
    if (st <= p) {
        C.push_back({st, p});
    } else {
        C.push_back({st, n - 1});
        C.push_back({0, p});
    }
    segs = intersect_sets(segs, C);
}

ll rnd_ll(ll l, ll r) {
    uniform_int_distribution<ll> dist(l, r);
    return dist(rng);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        ll n;
        cin >> n;
        n_global = n;
        Q_USED = 0;

        if (n <= 28) {
            bool found = false;
            for (ll i = 1; i <= n && !found; ++i) {
                for (ll j = i + 1; j <= n && !found; ++j) {
                    if (adjacent(i, j, n)) continue;
                    ll d = ask(i, j);
                    if (d == 1) {
                        give_answer(i, j);
                        found = true;
                    }
                }
            }
            if (!found) {
                give_answer(1, 3 <= n ? 3 : 1);
            }
            continue;
        }

        vector<GP> gps;
        const int MAX_SAMPLE = 200;
        while (Q_USED < MAX_SAMPLE && (int)gps.size() < 60 && Q_USED < Q_LIMIT - 20) {
            ll x = rnd_ll(1, n);
            ll delta = rnd_ll(2, n - 2);
            ll y = x + delta;
            if (y > n) y -= n;
            if (adjacent(x, y, n)) continue;
            ll d = ask(x, y);
            if (d == 1) {
                give_answer(x, y);
                goto next_test;
            }
            ll d0 = baseDist(x, y, n);
            if (d < d0) {
                gps.push_back({x, y, d, d0});
            }
        }

        if (gps.empty()) {
            while (Q_USED < Q_LIMIT - 1) {
                ll x = rnd_ll(1, n);
                ll delta = rnd_ll(2, n - 2);
                ll y = x + delta;
                if (y > n) y -= n;
                if (adjacent(x, y, n)) continue;
                ll d = ask(x, y);
                if (d == 1) {
                    give_answer(x, y);
                    goto next_test;
                }
            }
            give_answer(1, 3 <= n ? 3 : 1);
            continue;
        }

        unordered_map<ll,int> freq;
        for (auto &g : gps) {
            ll cw = cwDist(g.x, g.y, n);
            ll a = cw - g.d + 1;
            ll b = (n - cw) - g.d + 1;
            if (2 <= a && a <= n - 2) freq[a]++;
            if (2 <= b && b <= n - 2) freq[b]++;
        }

        if (freq.empty()) {
            while (Q_USED < Q_LIMIT - 1) {
                ll x = rnd_ll(1, n);
                ll delta = rnd_ll(2, n - 2);
                ll y = x + delta;
                if (y > n) y -= n;
                if (adjacent(x, y, n)) continue;
                ll d = ask(x, y);
                if (d == 1) {
                    give_answer(x, y);
                    goto next_test;
                }
            }
            give_answer(1, 3 <= n ? 3 : 1);
            continue;
        }

        ll arcLen = -1;
        int bestF = -1;
        for (auto &kv : freq) {
            if (kv.second > bestF || (kv.second == bestF && kv.first < arcLen)) {
                bestF = kv.second;
                arcLen = kv.first;
            }
        }

        vector<pair<ll,ll>> segs;
        segs.push_back({0, n - 1});

        for (auto &g : gps) {
            ll cw1 = cwDist(g.x, g.y, n);
            ll cw2 = n - cw1;
            ll a1 = cw1 - g.d + 1;
            ll a2 = cw2 - g.d + 1;
            if (a1 == arcLen) {
                apply_constraint(segs, g.x, cw1, arcLen, n);
            }
            if (!segs.empty() && a2 == arcLen) {
                apply_constraint(segs, g.y, cw2, arcLen, n);
            }
            if (segs.empty()) break;
        }

        if (segs.empty()) {
            while (Q_USED < Q_LIMIT - 1) {
                ll x = rnd_ll(1, n);
                ll delta = rnd_ll(2, n - 2);
                ll y = x + delta;
                if (y > n) y -= n;
                if (adjacent(x, y, n)) continue;
                ll d = ask(x, y);
                if (d == 1) {
                    give_answer(x, y);
                    goto next_test;
                }
            }
            give_answer(1, 3 <= n ? 3 : 1);
            continue;
        }

        unordered_set<ll> tried;
        while (Q_USED < Q_LIMIT - 1) {
            ll total = seg_total_len(segs);
            if (total == 0) break;
            ll U0;
            if (total <= 300) {
                bool found = false;
                for (auto &sg : segs) {
                    for (ll p = sg.first; p <= sg.second; ++p) {
                        if ((int)tried.size() >= Q_LIMIT - Q_USED - 1) { found = true; break; }
                        if (tried.count(p)) continue;
                        U0 = p;
                        tried.insert(p);
                        found = true;
                        break;
                    }
                    if (found) break;
                }
                if (!found) break;
            } else {
                ll kpos = rnd_ll(0, total - 1);
                ll acc = 0;
                ll pos = -1;
                for (auto &sg : segs) {
                    ll len = sg.second - sg.first + 1;
                    if (kpos < acc + len) {
                        pos = sg.first + (kpos - acc);
                        break;
                    }
                    acc += len;
                }
                if (pos < 0) pos = segs[0].first;
                U0 = pos;
                if (tried.count(U0)) continue;
                tried.insert(U0);
            }
            ll u = U0 + 1;
            ll v = (U0 + arcLen) % n + 1;
            if (adjacent(u, v, n)) continue;
            ll d = ask(u, v);
            if (d == 1) {
                give_answer(u, v);
                goto next_test;
            }
        }

        {
            ll u = 1;
            ll v = (1 + arcLen - 1) % n + 1;
            if (adjacent(u, v, n)) {
                v = (v % n) + 1;
            }
            give_answer(u, v);
        }

        next_test:;
    }
    return 0;
}