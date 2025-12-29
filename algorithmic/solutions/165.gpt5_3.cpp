#include <bits/stdc++.h>
using namespace std;

struct Pos { int i, j; };

inline int manhattan(const Pos& a, const Pos& b){
    return abs(a.i - b.i) + abs(a.j - b.j);
}

int compute_cost(const Pos& cur, const string& w, const array<vector<Pos>,26>& pos){
    int letters[5];
    for(int l=0;l<5;l++) letters[l] = w[l]-'A';
    const auto& P0 = pos[letters[0]];
    vector<int> dp_prev(P0.size());
    for(size_t k=0;k<P0.size();k++){
        dp_prev[k] = manhattan(cur, P0[k]) + 1;
    }
    for(int l=1;l<5;l++){
        const auto& Pprev = pos[letters[l-1]];
        const auto& Pcur = pos[letters[l]];
        vector<int> dp_cur(Pcur.size(), INT_MAX/4);
        for(size_t k=0;k<Pcur.size();k++){
            int best = INT_MAX/4;
            for(size_t kp=0;kp<Pprev.size();kp++){
                int val = dp_prev[kp] + manhattan(Pprev[kp], Pcur[k]) + 1;
                if(val < best) best = val;
            }
            dp_cur[k] = best;
        }
        dp_prev.swap(dp_cur);
    }
    int ans = INT_MAX/4;
    for(size_t k=0;k<dp_prev.size();k++) ans = min(ans, dp_prev[k]);
    return ans;
}

vector<Pos> reconstruct_path(const Pos& cur, const string& w, const array<vector<Pos>,26>& pos){
    int letters[5];
    for(int l=0;l<5;l++) letters[l] = w[l]-'A';
    const auto& P0 = pos[letters[0]];
    vector<int> dp0(P0.size());
    vector<vector<int>> par(5);
    par[0].assign(P0.size(), -1);
    for(size_t k=0;k<P0.size();k++){
        dp0[k] = manhattan(cur, P0[k]) + 1;
    }
    vector<vector<int>> dps(5);
    dps[0] = dp0;

    for(int l=1;l<5;l++){
        const auto& Pprev = pos[letters[l-1]];
        const auto& Pcur = pos[letters[l]];
        vector<int> dp_cur(Pcur.size(), INT_MAX/4);
        par[l].assign(Pcur.size(), -1);
        for(size_t k=0;k<Pcur.size();k++){
            int best = INT_MAX/4;
            int bestp = -1;
            for(size_t kp=0;kp<Pprev.size();kp++){
                int val = dps[l-1][kp] + manhattan(Pprev[kp], Pcur[k]) + 1;
                if(val < best){
                    best = val;
                    bestp = (int)kp;
                }
            }
            dp_cur[k] = best;
            par[l][k] = bestp;
        }
        dps[l] = move(dp_cur);
    }
    const auto& Plast = pos[letters[4]];
    int best = INT_MAX/4, bestk = -1;
    for(size_t k=0;k<Plast.size();k++){
        if(dps[4][k] < best){
            best = dps[4][k];
            bestk = (int)k;
        }
    }
    vector<Pos> path(5);
    int idx = bestk;
    for(int l=4;l>=1;l--){
        path[l] = pos[letters[l]][idx];
        idx = par[l][idx];
    }
    path[0] = pos[letters[0]][idx];
    return path;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    Pos cur;
    cin >> cur.i >> cur.j;
    vector<string> A(N);
    for(int i=0;i<N;i++) cin >> A[i];
    vector<string> T(M);
    for(int k=0;k<M;k++) cin >> T[k];

    array<vector<Pos>,26> pos;
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            int c = A[i][j]-'A';
            pos[c].push_back({i,j});
        }
    }

    vector<int> used(M, 0);
    for(int step=0; step<M; step++){
        int bestIdx = -1;
        int bestCost = INT_MAX/4;
        for(int k=0;k<M;k++){
            if(used[k]) continue;
            int cost = compute_cost(cur, T[k], pos);
            if(cost < bestCost){
                bestCost = cost;
                bestIdx = k;
            }
        }
        if(bestIdx == -1){
            // Fallback: should not happen
            break;
        }
        vector<Pos> path = reconstruct_path(cur, T[bestIdx], pos);
        for(auto &p : path){
            cout << p.i << ' ' << p.j << '\n';
        }
        cur = path.back();
        used[bestIdx] = 1;
    }
    return 0;
}