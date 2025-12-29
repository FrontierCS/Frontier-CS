#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static inline ll manhattan(ll x1, ll y1, ll x2, ll y2) {
    return llabs(x1 - x2) + llabs(y1 - y2);
}

struct PairHash {
    size_t operator()(const pair<ll,ll>& p) const noexcept {
        static const uint64_t FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        uint64_t x = (uint64_t)(p.first) + 0x9e3779b97f4a7c15ULL;
        uint64_t y = (uint64_t)(p.second) + 0x9e3779b97f4a7c15ULL;
        x ^= FIXED_RANDOM;
        y ^= (FIXED_RANDOM << 1);
        x ^= x >> 23;
        x *= 0x2127599bf4325c37ULL;
        x ^= x >> 47;
        y ^= y >> 23;
        y *= 0x2127599bf4325c37ULL;
        y ^= y >> 47;
        return (size_t)(x ^ (y + 0x9e3779b97f4a7c15ULL + (x<<6) + (x>>2)));
    }
};

struct ProbeInfo {
    vector<ll> val;
    vector<int> cnt;
    unordered_map<ll,int> idx;
};

struct Edge {
    int diff;
    ll x, y;
    vector<int> didx; // per probe
};

struct SolveState {
    int k = 0;
    ll b = 0;
    vector<ll> sums, diffs;
    vector<pair<ll,ll>> probes;
    vector<vector<ll>> obs; // probes' observed distances, each size k
    vector<ProbeInfo> pinfo;
    vector<vector<Edge>> edges; // per sum index
};

struct Solution {
    vector<pair<ll,ll>> pts;      // size k (points for each sum index)
    vector<int> diffForSum;       // size k
    bool ok = false;
};

static vector<ll> queryDistances(int k, const vector<pair<ll,ll>>& ps) {
    int d = (int)ps.size();
    cout << "? " << d;
    for (auto [x,y] : ps) cout << " " << x << " " << y;
    cout << endl;

    vector<ll> res;
    res.reserve((size_t)k * d);
    for (int i = 0; i < k * d; i++) {
        ll v;
        if (!(cin >> v)) exit(0);
        if (v == -1) exit(0);
        res.push_back(v);
    }
    return res;
}

static ProbeInfo buildProbeInfo(const vector<ll>& sortedDists) {
    ProbeInfo info;
    info.val.clear();
    info.cnt.clear();
    info.idx.clear();
    info.idx.reserve(sortedDists.size() * 2 + 3);

    for (ll d : sortedDists) {
        if (info.val.empty() || info.val.back() != d) {
            info.val.push_back(d);
            info.cnt.push_back(1);
        } else {
            info.cnt.back()++;
        }
    }
    for (int i = 0; i < (int)info.val.size(); i++) info.idx.emplace(info.val[i], i);
    return info;
}

static SolveState buildState(int k, ll b, const vector<ll>& sums, const vector<ll>& diffs,
                            const vector<pair<ll,ll>>& probes, const vector<vector<ll>>& obs) {
    SolveState st;
    st.k = k;
    st.b = b;
    st.sums = sums;
    st.diffs = diffs;
    st.probes = probes;
    st.obs = obs;

    int m = (int)probes.size();
    st.pinfo.resize(m);
    for (int p = 0; p < m; p++) st.pinfo[p] = buildProbeInfo(obs[p]);

    st.edges.assign(k, {});
    for (int i = 0; i < k; i++) {
        ll s = sums[i];
        st.edges[i].reserve(k);
        for (int j = 0; j < k; j++) {
            ll u = diffs[j];
            if ( ((s ^ u) & 1LL) ) continue; // parity mismatch
            ll x = (s + u) / 2;
            ll y = (s - u) / 2;
            if (x < -b || x > b || y < -b || y > b) continue;

            Edge e;
            e.diff = j;
            e.x = x; e.y = y;
            e.didx.assign(m, -1);

            bool ok = true;
            for (int p = 0; p < m; p++) {
                ll dist = manhattan(x, y, probes[p].first, probes[p].second);
                auto it = st.pinfo[p].idx.find(dist);
                if (it == st.pinfo[p].idx.end()) { ok = false; break; }
                e.didx[p] = it->second;
            }
            if (ok) st.edges[i].push_back(std::move(e));
        }
        // Small heuristic: sort by diff to stabilize
        sort(st.edges[i].begin(), st.edges[i].end(), [](const Edge& a, const Edge& b){
            if (a.diff != b.diff) return a.diff < b.diff;
            if (a.x != b.x) return a.x < b.x;
            return a.y < b.y;
        });
    }
    return st;
}

