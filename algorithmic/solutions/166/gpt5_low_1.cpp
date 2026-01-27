#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            cin >> h[i][j];
        }
    }

    // Build snake path
    vector<pair<int,int>> pos;
    pos.reserve(N*N);
    for(int i=0;i<N;i++){
        if(i%2==0){
            for(int j=0;j<N;j++) pos.emplace_back(i,j);
        }else{
            for(int j=N-1;j>=0;j--) pos.emplace_back(i,j);
        }
    }
    int M = N*N;
    vector<int> a(M);
    for(int idx=0; idx<M; idx++){
        auto [i,j] = pos[idx];
        a[idx] = h[i][j];
    }
    // Find rotation start so that cumulative sums are nonnegative
    long long best = LLONG_MAX;
    int k = -1;
    long long s = 0;
    for(int i=0;i<M;i++){
        s += a[i];
        if(s < best){
            best = s;
            k = i;
        }
    }
    int start = (k + 1) % M;

    vector<string> ops;
    auto add_moves = [&](int si, int sj, int ti, int tj){
        int di = ti - si;
        int dj = tj - sj;
        if(di > 0) ops.insert(ops.end(), di, "D");
        if(di < 0) ops.insert(ops.end(), -di, "U");
        if(dj > 0) ops.insert(ops.end(), dj, "R");
        if(dj < 0) ops.insert(ops.end(), -dj, "L");
    };

    // Move from (0,0) to starting cell with empty load
    auto [si, sj] = make_pair(0,0);
    auto [ti, tj] = pos[start];
    add_moves(si, sj, ti, tj);
    si = ti; sj = tj;

    long long load = 0;
    // Process cells in rotated snake order
    for(int t=0; t<M; t++){
        int idx = (start + t) % M;
        auto [ci, cj] = pos[idx];
        int val = h[ci][cj];
        if(val > 0){
            ops.push_back("+" + to_string(val));
            load += val;
            h[ci][cj] = 0;
        }else if(val < 0){
            int d = -val;
            ops.push_back("-" + to_string(d));
            load -= d;
            h[ci][cj] = 0;
        }
        if(t < M-1){
            auto [ni, nj] = pos[(start + t + 1) % M];
            // they are adjacent
            if(ni == ci){
                if(nj == cj+1) ops.push_back("R");
                else if(nj == cj-1) ops.push_back("L");
            }else if(nj == cj){
                if(ni == ci+1) ops.push_back("D");
                else if(ni == ci-1) ops.push_back("U");
            }else{
                // Fallback (shouldn't happen), but ensure movement
                add_moves(ci, cj, ni, nj);
            }
        }
    }

    // Output operations
    for(auto &op : ops){
        cout << op << '\n';
    }
    return 0;
}