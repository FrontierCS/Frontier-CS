#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static const int MAX_ITERS_TERNARY = 60; // sufficient for n up to 1e9
static const int FINAL_CHECK_WINDOW = 8;

ll N;

ll cycDist(ll u, ll v) {
    ll d = llabs(u - v);
    if (N - d < d) d = N - d;
    return d;
}

ll ask(ll x, ll y) {
    cout << "? " << x << " " << y << endl;
    cout.flush();
    ll ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

struct ArgmaxResult {
    ll index;
    ll value;
};

ArgmaxResult findArgmax(ll base) {
    unordered_map<ll, ll> memo;
    memo.reserve(1 << 12);
    memo.max_load_factor(0.7f);

    auto getVal = [&](ll i)->ll {
        if (i == base) return 0;
        auto it = memo.find(i);
        if (it != memo.end()) return it->second;
        ll cd = cycDist(base, i);
        ll d = ask(base, i);
        ll val = cd - d;
        memo[i] = val;
        return val;
    };

    ll l = 1, r = N;
    int iters = 0;
    while (r - l > FINAL_CHECK_WINDOW && iters < MAX_ITERS_TERNARY) {
        ll m1 = l + (r - l) / 3;
        ll m2 = r - (r - l) / 3;
        ll v1 = getVal(m1);
        ll v2 = getVal(m2);
        if (v1 < v2) {
            l = m1;
        } else if (v1 > v2) {
            r = m2;
        } else {
            // Shrink towards the middle to avoid getting stuck
            l = m1;
            r = m2;
        }
        ++iters;
    }

    ll bestIdx = l, bestVal = getVal(l);
    for (ll i = l + 1; i <= r; ++i) {
        ll val = getVal(i);
        if (val > bestVal) {
            bestVal = val;
            bestIdx = i;
        }
    }
    return {bestIdx, bestVal};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        cin >> N;

        vector<ll> bases;
        bases.push_back(1);
        bases.push_back((N / 3) + 1);
        bases.push_back((2 * (N / 3)) + 1);
        for (ll &b : bases) {
            if (b > N) b -= N;
            if (b < 1) b += N;
        }
        bases.erase(unique(bases.begin(), bases.end()), bases.end());

        ll b = -1, a = -1;

        ArgmaxResult resB = { -1, 0 };
        bool gotB = false;
        for (ll base : bases) {
            resB = findArgmax(base);
            if (resB.value > 0) {
                b = resB.index;
                gotB = true;
                break;
            }
        }

        if (!gotB) {
            // Fallback: try more bases deterministically
            vector<ll> more;
            more.push_back((N / 2) + 1);
            more.push_back((N / 4) + 1);
            more.push_back((3 * (N / 4)) + 1);
            for (ll &bb : more) {
                if (bb > N) bb -= N;
                if (bb < 1) bb += N;
                bool exist = false;
                for (auto v : bases) if (v == bb) exist = true;
                if (!exist) bases.push_back(bb);
            }
            for (size_t i = bases.size(); i < bases.size(); ++i) (void)i; // placeholder

            for (size_t i = 3; i < bases.size(); ++i) {
                ArgmaxResult tmp = findArgmax(bases[i]);
                if (tmp.value > 0) {
                    b = tmp.index;
                    gotB = true;
                    break;
                }
            }
        }

        if (!gotB) {
            // As a last resort, try to detect any benefit directly for some targets and pick the best
            ll bestVal = -1, bestIdx = 1;
            for (int k = 0; k < 12; ++k) {
                ll pos = 1 + (N * (k + 1)) / 13;
                if (pos > N) pos -= N;
                ll cd = cycDist(1, pos);
                ll d = ask(1, pos);
                ll val = cd - d;
                if (val > bestVal) {
                    bestVal = val;
                    bestIdx = pos;
                }
            }
            if (bestVal > 0) {
                b = bestIdx;
                gotB = true;
            }
        }

        if (!gotB) {
            // If still not found, we try to find a pair (s,t) that uses the chord and then deduce endpoints
            // Try a few (s, t = s + N/2) pairs
            vector<ll> starts = {1, (N/3)+1, (2*(N/3))+1, (N/2)+1};
            bool foundPair = false;
            ll s_used = -1, t_used = -1, Dst = -1, kdist = -1;

            auto add_mod = [&](ll x, ll d)->ll {
                ll y = x + d;
                y %= N;
                if (y == 0) y = N;
                return y;
            };

            for (ll s : starts) {
                if (s > N) s -= N;
                ll t = add_mod(s, N/2);
                ll dc = cycDist(s, t);
                ll d = ask(s, t);
                if (d < dc) {
                    foundPair = true;
                    s_used = s; t_used = t; Dst = d; kdist = dc;
                    break;
                }
            }
            if (foundPair) {
                // Binary search for gap (A, B) on arc from s_used to t_used (shorter direction)
                auto onArc = [&](ll s, ll len)->ll {
                    return add_mod(s, len);
                };
                auto sumGreater = [&](ll i)->bool {
                    ll ds = ask(s_used, i);
                    ll dt = ask(i, t_used);
                    return (ds + dt) > Dst;
                };
                // left boundary: first index > s_used such that sumGreater is true
                ll L = 1, R = kdist - 1;
                ll leftFail = -1;
                while (L <= R) {
                    ll mid = (L + R) / 2;
                    ll m = onArc(s_used, mid);
                    bool inside = sumGreater(m);
                    if (inside) {
                        leftFail = mid;
                        R = mid - 1;
                    } else {
                        L = mid + 1;
                    }
                }
                ll A = onArc(s_used, (leftFail == -1 ? 0 : leftFail - 1));

                // right boundary: last index < kdist such that sumGreater is true
                L = 1; R = kdist - 1;
                ll rightFail = -1;
                while (L <= R) {
                    ll mid = (L + R) / 2;
                    ll m = onArc(s_used, mid);
                    bool inside = sumGreater(m);
                    if (inside) {
                        rightFail = mid;
                        L = mid + 1;
                    } else {
                        R = mid - 1;
                    }
                }
                ll B = onArc(s_used, (rightFail == -1 ? kdist : rightFail + 1));
                // Now we have two candidates for endpoints: A and B
                // Verify which pair is the chord (distance 1 but not adjacent in cycle unless that equals chord)
                // However, A and B should be the endpoints in arc order; return them as chord endpoints.
                a = A;
                b = B;
            } else {
                // Fall back to safe guess (shouldn't happen): guess 1 2 and exit on -1
                cout << "! " << 1 << " " << 2 << endl;
                cout.flush();
                int r; if (!(cin >> r)) return 0;
                if (r == -1) return 0;
                continue;
            }
        }

        if (gotB) {
            // Now find 'a' by argmax relative to b
            ArgmaxResult resA = findArgmax(b);
            a = resA.index;
            // If d(a,b) != 1 (rare due to search issues), fallback to pair-finding method
            ll dab = ask(a, b);
            if (dab != 1) {
                // Try swapping to nearest candidates around resA
                bool fixed = false;
                for (ll delta = 1; delta <= 3 && !fixed; ++delta) {
                    ll cand = a + delta; if (cand > N) cand -= N;
                    if (ask(cand, b) == 1) { a = cand; fixed = true; break; }
                    cand = a - delta; if (cand < 1) cand += N;
                    if (ask(cand, b) == 1) { a = cand; fixed = true; break; }
                }
                if (!fixed) {
                    // Use the pair-finding method as final resort:
                    auto add_mod = [&](ll x, ll d)->ll {
                        ll y = x + d;
                        y %= N;
                        if (y == 0) y = N;
                        return y;
                    };
                    vector<ll> starts = {1, (N/3)+1, (2*(N/3))+1, (N/2)+1};
                    bool foundPair = false;
                    ll s_used = -1, t_used = -1, Dst = -1, kdist = -1;

                    for (ll s : starts) {
                        if (s > N) s -= N;
                        ll t = add_mod(s, N/2);
                        ll dc = cycDist(s, t);
                        ll d = ask(s, t);
                        if (d < dc) {
                            foundPair = true;
                            s_used = s; t_used = t; Dst = d; kdist = dc;
                            break;
                        }
                    }
                    if (foundPair) {
                        auto onArc = [&](ll s, ll len)->ll {
                            return add_mod(s, len);
                        };
                        auto sumGreater = [&](ll i)->bool {
                            ll ds = ask(s_used, i);
                            ll dt = ask(i, t_used);
                            return (ds + dt) > Dst;
                        };
                        ll L = 1, R = kdist - 1;
                        ll leftFail = -1;
                        while (L <= R) {
                            ll mid = (L + R) / 2;
                            ll m = onArc(s_used, mid);
                            bool inside = sumGreater(m);
                            if (inside) {
                                leftFail = mid;
                                R = mid - 1;
                            } else {
                                L = mid + 1;
                            }
                        }
                        ll A = onArc(s_used, (leftFail == -1 ? 0 : leftFail - 1));

                        L = 1; R = kdist - 1;
                        ll rightFail = -1;
                        while (L <= R) {
                            ll mid = (L + R) / 2;
                            ll m = onArc(s_used, mid);
                            bool inside = sumGreater(m);
                            if (inside) {
                                rightFail = mid;
                                L = mid + 1;
                            } else {
                                R = mid - 1;
                            }
                        }
                        ll B = onArc(s_used, (rightFail == -1 ? kdist : rightFail + 1));
                        a = A;
                        b = B;
                    }
                }
            }
        }

        cout << "! " << a << " " << b << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) return 0;
        if (r == -1) return 0;
    }
    return 0;
}