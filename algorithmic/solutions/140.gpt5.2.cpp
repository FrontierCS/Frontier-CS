#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct MultiCount {
    vector<ll> vals;
    vector<int> cnt;
    unordered_map<ll,int> pos;

    MultiCount() {}

    explicit MultiCount(const vector<ll>& dists) {
        vals.clear(); cnt.clear(); pos.clear();
        for (ll d : dists) {
            if (vals.empty() || vals.back() != d) {
                vals.push_back(d);
                cnt.push_back(1);
            } else {
                cnt.back()++;
            }
        }
        pos.reserve(vals.size() * 2 + 1);
        for (int i = 0; i < (int)vals.size(); i++) pos[vals[i]] = i;
    }

    inline bool has(ll d) const {
        return pos.find(d) != pos.end();
    }
    inline int idx(ll d) const {
        auto it = pos.find(d);
        if (it == pos.end()) return -1;
        return it->second;
    }
};

struct PairInfo {
    int vIdx;
    ll x, y;
    vector<int> pidx; // indices into MultiCount arrays for each probe
};

static ll B;
static int K, W;
static ll M = 100000000LL;

static vector<ll> Uvals, Vvals;
static vector<pair<ll,ll>> probes;
static vector<vector<ll>> probeDists;

static vector<MultiCount> mcs;
static vector<vector<PairInfo>> candU;

static vector<pair<ll,ll>> answerPts;
static vector<char> assignedU;
static uint32_t usedVmask;

static inline ll manhattan(ll x1, ll y1, ll x2, ll y2) {
    return llabs(x1 - x2) + llabs(y1 - y2);
}

static vector<ll> askPoint(ll x, ll y) {
    cout << "? 1 " << x << " " << y << endl;
    cout.flush();
    vector<ll> res(K);
    for (int i = 0; i < K; i++) {
        if (!(cin >> res[i])) exit(0);
        if (res[i] == -1) exit(0);
    }
    return res;
}

static bool dfs(int depth) {
    if (depth == K) return true;

    int bestU = -1;
    int bestCnt = INT_MAX;

    for (int i = 0; i < K; i++) {
        if (assignedU[i]) continue;
        int c = 0;
        for (const auto &pi : candU[i]) {
            if (usedVmask & (1u << pi.vIdx)) continue;
            bool ok = true;
            for (int p = 0; p < (int)mcs.size(); p++) {
                int id = pi.pidx[p];
                if (id < 0 || mcs[p].cnt[id] == 0) { ok = false; break; }
            }
            if (ok) c++;
        }
        if (c == 0) return false;
        if (c < bestCnt) {
            bestCnt = c;
            bestU = i;
            if (bestCnt == 1) break;
        }
    }

    assignedU[bestU] = 1;

    // Try candidates (optional heuristic: sort by how "rare" the distances are)
    // Create order list for stability
    vector<int> ord(candU[bestU].size());
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        const auto &A = candU[bestU][a];
        const auto &B = candU[bestU][b];
        long long scoreA = 0, scoreB = 0;
        for (int p = 0; p < (int)mcs.size(); p++) {
            scoreA += mcs[p].cnt[A.pidx[p]];
            scoreB += mcs[p].cnt[B.pidx[p]];
        }
        if (scoreA != scoreB) return scoreA < scoreB;
        return A.vIdx < B.vIdx;
    });

    for (int idxo : ord) {
        const auto &pi = candU[bestU][idxo];
        if (usedVmask & (1u << pi.vIdx)) continue;

        bool ok = true;
        for (int p = 0; p < (int)mcs.size(); p++) {
            int id = pi.pidx[p];
            if (mcs[p].cnt[id] == 0) { ok = false; break; }
        }
        if (!ok) continue;

        usedVmask |= (1u << pi.vIdx);
        for (int p = 0; p < (int)mcs.size(); p++) mcs[p].cnt[pi.pidx[p]]--;
        answerPts[bestU] = {pi.x, pi.y};

        if (dfs(depth + 1)) return true;

        for (int p = 0; p < (int)mcs.size(); p++) mcs[p].cnt[pi.pidx[p]]++;
        usedVmask &= ~(1u << pi.vIdx);
    }

    assignedU[bestU] = 0;
    return false;
}

