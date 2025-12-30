#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct LLHash {
    size_t operator()(const long long& x) const noexcept {
        static const uint64_t FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        uint64_t z = x + FIXED_RANDOM + 0x9e3779b97f4a7c15ULL;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        z = z ^ (z >> 31);
        return (size_t)z;
    }
};

static int K;
static ll BOUND_B;
static int WMAX;

static int total_probes_used = 0;
static int waves_used = 0;

bool read_ints(vector<ll>& v, int cnt) {
    v.resize(cnt);
    for (int i = 0; i < cnt; ++i) {
        if (!(cin >> v[i])) return false;
    }
    return true;
}

vector<ll> query_point(ll s, ll t) {
    if (waves_used >= WMAX) {
        // Should not happen in correct interaction, but to avoid undefined behavior:
        // Return empty (caller should handle lack of input).
        return {};
    }
    cout << "? 1 " << s << " " << t << endl;
    cout.flush();
    vector<ll> res;
    if (!read_ints(res, K)) {
        // If interaction fails, return empty.
        return {};
    }
    waves_used++;
    total_probes_used += 1;
    return res;
}

ll g_L0(ll u, ll v, ll L) {
    // d(L,0) = L - (u+v)/2 + |(u - v)/2|
    // Only valid for same parity u and v to keep integer math with halves.
    if (((u ^ v) & 1LL) != 0) {
        // Not integer pair for (x,y), but the formula might still be integer; still, we avoid using mismatched parity.
        // Return a sentinel (negative) that will not match any real distance (distances are non-negative).
        return -1e18;
    }
    ll halfSum = (u + v) / 2;
    ll halfDiffAbs = llabs(u - v) / 2;
    return L - halfSum + halfDiffAbs;
}

ll g_0L(ll u, ll v, ll L) {
    // d(0,L) = L - (u - v)/2 + |(u + v)/2|
    if (((u ^ v) & 1LL) != 0) {
        return -1e18;
    }
    ll halfDiff = (u - v) / 2;
    ll halfSumAbs = llabs(u + v) / 2;
    return L - halfDiff + halfSumAbs;
}

struct MatchSolver {
    int k;
    ll b;
    ll L;
    const vector<ll> &U, &V;
    vector<vector<int>> candidates;
    vector<vector<ll>> w1, w2;
    bool use_w1, use_w2;
    unordered_map<ll,int,LLHash> cnt1, cnt2;
    vector<int> order;
    vector<int> matchV; // match for U->V indices
    vector<char> usedV;

    MatchSolver(int kk, ll bb, ll LL, const vector<ll>& UU, const vector<ll>& VV)
        : k(kk), b(bb), L(LL), U(UU), V(VV), use_w1(false), use_w2(false) {
        matchV.assign(k, -1);
        usedV.assign(k, 0);
    }

    void set_counts_w1(const vector<ll>& W1) {
        use_w1 = true;
        cnt1.clear();
        for (ll x : W1) cnt1[x]++;
    }

    void set_counts_w2(const vector<ll>& W2) {
        use_w2 = true;
        cnt2.clear();
        for (ll x : W2) cnt2[x]++;
    }

    bool within_bounds(ll x, ll y) {
        return (x >= -b && x <= b && y >= -b && y <= b);
    }

