#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> p, r;
    DSU(int n=0){init(n);}
    void init(int n){
        p.resize(n);
        r.assign(n,0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){
        while(p[x]!=x){
            p[x]=p[p[x]];
            x=p[x];
        }
        return x;
    }
    void unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
    }
};

static const int N = 10;

pair<int,int> find_empty_by_index(const array<array<int,N>,N>& board, int p){
    int cnt = 0;
    for(int r=0;r<N;r++){
        for(int c=0;c<N;c++){
            if(board[r][c]==0){
                ++cnt;
                if(cnt==p) return {r,c};
            }
        }
    }
    return {-1,-1}; // should not happen
}

array<array<int,N>,N> tilt_board(const array<array<int,N>,N>& board, char dir){
    array<array<int,N>,N> res{};
    for(int i=0;i<N;i++) for(int j=0;j<N;j++) res[i][j]=0;
    if(dir=='L'){
        for(int r=0;r<N;r++){
            int c2=0;
            for(int c=0;c<N;c++){
                if(board[r][c]!=0){
                    res[r][c2++] = board[r][c];
                }
            }
        }
    }else if(dir=='R'){
        for(int r=0;r<N;r++){
            int c2=N-1;
            for(int c=N-1;c>=0;c--){
                if(board[r][c]!=0){
                    res[r][c2--] = board[r][c];
                }
            }
        }
    }else if(dir=='F'){ // up
        for(int c=0;c<N;c++){
            int r2=0;
            for(int r=0;r<N;r++){
                if(board[r][c]!=0){
                    res[r2++][c] = board[r][c];
                }
            }
        }
    }else if(dir=='B'){ // down
        for(int c=0;c<N;c++){
            int r2=N-1;
            for(int r=N-1;r>=0;r--){
                if(board[r][c]!=0){
                    res[r2--][c] = board[r][c];
                }
            }
        }
    }
    return res;
}

long long evaluate_board(const array<array<int,N>,N>& board){
    DSU dsu(N*N);
    auto id = [&](int r,int c){return r*N+c;};
    for(int r=0;r<N;r++){
        for(int c=0;c<N;c++){
            int v = board[r][c];
            if(v==0) continue;
            if(r+1<N && board[r+1][c]==v) dsu.unite(id(r,c), id(r+1,c));
            if(c+1<N && board[r][c+1]==v) dsu.unite(id(r,c), id(r,c+1));
        }
    }
    unordered_map<int,int> comp;
    comp.reserve(200);
    for(int r=0;r<N;r++){
        for(int c=0;c<N;c++){
            if(board[r][c]==0) continue;
            int root = dsu.find(id(r,c));
            comp[root]++;
        }
    }
    long long s = 0;
    for(auto &kv : comp){
        long long sz = kv.second;
        s += sz*sz;
    }
    return s;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavors(100);
    for(int i=0;i<100;i++){
        if(!(cin>>flavors[i])) return 0;
    }

    array<array<int,N>,N> board{};
    for(int i=0;i<N;i++) for(int j=0;j<N;j++) board[i][j]=0;

    vector<vector<char>> pref(4);
    pref[1] = {'L','F','R','B'}; // flavor 1 -> top-left preference
    pref[2] = {'R','F','L','B'}; // flavor 2 -> top-right preference
    pref[3] = {'L','B','R','F'}; // flavor 3 -> bottom-left preference

    for(int t=0;t<100;t++){
        int p;
        if(!(cin>>p)) return 0;

        auto pos = find_empty_by_index(board, p);
        array<array<int,N>,N> base = board;
        base[pos.first][pos.second] = flavors[t];

        long long bestScore = LLONG_MIN;
        char bestDir = 'L';

        array<char,4> dirs = {'L','R','F','B'};
        // tie-break map
        array<int,256> prio; prio.fill(1000);
        for(int i=0;i<(int)pref[flavors[t]].size();i++){
            prio[(unsigned char)pref[flavors[t]][i]] = i;
        }

        for(char d: dirs){
            auto sim = tilt_board(base, d);
            long long sc = evaluate_board(sim);
            if(sc > bestScore){
                bestScore = sc;
                bestDir = d;
            } else if(sc == bestScore){
                if(prio[(unsigned char)d] < prio[(unsigned char)bestDir]){
                    bestDir = d;
                }
            }
        }

        cout << bestDir << '\n' << flush;

        board = tilt_board(base, bestDir);
    }

    return 0;
}