static bool solveWithCurrentProbes() {
    if ((int)probes.size() == 0) return false;

    mcs.clear();
    mcs.reserve(probes.size());
    for (int i = 0; i < (int)probes.size(); i++) {
        mcs.emplace_back(MultiCount(probeDists[i]));
    }

    candU.assign(K, {});
    int P = (int)probes.size();
    for (int i = 0; i < K; i++) {
        candU[i].reserve(K);
        for (int j = 0; j < K; j++) {
            ll u = Uvals[i], v = Vvals[j];
            if ( ((u + v) & 1LL) || ((u - v) & 1LL) ) continue;
            ll x = (u + v) / 2;
            ll y = (u - v) / 2;
            if (x < -B || x > B || y < -B || y > B) continue;

            PairInfo pi;
            pi.vIdx = j;
            pi.x = x; pi.y = y;
            pi.pidx.resize(P);

            bool ok = true;
            for (int p = 0; p < P; p++) {
                ll d = manhattan(x, y, probes[p].first, probes[p].second);
                int id = mcs[p].idx(d);
                if (id < 0) { ok = false; break; }
                pi.pidx[p] = id;
            }
            if (!ok) continue;
            candU[i].push_back(std::move(pi));
        }
        if (candU[i].empty()) return false;
    }

    // Simple necessary condition: candidates must allow a full matching size-wise (rough check)
    // (Not implemented; DFS will handle.)

    answerPts.assign(K, {0, 0});
    assignedU.assign(K, 0);
    usedVmask = 0;

    return dfs(0);
}

static vector<pair<ll,ll>> buildExtraPoints(ll b) {
    set<pair<ll,ll>> seen;
    vector<pair<ll,ll>> pts;

    auto add = [&](ll x, ll y) {
        x = max(-100000000LL, min(100000000LL, x));
        y = max(-100000000LL, min(100000000LL, y));
        if (x < -b) x = -b;
        if (x > b) x = b;
        if (y < -b) y = -b;
        if (y > b) y = b;

        // avoid strict corners (±b, ±b) which can be redundant (linear)
        if (llabs(x) == b && llabs(y) == b && b > 0) {
            if (y > -b) y--;
            else if (y < b) y++;
            else if (x > -b) x--;
            else if (x < b) x++;
        }

        pair<ll,ll> p = {x,y};
        if (seen.insert(p).second) pts.push_back(p);
    };

    add(0, 0);
    add(b, 0);
    add(0, b);
    add(-b, 0);
    add(0, -b);

    if (b >= 1) {
        add(b, 1);
        add(1, b);
        add(-b, 1);
        add(1, -b);
        add(-1, b);
        add(b, -1);
        add(-b, -1);
        add(-1, -b);
    }

    add(b/2, b/3);
    add(-b/2, b/3);
    add(b/3, -b/2);
    add(-b/3, -b/2);

    // pseudo-random within [-b,b]
    unsigned long long seed = 88172645463325252ull;
    auto rnd = [&]() -> unsigned long long {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        seed ^= seed << 8;
        return seed;
    };

    ll span = 2*b + 1;
    if (span <= 0) span = 1;

    for (int t = 0; t < 80 && (int)pts.size() < 60; t++) {
        ll x = (ll)(rnd() % (unsigned long long)span) - b;
        ll y = (ll)(rnd() % (unsigned long long)span) - b;
        // nudge off corners
        if (llabs(x) == b && llabs(y) == b && b > 0) {
            if (y > -b) y--;
            else y++;
        }
        add(x, y);
    }

    // Additional fixed-ish points (clamped)
    add(12345 % span - b, 67890 % span - b);
    add(31415 % span - b, -27182 % span - b);
    add(-99991 % span - b, 42421 % span - b);

    return pts;
}

