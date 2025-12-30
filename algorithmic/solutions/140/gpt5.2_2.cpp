#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct ProbeConstraint {
    ll s, t;
    vector<ll> dist; // size k, sorted
};

struct ProbeInfo {
    ll s, t;
    unordered_map<ll, int> idx; // distance value -> compressed id
    vector<int> cnt;            // counts for each id
};

struct Edge {
    int bIdx;
    ll x, y;
    vector<int> dId; // per probe id (compressed index into cnt)
};

static int K;
static ll BND;

static vector<ll> ask_point(ll s, ll t) {
    cout << "? 1 " << s << " " << t << "\n";
    cout.flush();
    vector<ll> res(K);
    for (int i = 0; i < K; i++) {
        if (!(cin >> res[i])) exit(0);
    }
    return res;
}

static vector<ll> predicted_dists(const vector<pair<ll,ll>>& pts, ll s, ll t) {
    vector<ll> v;
    v.reserve(pts.size());
    for (auto &p : pts) v.push_back(llabs(p.first - s) + llabs(p.second - t));
    sort(v.begin(), v.end());
    return v;
}

static bool solve_with_constraints(const vector<ll>& A, const vector<ll>& Bb,
                                  const vector<ProbeConstraint>& cons,
                                  vector<pair<ll,ll>>& outPts) {
    int m = (int)cons.size();
    vector<ProbeInfo> probes;
    probes.reserve(m);
    probes.clear();

    for (const auto& c : cons) {
        ProbeInfo p;
        p.s = c.s;
        p.t = c.t;
        p.idx.reserve(64);
        vector<ll> uniq;
        uniq.reserve(K);
        for (ll x : c.dist) {
            if (uniq.empty() || uniq.back() != x) uniq.push_back(x);
        }
        p.cnt.assign((int)uniq.size(), 0);
        for (int i = 0; i < (int)uniq.size(); i++) p.idx[uniq[i]] = i;
        for (ll x : c.dist) p.cnt[p.idx[x]]++;
        probes.push_back(std::move(p));
    }

    vector<vector<Edge>> edges(K);
    for (int ai = 0; ai < K; ai++) {
        edges[ai].clear();
        edges[ai].reserve(K);
        for (int bj = 0; bj < K; bj++) {
            ll a = A[ai], b = Bb[bj];
            if ( ((a ^ b) & 1LL) ) continue; // parity mismatch
            ll x = (a - b) / 2;
            ll y = (a + b) / 2;
            if (x < -BND || x > BND || y < -BND || y > BND) continue;

            Edge e;
            e.bIdx = bj;
            e.x = x; e.y = y;
            e.dId.resize(m);
            bool ok = true;
            for (int pi = 0; pi < m; pi++) {
                ll d = llabs(x - probes[pi].s) + llabs(y - probes[pi].t);
                auto it = probes[pi].idx.find(d);
                if (it == probes[pi].idx.end()) { ok = false; break; }
                e.dId[pi] = it->second;
            }
            if (!ok) continue;
            edges[ai].push_back(std::move(e));
        }
        if (edges[ai].empty()) return false;
    }

    vector<int> orderA(K);
    iota(orderA.begin(), orderA.end(), 0);
    stable_sort(orderA.begin(), orderA.end(), [&](int i, int j){
        return edges[i].size() < edges[j].size();
    });

    vector<pair<ll,ll>> assigned(K, {0,0});
    unsigned usedBMask = 0;

    auto dfs = [&](auto&& self, int pos) -> bool {
        if (pos == K) return true;
        int ai = orderA[pos];

        // Small heuristic: try B choices in an order that prefers rarer distances
        // (approx: sum of remaining counts)
        vector<int> idxs(edges[ai].size());
        iota(idxs.begin(), idxs.end(), 0);
        if ((int)idxs.size() > 1 && m > 0) {
            sort(idxs.begin(), idxs.end(), [&](int ii, int jj){
                const Edge& e1 = edges[ai][ii];
                const Edge& e2 = edges[ai][jj];
                int s1 = 0, s2 = 0;
                for (int pi = 0; pi < m; pi++) {
                    s1 += probes[pi].cnt[e1.dId[pi]];
                    s2 += probes[pi].cnt[e2.dId[pi]];
                }
                return s1 < s2;
            });
        }

        for (int id : idxs) {
            const Edge& e = edges[ai][id];
            if (usedBMask & (1u << e.bIdx)) continue;

            bool ok = true;
            for (int pi = 0; pi < m; pi++) {
                if (probes[pi].cnt[e.dId[pi]] <= 0) { ok = false; break; }
            }
            if (!ok) continue;

            usedBMask |= (1u << e.bIdx);
            for (int pi = 0; pi < m; pi++) probes[pi].cnt[e.dId[pi]]--;
            assigned[ai] = {e.x, e.y};

            if (self(self, pos + 1)) return true;

            for (int pi = 0; pi < m; pi++) probes[pi].cnt[e.dId[pi]]++;
            usedBMask &= ~(1u << e.bIdx);
        }
        return false;
    };

    bool ok = dfs(dfs, 0);
    if (!ok) return false;

    outPts = assigned;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int w;
    if (!(cin >> BND >> K >> w)) return 0;

    int wavesUsed = 0;

    auto query_add_constraint = [&](ll s, ll t, vector<ProbeConstraint>& cons, set<pair<ll,ll>>& used) {
        ProbeConstraint c;
        c.s = s; c.t = t;
        c.dist = ask_point(s, t);
        cons.push_back(std::move(c));
        used.insert({s,t});
        wavesUsed++;
    };

    // Corner queries to get A=x+y and B=-x+y (exactly linear inside box)
    vector<ll> distA = ask_point(-BND, -BND); wavesUsed++;
    vector<ll> distB = ask_point( BND, -BND); wavesUsed++;

    vector<ll> A(K), Bb(K);
    for (int i = 0; i < K; i++) {
        A[i] = distA[i] - 2 * BND;
        Bb[i] = distB[i] - 2 * BND;
    }

    vector<ProbeConstraint> constraints;
    set<pair<ll,ll>> usedProbes;
    usedProbes.insert({-BND, -BND});
    usedProbes.insert({ BND, -BND});

    auto clampll = [&](ll x, ll lo, ll hi){ return max(lo, min(hi, x)); };

    // Deterministic RNG
    uint64_t seed = 1469598103934665603ULL;
    seed ^= (uint64_t)BND + 0x9e3779b97f4a7c15ULL + (seed<<6) + (seed>>2);
    seed ^= (uint64_t)K + 0x9e3779b97f4a7c15ULL + (seed<<6) + (seed>>2);
    auto rng64 = [&]() -> uint64_t {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        seed ^= seed << 8;
        return seed;
    };

    auto gen_new_probe = [&](bool preferInside) -> pair<ll,ll> {
        const ll LIM = 100000000LL;
        for (int it = 0; it < 100000; it++) {
            ll s, t;
            if (preferInside) {
                ll lo = -BND, hi = BND;
                ll span = hi - lo + 1;
                s = lo + (ll)(rng64() % (uint64_t)span);
                t = lo + (ll)(rng64() % (uint64_t)span);
            } else {
                ll span = 2 * LIM + 1;
                s = -LIM + (ll)(rng64() % (uint64_t)span);
                t = -LIM + (ll)(rng64() % (uint64_t)span);
            }
            if (!usedProbes.count({s,t})) return {s,t};
        }
        // fallback deterministic
        ll s = clampll((ll)((int64_t)(rng64() % 200000001ULL) - 100000000LL), -100000000LL, 100000000LL);
        ll t = clampll((ll)((int64_t)(rng64() % 200000001ULL) - 100000000LL), -100000000LL, 100000000LL);
        return {s,t};
    };

    auto add_initial_constraints = [&]() {
        vector<pair<ll,ll>> init;
        init.push_back({0,0});
        init.push_back({BND,0});
        init.push_back({0,BND});
        init.push_back({-BND,0});
        init.push_back({0,-BND});
        init.push_back({clampll(BND/2, -BND, BND), clampll(BND/3, -BND, BND)});
        init.push_back({clampll(-BND/3, -BND, BND), clampll(BND/2, -BND, BND)});
        init.push_back({clampll(BND/5, -BND, BND), clampll(-BND/7, -BND, BND)});

        for (auto [s,t] : init) {
            if (wavesUsed >= w) break;
            if (usedProbes.count({s,t})) continue;
            query_add_constraint(s,t,constraints,usedProbes);
        }
    };

    add_initial_constraints();

    vector<pair<ll,ll>> bestPts;
    bool haveBest = false;

    while (true) {
        vector<pair<ll,ll>> pts;
        bool ok = solve_with_constraints(A, Bb, constraints, pts);
        if (!ok) {
            if (wavesUsed >= w) break;
            auto [s,t] = gen_new_probe(true);
            query_add_constraint(s,t,constraints,usedProbes);
            continue;
        }

        haveBest = true;
        bestPts = pts;

        int goodValidations = 0;
        bool needResolve = false;
        while (wavesUsed < w && goodValidations < 2) {
            auto [s,t] = gen_new_probe(false);
            vector<ll> got = ask_point(s,t);
            wavesUsed++;
            usedProbes.insert({s,t});

            vector<ll> pred = predicted_dists(pts, s, t);
            if (pred == got) {
                goodValidations++;
            } else {
                ProbeConstraint c;
                c.s = s; c.t = t; c.dist = std::move(got);
                constraints.push_back(std::move(c));
                needResolve = true;
                break;
            }
        }

        if (!needResolve) {
            cout << "!";
            for (int i = 0; i < K; i++) {
                cout << " " << pts[i].first << " " << pts[i].second;
            }
            cout << "\n";
            cout.flush();
            return 0;
        }
        // else loop again with added constraint(s)
    }

    // Fallback output
    cout << "!";
    if (haveBest) {
        for (int i = 0; i < K; i++) cout << " " << bestPts[i].first << " " << bestPts[i].second;
    } else {
        for (int i = 0; i < K; i++) cout << " 0 0";
    }
    cout << "\n";
    cout.flush();
    return 0;
}