static vector<pair<ll,ll>> sortedPointSet(const vector<pair<ll,ll>>& pts) {
    vector<pair<ll,ll>> v = pts;
    sort(v.begin(), v.end());
    return v;
}

static Solution solveKuhn(const SolveState& st, int forbidSum, int forbidDiff) {
    int k = st.k;
    vector<int> mt(k, -1);
    vector<int> used(k, 0);
    int iter = 1;

    function<bool(int)> dfs = [&](int v) -> bool {
        if (used[v] == iter) return false;
        used[v] = iter;
        for (const auto& e : st.edges[v]) {
            if (v == forbidSum && e.diff == forbidDiff) continue;
            int to = e.diff;
            if (mt[to] == -1 || dfs(mt[to])) {
                mt[to] = v;
                return true;
            }
        }
        return false;
    };

    for (int v = 0; v < k; v++, iter++) {
        if (!dfs(v)) return Solution{{}, {}, false};
    }

    vector<int> diffForSum(k, -1);
    vector<pair<ll,ll>> pts(k, {0,0});
    // mt[diff] = sum
    for (int d = 0; d < k; d++) {
        int s = mt[d];
        diffForSum[s] = d;
    }
    for (int s = 0; s < k; s++) {
        int d = diffForSum[s];
        bool found = false;
        for (const auto& e : st.edges[s]) {
            if (e.diff == d && !(s == forbidSum && d == forbidDiff)) {
                pts[s] = {e.x, e.y};
                found = true;
                break;
            }
        }
        if (!found) return Solution{{}, {}, false};
    }
    return Solution{pts, diffForSum, true};
}

struct BacktrackCtx {
    const SolveState* st = nullptr;
    int k = 0, m = 0;
    int forbidSum = -1, forbidDiff = -1;

    vector<vector<int>> remCnt;
    int usedDiffMask = 0;
    vector<char> usedSum;
    vector<pair<ll,ll>> ptsForSum;
    vector<int> diffForSum;
    Solution out;
    bool found = false;

    bool edgeFeasible(int sumIdx, const Edge& e) {
        if ((usedDiffMask >> e.diff) & 1) return false;
        if (sumIdx == forbidSum && e.diff == forbidDiff) return false;
        for (int p = 0; p < m; p++) {
            int idx = e.didx[p];
            if (idx < 0) return false;
            if (remCnt[p][idx] <= 0) return false;
        }
        return true;
    }

    int feasibleCount(int sumIdx) {
        int c = 0;
        for (const auto& e : st->edges[sumIdx]) if (edgeFeasible(sumIdx, e)) c++;
        return c;
    }

