#include <bits/stdc++.h>
using namespace std;

struct Pos { int r,c; };

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n,m;
    if(!(cin>>n>>m)) return 0;
    vector<string> s(n);
    for(int i=0;i<n;i++) cin>>s[i];
    int sr,sc,er,ec;
    cin>>sr>>sc>>er>>ec;
    --sr;--sc;--er;--ec;
    auto inb=[&](int r,int c){return r>=0&&r<n&&c>=0&&c<m;};
    if(s[sr][sc]!='1' || s[er][ec]!='1'){
        cout << -1 << "\n";
        return 0;
    }
    int total=0;
    for(int i=0;i<n;i++) for(int j=0;j<m;j++) if(s[i][j]=='1') total++;

    // connectivity check
    vector<vector<int>> vis(n, vector<int>(m,0));
    queue<Pos> q;
    q.push({sr,sc});
    vis[sr][sc]=1;
    int cnt=1;
    int dr[4]={0,0,-1,1};
    int dc[4]={-1,1,0,0};
    while(!q.empty()){
        auto p=q.front();q.pop();
        for(int k=0;k<4;k++){
            int nr=p.r+dr[k], nc=p.c+dc[k];
            if(inb(nr,nc) && !vis[nr][nc] && s[nr][nc]=='1'){
                vis[nr][nc]=1;
                cnt++;
                q.push({nr,nc});
            }
        }
    }
    if(cnt!=total){
        cout << -1 << "\n";
        return 0;
    }

    auto neighbors = vector<pair<char,Pos>>{
        {'L',{0,-1}},
        {'R',{0,1}},
        {'U',{-1,0}},
        {'D',{1,0}}
    };
    auto sim = [&](const string &moves){
        vector<vector<int>> v(n, vector<int>(m,0));
        int r=sr,c=sc;
        v[r][c]=1;
        int visited=1;
        auto step=[&](char ch){
            int idx = (ch=='L'?0: ch=='R'?1: ch=='U'?2:3);
            int nr=r+neighbors[idx].second.r, nc=c+neighbors[idx].second.c;
            if(inb(nr,nc) && s[nr][nc]=='1'){ r=nr; c=nc; }
            if(!v[r][c]){ v[r][c]=1; visited++; }
        };
        for(char ch: moves) step(ch);
        return tuple<int,int,int>(r,c,visited);
    };

    auto build_path = [&](mt19937 &rng)->string{
        // Greedy covering walk
        vector<vector<int>> seen(n, vector<int>(m,0));
        int r=sr,c=sc;
        seen[r][c]=1;
        int seen_cnt=1;
        string path;
        vector<int> order = {0,1,2,3};
        while(seen_cnt<total){
            shuffle(order.begin(), order.end(), rng);
            bool moved=false;
            for(int idx: order){
                int nr=r+dr[idx], nc=c+dc[idx];
                if(inb(nr,nc) && s[nr][nc]=='1' && !seen[nr][nc]){
                    path.push_back(neighbors[idx].first);
                    r=nr; c=nc;
                    if(!seen[r][c]){ seen[r][c]=1; seen_cnt++; }
                    moved=true;
                    break;
                }
            }
            if(moved) continue;
            // BFS to nearest unvisited cell
            vector<vector<int>> d(n, vector<int>(m,-1));
            vector<vector<pair<int,int>>> par(n, vector<pair<int,int>>(m,{-1,-1}));
            queue<Pos> qq;
            qq.push({r,c});
            d[r][c]=0;
            Pos target={-1,-1};
            while(!qq.empty()){
                auto p=qq.front();qq.pop();
                if(!seen[p.r][p.c]){
                    target=p; break;
                }
                // Prefer cells that have unvisited neighbor
                for(int k=0;k<4;k++){
                    int nr=p.r+dr[k], nc=p.c+dc[k];
                    if(inb(nr,nc) && s[nr][nc]=='1' && d[nr][nc]==-1){
                        d[nr][nc]=d[p.r][p.c]+1;
                        par[nr][nc]={p.r,p.c};
                        qq.push({nr,nc});
                    }
                }
            }
            if(target.r==-1){
                // No unvisited cell in BFS reached: pick cell with unvisited neighbor
                // fallback: search any unvisited cell
                for(int i=0;i<n && target.r==-1;i++){
                    for(int j=0;j<m && target.r==-1;j++){
                        if(s[i][j]=='1' && !seen[i][j]){
                            // run BFS to (i,j)
                            for(int a=0;a<n;a++){ for(int b=0;b<m;b++){ d[a][b]=-1; par[a][b]={-1,-1}; } }
                            queue<Pos> qq2;
                            qq2.push({r,c});
                            d[r][c]=0;
                            while(!qq2.empty()){
                                auto p=qq2.front();qq2.pop();
                                if(p.r==i && p.c==j){ target=p; break; }
                                for(int k=0;k<4;k++){
                                    int nr=p.r+dr[k], nc=p.c+dc[k];
                                    if(inb(nr,nc) && s[nr][nc]=='1' && d[nr][nc]==-1){
                                        d[nr][nc]=d[p.r][p.c]+1;
                                        par[nr][nc]={p.r,p.c};
                                        qq2.push({nr,nc});
                                    }
                                }
                            }
                            if(target.r!=-1) break;
                        }
                    }
                }
                if(target.r==-1){
                    // should not happen due to connectivity
                    break;
                }
            }
            // reconstruct path from (r,c) to target
            vector<pair<int,int>> revp;
            Pos cur=target;
            while(!(cur.r==r && cur.c==c)){
                revp.push_back({cur.r,cur.c});
                auto pr=par[cur.r][cur.c];
                cur={pr.first, pr.second};
            }
            reverse(revp.begin(), revp.end());
            // append moves
            int prr=r, pcc=c;
            for(auto [nr,nc]: revp){
                if(nr==prr && nc==pcc-1) path.push_back('L');
                else if(nr==prr && nc==pcc+1) path.push_back('R');
                else if(nr==prr-1 && nc==pcc) path.push_back('U');
                else if(nr==prr+1 && nc==pcc) path.push_back('D');
                prr=nr; pcc=nc;
                if(!seen[prr][pcc]){ seen[prr][pcc]=1; seen_cnt++; }
            }
            r=prr; c=pcc;
            if((int)path.size() > 500000) break; // keep palindrome under 1e6
        }
        return path;
    };

    auto start_time = chrono::steady_clock::now();
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    string best="";
    // Try multiple random paths
    int iterations = 2000;
    for(int it=0; it<iterations; ++it){
        if(chrono::duration<double>(chrono::steady_clock::now()-start_time).count() > 0.95) break;
        string P = build_path(rng);
        if(P.empty() && total>1) continue;
        if((int)P.size() > 500000) continue;
        // Try centers including none
        vector<char> centers = {'#','L','R','U','D'};
        for(char c: centers){
            string S;
            S.reserve(P.size()*2 + (c=='#'?0:1));
            S += P;
            if(c!='#') S.push_back(c);
            for(int i=(int)P.size()-1;i>=0;i--) S.push_back(P[i]);
            auto [fr,fc,viscount] = sim(S);
            if(viscount==total && fr==er && fc==ec){
                cout << S << "\n";
                return 0;
            }
        }
    }

    cout << -1 << "\n";
    return 0;
}