#include <bits/stdc++.h>
using namespace std;

struct Score {
    int largestTreeSize;
    int totalMatchedEdges;
    int largestCompSize;
};

static inline bool inb(int r, int c, int N){ return (0<=r && r<N && 0<=c && c<N); }

Score evaluate(const vector<vector<int>>& g, int N, int er, int ec){
    int totalEdges = 0;
    // count total matched edges
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            if(g[i][j]==0) continue;
            if(i+1<N && g[i+1][j]!=0){
                if( (g[i][j]&8) && (g[i+1][j]&2) ) totalEdges++;
            }
            if(j+1<N && g[i][j]!=0 && g[i][j+1]!=0){
                if( (g[i][j]&4) && (g[i][j+1]&1) ) totalEdges++;
            }
        }
    }
    int NN = N*N;
    vector<char> vis(NN, 0);
    auto id = [&](int r,int c){return r*N + c;};
    int largestTree = 0;
    int largestComp = 0;
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            if(g[i][j]==0) continue;
            int u = id(i,j);
            if(vis[u]) continue;
            // BFS
            int nodes = 0;
            long long edgeHalf = 0;
            queue<pair<int,int>> q;
            vis[u] = 1;
            q.push({i,j});
            while(!q.empty()){
                auto [r,c] = q.front(); q.pop();
                nodes++;
                // check neighbors with matched edges
                // up
                if(r-1>=0 && g[r-1][c]!=0){
                    if( (g[r][c]&2) && (g[r-1][c]&8) ){
                        edgeHalf++;
                        int v = id(r-1,c);
                        if(!vis[v]){
                            vis[v]=1;
                            q.push({r-1,c});
                        }
                    }
                }
                // down
                if(r+1<N && g[r+1][c]!=0){
                    if( (g[r][c]&8) && (g[r+1][c]&2) ){
                        edgeHalf++;
                        int v = id(r+1,c);
                        if(!vis[v]){
                            vis[v]=1;
                            q.push({r+1,c});
                        }
                    }
                }
                // left
                if(c-1>=0 && g[r][c-1]!=0){
                    if( (g[r][c]&1) && (g[r][c-1]&4) ){
                        edgeHalf++;
                        int v = id(r,c-1);
                        if(!vis[v]){
                            vis[v]=1;
                            q.push({r,c-1});
                        }
                    }
                }
                // right
                if(c+1<N && g[r][c+1]!=0){
                    if( (g[r][c]&4) && (g[r][c+1]&1) ){
                        edgeHalf++;
                        int v = id(r,c+1);
                        if(!vis[v]){
                            vis[v]=1;
                            q.push({r,c+1});
                        }
                    }
                }
            }
            int edges = (int)(edgeHalf/2);
            largestComp = max(largestComp, nodes);
            if(edges == nodes-1){
                largestTree = max(largestTree, nodes);
            }
        }
    }
    return Score{largestTree, totalEdges, largestComp};
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    int T;
    if(!(cin>>N>>T)) {
        cout<<"\n";
        return 0;
    }
    vector<vector<int>> g(N, vector<int>(N));
    int er=-1, ec=-1;
    for(int i=0;i<N;i++){
        string s; cin>>s;
        for(int j=0;j<N;j++){
            char c = s[j];
            int v;
            if('0'<=c && c<='9') v = c-'0';
            else v = 10 + (c-'a');
            g[i][j] = v;
            if(v==0){ er=i; ec=j; }
        }
    }

    // Random engine
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    auto eval0 = evaluate(g,N,er,ec);
    int bestS = eval0.largestTreeSize;
    int bestE = eval0.totalMatchedEdges;
    vector<char> bestMoves; bestMoves.reserve(T);
    vector<char> moves; moves.reserve(100000); // exploration not bounded by T
    char lastMove = 0;

    auto applyMove = [&](char mv){
        if(mv=='U'){ // move tile above into empty
            swap(g[er][ec], g[er-1][ec]); er--;
        }else if(mv=='D'){
            swap(g[er][ec], g[er+1][ec]); er++;
        }else if(mv=='L'){
            swap(g[er][ec], g[er][ec-1]); ec--;
        }else if(mv=='R'){
            swap(g[er][ec], g[er][ec+1]); ec++;
        }
    };
    auto undoMove = [&](char mv){
        // inverse
        if(mv=='U') applyMove('D');
        else if(mv=='D') applyMove('U');
        else if(mv=='L') applyMove('R');
        else if(mv=='R') applyMove('L');
    };

    auto opposite = [&](char mv)->char{
        if(mv=='U') return 'D';
        if(mv=='D') return 'U';
        if(mv=='L') return 'R';
        if(mv=='R') return 'L';
        return 0;
    };

    // Time limit management
    const double TIME_LIMIT = 1.9; // seconds
    auto time_start = chrono::high_resolution_clock::now();

    // Main exploration loop
    while(true){
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - time_start).count();
        if(elapsed > TIME_LIMIT) break;

        // If we already have perfect tree, stop
        if(bestS == N*N - 1) break;

        // build candidate moves
        vector<char> cand;
        if(er-1>=0) cand.push_back('U');
        if(er+1<N)  cand.push_back('D');
        if(ec-1>=0) cand.push_back('L');
        if(ec+1<N)  cand.push_back('R');

        // avoid immediate backtracking if possible
        if(lastMove){
            char opp = opposite(lastMove);
            if(cand.size()>=2){
                // erase opp from cand
                vector<char> tmp;
                for(char mv: cand) if(mv!=opp) tmp.push_back(mv);
                if(!tmp.empty()) cand.swap(tmp);
            }
        }

        if(cand.empty()) break;

        // Randomness chance
        bool randomMove = (uniform_real_distribution<double>(0.0,1.0)(rng) < 0.10);

        char chosen = cand[uniform_int_distribution<int>(0,(int)cand.size()-1)(rng)];
        if(!randomMove){
            // evaluate each candidate
            int bestLocalS = -1;
            int bestLocalE = -1;
            int bestLocalC = -1;
            vector<char> bestSet;
            for(char mv : cand){
                applyMove(mv);
                Score sc = evaluate(g,N,er,ec);
                undoMove(mv);
                // lexicographic compare: S, E, largestComp
                if(sc.largestTreeSize > bestLocalS ||
                   (sc.largestTreeSize == bestLocalS && sc.totalMatchedEdges > bestLocalE) ||
                   (sc.largestTreeSize == bestLocalS && sc.totalMatchedEdges == bestLocalE && sc.largestCompSize > bestLocalC)) {
                    bestLocalS = sc.largestTreeSize;
                    bestLocalE = sc.totalMatchedEdges;
                    bestLocalC = sc.largestCompSize;
                    bestSet.clear();
                    bestSet.push_back(mv);
                } else if(sc.largestTreeSize == bestLocalS && sc.totalMatchedEdges == bestLocalE && sc.largestCompSize == bestLocalC){
                    bestSet.push_back(mv);
                }
            }
            chosen = bestSet[uniform_int_distribution<int>(0,(int)bestSet.size()-1)(rng)];
        }

        // apply chosen
        applyMove(chosen);
        moves.push_back(chosen);
        lastMove = chosen;

        // update best if improved and within T
        if((int)moves.size() <= T){
            Score scNow = evaluate(g,N,er,ec);
            if(scNow.largestTreeSize > bestS ||
               (scNow.largestTreeSize == bestS && scNow.totalMatchedEdges > bestE)) {
                bestS = scNow.largestTreeSize;
                bestE = scNow.totalMatchedEdges;
                bestMoves = moves;
                if(bestS == N*N - 1) break;
            }
        }
    }

    // Output bestMoves (ensure not exceeding T)
    if((int)bestMoves.size() > T){
        bestMoves.resize(T);
    }
    string out(bestMoves.begin(), bestMoves.end());
    cout << out << "\n";
    return 0;
}