    void build_candidates() {
        candidates.assign(k, {});
        w1.assign(k, vector<ll>(k, (ll)-4e18));
        w2.assign(k, vector<ll>(k, (ll)-4e18));
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                if (((U[i] ^ V[j]) & 1LL) != 0) continue; // parity mismatch
                ll x = (U[i] + V[j]) / 2;
                ll y = (U[i] - V[j]) / 2;
                if (!within_bounds(x, y)) continue;
                ll val1 = g_L0(U[i], V[j], L);
                ll val2 = g_0L(U[i], V[j], L);
                w1[i][j] = val1;
                w2[i][j] = val2;
                bool ok = true;
                if (use_w1) {
                    if (cnt1.find(val1) == cnt1.end()) ok = false;
                }
                if (use_w2) {
                    if (cnt2.find(val2) == cnt2.end()) ok = false;
                }
                if (ok) candidates[i].push_back(j);
            }
        }
        order.resize(k);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            return candidates[a].size() < candidates[b].size();
        });
        // Also for each candidates list, sort by rarity of w1/w2 values to prune earlier
        for (int idx = 0; idx < k; ++idx) {
            int i = order[idx];
            sort(candidates[i].begin(), candidates[i].end(), [&](int j1, int j2){
                long long score1 = 0, score2 = 0;
                if (use_w1) {
                    auto it1 = cnt1.find(w1[i][j1]);
                    auto it2 = cnt1.find(w1[i][j2]);
                    score1 = (it1 == cnt1.end() ? (ll)1e15 : it1->second);
                    score2 = (it2 == cnt1.end() ? (ll)1e15 : it2->second);
                }
                if (use_w2) {
                    auto it1 = cnt2.find(w2[i][j1]);
                    auto it2 = cnt2.find(w2[i][j2]);
                    long long t1 = (it1 == cnt2.end() ? (ll)1e15 : it1->second);
                    long long t2 = (it2 == cnt2.end() ? (ll)1e15 : it2->second);
                    // combine scores minimizing both
                    score1 += t1;
                    score2 += t2;
                }
                if (!use_w1 && !use_w2) {
                    // no counts; prefer arbitrary stable
                    return j1 < j2;
                }
                if (score1 != score2) return score1 < score2;
                return j1 < j2;
            });
        }
    }

    bool dfs(int pos) {
        if (pos == k) return true;
        int i = order[pos];
        // If no candidates, fail
        if (candidates[i].empty()) return false;
        for (int j : candidates[i]) {
            if (usedV[j]) continue;
            ll v1 = w1[i][j];
            ll v2 = w2[i][j];
            if (use_w1) {
                auto it = cnt1.find(v1);
                if (it == cnt1.end() || it->second <= 0) continue;
            }
            if (use_w2) {
                auto it = cnt2.find(v2);
                if (it == cnt2.end() || it->second <= 0) continue;
            }
            usedV[j] = 1;
            matchV[i] = j;
            bool dec1 = false, dec2 = false;
            if (use_w1) {
                cnt1[v1]--; dec1 = true;
            }
            if (use_w2) {
                cnt2[v2]--; dec2 = true;
            }
            if (dfs(pos + 1)) return true;
            if (dec1) cnt1[v1]++;
            if (dec2) cnt2[v2]++;
            usedV[j] = 0;
            matchV[i] = -1;
        }
        return false;
    }

    bool solve_with_counts() {
        build_candidates();
        return dfs(0);
    }

    // Fallback: find any perfect matching ignoring counts (only parity/bounds)
    bool solve_any_matching() {
        use_w1 = false; use_w2 = false;
        build_candidates();
        return dfs(0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll b;
    int k, w;
    if (!(cin >> b >> k >> w)) {
        return 0;
    }
    BOUND_B = b;
    K = k;
    WMAX = w;

    ll L = b; // Choose L = b to ensure sign-known in corner queries.

    vector<ll> distU, distV, distW1, distW2;

    // Strategy:
    // - If w >= 4: query (L,L), (L,-L), (L,0), (0,L)
    // - If w == 3: query (L,L), (L,-L), (L,0)
    // - If w <= 2: query (L,L), (L,-L)
    if (w >= 4) {
        distU = query_point(L, L);
        distV = query_point(L, -L);
        distW1 = query_point(L, 0);
        distW2 = query_point(0, L);
    } else if (w == 3) {
        distU = query_point(L, L);
        distV = query_point(L, -L);
        distW1 = query_point(L, 0);
    } else {
        distU = query_point(L, L);
        distV = query_point(L, -L);
    }

    // Transform to U = x+y, V = x-y
    vector<ll> Uvals, Vvals;
    Uvals.reserve(k);
    Vvals.reserve(k);
    for (ll d : distU) Uvals.push_back(2 * L - d);
    for (ll d : distV) Vvals.push_back(2 * L - d);

    // Prepare solver
    MatchSolver solver(k, b, L, Uvals, Vvals);

    bool solved = false;
    if (!distW1.empty()) solver.set_counts_w1(distW1);
    if (!distW2.empty()) solver.set_counts_w2(distW2);

    if (!distW1.empty() || !distW2.empty()) {
        solved = solver.solve_with_counts();
    }
    if (!solved) {
        // Fallback to any matching using only parity/bounds
        solved = solver.solve_any_matching();
    }

    vector<pair<ll,ll>> points;
    points.reserve(k);
    if (solved) {
        for (int idx = 0; idx < k; ++idx) {
            int i = idx;
            int j = solver.matchV[i];
            if (j < 0) {
                // Should not happen; fallback random pairing
                j = 0;
            }
            ll x = (Uvals[i] + Vvals[j]) / 2;
            ll y = (Uvals[i] - Vvals[j]) / 2;
            points.emplace_back(x, y);
        }
    } else {
        // As a last resort, pair greedily by parity and bounds
        vector<int> usedV(k, 0);
        for (int i = 0; i < k; ++i) {
            bool ok = false;
            for (int j = 0; j < k; ++j) {
                if (usedV[j]) continue;
                if (((Uvals[i] ^ Vvals[j]) & 1LL) != 0) continue;
                ll x = (Uvals[i] + Vvals[j]) / 2;
                ll y = (Uvals[i] - Vvals[j]) / 2;
                if (x < -b || x > b || y < -b || y > b) continue;
                usedV[j] = 1;
                points.emplace_back(x, y);
                ok = true;
                break;
            }
            if (!ok) {
                // If cannot find, just pair with first unused
                int j = -1;
                for (int t = 0; t < k; ++t) if (!usedV[t]) { j = t; break; }
                if (j == -1) j = 0;
                usedV[j] = 1;
                ll x = (Uvals[i] + Vvals[j]) / 2;
                ll y = (Uvals[i] - Vvals[j]) / 2;
                points.emplace_back(x, y);
            }
        }
    }

    // Output final answer
    cout << "!";
    for (int i = 0; i < (int)points.size(); ++i) {
        cout << " " << points[i].first << " " << points[i].second;
    }
    cout << endl;
    cout.flush();

    return 0;
}