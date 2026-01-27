#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Anchor {
    ll s, t;
    ll A, B;
    vector<ll> dist; // size k
    unordered_map<ll,int> cnt;
    vector<pair<ll,int>> cntList; // for iteration
};

int b, k, w;
ll M;

// Global query count (waves)
int waves_used = 0;

// Query a wave with d probes
vector<ll> queryWave(const vector<pair<ll,ll>>& probes) {
    int d = (int)probes.size();
    cout << "? " << d;
    for (auto &p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
    cout.flush();
    waves_used++;
    vector<ll> res;
    res.resize(1LL * k * d);
    for (int i = 0; i < k * d; i++) {
        if (!(cin >> res[i])) {
            // If judge ends or error, keep going with zeros; in non-interactive this won't run
            res[i] = 0;
        }
    }
    return res;
}

bool recMatch(int pos,
              const vector<ll>& U, const vector<ll>& V,
              const vector<vector<int>>& orderAdj,
              const vector<vector<vector<ll>>>& dvals,
              vector<int>& orderU, vector<int>& matchUtoV,
              vector<int>& usedV,
              vector<unordered_map<ll,int>>& remCnt) {
    int n = (int)U.size();
    if (pos == n) return true;
    int i = orderU[pos];
    // Try all candidate V for U[i]
    for (int j : orderAdj[i]) {
        if (usedV[j]) continue;
        bool ok = true;
        // Check counts for all anchors
        for (int m = 0; m < (int)remCnt.size(); m++) {
            ll d = dvals[m][i][j];
            auto it = remCnt[m].find(d);
            if (it == remCnt[m].end() || it->second <= 0) { ok = false; break; }
        }
        if (!ok) continue;
        // Assign
        usedV[j] = 1;
        for (int m = 0; m < (int)remCnt.size(); m++) {
            ll d = dvals[m][i][j];
            remCnt[m][d]--;
        }
        matchUtoV[i] = j;
        if (recMatch(pos + 1, U, V, orderAdj, dvals, orderU, matchUtoV, usedV, remCnt)) return true;
        // Backtrack
        matchUtoV[i] = -1;
        for (int m = 0; m < (int)remCnt.size(); m++) {
            ll d = dvals[m][i][j];
            remCnt[m][d]++;
        }
        usedV[j] = 0;
    }
    return false;
}

bool attempt_match(const vector<ll>& U, const vector<ll>& V, const vector<Anchor>& anchors,
                   vector<pair<ll,ll>>& outXY) {
    int n = (int)U.size();
    int m = (int)anchors.size();
    // Build counts maps (remaining)
    vector<unordered_map<ll,int>> remCnt(m);
    for (int a = 0; a < m; a++) remCnt[a] = anchors[a].cnt;

    // Precompute distances for each pair (i,j) for each anchor
    vector<vector<vector<ll>>> dvals(m, vector<vector<ll>>(n, vector<ll>(n, 0)));
    for (int a = 0; a < m; a++) {
        ll A = anchors[a].A, B = anchors[a].B;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                ll d = max(llabs(U[i] - A), llabs(V[j] - B));
                dvals[a][i][j] = d;
            }
        }
    }

    // Build adjacency per U index based on:
    // - parity of U and V
    // - x,y inside [-b,b]
    // - distance to each anchor must be present in that anchor's multiset (at least once)
    vector<vector<int>> adj(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if ( ((U[i] + V[j]) & 1LL) != 0 ) continue;
            ll x = (U[i] + V[j]) / 2;
            ll y = (U[i] - V[j]) / 2;
            if (x < -b || x > b || y < -b || y > b) continue;
            bool ok = true;
            for (int a = 0; a < m; a++) {
                ll d = dvals[a][i][j];
                auto it = remCnt[a].find(d);
                if (it == remCnt[a].end()) { ok = false; break; }
            }
            if (!ok) continue;
            adj[i].push_back(j);
        }
    }

    // Order U indices by increasing degree
    vector<int> orderU(n);
    iota(orderU.begin(), orderU.end(), 0);
    sort(orderU.begin(), orderU.end(), [&](int a, int b){
        return adj[a].size() < adj[b].size();
    });

    // Reorder adjacency per order, and sort each by some heuristic (optional)
    vector<vector<int>> orderAdj(n);
    for (int idx = 0; idx < n; idx++) {
        int i = orderU[idx];
        orderAdj[i] = adj[i];
        // Heuristic: no particular ordering; keep as is
    }

    // Prepare recursion
    vector<int> usedV(n, 0);
    vector<int> matchUtoV(n, -1);

    bool ok = recMatch(0, U, V, orderAdj, dvals, orderU, matchUtoV, usedV, remCnt);
    if (!ok) return false;

    // Build output XY
    outXY.clear();
    outXY.reserve(n);
    for (int i = 0; i < n; i++) {
        int j = matchUtoV[i];
        ll x = (U[i] + V[j]) / 2;
        ll y = (U[i] - V[j]) / 2;
        outXY.emplace_back(x, y);
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> b >> k >> w)) {
        return 0;
    }
    M = b;

    // Step 1: Query for U = x+y using p1 = (-M, -M)
    {
        vector<pair<ll,ll>> probes;
        probes.push_back({-M, -M});
        auto res = queryWave(probes);
        // res size k
        // do nothing else here
        // We'll reuse res to compute U later
        // Actually, we need U; store in vector
    }

    // Read again via query since above result consumed: we need the values; store them
    // Actually we already have them; restructure:
    // Let's requery with p1 and store values properly
    waves_used--; // Undo last increment since we'll re-issue below to store
    vector<pair<ll,ll>> p1 = {{-M, -M}};
    auto R1 = queryWave(p1);
    vector<ll> U;
    U.reserve(k);
    for (int i = 0; i < k; i++) U.push_back(R1[i] - 2LL * M);

    // Step 2: Query for V = x - y using p3 = (-M, M)
    vector<pair<ll,ll>> p3 = {{-M, M}};
    auto R3 = queryWave(p3);
    vector<ll> V;
    V.reserve(k);
    for (int i = 0; i < k; i++) V.push_back(R3[i] - 2LL * M);

    // Additional anchors
    int remaining_waves = w - waves_used;
    vector<Anchor> anchors;

    // We try to use at least 2 additional anchors if possible
    int target_additional = 2;
    if (remaining_waves <= 0) target_additional = 0;
    else target_additional = min(target_additional, remaining_waves);

    // Use deterministic anchors first: (0,0) and (M,0) if allowed
    vector<pair<ll,ll>> addList;
    if (target_additional >= 1) addList.push_back({0, 0});
    if (target_additional >= 2) addList.push_back({M, 0});

    for (auto &pt : addList) {
        Anchor A;
        A.s = pt.first; A.t = pt.second;
        A.A = A.s + A.t; A.B = A.s - A.t;
        vector<pair<ll,ll>> qq;
        qq.push_back({A.s, A.t});
        A.dist = queryWave(qq);
        A.cnt.clear();
        for (ll d : A.dist) A.cnt[d]++;
        A.cntList.clear();
        A.cntList.reserve(A.cnt.size());
        for (auto &it : A.cnt) A.cntList.push_back(it);
        anchors.push_back(std::move(A));
    }

    // If matching fails and we have more waves available, add random anchors one by one
    auto solve_and_output = [&](vector<Anchor>& anc)->bool{
        vector<pair<ll,ll>> XY;
        bool ok = attempt_match(U, V, anc, XY);
        if (!ok) return false;
        // Output result
        cout << "!";
        for (auto &p : XY) {
            cout << " " << p.first << " " << p.second;
        }
        cout << endl;
        cout.flush();
        return true;
    };

    // Try with current anchors
    if (solve_and_output(anchors)) return 0;

    // Add more anchors if possible
    int waves_left = w - waves_used;
    // We will add up to some number (e.g., 6) while waves are available
    int max_extra = min(6, waves_left);
    std::mt19937_64 rng( (uint64_t) (123456789ULL ^ ((unsigned long long)b<<1) ^ (unsigned long long)(k*0x9e3779b97f4a7c15ULL)) );
    for (int iter = 0; iter < max_extra; iter++) {
        ll s = (ll)( (long long) ( (rng() % (2LL*M + 1)) - M ) );
        ll t = (ll)( (long long) ( (rng() % (2LL*M + 1)) - M ) );
        // ensure not duplicate of previous anchors
        bool dup = false;
        for (auto &a : anchors) {
            if (a.s == s && a.t == t) { dup = true; break; }
        }
        if (dup) { iter--; continue; }
        Anchor A;
        A.s = s; A.t = t;
        A.A = A.s + A.t; A.B = A.s - A.t;
        vector<pair<ll,ll>> qq;
        qq.push_back({A.s, A.t});
        A.dist = queryWave(qq);
        A.cnt.clear();
        for (ll d : A.dist) A.cnt[d]++;
        A.cntList.clear();
        for (auto &it : A.cnt) A.cntList.push_back(it);
        anchors.push_back(std::move(A));
        if (solve_and_output(anchors)) return 0;
    }

    // Fallback: try with only one anchor (if exists) or no anchors, do arbitrary pairing
    vector<pair<ll,ll>> XY;
    int n = (int)U.size();
    XY.reserve(n);
    vector<ll> U_sorted = U, V_sorted = V;
    sort(U_sorted.begin(), U_sorted.end());
    sort(V_sorted.begin(), V_sorted.end());
    for (int i = 0; i < n; i++) {
        // Find first V with same parity and within bounds
        bool paired = false;
        for (int j = 0; j < (int)V_sorted.size(); j++) {
            if ((U_sorted[i] + V_sorted[j]) % 2 != 0) continue;
            ll x = (U_sorted[i] + V_sorted[j]) / 2;
            ll y = (U_sorted[i] - V_sorted[j]) / 2;
            if (x < -b || x > b || y < -b || y > b) continue;
            XY.emplace_back(x, y);
            V_sorted.erase(V_sorted.begin() + j);
            paired = true;
            break;
        }
        if (!paired) {
            // If cannot find, just pair with something
            ll v = V_sorted.back();
            V_sorted.pop_back();
            ll x = (U_sorted[i] + v) / 2;
            ll y = (U_sorted[i] - v) / 2;
            XY.emplace_back(x, y);
        }
    }

    cout << "!";
    for (auto &p : XY) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
    cout.flush();

    return 0;
}