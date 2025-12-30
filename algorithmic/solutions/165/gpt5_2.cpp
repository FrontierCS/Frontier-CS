#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for(int i=0;i<N;i++) cin >> grid[i];
    vector<string> t(M);
    for(int k=0;k<M;k++) cin >> t[k];

    // Build a superstring S by greedy pairwise overlap (limit overlap length to 5)
    auto overlap = [](const string& a, const string& b) -> int {
        int maxk = min<int>(5, min(a.size(), b.size()));
        for(int k = maxk; k >= 1; --k) {
            bool ok = true;
            for(int i = 0; i < k; ++i) {
                if(a[a.size()-k+i] != b[i]) { ok = false; break; }
            }
            if(ok) return k;
        }
        return 0;
    };

    vector<string> arr = t;
    while(arr.size() > 1) {
        int bestI = -1, bestJ = -1, bestK = -1;
        bool ij = true; // true: arr[i] + arr[j], false: arr[j] + arr[i]
        int S = arr.size();
        for(int i=0;i<S;i++) {
            for(int j=i+1;j<S;j++) {
                int k1 = overlap(arr[i], arr[j]);
                if(k1 > bestK) { bestK = k1; bestI = i; bestJ = j; ij = true; }
                int k2 = overlap(arr[j], arr[i]);
                if(k2 > bestK) { bestK = k2; bestI = i; bestJ = j; ij = false; }
            }
        }
        if(bestI == -1) { // should not happen
            break;
        }
        string merged;
        if(ij) {
            merged = arr[bestI] + arr[bestJ].substr(bestK);
        } else {
            merged = arr[bestJ] + arr[bestI].substr(bestK);
        }
        // place merged at bestI, remove bestJ
        arr[bestI] = merged;
        arr.erase(arr.begin() + bestJ);
    }
    string S = arr.empty() ? string() : arr[0];

    // Precompute positions for each letter
    vector<vector<pair<int,int>>> pos(26);
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            pos[grid[i][j]-'A'].push_back({i,j});
        }
    }

    // If S is empty (shouldn't be), do nothing
    if(S.empty()) {
        return 0;
    }

    int L = (int)S.size();
    // Build occurrences for each character in S
    vector<vector<pair<int,int>>> occ(L);
    for(int i=0;i<L;i++) {
        int c = S[i]-'A';
        occ[i] = pos[c];
        // pos[c] guaranteed to have at least one element
    }

    // DP to minimize movement cost
    const long long INF = (1LL<<60);
    vector<vector<long long>> dp(L);
    vector<vector<int>> par(L);
    for(int i=0;i<L;i++){
        int sz = occ[i].size();
        dp[i].assign(sz, INF);
        par[i].assign(sz, -1);
    }

    auto manh = [](pair<int,int> a, pair<int,int> b) {
        return llabs(a.first - b.first) + llabs(a.second - b.second);
    };

    // Base
    for(int a=0;a<(int)occ[0].size();a++){
        dp[0][a] = manh({si,sj}, occ[0][a]) + 1;
    }
    // Transition
    for(int i=1;i<L;i++){
        int szp = occ[i-1].size();
        int szc = occ[i].size();
        for(int a=0;a<szc;a++){
            long long best = INF;
            int bestb = -1;
            for(int b=0;b<szp;b++){
                long long cost = dp[i-1][b] + manh(occ[i-1][b], occ[i][a]) + 1;
                if(cost < best){
                    best = cost;
                    bestb = b;
                }
            }
            dp[i][a] = best;
            par[i][a] = bestb;
        }
    }

    // Reconstruct path
    int lastIdx = 0;
    long long bestCost = INF;
    for(int a=0;a<(int)occ[L-1].size();a++){
        if(dp[L-1][a] < bestCost){
            bestCost = dp[L-1][a];
            lastIdx = a;
        }
    }
    vector<pair<int,int>> path(L);
    int cur = lastIdx;
    for(int i=L-1;i>=0;i--){
        path[i] = occ[i][cur];
        if(i>0) cur = par[i][cur];
    }

    // Output moves
    for(auto &p : path){
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}