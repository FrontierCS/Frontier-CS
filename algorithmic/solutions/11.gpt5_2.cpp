#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<string> grid;
    int sr, sc, er, ec;
    int N;
    vector<int> blanks; // list of blank ids
    vector<int> idOf;   // 0..N-1, but only blanks matter
    vector<array<int,4>> nextPos; // nextPos[pos][dir]
    vector<char> dirChar = {'L','R','U','D'};
    int dx[4] = {0, 0, -1, 1};
    int dy[4] = {-1, 1, 0, 0};
    int opp[4] = {1,0,3,2};
    int charToIdx[256];

    int srId, erId;

    Solver() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        memset(charToIdx, -1, sizeof(charToIdx));
        charToIdx['L'] = 0; charToIdx['R'] = 1; charToIdx['U'] = 2; charToIdx['D'] = 3;
    }

    int enc(int r, int c){ return r*m + c; }
    pair<int,int> dec(int id){ return {id/m, id%m}; }

    bool inb(int r,int c){ return r>=0 && r<n && c>=0 && c<m; }

    bool readInput() {
        if(!(cin>>n>>m)) return false;
        grid.resize(n);
        for(int i=0;i<n;i++) cin>>grid[i];
        cin>>sr>>sc>>er>>ec;
        --sr;--sc;--er;--ec;
        N = n*m;
        idOf.resize(N);
        nextPos.assign(N, {0,0,0,0});
        return true;
    }

    bool buildTransitionsAndCheckConn() {
        // Build nextPos and check connectivity from sr
        vector<int> isBlank(N, 0);
        int totalBlank=0;
        for(int r=0;r<n;r++){
            for(int c=0;c<m;c++){
                int id=enc(r,c);
                if(grid[r][c]=='1'){ isBlank[id]=1; totalBlank++; }
            }
        }
        if(!isBlank[enc(sr,sc)] || !isBlank[enc(er,ec)]) return false;

        // Precompute nextPos for all positions (for blanks only meaningful)
        for(int r=0;r<n;r++){
            for(int c=0;c<m;c++){
                int id=enc(r,c);
                for(int d=0;d<4;d++){
                    int nr=r+dx[d], nc=c+dy[d];
                    if(inb(nr,nc) && grid[nr][nc]=='1'){
                        nextPos[id][d]=enc(nr,nc);
                    }else{
                        nextPos[id][d]=id;
                    }
                }
            }
        }
        // BFS connectivity from sr
        vector<int> vis(N,0);
        queue<int>q;
        int sId=enc(sr,sc);
        vis[sId]=1;
        q.push(sId);
        int cnt=1;
        while(!q.empty()){
            int u=q.front(); q.pop();
            for(int d=0;d<4;d++){
                int v=nextPos[u][d];
                if(v!=u && !vis[v]){
                    vis[v]=1;
                    q.push(v);
                    cnt++;
                }
            }
        }
        if(cnt!=totalBlank) return false;

        srId = enc(sr,sc);
        erId = enc(er,ec);
        return true;
    }

    void buildTree_DFS(const array<int,4>& order, vector<int>& parent, vector<char>& moveFromParent, vector<vector<int>>& children) {
        parent.assign(N, -1);
        moveFromParent.assign(N, '?');
        children.assign(N, {});
        vector<int> vis(N, 0);
        function<void(int)> dfs = [&](int u){
            vis[u]=1;
            auto [r,c]=dec(u);
            for(int idx=0; idx<4; idx++){
                int d = order[idx];
                int nr=r+dx[d], nc=c+dy[d];
                if(!inb(nr,nc) || grid[nr][nc]!='1') continue;
                int v=enc(nr,nc);
                if(!vis[v]){
                    parent[v]=u;
                    moveFromParent[v]=dirChar[d];
                    children[u].push_back(v);
                    dfs(v);
                }
            }
        };
        dfs(srId);
    }

    void buildTree_BFS(const array<int,4>& order, vector<int>& parent, vector<char>& moveFromParent, vector<vector<int>>& children) {
        parent.assign(N, -1);
        moveFromParent.assign(N, '?');
        children.assign(N, {});
        vector<int> vis(N, 0);
        queue<int> q;
        vis[srId]=1;
        q.push(srId);
        while(!q.empty()){
            int u=q.front(); q.pop();
            auto [r,c]=dec(u);
            for(int idx=0; idx<4; idx++){
                int d=order[idx];
                int nr=r+dx[d], nc=c+dy[d];
                if(!inb(nr,nc) || grid[nr][nc]!='1') continue;
                int v=enc(nr,nc);
                if(!vis[v]){
                    vis[v]=1;
                    parent[v]=u;
                    moveFromParent[v]=dirChar[d];
                    children[u].push_back(v);
                    q.push(v);
                }
            }
        }
    }

    void buildPathInfo(const vector<int>& parent, vector<int>& nextOnPath, vector<char>& edgeToChildOnPath, vector<char>& oppMove) {
        int cur = erId;
        vector<int> path;
        vector<int> onPath(N, 0);
        while(cur!=-1){
            path.push_back(cur);
            onPath[cur]=1;
            cur = parent[cur];
        }
        nextOnPath.assign(N, -1);
        edgeToChildOnPath.assign(N, '?');
        oppMove.assign(N, '?');
        for(int i=(int)path.size()-1; i>0; --i){
            int u = path[i-1]; // parent
            int v = path[i];   // child
            nextOnPath[u]=v;
        }
    }

    void emitW(int u, const vector<vector<int>>& children, const vector<int>& nextOnPath, const vector<char>& moveFromParent, vector<char>& W) {
        int pathChild = nextOnPath[u];
        // Explore non-path children
        for(int v: children[u]){
            if(v==pathChild) continue;
            char mv = moveFromParent[v];
            W.push_back(mv);
            emitW(v, children, nextOnPath, moveFromParent, W);
            // back to u
            int d = charToIdx[(int)mv];
            W.push_back(dirChar[opp[d]]);
        }
        // Then path child if any
        if(pathChild!=-1){
            char mv = moveFromParent[pathChild];
            W.push_back(mv);
            emitW(pathChild, children, nextOnPath, moveFromParent, W);
            // do not go back
        }
    }

    int runSeqFrom(int startPos, const vector<char>& S) {
        int pos = startPos;
        for(char ch: S){
            int d = charToIdx[(int)ch];
            pos = nextPos[pos][d];
        }
        return pos;
    }

    int runPalFromER(const vector<char>& T) {
        int pos = erId;
        for(char ch: T){
            int d = charToIdx[(int)ch];
            pos = nextPos[pos][d];
        }
        for(int i=(int)T.size()-1;i>=0;i--){
            int d = charToIdx[(int)T[i]];
            pos = nextPos[pos][d];
        }
        return pos;
    }

    bool tryWithTree(const array<int,4>& order, bool useDFS, vector<char>& outS) {
        vector<int> parent;
        vector<char> moveFromParent;
        vector<vector<int>> children;
        if(useDFS) buildTree_DFS(order, parent, moveFromParent, children);
        else buildTree_BFS(order, parent, moveFromParent, children);

        // If er not reached by tree (shouldn't happen if connected), return false
        if(parent[erId]==-1 && erId!=srId) return false;

        // Build path info
        vector<int> nextOnPath;
        vector<char> edgeToChildOnPath, oppMove;
        buildPathInfo(parent, nextOnPath, edgeToChildOnPath, oppMove);

        // Emit W
        vector<char> W;
        emitW(srId, children, nextOnPath, moveFromParent, W);

        // Precompute g(x) = run reverse(W) from x
        vector<char> Wrev = W;
        reverse(Wrev.begin(), Wrev.end());
        vector<int> gDest(N, -1);
        // Only consider blanks: but running from non-blank not used. We'll skip positions which are blocked by leaving -1.
        for(int r=0;r<n;r++){
            for(int c=0;c<m;c++){
                if(grid[r][c]!='1') continue;
                int x = enc(r,c);
                gDest[x] = runSeqFrom(x, Wrev);
            }
        }
        // Build P_set: g(x) == erId
        vector<char> isTarget(N, 0);
        for(int r=0;r<n;r++){
            for(int c=0;c<m;c++){
                if(grid[r][c]!='1') continue;
                int x=enc(r,c);
                if(gDest[x]==erId) isTarget[x]=1;
            }
        }

        // BFS over states s = result of palindrome T from er
        vector<int> parentState(N, -1);
        vector<char> parentMoveState(N, '?');
        vector<char> visited(N, 0);
        queue<int> q;
        visited[erId]=1;
        parentState[erId]=-1;
        q.push(erId);

        auto reconstructT = [&](int s)->vector<char>{
            vector<char> tmp;
            int cur=s;
            while(parentState[cur]!=-1){
                tmp.push_back(parentMoveState[cur]);
                cur = parentState[cur];
            }
            reverse(tmp.begin(), tmp.end());
            return tmp;
        };

        // If er itself is target (i.e., reverse(W) from er returns er), T can be empty
        if(isTarget[erId]){
            vector<char> T; // empty
            outS.clear();
            outS.reserve(W.size()*2);
            outS.insert(outS.end(), W.begin(), W.end());
            // T + reverse(T): nothing
            outS.insert(outS.end(), Wrev.begin(), Wrev.end());
            return true;
        }

        bool found=false;
        int foundState=-1;
        while(!q.empty()){
            int s = q.front(); q.pop();
            // reconstruct T for s once
            vector<char> T = reconstructT(s);
            // Try all 4 moves
            for(int d=0; d<4; d++){
                T.push_back(dirChar[d]);
                int ns = runPalFromER(T);
                T.pop_back();
                if(ns<0) continue;
                if(!visited[ns]){
                    visited[ns]=1;
                    parentState[ns]=s;
                    parentMoveState[ns]=dirChar[d];
                    if(isTarget[ns]){
                        found=true;
                        foundState=ns;
                        break;
                    }
                    q.push(ns);
                }
            }
            if(found) break;
        }

        if(!found) return false;

        // Reconstruct T from foundState
        vector<char> T = reconstructT(foundState);

        // Compose final S = W + T + reverse(T) + reverse(W)
        vector<char> Trev = T;
        reverse(Trev.begin(), Trev.end());
        outS.clear();
        outS.reserve(W.size() + T.size() + Trev.size() + Wrev.size());
        outS.insert(outS.end(), W.begin(), W.end());
        outS.insert(outS.end(), T.begin(), T.end());
        outS.insert(outS.end(), Trev.begin(), Trev.end());
        outS.insert(outS.end(), Wrev.begin(), Wrev.end());

        // Safety: ensure length <= 1e6
        if(outS.size()>1000000u) return false;

        // Optional: verify correctness by simulating and coverage? We assume W covers all.
        return true;
    }

    void solve() {
        if(!buildTransitionsAndCheckConn()){
            cout << "-1\n";
            return;
        }

        vector<array<int,4>> perms;
        array<int,4> base = {0,1,2,3};
        sort(base.begin(), base.end());
        do {
            perms.push_back(base);
        } while(next_permutation(base.begin(), base.end()));

        vector<char> answer;
        bool ok=false;

        // Try DFS-based trees with different neighbor orders
        for(auto &perm : perms){
            if(tryWithTree(perm, true, answer)){
                ok=true; break;
            }
        }
        // If not found, try BFS-based trees
        if(!ok){
            for(auto &perm : perms){
                if(tryWithTree(perm, false, answer)){
                    ok=true; break;
                }
            }
        }

        if(!ok){
            cout << "-1\n";
            return;
        }

        // Output answer
        if(answer.empty()){
            cout << "\n";
        }else{
            for(char c: answer) cout << c;
            cout << "\n";
        }
    }
};

int main(){
    Solver solver;
    if(!solver.readInput()) return 0;
    solver.solve();
    return 0;
}