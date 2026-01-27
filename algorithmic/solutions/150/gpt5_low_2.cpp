#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    vector<string> s(M);
    for(int i=0;i<M;i++) cin >> s[i];

    // Sort strings by length descending, keep original order for ties
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    stable_sort(idx.begin(), idx.end(), [&](int a, int b){
        if (s[a].size() != s[b].size()) return s[a].size() > s[b].size();
        return a < b;
    });

    vector<string> grid(N, string(N, '.'));

    auto try_place = [&](const string& t, int& best_dir, int& best_i, int& best_j, int& best_new) {
        best_new = INT_MAX;
        best_dir = -1; best_i = -1; best_j = -1;
        int L = (int)t.size();
        // dir 0: horizontal, dir 1: vertical
        for(int dir=0; dir<2; dir++){
            if(dir==0){
                for(int i=0;i<N;i++){
                    for(int j=0;j<N;j++){
                        int conflicts = 0, newcells = 0;
                        for(int p=0;p<L;p++){
                            int jj = (j + p) % N;
                            char gch = grid[i][jj];
                            char tch = t[p];
                            if(gch == '.') newcells++;
                            else if(gch != tch){ conflicts = 1; break; }
                        }
                        if(conflicts==0){
                            if(newcells < best_new){
                                best_new = newcells;
                                best_dir = 0; best_i = i; best_j = j;
                                if(best_new == 0) return; // can't do better
                            }
                        }
                    }
                }
            }else{
                for(int i=0;i<N;i++){
                    for(int j=0;j<N;j++){
                        int conflicts = 0, newcells = 0;
                        for(int p=0;p<L;p++){
                            int ii = (i + p) % N;
                            char gch = grid[ii][j];
                            char tch = t[p];
                            if(gch == '.') newcells++;
                            else if(gch != tch){ conflicts = 1; break; }
                        }
                        if(conflicts==0){
                            if(newcells < best_new){
                                best_new = newcells;
                                best_dir = 1; best_i = i; best_j = j;
                                if(best_new == 0) return;
                            }
                        }
                    }
                }
            }
        }
    };

    for(int id : idx){
        const string &t = s[id];
        int dir, bi, bj, bnew;
        try_place(t, dir, bi, bj, bnew);
        if(dir == -1) continue; // cannot place without conflict
        int L = (int)t.size();
        if(dir==0){
            int i = bi, j = bj;
            for(int p=0;p<L;p++){
                int jj = (j + p) % N;
                grid[i][jj] = t[p];
            }
        }else{
            int i = bi, j = bj;
            for(int p=0;p<L;p++){
                int ii = (i + p) % N;
                grid[ii][j] = t[p];
            }
        }
    }

    for(int i=0;i<N;i++){
        cout << grid[i] << '\n';
    }
    return 0;
}