    bool rec(int depth) {
        if (depth == k) {
            out.ok = true;
            out.pts = ptsForSum;
            out.diffForSum = diffForSum;
            return true;
        }

        int bestSum = -1;
        int bestCnt = INT_MAX;

        for (int i = 0; i < k; i++) {
            if (usedSum[i]) continue;
            int c = feasibleCount(i);
            if (c == 0) return false;
            if (c < bestCnt) {
                bestCnt = c;
                bestSum = i;
                if (c == 1) break;
            }
        }

        // Try edges in an order that prefers rarer distances in remaining counts
        vector<int> order;
        order.reserve(st->edges[bestSum].size());
        for (int idx = 0; idx < (int)st->edges[bestSum].size(); idx++) order.push_back(idx);

        auto scoreEdge = [&](const Edge& e) -> long long {
            long long s = 0;
            for (int p = 0; p < m; p++) {
                int idx = e.didx[p];
                s += remCnt[p][idx];
            }
            return s;
        };
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            const auto& ea = st->edges[bestSum][a];
            const auto& eb = st->edges[bestSum][b];
            long long sa = scoreEdge(ea), sb = scoreEdge(eb);
            if (sa != sb) return sa < sb;
            if (ea.diff != eb.diff) return ea.diff < eb.diff;
            if (ea.x != eb.x) return ea.x < eb.x;
            return ea.y < eb.y;
        });

        usedSum[bestSum] = 1;
        for (int idx : order) {
            const Edge& e = st->edges[bestSum][idx];
            if (!edgeFeasible(bestSum, e)) continue;

            // apply
            usedDiffMask |= (1 << e.diff);
            ptsForSum[bestSum] = {e.x, e.y};
            diffForSum[bestSum] = e.diff;
            for (int p = 0; p < m; p++) remCnt[p][e.didx[p]]--;

            if (rec(depth + 1)) return true;

            // undo
            for (int p = 0; p < m; p++) remCnt[p][e.didx[p]]++;
            diffForSum[bestSum] = -1;
            ptsForSum[bestSum] = {0, 0};
            usedDiffMask &= ~(1 << e.diff);
        }
        usedSum[bestSum] = 0;
        return false;
    }
};

static Solution solveBacktrack(const SolveState& st, int forbidSum, int forbidDiff) {
    BacktrackCtx ctx;
    ctx.st = &st;
    ctx.k = st.k;
    ctx.m = (int)st.probes.size();
    ctx.forbidSum = forbidSum;
    ctx.forbidDiff = forbidDiff;

    ctx.remCnt.assign(ctx.m, {});
    for (int p = 0; p < ctx.m; p++) ctx.remCnt[p] = st.pinfo[p].cnt;

    ctx.usedDiffMask = 0;
    ctx.usedSum.assign(ctx.k, 0);
    ctx.ptsForSum.assign(ctx.k, {0,0});
    ctx.diffForSum.assign(ctx.k, -1);
    ctx.out = Solution{{}, {}, false};

    if (!ctx.rec(0)) return Solution{{}, {}, false};
    return ctx.out;
}

static Solution solveOnce(const SolveState& st, int forbidSum = -1, int forbidDiff = -1) {
    int m = (int)st.probes.size();
    if (m == 0) return solveKuhn(st, forbidSum, forbidDiff);
    return solveBacktrack(st, forbidSum, forbidDiff);
}

