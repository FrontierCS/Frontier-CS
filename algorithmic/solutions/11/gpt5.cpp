#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;

const int DL = 0, DR = 1, DU = 2, DD = 3;
const int dirs[4][2] = {{0,-1},{0,1},{-1,0},{1,0}};
const char dirChar[4] = {'L','R','U','D'};
int opp[4] = {DR, DL, DD, DU};

int V;
vector<int> idOf; // size n*m, -1 if blocked
vector<pair<int,int>> coord; // id -> (r,c)
vector<array<int,4>> toMove; // toMove[id][dir] -> id'

inline int getId(int r, int c){
    if(r<0||r>=n||c<0||c>=m) return -1;
    return idOf[r*m + c];
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin>>n>>m)) return 0;
    grid.resize(n);
    for(int i=0;i<n;i++) cin>>grid[i];
    cin>>sr>>sc>>er>>ec;
    --sr; --sc; --er; --ec;

    idOf.assign(n*m, -1);
    V = 0;
    coord.clear(); coord.reserve(n*m);
    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            if(grid[i][j]=='1'){
                idOf[i*m+j] = V++;
                coord.emplace_back(i,j);
            }
        }
    }
    if(idOf[sr*m+sc] == -1 || idOf[er*m+ec] == -1){
        cout << -1 << '\n';
        return 0;
    }
    int sid = idOf[sr*m+sc];
    int eid = idOf[er*m+ec];

    // Precompute toMove
    toMove.assign(V, {0,0,0,0});
    for(int id=0; id<V; ++id){
        int r = coord[id].first;
        int c = coord[id].second;
        for(int d=0; d<4; ++d){
            int nr = r + dirs[d][0];
            int nc = c + dirs[d][1];
            int nid = getId(nr,nc);
            if(nid==-1) nid = id;
            toMove[id][d] = nid;
        }
    }

    // Connectivity check
    vector<int> q;
    vector<char> vis(V, 0);
    q.reserve(V);
    q.push_back(sid);
    vis[sid] = 1;
    for(size_t qi=0; qi<q.size(); ++qi){
        int u = q[qi];
        for(int d=0; d<4; ++d){
            int v = toMove[u][d];
            if(v!=u && !vis[v]){
                vis[v] = 1;
                q.push_back(v);
            }
        }
    }
    if((int)q.size() != V || !vis[eid]){
        cout << -1 << '\n';
        return 0;
    }

    // Build DFS tree path visiting all nodes and returning to s
    vector<char> used(V, 0);
    string pathA;
    pathA.reserve(2*V);
    function<void(int)> dfs = [&](int u){
        used[u] = 1;
        // Order of directions can be fixed
        static int order[4] = {DU, DL, DD, DR}; // U, L, D, R (arbitrary)
        for(int k=0;k<4;k++){
            int d = order[k];
            int v = toMove[u][d];
            if(v!=u && !used[v]){
                pathA.push_back(dirChar[d]);
                dfs(v);
                pathA.push_back(dirChar[opp[d]]);
            }
        }
    };
    dfs(sid);

    // BFS shortest path from s to e
    vector<int> parent(V, -1);
    vector<int> parentDir(V, -1);
    queue<int> qu;
    vector<char> seen(V, 0);
    qu.push(sid);
    seen[sid]=1;
    while(!qu.empty()){
        int u = qu.front(); qu.pop();
        if(u==eid) break;
        for(int d=0; d<4; ++d){
            int v = toMove[u][d];
            if(v!=u && !seen[v]){
                seen[v]=1;
                parent[v]=u;
                parentDir[v]=d;
                qu.push(v);
            }
        }
    }
    string pathB;
    if(!seen[eid]){
        cout << -1 << '\n';
        return 0;
    } else {
        vector<char> rev;
        int cur=eid;
        while(cur!=sid){
            int pd = parentDir[cur];
            rev.push_back(dirChar[pd]);
            cur = parent[cur];
        }
        reverse(rev.begin(), rev.end());
        pathB.assign(rev.begin(), rev.end());
    }

    string Q = pathA + pathB;

    // Verify p0 after Q is eid
    auto apply_seq = [&](int startId, const string &seq)->int{
        int id = startId;
        for(char ch: seq){
            int d;
            if(ch=='L') d=DL; else if(ch=='R') d=DR; else if(ch=='U') d=DU; else d=DD;
            id = toMove[id][d];
        }
        return id;
    };
    int p0 = apply_seq(sid, Q);
    if(p0 != eid){
        // Shouldn't happen, but safety
        // Try to fix by adding explicit shortest path from current to eid
        // However for correctness, we will check and if fails, output -1
        // But usually p0==eid
        // Attempt to compute path from p0 to eid
        vector<int> par2(V,-1), pdir2(V,-1);
        queue<int> qu2;
        vector<char> seen2(V,0);
        qu2.push(p0); seen2[p0]=1;
        while(!qu2.empty()){
            int u=qu2.front(); qu2.pop();
            if(u==eid) break;
            for(int d=0;d<4;d++){
                int v=toMove[u][d];
                if(v!=u && !seen2[v]){
                    seen2[v]=1; par2[v]=u; pdir2[v]=d; qu2.push(v);
                }
            }
        }
        if(!seen2[eid]){
            cout << -1 << '\n';
            return 0;
        }
        vector<char> rev;
        int cur=eid;
        while(cur!=p0){
            rev.push_back(dirChar[pdir2[cur]]);
            cur = par2[cur];
        }
        reverse(rev.begin(), rev.end());
        string extra(rev.begin(), rev.end());
        Q += extra;
        p0 = apply_seq(sid, Q);
        if(p0!=eid){
            cout << -1 << '\n';
            return 0;
        }
    }

    string Qrev(Q.rbegin(), Q.rend());

    // Precompute Y_map[x] = apply reverse(Q) from x
    vector<int> Y_map(V);
    for(int x=0;x<V;x++){
        Y_map[x] = apply_seq(x, Qrev);
    }

    vector<char> preimage(V, 0);
    vector<int> preList; preList.reserve(V);
    for(int x=0;x<V;x++){
        if(Y_map[x]==eid){
            preimage[x]=1;
            preList.push_back(x);
        }
    }

    // Distance from p0 to all for sorting preList
    vector<int> distAll(V, -1);
    {
        queue<int> qq;
        distAll[p0]=0; qq.push(p0);
        while(!qq.empty()){
            int u=qq.front(); qq.pop();
            for(int d=0;d<4;d++){
                int v=toMove[u][d];
                if(v!=u && distAll[v]==-1){
                    distAll[v]=distAll[u]+1;
                    qq.push(v);
                }
            }
        }
        sort(preList.begin(), preList.end(), [&](int a, int b){
            int da = distAll[a]==-1?INT_MAX:distAll[a];
            int db = distAll[b]==-1?INT_MAX:distAll[b];
            if(da!=db) return da<db;
            return a<b;
        });
    }

    auto apply_moves = [&](int startId, const vector<int> &moves)->int{
        int id = startId;
        for(int d: moves) id = toMove[id][d];
        return id;
    };
    auto apply_reverse_moves = [&](int startId, const vector<int> &moves)->int{
        int id = startId;
        for(int i=(int)moves.size()-1;i>=0;i--){
            id = toMove[id][moves[i]];
        }
        return id;
    };

    auto test_R = [&](const vector<int>& R, int center)->pair<bool,pair<vector<int>,int>>{
        int posAfterR = apply_moves(p0, R);
        // even palindrome
        int evenEnd = apply_reverse_moves(posAfterR, R);
        if(preimage[evenEnd]){
            return {true, {R, -1}};
        }
        // odd with center char
        if(center==-2){
            for(int c=0;c<4;c++){
                int midPos = toMove[posAfterR][c];
                int finalx = apply_reverse_moves(midPos, R);
                if(preimage[finalx]){
                    return {true, {R, c}};
                }
            }
        } else if(center>=0 && center<4){
            int midPos = toMove[posAfterR][center];
            int finalx = apply_reverse_moves(midPos, R);
            if(preimage[finalx]){
                return {true, {R, center}};
            }
        }
        return {false, {}};
    };

    vector<int> Rfound;
    int centerFound = -1;
    bool found = false;

    auto finish_and_print = [&](const vector<int>& R, int center)->void{
        string H = Q;
        H.reserve(Q.size() + R.size());
        for(int d: R) H.push_back(dirChar[d]);
        string M;
        if(center==-1){
            M.reserve(2*H.size());
            M += H;
            for(int i=(int)H.size()-1;i>=0;i--) M.push_back(H[i]);
        }else{
            M.reserve(2*H.size()+1);
            M += H;
            M.push_back(dirChar[center]);
            for(int i=(int)H.size()-1;i>=0;i--) M.push_back(H[i]);
        }
        if(M.size() > 1000000u){
            cout << -1 << '\n';
        }else{
            cout << M << '\n';
        }
    };

    // Stage 1: Empty R
    {
        vector<int> R;
        auto res = test_R(R, -2);
        if(res.first){
            Rfound = res.second.first;
            centerFound = res.second.second;
            finish_and_print(Rfound, centerFound);
            return 0;
        }
    }

    // Stage 2: single direction repeats
    int T1 = max(n, m);
    for(int d=0; d<4 && !found; ++d){
        for(int t=1; t<=T1 && !found; ++t){
            vector<int> R(t, d);
            auto res = test_R(R, -2);
            if(res.first){
                found = true;
                Rfound = res.second.first; centerFound = res.second.second;
                finish_and_print(Rfound, centerFound);
                return 0;
            }
        }
    }

    // Stage 3: two-direction patterns
    vector<pair<int,int>> pairs = {
        {DL, DU}, {DU, DL}, {DR, DD}, {DD, DR},
        {DL, DD}, {DD, DL}, {DR, DU}, {DU, DR}
    };
    for(auto pr: pairs){
        int d1=pr.first, d2=pr.second;
        int lim1 = (d1==DU||d1==DD)? n : m;
        int lim2 = (d2==DU||d2==DD)? n : m;
        lim1 = min(lim1, 30);
        lim2 = min(lim2, 30);
        for(int t1=1; t1<=lim1 && !found; ++t1){
            for(int t2=1; t2<=lim2 && !found; ++t2){
                vector<int> R; R.reserve(t1+t2);
                R.insert(R.end(), t1, d1);
                R.insert(R.end(), t2, d2);
                auto res = test_R(R, -2);
                if(res.first){
                    found = true;
                    Rfound = res.second.first; centerFound = res.second.second;
                    finish_and_print(Rfound, centerFound);
                    return 0;
                }
            }
        }
        if(found) break;
    }

    // Stage 4: swirl patterns
    auto try_swirl = [&](int k)->bool{
        vector<int> order = {DL, DU, DR, DD}; // L,U,R,D
        int limH = min(m, 30), limV = min(n, 30);
        vector<int> R;
        R.reserve( (limH+limV)*k*2 );
        for(int i=0;i<k;i++){
            R.insert(R.end(), limH, DL);
            R.insert(R.end(), limV, DU);
            R.insert(R.end(), limH, DR);
            R.insert(R.end(), limV, DD);
        }
        auto res = test_R(R, -2);
        if(res.first){
            finish_and_print(res.second.first, res.second.second);
            return true;
        }
        return false;
    };
    for(int k=1;k<=5 && !found;k++){
        if(try_swirl(k)){ return 0; }
    }

    // Stage 5: BFS to each preimage z with small pads
    // Precompute BFS parents from p0 for each z as needed
    auto bfs_path = [&](int start, int target)->vector<int>{
        if(start==target) return {};
        vector<int> par(V, -1), pdir(V, -1);
        queue<int> qu2;
        vector<char> seen2(V, 0);
        seen2[start]=1; qu2.push(start);
        while(!qu2.empty()){
            int u=qu2.front(); qu2.pop();
            if(u==target) break;
            for(int d=0; d<4; ++d){
                int v=toMove[u][d];
                if(v!=u && !seen2[v]){
                    seen2[v]=1;
                    par[v]=u; pdir[v]=d; qu2.push(v);
                }
            }
        }
        vector<int> path;
        if(par[target]==-1 && start!=target) return path;
        int cur=target;
        vector<int> tmp;
        while(cur!=start){
            tmp.push_back(pdir[cur]);
            cur = par[cur];
        }
        reverse(tmp.begin(), tmp.end());
        path = tmp;
        return path;
    };

    int padLim = 10;
    for(size_t idx=0; idx<preList.size() && !found; ++idx){
        int z = preList[idx];
        vector<int> path = bfs_path(p0, z);
        if(path.empty() && p0!=z) continue;
        // try just path
        {
            auto res = test_R(path, -2);
            if(res.first){
                finish_and_print(res.second.first, res.second.second);
                return 0;
            }
        }
        // try with small pads
        for(int d=0; d<4 && !found; ++d){
            for(int t=1; t<=padLim && !found; ++t){
                vector<int> R = path;
                R.insert(R.end(), t, d);
                auto res = test_R(R, -2);
                if(res.first){
                    finish_and_print(res.second.first, res.second.second);
                    return 0;
                }
            }
        }
        // try path + two-direction pad
        for(auto pr: pairs){
            int d1=pr.first, d2=pr.second;
            for(int t1=1; t1<=5 && !found; ++t1){
                for(int t2=1; t2<=5 && !found; ++t2){
                    vector<int> R = path;
                    R.insert(R.end(), t1, d1);
                    R.insert(R.end(), t2, d2);
                    auto res = test_R(R, -2);
                    if(res.first){
                        finish_and_print(res.second.first, res.second.second);
                        return 0;
                    }
                }
            }
        }
    }

    // Stage 6: Random sequences
    mt19937 rng((uint32_t)(sr*131 + sc*733 + er*917 + ec*239 + V*997 + 1234567));
    auto rand_int = [&](int l, int r)->int{
        uniform_int_distribution<int> dist(l,r);
        return dist(rng);
    };
    int randomTries = 6000;
    for(int attempt=0; attempt<randomTries; ++attempt){
        int lenType = rand_int(0, 2);
        vector<int> R;
        if(lenType==0){
            int L = rand_int(10, 60);
            R.resize(L);
            for(int i=0;i<L;i++) R[i] = rand_int(0,3);
        } else if(lenType==1){
            // random macro: dir repeated
            int d = rand_int(0,3);
            int t = rand_int(1, max(5, (d==DU||d==DD)? n : m));
            R.assign(t, d);
        } else {
            // two-dir macro
            int d1 = rand_int(0,3), d2 = rand_int(0,3);
            int t1 = rand_int(1, min(10, (d1==DU||d1==DD)? n : m));
            int t2 = rand_int(1, min(10, (d2==DU||d2==DD)? n : m));
            R.reserve(t1+t2);
            R.insert(R.end(), t1, d1);
            R.insert(R.end(), t2, d2);
        }
        auto res = test_R(R, -2);
        if(res.first){
            finish_and_print(res.second.first, res.second.second);
            return 0;
        }
    }

    // As a last attempt, try longer random sequences
    randomTries = 4000;
    for(int attempt=0; attempt<randomTries; ++attempt){
        int L = rand_int(100, 300);
        vector<int> R(L);
        for(int i=0;i<L;i++) R[i] = rand_int(0,3);
        auto res = test_R(R, -2);
        if(res.first){
            finish_and_print(res.second.first, res.second.second);
            return 0;
        }
    }

    // If still not found, output -1
    cout << -1 << '\n';
    return 0;
}