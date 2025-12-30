#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct SplitMix64Hash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return splitmix64(x + FIXED_RANDOM);
    }
    size_t operator()(long long x) const { return operator()((uint64_t)x); }
};

struct Probe {
    ll x, y;
    vector<ll> dists; // size k
    unordered_map<ll, int, SplitMix64Hash> cnt;
};

static ll BOUND_A = 100000000LL;

static ll b;
static int k, w;
static int usedWaves = 0;

static vector<ll> sVals, dVals; // size k each
static vector<vector<char>> validEdge;
static vector<vector<int>> X, Y; // only valid if validEdge[i][j]

static vector<Probe> probes; // additional probes used for pairing
static vector<vector<vector<ll>>> edgeDists; // edgeDists[i][j][pIdx] for probe idx

static void die() { exit(0); }

static vector<ll> queryOne(ll sx, ll sy) {
    if (usedWaves >= w) return {};
    usedWaves++;
    cout << "? 1 " << sx << " " << sy << endl;
    cout.flush();
    vector<ll> res(k);
    for (int i = 0; i < k; i++) {
        if (!(cin >> res[i])) die();
        if (res[i] == -1) die();
    }
    return res;
}

static bool addProbe(ll px, ll py) {
    auto dist = queryOne(px, py);
    if ((int)dist.size() != k) return false;
    Probe pr;
    pr.x = px;
    pr.y = py;
    pr.dists = dist;
    for (ll v : dist) pr.cnt[v]++;

    int pIdx = (int)probes.size();
    probes.push_back(std::move(pr));

    // extend edgeDists by one probe dimension
    for (int i = 0; i < k; i++) {
        for (int j = 0; j < k; j++) {
            if (!validEdge[i][j]) continue;
            ll dx = llabs((ll)X[i][j] - px);
            ll dy = llabs((ll)Y[i][j] - py);
            edgeDists[i][j].push_back(dx + dy);
        }
    }
    (void)pIdx;
    return true;
}

static vector<pair<int,int>> pointsFromAssignment(const vector<int>& chosenD) {
    vector<pair<int,int>> pts;
    pts.reserve(k);
    for (int i = 0; i < k; i++) {
        int j = chosenD[i];
        pts.push_back({X[i][j], Y[i][j]});
    }
    sort(pts.begin(), pts.end());
    return pts;
}

struct Solver {
    int maxSol;
    vector<vector<pair<int,int>>> found; // sorted point multisets
    vector<int> chosenD; // for each s-index, chosen d-index
    int usedDmask = 0;

    vector<unordered_map<ll,int,SplitMix64Hash>> rem; // remaining counts per probe

    bool isNewSolution(const vector<pair<int,int>>& sol) {
        for (auto &s : found) if (s == sol) return false;
        return true;
    }

    void recordSolution() {
        auto sol = pointsFromAssignment(chosenD);
        if (isNewSolution(sol)) found.push_back(std::move(sol));
    }

    int optionCountForS(int si, vector<int>* optOut) {
        int cnt = 0;
        if (optOut) optOut->clear();
        for (int dj = 0; dj < k; dj++) {
            if (usedDmask & (1 << dj)) continue;
            if (!validEdge[si][dj]) continue;
            bool ok = true;
            for (int p = 0; p < (int)probes.size(); p++) {
                ll v = edgeDists[si][dj][p];
                auto it = rem[p].find(v);
                if (it == rem[p].end() || it->second <= 0) { ok = false; break; }
            }
            if (!ok) continue;
            cnt++;
            if (optOut) optOut->push_back(dj);
        }
        return cnt;
    }

