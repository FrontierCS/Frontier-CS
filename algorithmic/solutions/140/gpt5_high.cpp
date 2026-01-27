#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static const ll LIM = 100000000LL; // 1e8

// Send a wave with d=1 probe at (x,y) and read k distances
vector<ll> query_point(ll x, ll y, int k) {
    cout << "? 1 " << x << " " << y << "\n" << flush;
    vector<ll> res(k);
    for (int i = 0; i < k; ++i) {
        if (!(cin >> res[i])) {
            // In case of interaction failure, exit gracefully.
            exit(0);
        }
    }
    sort(res.begin(), res.end());
    return res;
}

struct QPoint {
    ll x, y;
};

// Matching solver using backtracking with multiset distance constraints
struct Matcher {
    int k;
    vector<ll> S; // s_i = x+y, sorted
    vector<ll> T; // t_i = x-y, sorted
    vector<QPoint> Qs; // query points
    vector<map<ll,int>> distCounts; // per Q, multiset counts of distances
    vector<vector<vector<ll>>> pre; // pre[i][j][q] distance for pair (S[i],T[j]) to Qs[q]
    vector<vector<int>> cand; // candidate T indices per S
    vector<int> order; // order of S indices to process
    vector<int> matchT; // matchT[i] = j
    vector<char> usedT;

    bool dfs(int idx) {
        if (idx == (int)order.size()) return true;
        int i = order[idx];
        // dynamic ordering: sort candidates by current availability (optional)
        // Try candidates for i
        // To reduce branching, we can sort cand[i] by the rarity of distances
        vector<pair<int,int>> candWithScore;
        candWithScore.reserve(cand[i].size());
        for (int j : cand[i]) {
            if (usedT[j]) continue;
            int score = 0;
            bool ok = true;
            for (int q = 0; q < (int)Qs.size(); ++q) {
                ll d = pre[i][j][q];
                auto it = distCounts[q].find(d);
                if (it == distCounts[q].end() || it->second <= 0) { ok = false; break; }
                score += it->second; // higher score means more available; not ideal but fine
            }
            if (ok) candWithScore.emplace_back(score, j);
        }
        sort(candWithScore.begin(), candWithScore.end()); // try rarer first

        for (auto &p : candWithScore) {
            int j = p.second;
            // Check availability and apply
            bool ok = true;
            for (int q = 0; q < (int)Qs.size(); ++q) {
                ll d = pre[i][j][q];
                auto it = distCounts[q].find(d);
                if (it == distCounts[q].end() || it->second <= 0) { ok = false; break; }
            }
            if (!ok) continue;

            // commit
            for (int q = 0; q < (int)Qs.size(); ++q) {
                ll d = pre[i][j][q];
                distCounts[q][d]--;
            }
            usedT[j] = 1;
            matchT[i] = j;

            if (dfs(idx + 1)) return true;

            // rollback
            for (int q = 0; q < (int)Qs.size(); ++q) {
                ll d = pre[i][j][q];
                distCounts[q][d]++;
            }
            usedT[j] = 0;
            matchT[i] = -1;
        }
        return false;
    }

