#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct custom_hash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        return splitmix64(x + FIXED_RANDOM);
    }
    size_t operator()(long long x) const { return operator()((uint64_t)x); }
};

static ll B;
static int K;
static int W;

static const ll LIM = 100000000LL;
static const ll BASE = 200000001LL; // 2*LIM+1

static uint64_t seed64 = 88172645463325252ULL;

static uint64_t rng64() {
    seed64 ^= seed64 << 7;
    seed64 ^= seed64 >> 9;
    return seed64;
}

static ll keyOf(ll s, ll t) {
    // assumes s,t in [-LIM, LIM]
    return (s + LIM) * BASE + (t + LIM);
}

static vector<ll> ask1(ll s, ll t) {
    cout << "? 1 " << s << " " << t << "\n" << flush;
    vector<ll> res(K);
    for (int i = 0; i < K; i++) {
        if (!(cin >> res[i])) exit(0);
    }
    return res;
}

static bool solveMatching(
    const vector<ll>& U,
    const vector<ll>& V,
    const vector<pair<ll,ll>>& probes,
    const vector<vector<ll>>& responses,
    vector<pair<ll,ll>>& outPoints
) {
    int m = (int)probes.size();
    if (m == 0) return false;

    // Compress response distances for each probe
    vector<vector<ll>> uniqVals(m);
    vector<vector<int>> cnt0(m);
    vector<unordered_map<ll,int,custom_hash>> idxMap(m);

    for (int p = 0; p < m; p++) {
        vector<ll> r = responses[p];
        sort(r.begin(), r.end());
        uniqVals[p].clear();
        cnt0[p].clear();
        for (ll x : r) {
            if (uniqVals[p].empty() || uniqVals[p].back() != x) {
                uniqVals[p].push_back(x);
                cnt0[p].push_back(1);
            } else {
                cnt0[p].back()++;
            }
        }
        idxMap[p].reserve(uniqVals[p].size() * 2 + 1);
        for (int i = 0; i < (int)uniqVals[p].size(); i++) idxMap[p][uniqVals[p][i]] = i;
    }

    // Precompute candidate edges and distance indices
    vector<vector<vector<int>>> distIdx(K, vector<vector<int>>(K, vector<int>(m, -1)));
    vector<vector<int>> cand(K);
    for (int i = 0; i < K; i++) cand[i].clear();

    for (int i = 0; i < K; i++) {
        ll u = U[i];
        for (int j = 0; j < K; j++) {
            ll v = V[j];
            if (((u + v) & 1LL) != 0) continue;
            ll x = (u + v) / 2;
            ll y = (u - v) / 2;
            if (x < -B || x > B || y < -B || y > B) continue;

            bool ok = true;
            for (int p = 0; p < m; p++) {
                ll s = probes[p].first, t = probes[p].second;
                ll d = llabs(x - s) + llabs(y - t);
                auto it = idxMap[p].find(d);
                if (it == idxMap[p].end()) { ok = false; break; }
                distIdx[i][j][p] = it->second;
            }
            if (!ok) continue;
            cand[i].push_back(j);
        }
        if (cand[i].empty()) return false;
    }

    vector<int> order(K);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return cand[a].size() < cand[b].size();
    });

    vector<vector<int>> cnt = cnt0;
    vector<int> matchU(K, -1);

    function<bool(int, uint32_t)> dfs = [&](int pos, uint32_t usedMask) -> bool {
        if (pos == K) return true;
        int i = order[pos];

        // Try candidates
        for (int j : cand[i]) {
            if (usedMask & (1u << j)) continue;

            // Check availability
            bool ok = true;
            for (int p = 0; p < m; p++) {
                int idx = distIdx[i][j][p];
                if (idx < 0 || cnt[p][idx] == 0) { ok = false; break; }
            }
            if (!ok) continue;

            // Apply
            for (int p = 0; p < m; p++) {
                int idx = distIdx[i][j][p];
                cnt[p][idx]--;
            }
            matchU[i] = j;

            if (dfs(pos + 1, usedMask | (1u << j))) return true;

            // Rollback
            matchU[i] = -1;
            for (int p = 0; p < m; p++) {
                int idx = distIdx[i][j][p];
                cnt[p][idx]++;
            }
        }
        return false;
    };

    if (!dfs(0, 0u)) return false;

    outPoints.assign(K, {0, 0});
    for (int i = 0; i < K; i++) {
        int j = matchU[i];
        if (j < 0) return false;
        ll u = U[i], v = V[j];
        ll x = (u + v) / 2;
        ll y = (u - v) / 2;
        outPoints[i] = {x, y};
    }
    return true;
}

static vector<ll> predictDistances(const vector<pair<ll,ll>>& points, ll s, ll t) {
    vector<ll> d;
    d.reserve(points.size());
    for (auto [x, y] : points) d.push_back(llabs(x - s) + llabs(y - t));
    sort(d.begin(), d.end());
    return d;
}