    void dfs(int assigned) {
        if ((int)found.size() >= maxSol) return;
        if (assigned == k) {
            recordSolution();
            return;
        }

        int bestS = -1;
        vector<int> bestOpts;
        int bestCnt = INT_MAX;

        for (int si = 0; si < k; si++) {
            if (chosenD[si] != -1) continue;
            vector<int> opts;
            int c = optionCountForS(si, &opts);
            if (c == 0) return;
            if (c < bestCnt) {
                bestCnt = c;
                bestS = si;
                bestOpts = std::move(opts);
                if (bestCnt == 1) break;
            }
        }
        if (bestS == -1) return;

        // sort options by rarity heuristic
        auto scoreDj = [&](int dj) -> long long {
            long long s = 0;
            for (int p = 0; p < (int)probes.size(); p++) {
                ll v = edgeDists[bestS][dj][p];
                auto it = rem[p].find(v);
                s += (it == rem[p].end() ? (long long)1e18 : it->second);
            }
            return s;
        };
        sort(bestOpts.begin(), bestOpts.end(), [&](int a, int b) {
            return scoreDj(a) < scoreDj(b);
        });

        for (int dj : bestOpts) {
            // apply
            vector<ll> vals;
            vals.reserve(probes.size());
            bool ok = true;
            for (int p = 0; p < (int)probes.size(); p++) {
                ll v = edgeDists[bestS][dj][p];
                auto it = rem[p].find(v);
                if (it == rem[p].end() || it->second <= 0) { ok = false; break; }
                vals.push_back(v);
            }
            if (!ok) continue;

            for (int p = 0; p < (int)probes.size(); p++) {
                ll v = vals[p];
                auto it = rem[p].find(v);
                it->second--;
                if (it->second == 0) rem[p].erase(it);
            }

            chosenD[bestS] = dj;
            int prevMask = usedDmask;
            usedDmask |= (1 << dj);

            dfs(assigned + 1);

            usedDmask = prevMask;
            chosenD[bestS] = -1;

            // restore
            for (int p = 0; p < (int)probes.size(); p++) {
                rem[p][vals[p]]++;
            }

            if ((int)found.size() >= maxSol) return;
        }
    }

    vector<vector<pair<int,int>>> solveUpTo(int maxSol_) {
        maxSol = maxSol_;
        found.clear();
        chosenD.assign(k, -1);
        usedDmask = 0;

        rem.clear();
        rem.reserve(probes.size());
        for (auto &pr : probes) rem.push_back(pr.cnt);

        dfs(0);
        return found;
    }
};

static pair<ll,ll> nextProbeCandidate(int idx, uint64_t& seed) {
    static vector<pair<ll,ll>> fixed = {
        {0,0},
        {1,0},
        {0,1},
        {1,2},
        {-3,5},
        {7,-11},
        {12345,-54321},
        {-22222,33333},
        {10000000,-20000000},
        {-30000000,40000000},
        {9999999,8888888},
        {-7777777,-6666666},
        {31415926,-27182818}
    };
    if (idx < (int)fixed.size()) return fixed[idx];

    auto nxt = [&]() -> ll {
        seed = seed * 6364136223846793005ULL + 1442695040888963407ULL;
        uint64_t v = seed >> 1;
        ll r = (ll)(v % 200000001ULL) - 100000000LL;
        return r;
    };

    return {nxt(), nxt()};
}

