#include <bits/stdc++.h>
using namespace std;

int idx(char c){
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
    vector<string> init(n), target(n);
    for(int i=0;i<n;i++) cin>>init[i];
    for(int i=0;i<n;i++) cin>>target[i];
    struct Pres { int r,c; vector<string> a; };
    vector<Pres> pres(k);
    for(int t=0;t<k;t++){
        int r,c; cin>>r>>c;
        pres[t].r=r; pres[t].c=c;
        pres[t].a.resize(r);
        for(int i=0;i<r;i++) cin>>pres[t].a[i];
    }
    auto countGrid = [&](const vector<string>& g){
        array<long long,62> cnt{}; cnt.fill(0);
        for(int i=0;i<n;i++) for(int j=0;j<m;j++) cnt[idx(g[i][j])]++; 
        return cnt;
    };
    auto cntI = countGrid(init);
    auto cntT = countGrid(target);
    vector<tuple<int,int,int>> ops;
    vector<string> cur = init;
    int usedPresets = 0;

    auto applySwap = [&](int code, int x, int y){
        // x,y are 1-based
        int i=x-1, j=y-1;
        if(code==-3){
            // swap (x,y) with (x-1,y)
            swap(cur[i][j], cur[i-1][j]);
        }else if(code==-2){
            // swap (x,y) with (x,y-1)
            swap(cur[i][j], cur[i][j-1]);
        }else if(code==-4){
            swap(cur[i][j], cur[i+1][j]);
        }else if(code==-1){
            swap(cur[i][j], cur[i][j+1]);
        }else if(code==0){
            // rotate 2x2 at (x,y)
            char a = cur[i+1][j];
            char b = cur[i][j];
            char c = cur[i][j+1];
            char d = cur[i+1][j+1];
            cur[i][j] = a;
            cur[i][j+1] = b;
            cur[i+1][j+1] = c;
            cur[i+1][j] = d;
        }
        ops.emplace_back(code,x,y);
    };

    auto trySinglePreset = [&]()->bool{
        for(int t=0;t<k;t++){
            int r=pres[t].r, c=pres[t].c;
            // precompute counts of preset
            array<long long,62> cntP{}; cntP.fill(0);
            for(int i=0;i<r;i++) for(int j=0;j<c;j++) cntP[idx(pres[t].a[i][j])]++;
            for(int i=0;i+ r<=n;i++){
                for(int j=0;j+ c<=m;j++){
                    array<long long,62> cntS{}; cntS.fill(0);
                    for(int x=0;x<r;x++) for(int y=0;y<c;y++) cntS[idx(cur[i+x][j+y])]++;
                    // after applying: cntI - cntS + cntP
                    bool ok=true;
                    for(int z=0;z<62;z++){
                        long long val = cntI[z] - cntS[z] + cntP[z];
                        if(val != cntT[z]){ ok=false; break; }
                    }
                    if(ok){
                        // apply preset
                        ops.emplace_back(t+1, i+1, j+1);
                        for(int x=0;x<r;x++) for(int y=0;y<c;y++) cur[i+x][j+y]=pres[t].a[x][y];
                        usedPresets++;
                        return true;
                    }
                }
            }
        }
        return false;
    };

    bool countsMatch = true;
    for(int z=0;z<62;z++) if(cntI[z]!=cntT[z]) { countsMatch=false; break; }
    if(!countsMatch){
        bool done = trySinglePreset();
        if(!done){
            cout << -1 << "\n";
            return 0;
        }
    }

    // Now cur has same multiset as target; arrange via adjacent swaps
    // For each position in row-major, bring the target char here from later area
    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            if(cur[i][j]==target[i][j]) continue;
            // find target char in area i..n-1, j..m-1
            int fi=-1,fj=-1;
            for(int x=i;x<n;x++){
                for(int y=(x==i?j:0); y<m; y++){
                    if(cur[x][y]==target[i][j]){
                        fi=x; fj=y; goto found;
                    }
                }
            }
            found:
            if(fi==-1){
                // should not happen
                cout << -1 << "\n";
                return 0;
            }
            // move up from fi to i
            for(int x=fi; x>i; x--){
                applySwap(-3, x+1, fj+1); // swap (x+1,fj+1) with (x,fj+1); but here applying -3 with current (x+1, fj+1)? Careful.
                // Correction: we want to swap (x, fj) with (x-1, fj). In 1-based: (-3, x, fj+1)
                ops.pop_back(); // remove wrong
                // redo properly
            }
            // We removed last op; now do correct sequence
            for(int x=fi; x>i; x--){
                applySwap(-3, x, fj+1);
            }
            // move left from fj to j along row i
            for(int y=fj; y>j; y--){
                applySwap(-2, i+1, y+1);
            }
        }
    }

    // Validate within limits
    if((int)ops.size() > 400000 || usedPresets > 400){
        cout << -1 << "\n";
        return 0;
    }
    // Final check: cur equals target
    if(cur != target){
        cout << -1 << "\n";
        return 0;
    }
    cout << ops.size() << "\n";
    for(auto &t: ops){
        int a,b,c; tie(a,b,c)=t;
        cout << a << " " << b << " " << c << "\n";
    }
    return 0;
}