static bool fallbackAnyMatching(const vector<ll>& U, const vector<ll>& V, vector<pair<ll,ll>>& outPoints) {
    vector<vector<int>> cand(K);
    for (int i = 0; i < K; i++) {
        ll u = U[i];
        for (int j = 0; j < K; j++) {
            ll v = V[j];
            if (((u + v) & 1LL) != 0) continue;
            ll x = (u + v) / 2;
            ll y = (u - v) / 2;
            if (x < -B || x > B || y < -B || y > B) continue;
            cand[i].push_back(j);
        }
        if (cand[i].empty()) return false;
    }

    vector<int> order(K);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return cand[a].size() < cand[b].size();
    });

    vector<int> matchU(K, -1);
    function<bool(int, uint32_t)> dfs = [&](int pos, uint32_t used) -> bool {
        if (pos == K) return true;
        int i = order[pos];
        for (int j : cand[i]) {
            if (used & (1u << j)) continue;
            matchU[i] = j;
            if (dfs(pos + 1, used | (1u << j))) return true;
            matchU[i] = -1;
        }
        return false;
    };

    if (!dfs(0, 0u)) return false;

    outPoints.assign(K, {0, 0});
    for (int i = 0; i < K; i++) {
        int j = matchU[i];
        ll u = U[i], v = V[j];
        outPoints[i] = {(u + v) / 2, (u - v) / 2};
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> B >> K >> W;
    if (!cin) return 0;

    // Corner queries to get U=x+y and V=x-y
    vector<ll> d1 = ask1(B, B);
    vector<ll> d2 = ask1(-B, B);

    vector<ll> U(K), V(K);
    for (int i = 0; i < K; i++) U[i] = 2 * B - d1[i];
    for (int i = 0; i < K; i++) V[i] = d2[i] - 2 * B;

    int queriesUsed = 2;
    int probesUsed = 2;

    unordered_set<ll, custom_hash> usedProbeKeys;
    auto markUsed = [&](ll s, ll t) {
        if (s < -LIM || s > LIM || t < -LIM || t > LIM) return;
        usedProbeKeys.insert(keyOf(s, t));
    };
    markUsed(B, B);
    markUsed(-B, B);

    vector<pair<ll,ll>> probes;
    vector<vector<ll>> responses;

    auto addConstraintProbe = [&](ll s, ll t, const vector<ll>* alreadyAns = nullptr) -> bool {
        if (queriesUsed >= W) return false;
        vector<ll> ans;
        if (alreadyAns) ans = *alreadyAns;
        else ans = ask1(s, t);
        queriesUsed++;
        probesUsed++;
        probes.push_back({s, t});
        responses.push_back(ans);
        if (s >= -LIM && s <= LIM && t >= -LIM && t <= LIM) usedProbeKeys.insert(keyOf(s, t));
        return true;
    };

    auto pickNewProbe = [&]() -> pair<ll,ll> {
        for (int it = 0; it < 5000; it++) {
            ll s = (ll)(rng64() % BASE) - LIM;
            ll t = (ll)(rng64() % BASE) - LIM;
            ll kkey = keyOf(s, t);
            if (usedProbeKeys.find(kkey) != usedProbeKeys.end()) continue;
            usedProbeKeys.insert(kkey);
            return {s, t};
        }
        // fallback
        ll s = (ll)(rng64() % BASE) - LIM;
        ll t = (ll)(rng64() % BASE) - LIM;
        return {s, t};
    };

    // Seed with some fixed probes (skip duplicates)
    vector<pair<ll,ll>> fixed = {
        {0, 0},
        {LIM, 0}, {0, LIM}, {-LIM, 0}, {0, -LIM},
        {LIM, LIM}, {-LIM, LIM}, {LIM, -LIM}, {-LIM, -LIM}
    };
    for (auto [s, t] : fixed) {
        if (queriesUsed >= W) break;
        ll kkey = keyOf(s, t);
        if (usedProbeKeys.find(kkey) != usedProbeKeys.end()) continue;
        usedProbeKeys.insert(kkey);
        addConstraintProbe(s, t);
    }

    vector<pair<ll,ll>> points;
    bool solved = false;

    int maxExtra = min(200, W); // safety cap
    while (queriesUsed < W && queriesUsed < maxExtra) {
        if ((int)probes.size() < 3) {
            auto [s, t] = pickNewProbe();
            addConstraintProbe(s, t);
            continue;
        }

        vector<pair<ll,ll>> candidate;
        bool ok = solveMatching(U, V, probes, responses, candidate);

        if (!ok) {
            auto [s, t] = pickNewProbe();
            addConstraintProbe(s, t);
            continue;
        }

        // Verify with up to 2 fresh probes
        bool verified = true;
        int verifications = 0;
        while (verifications < 2 && queriesUsed < W) {
            auto [s, t] = pickNewProbe();
            vector<ll> ans = ask1(s, t);
            queriesUsed++;
            probesUsed++;

            vector<ll> pred = predictDistances(candidate, s, t);
            if (pred != ans) {
                // add as constraint and retry solving
                probes.push_back({s, t});
                responses.push_back(ans);
                verified = false;
                break;
            }
            verifications++;
        }

        if (verified) {
            points = move(candidate);
            solved = true;
            break;
        }
    }

    if (!solved) {
        // Last attempt with gathered constraints
        vector<pair<ll,ll>> candidate;
        if (solveMatching(U, V, probes, responses, candidate)) {
            points = move(candidate);
            solved = true;
        }
    }

    if (!solved) {
        // Fallback purely from parity/bounds
        if (!fallbackAnyMatching(U, V, points)) {
            points.assign(K, {0, 0});
        }
    }

    cout << "!";
    for (int i = 0; i < K; i++) {
        cout << " " << points[i].first << " " << points[i].second;
    }
    cout << "\n" << flush;
    return 0;
}