static void outputAnswer(const vector<pair<int,int>>& pts) {
    cout << "!";
    for (auto [x,y] : pts) cout << " " << x << " " << y;
    cout << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> b >> k >> w)) return 0;

    if (w < 4) {
        vector<pair<int,int>> pts(k, {0, 0});
        outputAnswer(pts);
        return 0;
    }

    ll A = BOUND_A;
    if (A < b) A = b;
    if (A > 100000000LL) A = 100000000LL;

    // 4 base queries to recover x+y and y-x multisets
    auto L1 = queryOne(A, A);         // 2A - (x+y)
    auto L2 = queryOne(-A, -A);       // 2A + (x+y) (unused)
    auto L3 = queryOne(-A, A);        // 2A - (y-x)
    auto L4 = queryOne(A, -A);        // 2A + (y-x) (unused)
    (void)L2; (void)L4;

    if ((int)L1.size() != k || (int)L3.size() != k) {
        vector<pair<int,int>> pts(k, {0, 0});
        outputAnswer(pts);
        return 0;
    }

    sVals.resize(k);
    dVals.resize(k);
    for (int i = 0; i < k; i++) sVals[i] = 2 * A - L1[i]; // x+y
    for (int i = 0; i < k; i++) dVals[i] = 2 * A - L3[i]; // y-x

    // Build candidate edges
    validEdge.assign(k, vector<char>(k, 0));
    X.assign(k, vector<int>(k, 0));
    Y.assign(k, vector<int>(k, 0));
    edgeDists.assign(k, vector<vector<ll>>(k));

    for (int i = 0; i < k; i++) {
        for (int j = 0; j < k; j++) {
            ll s = sVals[i], d = dVals[j];
            if (((s - d) & 1LL) != 0) continue;
            ll x = (s - d) / 2;
            ll y = (s + d) / 2;
            if (x < -b || x > b || y < -b || y > b) continue;
            validEdge[i][j] = 1;
            X[i][j] = (int)x;
            Y[i][j] = (int)y;
            edgeDists[i][j].clear();
        }
    }

    // If no additional waves left, just output any matching (greedy backtracking without probes).
    int remainingWaves = w - usedWaves;
    if (remainingWaves <= 0) {
        // simple greedy assignment
        vector<int> chosenD(k, -1);
        int usedMask = 0;
        function<bool(int)> rec = [&](int assigned) -> bool {
            if (assigned == k) return true;
            int bestS = -1, bestCnt = INT_MAX;
            vector<int> bestOpts;
            for (int si = 0; si < k; si++) if (chosenD[si] == -1) {
                vector<int> opts;
                for (int dj = 0; dj < k; dj++) {
                    if (usedMask & (1 << dj)) continue;
                    if (!validEdge[si][dj]) continue;
                    opts.push_back(dj);
                }
                if ((int)opts.size() == 0) return false;
                if ((int)opts.size() < bestCnt) {
                    bestCnt = (int)opts.size();
                    bestS = si;
                    bestOpts = std::move(opts);
                }
            }
            for (int dj : bestOpts) {
                chosenD[bestS] = dj;
                usedMask |= (1 << dj);
                if (rec(assigned + 1)) return true;
                usedMask &= ~(1 << dj);
                chosenD[bestS] = -1;
            }
            return false;
        };
        bool ok = rec(0);
        if (!ok) {
            vector<pair<int,int>> pts(k, {0,0});
            outputAnswer(pts);
            return 0;
        }
        auto pts = pointsFromAssignment(chosenD);
        outputAnswer(pts);
        return 0;
    }

    // Prepare probe candidates, add a few, solve, and iterate until unique or wave limit reached.
    set<pair<ll,ll>> usedProbeCoords;
    uint64_t seed = 1469598103934665603ULL ^ (uint64_t)b * 1315423911ULL ^ (uint64_t)k * 2654435761ULL;

    auto addNextProbe = [&]() -> bool {
        for (int idx = 0; idx < 1000; idx++) {
            auto [px, py] = nextProbeCandidate((int)usedProbeCoords.size(), seed);
            if (px < -100000000LL || px > 100000000LL || py < -100000000LL || py > 100000000LL) continue;
            if (usedProbeCoords.insert({px, py}).second) {
                if (usedWaves >= w) return false;
                return addProbe(px, py);
            }
        }
        return false;
    };

    // Add 2-3 probes upfront if possible to tighten constraints
    int upfront = min(3, w - usedWaves);
    for (int i = 0; i < upfront; i++) addNextProbe();

    Solver solver;
    vector<pair<int,int>> best;
    while (true) {
        auto sols = solver.solveUpTo(2);
        if (!sols.empty()) best = sols[0];

        if ((int)sols.size() == 1) {
            outputAnswer(sols[0]);
            return 0;
        }

        if (usedWaves >= w) break;
        if (!addNextProbe()) break;
    }

    if (best.empty()) best.assign(k, {0,0});
    outputAnswer(best);
    return 0;
}