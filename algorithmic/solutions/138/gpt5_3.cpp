#include <bits/stdc++.h>
using namespace std;

struct Preset {
    int n, m;
    vector<string> a;
    array<int,62> cnt;
};

int idOf(char c){
    if('a'<=c && c<='z') return c-'a';
    if('A'<=c && c<='Z') return 26 + (c-'A');
    if('0'<=c && c<='9') return 52 + (c-'0');
    return -1;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n,m,k;
    if(!(cin>>n>>m>>k)) return 0;
    vector<string> cur(n), target(n);
    for(int i=0;i<n;i++) cin>>cur[i];
    for(int i=0;i<n;i++) cin>>target[i];

    vector<Preset> P(k);
    for(int p=0;p<k;p++){
        int np, mp;
        cin>>np>>mp;
        P[p].n=np; P[p].m=mp;
        P[p].a.resize(np);
        for(int i=0;i<np;i++) cin>>P[p].a[i];
        P[p].cnt.fill(0);
        for(int i=0;i<np;i++)
            for(int j=0;j<mp;j++)
                P[p].cnt[idOf(P[p].a[i][j])]++;
    }

    // counts
    array<int,62> cntCur{}, cntTar{};
    cntCur.fill(0); cntTar.fill(0);
    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            cntCur[idOf(cur[i][j])]++;
            cntTar[idOf(target[i][j])]++;
        }
    }

    // check if impossible to create needed chars at all
    array<int,62> canCreate{};
    canCreate.fill(0);
    for(int p=0;p<k;p++){
        for(int c=0;c<62;c++){
            if(P[p].cnt[c]>0) canCreate[c]=1;
        }
    }
    for(int c=0;c<62;c++){
        if(cntTar[c] > cntCur[c] && !canCreate[c]){
            cout << -1 << "\n";
            return 0;
        }
    }

    vector<array<int,3>> ops; // {op, x, y} 1-based
    const int MAX_PRESETS = 400;
    auto buildDef = [&](array<int,62>& def){
        for(int c=0;c<62;c++) def[c]=cntTar[c]-cntCur[c];
    };

    auto buildPref = [&](vector< vector< array<int,62> > > &pref){
        pref.assign(n+1, vector<array<int,62>>(m+1));
        for(int i=0;i<=n;i++)
            for(int j=0;j<=m;j++)
                pref[i][j].fill(0);
        for(int i=1;i<=n;i++){
            for(int j=1;j<=m;j++){
                for(int c=0;c<62;c++){
                    pref[i][j][c] = pref[i-1][j][c] + pref[i][j-1][c] - pref[i-1][j-1][c];
                }
                int id = idOf(cur[i-1][j-1]);
                pref[i][j][id] += 1;
            }
        }
    };
    auto getRectCount = [&](vector< vector< array<int,62> > > &pref, int x1,int y1,int x2,int y2, array<int,62>& out){
        // x1,y1,x2,y2 are 0-based inclusive
        int a=x1+1, b=y1+1, c=x2+1, d=y2+1;
        for(int t=0;t<62;t++){
            out[t] = pref[c][d][t] - pref[a-1][d][t] - pref[c][b-1][t] + pref[a-1][b-1][t];
        }
    };

    // Greedy stamping to match counts if needed
    auto totalDef = [&](const array<int,62>& def)->long long{
        long long s=0;
        for(int c=0;c<62;c++) s += llabs((long long)def[c]);
        return s;
    };

    array<int,62> def{};
    buildDef(def);
    long long S = totalDef(def);

    int presetsUsed = 0;
    if(S!=0 && k>0){
        // Greedy iterations up to 400
        vector< vector< array<int,62> > > pref;
        while(S!=0 && presetsUsed < MAX_PRESETS){
            buildPref(pref);
            bool improved = false;
            long long bestS = LLONG_MAX;
            int bestP=-1, bestX=-1, bestY=-1;
            array<int,62> bestE{}; bestE.fill(0);

            for(int p=0;p<k && !improved;p++){
                int hh=P[p].n, ww=P[p].m;
                for(int x=0;x+hh<=n && !improved;x++){
                    for(int y=0;y+ww<=m;y++){
                        array<int,62> reg{};
                        getRectCount(pref, x,y, x+hh-1, y+ww-1, reg);
                        long long Sp = 0;
                        // E = fcnt - reg
                        for(int c=0;c<62;c++){
                            int E = P[p].cnt[c] - reg[c];
                            long long d = (long long)def[c] - (long long)E;
                            Sp += llabs(d);
                        }
                        if(Sp < S){
                            // first improvement
                            improved = true;
                            bestP = p; bestX = x; bestY = y;
                            // compute bestE
                            for(int c=0;c<62;c++) bestE[c] = P[p].cnt[c] - reg[c];
                        }else if(!improved && Sp < bestS){
                            bestS = Sp;
                            bestP = p; bestX = x; bestY = y;
                            for(int c=0;c<62;c++) bestE[c] = P[p].cnt[c] - reg[c];
                        }
                    }
                }
            }

            if(bestP==-1) break; // no placements (shouldn't happen)
            // Apply the chosen stamp (prefer improvement if found, else best equal or worse)
            ops.push_back({bestP+1, bestX+1, bestY+1});
            presetsUsed++;
            // Update grid and counts
            for(int i=0;i<P[bestP].n;i++){
                for(int j=0;j<P[bestP].m;j++){
                    cur[bestX+i][bestY+j] = P[bestP].a[i][j];
                }
            }
            for(int c=0;c<62;c++) cntCur[c] += bestE[c];
            buildDef(def);
            S = totalDef(def);
            // If no improvement after many steps, break to avoid infinite loop
            // but since max 400 steps, it's okay; continue
        }
    }

    // After greedy stamping, verify counts match
    bool countsMatch = true;
    for(int c=0;c<62;c++) if(cntCur[c]!=cntTar[c]) { countsMatch=false; break; }
    if(!countsMatch){
        cout << -1 << "\n";
        return 0;
    }

    // Phase 2: swap-only to arrange cur to target
    // We'll process cells in row-major order except last cell
    auto doSwapRight = [&](int x,int y){ // swap (x,y) with (x,y+1)
        swap(cur[x][y], cur[x][y+1]);
        ops.push_back({-1, x+1, y+1});
    };
    auto doSwapLeft = [&](int x,int y){ // swap (x,y) with (x,y-1)
        swap(cur[x][y], cur[x][y-1]);
        ops.push_back({-2, x+1, y+1});
    };
    auto doSwapUp = [&](int x,int y){ // swap (x,y) with (x-1,y)
        swap(cur[x][y], cur[x-1][y]);
        ops.push_back({-3, x+1, y+1});
    };

    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            if(i==n-1 && j==m-1) break;
            char c = target[i][j];
            int fx=-1, fy=-1;
            for(int x=i;x<n && fx==-1;x++){
                int starty = (x==i)? j : 0;
                for(int y=starty;y<m;y++){
                    if(cur[x][y]==c){ fx=x; fy=y; break; }
                }
            }
            if(fx==-1){
                // Should not happen because counts match
                cout << -1 << "\n";
                return 0;
            }
            // move from (fx,fy) to (i,j)
            // If fx>i, first move horizontally to column j within row fx
            if(fx > i){
                while(fy < j){ doSwapRight(fx, fy); fy++; }
                while(fy > j){ doSwapLeft(fx, fy); fy--; }
                // then move up
                while(fx > i){ doSwapUp(fx, fy); fx--; }
            }else{
                // fx == i
                while(fy > j){ doSwapLeft(fx, fy); fy--; }
                while(fy < j){ doSwapRight(fx, fy); fy++; }
            }
        }
    }

    if((int)ops.size() > 400000){
        cout << -1 << "\n";
        return 0;
    }
    cout << ops.size() << "\n";
    for(auto &op: ops){
        cout << op[0] << " " << op[1] << " " << op[2] << "\n";
    }
    return 0;
}