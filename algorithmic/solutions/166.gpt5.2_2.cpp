#include <bits/stdc++.h>
using namespace std;

static inline char moveDir(pair<int,int> a, pair<int,int> b){
    int di = b.first - a.first;
    int dj = b.second - a.second;
    if(di == -1 && dj == 0) return 'U';
    if(di == 1 && dj == 0) return 'D';
    if(di == 0 && dj == -1) return 'L';
    if(di == 0 && dj == 1) return 'R';
    return '?';
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<vector<int>> h(N, vector<int>(N));
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++) cin >> h[i][j];
    }

    vector<pair<int,int>> path;
    path.reserve(N*N);
    for(int i=0;i<N;i++){
        if(i % 2 == 0){
            for(int j=0;j<N;j++) path.push_back({i,j});
        }else{
            for(int j=N-1;j>=0;j--) path.push_back({i,j});
        }
    }

    vector<string> ops;
    ops.reserve(5000);

    long long load = 0;

    // Phase 1: traverse in snake order, load positives, partially fill negatives as possible.
    for(int idx=0; idx < (int)path.size(); idx++){
        auto [i,j] = path[idx];
        int cur = h[i][j];
        if(cur > 0){
            ops.push_back("+" + to_string(cur));
            load += cur;
            h[i][j] = 0;
        }else if(cur < 0){
            long long need = -1LL * cur;
            long long use = min(need, load);
            if(use > 0){
                ops.push_back("-" + to_string(use));
                load -= use;
                h[i][j] += (int)use; // still <= 0
            }
        }
        if(idx + 1 < (int)path.size()){
            char d = moveDir(path[idx], path[idx+1]);
            ops.push_back(string(1, d));
        }
    }

    // Phase 2: traverse back, fill remaining negatives.
    for(int idx=(int)path.size()-1; idx>=0; idx--){
        auto [i,j] = path[idx];
        int cur = h[i][j];
        if(cur < 0){
            long long d = -1LL * cur;
            // load must be sufficient
            if(d > 0){
                ops.push_back("-" + to_string(d));
                load -= d;
                h[i][j] = 0;
            }
        }
        if(idx > 0){
            char d = moveDir(path[idx], path[idx-1]);
            ops.push_back(string(1, d));
        }
    }

    // Output operations
    for(const auto &s : ops) cout << s << "\n";
    return 0;
}