#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static inline ll llabsll(ll x){ return x < 0 ? -x : x; }

struct Pairer {
    int k;
    ll b;
    vector<ll> U, V; // size k
    vector<ll> A, Bv; // size m
    vector<vector<ll>> D; // m x k
    vector<unordered_map<ll,int>> counts; // per j counts
    vector<vector<int>> cand; // candidates V index for each U index
    vector<vector<vector<ll>>> fvals; // [i][j][t] => f(U[i], V[j], A[t], Bv[t])
    vector<int> order;
    vector<int> matchUtoV;
    vector<char> usedV;
    vector<vector<int>> cand_sorted; // sorted by heuristic

    static inline ll dist_uvab(ll u, ll v, ll a, ll b) {
        // d = max(|u - a|, |v - b|)
        ll du = u - a; if (du < 0) du = -du;
        ll dv = v - b; if (dv < 0) dv = -dv;
        return du > dv ? du : dv;
    }

    bool dfs(int idx){
        if(idx == k) return true;
        int uidx = order[idx];
        auto &lst = cand_sorted[uidx];
        for(int vidx : lst){
            if(usedV[vidx]) continue;
            bool ok = true;
            // check counts availability
            for(size_t t = 0; t < A.size(); ++t){
                ll val = fvals[uidx][vidx][t];
                auto it = counts[t].find(val);
                if(it == counts[t].end() || it->second == 0){ ok = false; break; }
            }
            if(!ok) continue;
            // commit
            usedV[vidx] = 1;
            matchUtoV[uidx] = vidx;
            vector<pair<int,ll>> usedVals; usedVals.reserve(A.size());
            for(size_t t = 0; t < A.size(); ++t){
                ll val = fvals[uidx][vidx][t];
                counts[t][val]--;
                usedVals.emplace_back((int)t, val);
            }
            if(dfs(idx+1)) return true;
            // rollback
            for(auto &p : usedVals){
                counts[p.first][p.second]++;
            }
            matchUtoV[uidx] = -1;
            usedV[vidx] = 0;
        }
        return false;
    }

    bool solve(){
        int m = (int)A.size();
        counts.assign(m, {});
        for(int t=0;t<m;++t){
            for(ll v: D[t]) counts[t][v]++;
        }
        // precompute fvals
        fvals.assign(k, vector<vector<ll>>(k, vector<ll>(m, 0)));
        for(int i=0;i<k;++i){
            for(int j=0;j<k;++j){
                for(int t=0;t<m;++t){
                    fvals[i][j][t] = dist_uvab(U[i], V[j], A[t], Bv[t]);
                }
            }
        }
        // build candidate lists
        cand.assign(k, {});
        for(int i=0;i<k;++i){
            for(int j=0;j<k;++j){
                if(((U[i] + V[j]) & 1LL) != 0) continue; // parity must match
                // compute coordinates
                ll x = (U[i] + V[j]) / 2;
                ll y = (U[i] - V[j]) / 2;
                if(x < -b || x > b || y < -b || y > b) continue;
                bool ok = true;
                for(int t=0;t<m;++t){
                    ll val = fvals[i][j][t];
                    if(counts[t].find(val) == counts[t].end()){ ok = false; break; }
                }
                if(ok) cand[i].push_back(j);
            }
        }
        for(int i=0;i<k;++i){
            if(cand[i].empty()) return false;
        }
        // order U indices by smallest candidate size
        order.resize(k);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if(cand[a].size() != cand[b].size()) return cand[a].size() < cand[b].size();
            return a < b;
        });

        // sort candidates by heuristic rarity (sum of counts across waves)
        cand_sorted.assign(k, {});
        for(int idx=0; idx<k; ++idx){
            int i = order[idx];
            vector<pair<long long,int>> tmp; // (score, v)
            tmp.reserve(cand[i].size());
            for(int v : cand[i]){
                long long score = 0;
                for(int t=0;t<m;++t){
                    ll val = fvals[i][v][t];
                    auto it = counts[t].find(val);
                    int c = (it != counts[t].end() ? it->second : 0);
                    score += (long long)c;
                }
                tmp.emplace_back(score, v);
            }
            sort(tmp.begin(), tmp.end()); // prefer smaller score (rarer)
            cand_sorted[i].clear();
            for(auto &p: tmp) cand_sorted[i].push_back(p.second);
        }

        matchUtoV.assign(k, -1);
        usedV.assign(k, 0);
        return dfs(0);
    }
};

