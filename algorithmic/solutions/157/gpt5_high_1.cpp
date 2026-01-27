#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

int N;
int Tlim;

int dr[4] = {-1,1,0,0};
int dc[4] = {0,0,-1,1};
char mvch[4] = {'U','D','L','R'};

inline bool inb(int r,int c,int N){ return r>=0 && r<N && c>=0 && c<N; }

pair<int,int> evaluateS(const vector<int>& board) {
    // returns {S, tie_measure}: S is largest tree component size,
    // tie_measure here as largest connected component size (regardless of cycles)
    int NN = N*N;
    vector<int> id(NN,-1);
    int M=0;
    for(int k=0;k<NN;k++){
        if(board[k]!=0) id[k]=M++;
    }
    if(M==0) return {0,0};
    DSU dsu(M);
    auto has_edge_v = [&](int r, int c){
        int a = board[r*N+c];
        int b = board[(r+1)*N+c];
        if(a==0 || b==0) return false;
        bool ok = ( (a & 8) && (b & 2) );
        return ok;
    };
    auto has_edge_h = [&](int r, int c){
        int a = board[r*N+c];
        int b = board[r*N+c+1];
        if(a==0 || b==0) return false;
        bool ok = ( (a & 4) && (b & 1) );
        return ok;
    };
    // Union all edges
    for(int r=0;r<N-1;r++){
        for(int c=0;c<N;c++){
            if(has_edge_v(r,c)){
                int k1=r*N+c, k2=(r+1)*N+c;
                dsu.unite(id[k1], id[k2]);
            }
        }
    }
    for(int r=0;r<N;r++){
        for(int c=0;c<N-1;c++){
            if(has_edge_h(r,c)){
                int k1=r*N+c, k2=r*N+c+1;
                dsu.unite(id[k1], id[k2]);
            }
        }
    }
    vector<int> nodes(M,0), edges(M,0);
    for(int k=0;k<NN;k++){
        if(id[k]>=0){
            int root = dsu.find(id[k]);
            nodes[root]++;
        }
    }
    for(int r=0;r<N-1;r++){
        for(int c=0;c<N;c++){
            if(has_edge_v(r,c)){
                int k1=r*N+c;
                int root = dsu.find(id[k1]);
                edges[root]++;
            }
        }
    }
    for(int r=0;r<N;r++){
        for(int c=0;c<N-1;c++){
            if(has_edge_h(r,c)){
                int k1=r*N+c;
                int root = dsu.find(id[k1]);
                edges[root]++;
            }
        }
    }
    int bestTree = 0;
    int bestConn = 0;
    for(int i=0;i<M;i++){
        if(dsu.find(i)==i){
            if(nodes[i]>0){
                bestConn = max(bestConn, nodes[i]);
                if(edges[i] == nodes[i]-1){
                    bestTree = max(bestTree, nodes[i]);
                }
            }
        }
    }
    return {bestTree, bestConn};
}

bool applyMove(vector<int>& board, int& br, int& bc, char mv){
    int d = -1;
    if(mv=='U') d=0;
    else if(mv=='D') d=1;
    else if(mv=='L') d=2;
    else if(mv=='R') d=3;
    if(d==-1) return false;
    int nr = br + dr[d];
    int nc = bc + dc[d];
    if(!inb(nr,nc,N)) return false;
    swap(board[br*N+bc], board[nr*N+nc]);
    br = nr; bc = nc;
    return true;
}

char rev(char c){
    if(c=='U') return 'D';
    if(c=='D') return 'U';
    if(c=='L') return 'R';
    if(c=='R') return 'L';
    return '?';
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> N >> Tlim;
    vector<int> board(N*N);
    int br=-1, bc=-1;
    for(int i=0;i<N;i++){
        string s; cin >> s;
        for(int j=0;j<N;j++){
            char ch = s[j];
            int val;
            if('0'<=ch && ch<='9') val = ch - '0';
            else val = 10 + (ch - 'a');
            board[i*N+j] = val;
            if(val==0){ br=i; bc=j; }
        }
    }

    string ops;
    auto curEval = evaluateS(board);
    int curS = curEval.first;
    int bestConn = curEval.second;
    char last = '?';

    // Greedy local improvement with neutral wandering
    int steps = 0;
    int stagnation = 0;
    const int MAX_STAGNATION = N*N*5; // allow some neutral wandering

    while(steps < Tlim){
        // Evaluate all legal moves
        int bestS = -1;
        int bestConn2 = -1;
        vector<int> idxs;
        vector<pair<int,int>> scores(4, {-1,-1});
        vector<bool> legal(4,false);

        for(int k=0;k<4;k++){
            int nr = br + dr[k];
            int nc = bc + dc[k];
            if(!inb(nr,nc,N)) continue;
            legal[k]=true;
            vector<int> b2 = board;
            int r2 = br, c2 = bc;
            char mv = mvch[k];
            applyMove(b2, r2, c2, mv);
            auto ev = evaluateS(b2);
            scores[k] = ev;
            if(ev.first > bestS || (ev.first==bestS && ev.second > bestConn2)){
                bestS = ev.first;
                bestConn2 = ev.second;
            }
        }

        if(bestS < curS){
            // no non-decreasing move; stop to keep current S
            break;
        }

        // Gather candidates with bestS, bestConn2
        vector<int> cand;
        for(int k=0;k<4;k++){
            if(!legal[k]) continue;
            if(scores[k].first == bestS && scores[k].second == bestConn2){
                cand.push_back(k);
            }
        }
        // Prefer not to immediately reverse
        int chosen = -1;
        for(int k : cand){
            if(last!='?' && mvch[k]==rev(last)) continue;
            chosen = k; break;
        }
        if(chosen==-1 && !cand.empty()) chosen = cand[0];
        if(chosen==-1) {
            // no legal moves? shouldn't happen
            break;
        }

        // Apply chosen
        char mv = mvch[chosen];
        applyMove(board, br, bc, mv);
        ops.push_back(mv);
        steps++;

        if(bestS > curS){
            curS = bestS;
            bestConn = bestConn2;
            stagnation = 0;
        } else {
            stagnation++;
        }
        last = mv;

        if(stagnation > MAX_STAGNATION) break;
        // If already at full tree, we can stop
        if(curS == N*N-1) break;
    }

    cout << ops << '\n';
    return 0;
}