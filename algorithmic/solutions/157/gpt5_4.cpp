#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n=0): n(n), p(n), sz(n,1) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x? x : p[x]=find(p[x]); }
    void unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a;
        sz[a]+=sz[b];
    }
};

struct Score {
    int largestTree;
    int matchedEdges;
};

int N;
long long Tlim;
vector<vector<int>> board;
int br, bc;

inline int hexval(char c){
    if('0'<=c && c<='9') return c-'0';
    if('a'<=c && c<='f') return 10+(c-'a');
    if('A'<=c && c<='F') return 10+(c-'A');
    return 0;
}

inline bool validMove(char m){
    if(m=='U') return br>0;
    if(m=='D') return br<N-1;
    if(m=='L') return bc>0;
    if(m=='R') return bc<N-1;
    return false;
}

inline void doMove(char m){
    if(m=='U'){
        swap(board[br][bc], board[br-1][bc]);
        br--;
    }else if(m=='D'){
        swap(board[br][bc], board[br+1][bc]);
        br++;
    }else if(m=='L'){
        swap(board[br][bc], board[br][bc-1]);
        bc--;
    }else if(m=='R'){
        swap(board[br][bc], board[br][bc+1]);
        bc++;
    }
}

inline char opposite(char m){
    if(m=='U') return 'D';
    if(m=='D') return 'U';
    if(m=='L') return 'R';
    if(m=='R') return 'L';
    return '?';
}

Score computeScore(){
    int total = N*N;
    DSU uf(total);
    auto id = [&](int r,int c){ return r*N + c; };
    // Unite matching edges
    for(int i=0;i<N-1;i++){
        for(int j=0;j<N;j++){
            int a = board[i][j];
            int b = board[i+1][j];
            if(a!=0 && b!=0 && (a&8) && (b&2)){
                uf.unite(id(i,j), id(i+1,j));
            }
        }
    }
    for(int i=0;i<N;i++){
        for(int j=0;j<N-1;j++){
            int a = board[i][j];
            int b = board[i][j+1];
            if(a!=0 && b!=0 && (a&4) && (b&1)){
                uf.unite(id(i,j), id(i,j+1));
            }
        }
    }
    vector<int> vc(total,0), ec(total,0);
    // Count vertices per component (excluding blank)
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            int a = board[i][j];
            if(a!=0){
                int r = uf.find(id(i,j));
                vc[r]++;
            }
        }
    }
    int matchedEdges = 0;
    // Count edges per component
    for(int i=0;i<N-1;i++){
        for(int j=0;j<N;j++){
            int a = board[i][j];
            int b = board[i+1][j];
            if(a!=0 && b!=0 && (a&8) && (b&2)){
                int r = uf.find(id(i,j));
                ec[r]++;
                matchedEdges++;
            }
        }
    }
    for(int i=0;i<N;i++){
        for(int j=0;j<N-1;j++){
            int a = board[i][j];
            int b = board[i][j+1];
            if(a!=0 && b!=0 && (a&4) && (b&1)){
                int r = uf.find(id(i,j));
                ec[r]++;
                matchedEdges++;
            }
        }
    }
    int bestTree = 0;
    for(int i=0;i<total;i++){
        if(uf.find(i)==i){
            if(vc[i] >= 1 && ec[i] == vc[i]-1){
                if(vc[i] > bestTree) bestTree = vc[i];
            }
        }
    }
    return {bestTree, matchedEdges};
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if(!(cin>>N>>Tlim)) return 0;
    board.assign(N, vector<int>(N));
    br = bc = -1;
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            char ch; 
            cin >> ch;
            int v = hexval(ch);
            board[i][j] = v;
            if(v==0){ br=i; bc=j; }
        }
    }

    // Random engine
    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_real_distribution<double> ur(0.0,1.0);

    string ops;
    ops.reserve((size_t)Tlim);

    Score bestScore = computeScore();
    int bestK = 0;

    char last = 0;

    for(long long step=0; step<Tlim; ++step){
        vector<char> cand;
        const char dirs[4] = {'U','D','L','R'};
        for(char m: dirs){
            if(!validMove(m)) continue;
            if(last && m==opposite(last)) continue;
            cand.push_back(m);
        }
        if(cand.empty()){
            // If no non-reverse move, allow reverse
            for(char m: dirs){
                if(validMove(m)) cand.push_back(m);
            }
            if(cand.empty()) break; // should not happen
        }

        bool chooseRandom = (ur(rng) < (0.2 * (double)(Tlim - step) / (double)Tlim));
        char chosen = cand[0];
        Score chosenScore = {-1,-1};

        if(!chooseRandom){
            // Greedy select best next move
            for(char m: cand){
                doMove(m);
                Score sc = computeScore();
                // pick better: larger tree, then more matched edges
                if(sc.largestTree > chosenScore.largestTree ||
                   (sc.largestTree == chosenScore.largestTree && sc.matchedEdges > chosenScore.matchedEdges)){
                    chosenScore = sc;
                    chosen = m;
                }
                // undo
                doMove(opposite(m));
            }
        } else {
            chosen = cand[rng()%cand.size()];
        }

        doMove(chosen);
        ops.push_back(chosen);
        last = chosen;

        Score cur = computeScore();
        if(cur.largestTree > bestScore.largestTree ||
           (cur.largestTree == bestScore.largestTree && cur.matchedEdges > bestScore.matchedEdges)){
            bestScore = cur;
            bestK = (int)ops.size();
        }
    }

    if(bestK < 0 || bestK > (int)ops.size()) bestK = (int)ops.size();
    cout << string(ops.begin(), ops.begin()+bestK) << '\n';
    return 0;
}