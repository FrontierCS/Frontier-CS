#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<vector<long long>> h(N, vector<long long>(N));
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            cin >> h[i][j];
        }
    }
    vector<string> ops;
    auto dirChar = [&](int dr, int dc)->char{
        if(dr==0 && dc==1) return 'R';
        if(dr==0 && dc==-1) return 'L';
        if(dr==1 && dc==0) return 'D';
        if(dr==-1 && dc==0) return 'U';
        return '?';
    };
    auto opp = [&](char c)->char{
        if(c=='R') return 'L';
        if(c=='L') return 'R';
        if(c=='U') return 'D';
        if(c=='D') return 'U';
        return '?';
    };

    int r=0, c=0;
    auto has_next = [&](int r, int c)->bool{
        if(r%2==0){
            if(c < N-1) return true;
            else if(r < N-1) return true;
            else return false;
        }else{
            if(c > 0) return true;
            else if(r < N-1) return true;
            else return false;
        }
    };
    auto next_cell = [&](int r, int c)->pair<int,int>{
        if(r%2==0){
            if(c < N-1) return {r, c+1};
            else return {r+1, c};
        }else{
            if(c > 0) return {r, c-1};
            else return {r+1, c};
        }
    };

    while(has_next(r,c)){
        auto [nr, nc] = next_cell(r,c);
        int dr = nr - r, dc = nc - c;
        char dch = dirChar(dr, dc);
        long long val = h[r][c];
        if(val > 0){
            // load val at current
            ops.push_back("+" + to_string(val));
            h[r][c] -= val; // becomes 0
            // move to next with load val
            ops.push_back(string(1, dch));
            // unload at next
            ops.push_back("-" + to_string(val));
            h[nr][nc] += val;
            r = nr; c = nc;
        }else if(val < 0){
            long long need = -val;
            // move to next with load 0
            ops.push_back(string(1, dch));
            // load from next
            ops.push_back("+" + to_string(need));
            h[nr][nc] -= need;
            // move back with load
            ops.push_back(string(1, opp(dch)));
            // unload to current to make zero
            ops.push_back("-" + to_string(need));
            h[r][c] += need; // becomes 0
            // move to next again with load 0
            ops.push_back(string(1, dch));
            r = nr; c = nc;
        }else{
            // val == 0, just move
            ops.push_back(string(1, dch));
            r = nr; c = nc;
        }
    }
    // Output operations
    for(auto &s: ops) cout << s << '\n';
    return 0;
}