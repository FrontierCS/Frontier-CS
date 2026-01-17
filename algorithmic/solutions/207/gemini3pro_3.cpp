#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

struct Edge {
    int u, v;
    int t_start, t_end;
    int pos;
    int len;
};

struct Swap {
    int u, v;
};

int N, M;
vector<int> S;
vector<pair<int, int>> JerryMoves;
vector<int> Pos;
vector<int> LastChange;
vector<Edge> candidates;

// DSU structures
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    S.resize(N);
    for (int i = 0; i < N; ++i) cin >> S[i];

    cin >> M;
    JerryMoves.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> JerryMoves[i].first >> JerryMoves[i].second;
    }

    Pos.resize(N);
    iota(Pos.begin(), Pos.end(), 0);
    LastChange.assign(N, M); 

    for (int k = M - 1; k >= 0; --k) {
        int x = JerryMoves[k].first;
        int y = JerryMoves[k].second;

        vector<int> affected;
        if (x > 0) affected.push_back(x - 1);
        if (x < N - 1) affected.push_back(x);
        if (y > 0) affected.push_back(y - 1);
        if (y < N - 1) affected.push_back(y);
        
        sort(affected.begin(), affected.end());
        affected.erase(unique(affected.begin(), affected.end()), affected.end());
        
        for (int i : affected) {
            if (LastChange[i] > k) {
                candidates.push_back({Pos[i], Pos[i+1], k, LastChange[i] - 1, i, LastChange[i] - k});
            }
            LastChange[i] = k;
        }
        
        swap(Pos[x], Pos[y]);
    }
    
    for (int i = 0; i < N - 1; ++i) {
        if (LastChange[i] > 0) {
            candidates.push_back({Pos[i], Pos[i+1], 0, LastChange[i] - 1, i, LastChange[i]});
        }
    }

    // Pos is now Map_start (before J_0). 
    // Map_0 (at U_0) is obtained by applying J_0.
    vector<int> Map_0 = Pos;
    if (M > 0) {
        swap(Map_0[JerryMoves[0].first], Map_0[JerryMoves[0].second]);
    }

    vector<int> loc(N);
    for (int i = 0; i < N; ++i) {
        loc[S[i]] = Map_0[i];
    }
    
    DSU cycles(N);
    for (int i = 0; i < N; ++i) {
        cycles.unite(i, loc[i]);
    }
    
    vector<Edge> useful;
    useful.reserve(candidates.size());
    for (const auto& e : candidates) {
        if (cycles.find(e.u) == cycles.find(e.v)) {
            useful.push_back(e);
        }
    }
    
    sort(useful.begin(), useful.end(), [](const Edge& a, const Edge& b){
        return a.len < b.len;
    });
    
    DSU connected(N);
    vector<Swap> ans(M, {0, 0}); // Default to dummy swap 0 0
    vector<bool> time_used(M, false);
    
    for (const auto& e : useful) {
        if (connected.find(e.u) != connected.find(e.v)) {
            int t = -1;
            for (int k = e.t_start; k <= e.t_end; ++k) {
                if (!time_used[k]) {
                    t = k;
                    break;
                }
            }
            
            if (t != -1) {
                connected.unite(e.u, e.v);
                ans[t] = {e.pos, e.pos + 1};
                time_used[t] = true;
            }
        }
    }
    
    vector<pair<int, int>> needed_merges;
    for(int i=0; i<N; ++i) {
        if (connected.find(i) != connected.find(loc[i])) {
            needed_merges.push_back({i, loc[i]});
            connected.unite(i, loc[i]);
        }
    }

    DSU runningDSU(N);
    vector<int> CurrentMap = Map_0;
    vector<int> InvMap(N);
    for(int i=0; i<N; ++i) InvMap[CurrentMap[i]] = i;

    int merge_idx = 0;
    
    for (int k = 0; k < M; ++k) {
        if (time_used[k]) {
            int p = ans[k].u;
            int q = ans[k].v;
            int u = CurrentMap[p];
            int v = CurrentMap[q];
            
            runningDSU.unite(u, v);
            swap(CurrentMap[p], CurrentMap[q]);
            swap(InvMap[u], InvMap[v]);
        } else {
            while (merge_idx < needed_merges.size()) {
                int u = needed_merges[merge_idx].first;
                int v = needed_merges[merge_idx].second;
                if (runningDSU.find(u) != runningDSU.find(v)) {
                    int p = InvMap[u];
                    int q = InvMap[v];
                    ans[k] = {p, q};
                    time_used[k] = true;
                    
                    runningDSU.unite(u, v);
                    swap(CurrentMap[p], CurrentMap[q]);
                    swap(InvMap[u], InvMap[v]);
                    
                    merge_idx++;
                    break; 
                }
                merge_idx++;
            }
        }
        
        if (k < M - 1) {
            int jx = JerryMoves[k+1].first;
            int jy = JerryMoves[k+1].second;
            int u = CurrentMap[jx];
            int v = CurrentMap[jy];
            swap(CurrentMap[jx], CurrentMap[jy]);
            swap(InvMap[u], InvMap[v]);
        }
    }

    cout << M << "\n";
    long long total_V = 0;
    for (int k = 0; k < M; ++k) {
        cout << ans[k].u << " " << ans[k].v << "\n";
        total_V += abs(ans[k].u - ans[k].v);
    }
    cout << (long long)M * total_V << "\n";

    return 0;
}