static vector<pair<ll,ll>> fallbackGreedy() {
    vector<ll> U = Uvals, V = Vvals;
    sort(U.begin(), U.end());
    multiset<ll> Vm(V.begin(), V.end());
    vector<pair<ll,ll>> pts;
    pts.reserve(K);

    for (int i = 0; i < K; i++) {
        ll u = U[i];
        auto it = Vm.end();
        // try find v with same parity and within bounds
        for (auto jt = Vm.begin(); jt != Vm.end(); ++jt) {
            ll v = *jt;
            if (((u + v) & 1LL) || ((u - v) & 1LL)) continue;
            ll x = (u + v) / 2;
            ll y = (u - v) / 2;
            if (x < -B || x > B || y < -B || y > B) continue;
            it = jt;
            break;
        }
        if (it == Vm.end()) it = Vm.begin();
        ll v = *it;
        Vm.erase(it);

        ll x = 0, y = 0;
        if (!(((u + v) & 1LL) || ((u - v) & 1LL))) {
            x = (u + v) / 2;
            y = (u - v) / 2;
            if (x < -B || x > B || y < -B || y > B) { x = 0; y = 0; }
        }
        pts.push_back({x, y});
    }
    return pts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> B >> K >> W)) return 0;

    // Corner queries to get U=x+y and V=x-y multisets
    int queriesUsed = 0;

    if (W >= 1) {
        auto dA = askPoint(M, M);
        queriesUsed++;
        Uvals.resize(K);
        for (int i = 0; i < K; i++) Uvals[i] = 2*M - dA[i];
    } else {
        // Can't do anything
        cout << "! ";
        for (int i = 0; i < K; i++) cout << "0 0" << (i+1==K?'\n':' ');
        cout.flush();
        return 0;
    }

    if (W >= 2) {
        auto dB = askPoint(M, -M);
        queriesUsed++;
        Vvals.resize(K);
        for (int i = 0; i < K; i++) Vvals[i] = 2*M - dB[i];
    } else {
        // Only U known; output zeros
        cout << "! ";
        for (int i = 0; i < K; i++) cout << "0 0" << (i+1==K?'\n':' ');
        cout.flush();
        return 0;
    }

    if (K == 1) {
        ll u = Uvals[0], v = Vvals[0];
        ll x = (u + v) / 2;
        ll y = (u - v) / 2;
        cout << "! " << x << " " << y << endl;
        cout.flush();
        return 0;
    }

    vector<pair<ll,ll>> extras = buildExtraPoints(B);

    probes.clear();
    probeDists.clear();
    probes.reserve(extras.size());
    probeDists.reserve(extras.size());

    bool solved = false;
    vector<pair<ll,ll>> finalPts;

    // Add probes gradually; attempt solve periodically
    int maxExtraQueries = max(0, W - queriesUsed);
    int targetTries = min(maxExtraQueries, (int)extras.size());

    for (int i = 0; i < targetTries; i++) {
        auto [sx, sy] = extras[i];

        // Avoid using same point twice
        bool dup = false;
        for (auto &p : probes) if (p.first == sx && p.second == sy) { dup = true; break; }
        if (dup) continue;

        auto d = askPoint(sx, sy);
        queriesUsed++;
        probes.push_back({sx, sy});
        probeDists.push_back(std::move(d));

        // attempt solve after at least 1 extra probe, and then after each new one
        if (solveWithCurrentProbes()) {
            solved = true;
            finalPts = answerPts;
            break;
        }

        if (queriesUsed >= W) break;
    }

    if (!solved) {
        // Fallback: try solve with whatever probes we got (if none already attempted or last attempt failed)
        if (!probes.empty() && solveWithCurrentProbes()) {
            solved = true;
            finalPts = answerPts;
        } else {
            finalPts = fallbackGreedy();
        }
    }

    cout << "! ";
    for (int i = 0; i < K; i++) {
        cout << finalPts[i].first << " " << finalPts[i].second << (i + 1 == K ? '\n' : ' ');
    }
    cout.flush();
    return 0;
}