static vector<ll> query_wave(const vector<pair<ll,ll>>& pts, int k){
    int d = (int)pts.size();
    cout << "? " << d;
    for(auto &p: pts){
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
    cout.flush();
    vector<ll> res;
    res.reserve((size_t)k * d);
    for(int i=0;i<k*d;i++){
        ll x;
        if(!(cin >> x)){
            // If interactive input fails, exit gracefully.
            exit(0);
        }
        res.push_back(x);
    }
    return res;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll b;
    int k, w;
    if(!(cin >> b >> k >> w)){
        return 0;
    }

    // First two waves to get U and V
    int used_waves = 0;
    int used_probes = 0;

    // Wave to get U: s=b, t=b
    {
        vector<pair<ll,ll>> pts = { {b, b} };
        vector<ll> d = query_wave(pts, k);
        used_waves++; used_probes += 1;
        // U_i = (s + t) - d_i = 2b - d_i
        vector<ll> U(k);
        for(int i=0;i<k;i++) U[i] = 2*b - d[i];
        // store temporarily in global U vector via capturing
        // We'll move to variables below
        // Next wave to get V: s=b, t=-b
        vector<pair<ll,ll>> pts2 = { {b, -b} };
        vector<ll> d2 = query_wave(pts2, k);
        used_waves++; used_probes += 1;
        vector<ll> V(k);
        for(int i=0;i<k;i++) V[i] = 2*b - d2[i];

        // Now coupling waves
        vector<pair<ll,ll>> couplingPoints;
        // Add near-origin points
        couplingPoints.push_back({0,0});
        couplingPoints.push_back({1,0});
        couplingPoints.push_back({0,1});
        couplingPoints.push_back({1,1});
        couplingPoints.push_back({-1,0});
        couplingPoints.push_back({0,-1});
        couplingPoints.push_back({2,0});
        couplingPoints.push_back({0,2});
        couplingPoints.push_back({2,2});
        couplingPoints.push_back({-1,-1});
        couplingPoints.push_back({1,-1});
        couplingPoints.push_back({-1,1});
        // Add some scaled by b
        ll hb = max(1LL, b / 2);
        ll tb = max(1LL, b / 3);
        couplingPoints.push_back({hb, 0});
        couplingPoints.push_back({0, hb});
        couplingPoints.push_back({hb, hb});
        couplingPoints.push_back({hb, -hb});
        couplingPoints.push_back({-hb, hb});
        couplingPoints.push_back({-hb, -hb});
        couplingPoints.push_back({tb, 0});
        couplingPoints.push_back({0, tb});
        couplingPoints.push_back({tb, tb});
        couplingPoints.push_back({-tb, tb});
        couplingPoints.push_back({tb, -tb});

        vector<ll> A, Bv;
        vector<vector<ll>> Dlist;

        Pairer solver;
        solver.k = k;
        solver.b = b;
        solver.U = U;
        solver.V = V;

        bool solved = false;

        int max_extra = max(0, w - used_waves); // remaining waves allowed
        int to_query = min((int)couplingPoints.size(), max_extra);
        for(int idx=0; idx<to_query; ++idx){
            auto st = couplingPoints[idx];
            vector<pair<ll,ll>> pts3 = { st };
            vector<ll> d3 = query_wave(pts3, k);
            used_waves++; used_probes += 1;

            ll a = st.first + st.second;
            ll bb = st.first - st.second;
            A.push_back(a);
            Bv.push_back(bb);
            Dlist.push_back(d3);

            solver.A = A;
            solver.Bv = Bv;
            solver.D = Dlist;

            if(solver.solve()){
                solved = true;
                break;
            }
        }

        if(!solved){
            // If not solved yet and still have waves left, try a few random-ish points
            mt19937_64 rng(712367123);
            int extra_left = w - used_waves;
            for(int r=0; r<extra_left && !solved; ++r){
                // choose s,t in [-b, b] avoiding extremes (not both >=b or <=-b simultaneously)
                ll s = (ll)( (rng() % (2*b + 1)) - b );
                ll t = (ll)( (rng() % (2*b + 1)) - b );
                // Ensure within range [-1e8,1e8] automatically since b<=1e8
                vector<pair<ll,ll>> pts3 = { {s, t} };
                vector<ll> d3 = query_wave(pts3, k);
                used_waves++; used_probes += 1;

                ll a = s + t;
                ll bb = s - t;
                A.push_back(a);
                Bv.push_back(bb);
                Dlist.push_back(d3);

                solver.A = A;
                solver.Bv = Bv;
                solver.D = Dlist;

                if(solver.solve()){
                    solved = true;
                    break;
                }
            }
        }

        // If still not solved, attempt to solve with whatever constraints we have (might be slow but try)
        if(!solved){
            if(solver.solve()){
                solved = true;
            }
        }

        vector<pair<ll,ll>> ans;
        ans.reserve(k);
        if(solved){
            // Build coordinates
            for(int i=0;i<k;i++){
                int vj = solver.matchUtoV[i];
                if(vj < 0) {
                    // fallback pair by closest parity
                    vj = i;
                }
                ll u = U[i], v = V[vj];
                ll x = (u + v)/2;
                ll y = (u - v)/2;
                ans.emplace_back(x, y);
            }
        }else{
            // Fallback: pair sorted by value closeness to satisfy parity and bounds
            vector<int> idxU(k), idxV(k);
            iota(idxU.begin(), idxU.end(), 0);
            iota(idxV.begin(), idxV.end(), 0);
            sort(idxU.begin(), idxU.end(), [&](int a, int b){ return U[a] < U[b];});
            sort(idxV.begin(), idxV.end(), [&](int a, int b){ return V[a] < V[b];});

            vector<char> used(k, 0);
            for(int iu=0; iu<k; ++iu){
                int iU = idxU[iu];
                int chosen = -1;
                for(int iv=0; iv<k; ++iv){
                    int iV = idxV[iv];
                    if(used[iV]) continue;
                    if(((U[iU] + V[iV]) & 1LL) != 0) continue;
                    ll x = (U[iU] + V[iV]) / 2;
                    ll y = (U[iU] - V[iV]) / 2;
                    if(x < -b || x > b || y < -b || y > b) continue;
                    chosen = iV; break;
                }
                if(chosen == -1){
                    for(int iv=0; iv<k; ++iv){
                        if(!used[idxV[iv]]) { chosen = idxV[iv]; break; }
                    }
                }
                used[chosen] = 1;
                ll x = (U[iU] + V[chosen]) / 2;
                ll y = (U[iU] - V[chosen]) / 2;
                ans.emplace_back(x, y);
            }
        }

        // Output final answer
        cout << "!" ;
        for(auto &p: ans){
            cout << " " << p.first << " " << p.second;
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}