    bool solve() {
        // Prepare candidate lists using basic feasibility across all Qs and parity
        cand.assign(k, {});
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                // parity check: s and t must have same parity
                if (((S[i] ^ T[j]) & 1LL) != 0) continue;
                bool ok = true;
                for (int q = 0; q < (int)Qs.size(); ++q) {
                    ll d = pre[i][j][q];
                    auto it = distCounts[q].find(d);
                    if (it == distCounts[q].end()) { ok = false; break; }
                }
                if (ok) cand[i].push_back(j);
            }
        }
        // Order S indices by increasing candidate set size
        order.resize(k);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            return cand[a].size() < cand[b].size();
        });

        usedT.assign(k, 0);
        matchT.assign(k, -1);

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

    // Ensure we have enough waves. We'll attempt with up to needed waves; if w is small, we still try with what we can.
    // Core strategy requires at least 6 waves (4 corners + 2 extra points) for robust mapping.
    // We'll do 4 corners first.
    ll L = LIM;

    vector<ll> A = query_point(-L, -L, k);
    vector<ll> B2 = query_point(+L, +L, k);
    vector<ll> C = query_point(-L, +L, k);
    vector<ll> D = query_point(+L, -L, k);

    // Compute s values (x+y) and t values (x-y)
    vector<ll> S(k), T(k);

    // Pair smallest in A with largest in B2
    for (int i = 0; i < k; ++i) {
        ll a = A[i];
        ll bcomp = B2[k - 1 - i];
        // s = (a - b) / 2
        S[i] = (a - bcomp) / 2;
    }
    // Pair smallest in C with largest in D
    for (int i = 0; i < k; ++i) {
        ll c = C[i];
        ll dcomp = D[k - 1 - i];
        T[i] = (c - dcomp) / 2;
    }

    // Additional query points to determine pairing between S and T
    vector<QPoint> Qs;
    vector<vector<ll>> distsQ; // per Q, the k distances
    vector<pair<ll,ll>> extraPoints = {
        {0, 0},
        {12345678, -87654321},
        {-76543210, 23456789},
        {34567890, 5678901},
        {-11111111, -22222222},
        {33333333, -44444444},
        {55555555, 6666666}
    };

    int waves_used = 4;
    int extra_idx = 0;

    auto collectQ = [&](int count){
        for (int t = 0; t < count && extra_idx < (int)extraPoints.size() && waves_used < w; ++t) {
            ll qx = extraPoints[extra_idx].first;
            ll qy = extraPoints[extra_idx].second;
            extra_idx++;
            vector<ll> resp = query_point(qx, qy, k);
            Qs.push_back({qx, qy});
            distsQ.push_back(resp);
            waves_used++;
        }
    };

    // Try progressively with more Q points until mapping succeeds or out of waves
    // Start with 2, then 3, then more if needed
    bool solved = false;
    vector<pair<ll,ll>> solutions; // (x,y) for each of k
    for (int need = 2; need <= 6 && !solved; ++need) {
        if ((int)Qs.size() < need) {
            collectQ(need - (int)Qs.size());
        }
        if ((int)Qs.size() < need) break; // cannot proceed further

        // Build distance count maps
        Matcher matcher;
        matcher.k = k;
        matcher.S = S;
        matcher.T = T;
        matcher.Qs.assign(Qs.begin(), Qs.begin() + need);

        matcher.distCounts.clear();
        matcher.distCounts.resize(need);
        for (int qi = 0; qi < need; ++qi) {
            matcher.distCounts[qi].clear();
            for (ll v : distsQ[qi]) matcher.distCounts[qi][v]++;
        }

        // Precompute distances for all (i,j) pairs to all Qs
        matcher.pre.assign(k, vector<vector<ll>>(k, vector<ll>(need, 0)));
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                // If parity mismatch, we can skip computing, but we store anyway
                if (((matcher.S[i] ^ matcher.T[j]) & 1LL) == 0) {
                    ll x = (matcher.S[i] + matcher.T[j]) / 2;
                    ll y = (matcher.S[i] - matcher.T[j]) / 2;
                    for (int qi = 0; qi < need; ++qi) {
                        ll qx = matcher.Qs[qi].x;
                        ll qy = matcher.Qs[qi].y;
                        ll d = llabs(x - qx) + llabs(y - qy);
                        matcher.pre[i][j][qi] = d;
                    }
                } else {
                    for (int qi = 0; qi < need; ++qi) matcher.pre[i][j][qi] = -1; // invalid placeholder
                }
            }
        }

        if (matcher.solve()) {
            // Construct solution points
            solutions.clear();
            solutions.reserve(k);
            for (int i = 0; i < k; ++i) {
                int j = matcher.matchT[i];
                ll x = (matcher.S[i] + matcher.T[j]) / 2;
                ll y = (matcher.S[i] - matcher.T[j]) / 2;
                solutions.emplace_back(x, y);
            }
            solved = true;
            break;
        }
    }

    // Fallback if not solved: pair by parity and order (best effort)
    if (!solved) {
        // Simple greedy: for each S[i], pick first T[j] with same parity not used
        vector<char> used(k, 0);
        solutions.clear();
        for (int i = 0; i < k; ++i) {
            int pick = -1;
            for (int j = 0; j < k; ++j) {
                if (!used[j] && ((S[i] ^ T[j]) & 1LL) == 0) { pick = j; break; }
            }
            if (pick == -1) pick = 0;
            used[pick] = 1;
            ll x = (S[i] + T[pick]) / 2;
            ll y = (S[i] - T[pick]) / 2;
            solutions.emplace_back(x, y);
        }
    }

    // Output final answer
    cout << "! ";
    for (int i = 0; i < k; ++i) {
        cout << solutions[i].first << " " << solutions[i].second;
        if (i + 1 < k) cout << " ";
    }
    cout << "\n" << flush;

    return 0;
}