static bool verifyAgainstProbeLists(const vector<pair<ll,ll>>& pts,
                                   const vector<pair<ll,ll>>& probeCoords,
                                   const vector<vector<ll>>& probeObs) {
    int k = (int)pts.size();
    for (int p = 0; p < (int)probeCoords.size(); p++) {
        vector<ll> pred;
        pred.reserve(k);
        for (auto [x,y] : pts) pred.push_back(manhattan(x,y,probeCoords[p].first, probeCoords[p].second));
        sort(pred.begin(), pred.end());
        if (pred != probeObs[p]) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll b;
    int k;
    int w;
    if (!(cin >> b >> k >> w)) return 0;

    const ll L = 100000000LL;
    int maxQueries = min(w, 20000); // total probes limit, we use d=1 each wave

    vector<pair<ll,ll>> allProbes;           // including corner probes
    vector<vector<ll>> allObs;              // same size as allProbes

    auto addProbe = [&](ll x, ll y) {
        vector<ll> res = queryDistances(k, {{x,y}});
        allProbes.push_back({x,y});
        allObs.push_back(std::move(res));
    };

    // Always do the 2 corner probes if possible
    if (maxQueries < 2) {
        cout << "!";
        for (int i = 0; i < k; i++) cout << " 0 0";
        cout << endl;
        return 0;
    }

    int queriesUsed = 0;
    addProbe(L, L); queriesUsed++;
    addProbe(-L, L); queriesUsed++;

    vector<ll> sums(k), diffs(k);
    {
        const auto& DA = allObs[0];
        const auto& DC = allObs[1];
        for (int i = 0; i < k; i++) sums[i] = 2LL * L - DA[i];      // x + y
        for (int i = 0; i < k; i++) diffs[i] = DC[i] - 2LL * L;     // x - y
    }

    unordered_set<pair<ll,ll>, PairHash> usedProbes;
    usedProbes.reserve(1024);
    usedProbes.insert({L, L});
    usedProbes.insert({-L, L});

    // Some deterministic base probes for faster disambiguation
    vector<pair<ll,ll>> base = {
        {0, 0}, {L, 0}, {0, L}, {-L, 0}, {0, -L},
        {L/2, L/3}, {-L/3, L/2}, {L/7, -L/5}, {-L/11, -L/13},
        {12345678, -87654321}, {-76543210, 13579111}, {31415926, -27182818}
    };

    for (auto [x,y] : base) {
        if (queriesUsed >= maxQueries) break;
        if (usedProbes.insert({x,y}).second) {
            addProbe(x,y);
            queriesUsed++;
        }
    }

    mt19937_64 rng((uint64_t)(b * 1000003LL + k * 97LL + 123456789LL));

    auto genRandomProbe = [&]() -> pair<ll,ll> {
        uniform_int_distribution<ll> dist(-L, L);
        while (true) {
            ll x = dist(rng);
            ll y = dist(rng);
            pair<ll,ll> p = {x,y};
            if (usedProbes.find(p) != usedProbes.end()) continue;
            usedProbes.insert(p);
            return p;
        }
    };

    Solution best;
    bool haveBest = false;

    while (true) {
        // Build constraints only from non-corner probes for the solver.
        vector<pair<ll,ll>> solverProbes;
        vector<vector<ll>> solverObs;
        for (int i = 2; i < (int)allProbes.size(); i++) {
            solverProbes.push_back(allProbes[i]);
            solverObs.push_back(allObs[i]);
        }

        SolveState st = buildState(k, b, sums, diffs, solverProbes, solverObs);

        Solution sol = solveOnce(st);
        if (sol.ok) {
            // Verify against all probes (including corners) as an extra safety check
            if (!verifyAgainstProbeLists(sol.pts, allProbes, allObs)) {
                sol.ok = false;
            }
        }

        if (sol.ok) {
            best = sol;
            haveBest = true;

            // Check if unique: try to find an alternative solution with a different point set
            vector<pair<ll,ll>> solSet = sortedPointSet(sol.pts);
            bool ambiguous = false;

            // Try forbidding each used edge one by one; if any alternative yields different point set -> ambiguous
            for (int forbidSum = 0; forbidSum < k; forbidSum++) {
                int forbidDiff = sol.diffForSum[forbidSum];
                if (forbidDiff < 0) continue;
                Solution alt = solveOnce(st, forbidSum, forbidDiff);
                if (!alt.ok) continue;
                if (!verifyAgainstProbeLists(alt.pts, allProbes, allObs)) continue;
                if (sortedPointSet(alt.pts) != solSet) {
                    ambiguous = true;
                    break;
                }
            }

            if (!ambiguous) {
                cout << "!";
                for (int i = 0; i < k; i++) cout << " " << sol.pts[i].first << " " << sol.pts[i].second;
                cout << endl;
                return 0;
            }
        }

        if (queriesUsed >= maxQueries) break;

        // Add another probe to break ambiguity / help find solution
        auto [rx, ry] = genRandomProbe();
        addProbe(rx, ry);
        queriesUsed++;
    }

    if (haveBest) {
        cout << "!";
        for (int i = 0; i < k; i++) cout << " " << best.pts[i].first << " " << best.pts[i].second;
        cout << endl;
        return 0;
    }

    cout << "!";
    for (int i = 0; i < k; i++) cout << " 0 0";
    cout << endl;
    return 0;
}