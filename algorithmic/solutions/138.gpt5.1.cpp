#include <bits/stdc++.h>
using namespace std;

int char2idx(char c){
    if('a' <= c && c <= 'z') return c - 'a';
    if('A' <= c && c <= 'Z') return 26 + (c - 'A');
    return 52 + (c - '0'); // '0'-'9'
}
char idx2char(int x){
    if(x < 26) return char('a' + x);
    if(x < 52) return char('A' + (x - 26));
    return char('0' + (x - 52));
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n,m,k;
    if(!(cin >> n >> m >> k)) return 0;
    vector<string> A(n), B(n);
    for(int i=0;i<n;i++) cin >> A[i];
    for(int i=0;i<n;i++) cin >> B[i];

    struct Formula {
        int np, mp;
        vector<string> mat;
        array<int,62> cnt;
    };
    vector<Formula> F(k+1);
    for(int id=1; id<=k; ++id){
        int np, mp;
        cin >> np >> mp;
        F[id].np = np;
        F[id].mp = mp;
        F[id].mat.assign(np,string());
        for(int i=0;i<np;i++) cin >> F[id].mat[i];
        F[id].cnt.fill(0);
        for(int i=0;i<np;i++)
            for(int j=0;j<mp;j++)
                F[id].cnt[char2idx(F[id].mat[i][j])]++;
    }
    
    const int MAXT = 62;
    array<int,MAXT> cntA{}, cntB{};
    cntA.fill(0);
    cntB.fill(0);
    for(int i=0;i<n;i++)
        for(int j=0;j<m;j++){
            cntA[char2idx(A[i][j])]++;
            cntB[char2idx(B[i][j])]++;
        }
    
    bool same = true;
    for(int t=0;t<MAXT;t++) if(cntA[t] != cntB[t]){ same=false; break; }
    
    int N = n*m;
    // Build snake path and posOf
    vector<pair<int,int>> path;
    path.reserve(N);
    for(int i=0;i<n;i++){
        if(i%2==0){
            for(int j=0;j<m;j++) path.push_back({i,j});
        }else{
            for(int j=m-1;j>=0;j--) path.push_back({i,j});
        }
    }
    vector<vector<int>> posOf(n, vector<int>(m,-1));
    for(int idx=0; idx<N; ++idx){
        auto [x,y] = path[idx];
        posOf[x][y] = idx;
    }
    
    vector<char> arr(N);
    for(int idx=0; idx<N; ++idx){
        auto [x,y] = path[idx];
        arr[idx] = A[x][y];
    }
    vector<char> targetFlat(N);
    for(int idx=0; idx<N; ++idx){
        auto [x,y] = path[idx];
        targetFlat[idx] = B[x][y];
    }
    
    vector<tuple<int,int,int>> ops;
    ops.reserve(400000);
    
    auto addSwap = [&](int p1, int p2){
        auto [x1,y1] = path[p1];
        auto [x2,y2] = path[p2];
        int op, x, y;
        if(x1==x2){
            if(y1+1==y2){ op=-1; x=x1; y=y1; }
            else if(y1-1==y2){ op=-2; x=x1; y=y1; }
            else return;
        }else if(y1==y2){
            if(x1+1==x2){ op=-4; x=x1; y=y1; }
            else if(x1-1==y2){ op=-3; x=x1; y=y1; }
            else return;
        }else return;
        ops.emplace_back(op, x+1, y+1);
    };
    
    auto transform = [&](vector<char>& cur, const vector<char>& dest){
        int Sz = (int)cur.size();
        for(int i=0;i<Sz;i++){
            if(cur[i]==dest[i]) continue;
            int j=i+1;
            while(j<Sz && cur[j]!=dest[i]) j++;
            if(j==Sz){
                // should not happen if multisets equal
                continue;
            }
            for(int k=j;k>i;k--){
                swap(cur[k],cur[k-1]);
                addSwap(k-1,k);
            }
        }
    };
    
    if(same){
        transform(arr, targetFlat);
        if((int)ops.size() > 400000){
            cout << -1 << '\n';
            return 0;
        }
        cout << ops.size() << '\n';
        for(auto &t: ops){
            int op,x,y;
            tie(op,x,y) = t;
            cout << op << ' ' << x << ' ' << y << '\n';
        }
        return 0;
    }
    
    // Try to fix with exactly one preset formula
    bool foundFormula = false;
    int chosenId = -1;
    array<int,MAXT> delW{};
    array<int,MAXT> diff{};
    for(int t=0;t<MAXT;t++) diff[t] = cntB[t] - cntA[t];
    
    for(int id=1; id<=k; ++id){
        auto &fm = F[id];
        delW.fill(0);
        bool ok = true;
        for(int t=0;t<MAXT;t++){
            long long w = (long long)fm.cnt[t] - (long long)diff[t];
            if(w < 0 || w > cntA[t]){ ok=false; break; }
            delW[t] = (int)w;
        }
        if(!ok) continue;
        long long sumW = 0;
        for(int t=0;t<MAXT;t++) sumW += delW[t];
        if(sumW != (long long)fm.np * fm.mp) continue;
        // compute resulting counts to verify
        array<int,MAXT> after = cntA;
        for(int t=0;t<MAXT;t++) after[t] = after[t] - delW[t] + fm.cnt[t];
        bool good = true;
        for(int t=0;t<MAXT;t++) if(after[t] != cntB[t]){ good=false; break; }
        if(!good) continue;
        foundFormula = true;
        chosenId = id;
        break;
    }
    
    if(!foundFormula){
        cout << -1 << '\n';
        return 0;
    }
    
    // Build desired configuration before applying preset
    Formula &useF = F[chosenId];
    int np = useF.np, mp = useF.mp;
    int Sblock = np * mp;
    
    vector<vector<char>> before2D(n, vector<char>(m,'?'));
    // Block at top-left (0,0)
    vector<pair<int,int>> blockCells;
    blockCells.reserve(Sblock);
    for(int i=0;i<np;i++)
        for(int j=0;j<mp;j++)
            blockCells.push_back({i,j});
    int ptr = 0;
    for(int t=0;t<MAXT;t++){
        for(int c=0;c<delW[t];c++){
            auto [x,y] = blockCells[ptr++];
            before2D[x][y] = idx2char(t);
        }
    }
    // Remaining cells: fill with remaining counts A - delW
    array<int,MAXT> remain{};
    for(int t=0;t<MAXT;t++) remain[t] = cntA[t] - delW[t];
    
    vector<pair<int,int>> outsideCells;
    outsideCells.reserve(N-Sblock);
    for(int i=0;i<n;i++)
        for(int j=0;j<m;j++){
            if(i<np && j<mp) continue;
            outsideCells.push_back({i,j});
        }
    int outPtr = 0;
    for(int t=0;t<MAXT;t++){
        for(int c=0;c<remain[t];c++){
            if(outPtr >= (int)outsideCells.size()) break;
            auto [x,y] = outsideCells[outPtr++];
            before2D[x][y] = idx2char(t);
        }
    }
    // Flatten before2D into destBefore
    vector<char> destBefore(N);
    for(int idx=0; idx<N; ++idx){
        auto [x,y] = path[idx];
        destBefore[idx] = before2D[x][y];
    }
    
    // Permute A -> before2D
    transform(arr, destBefore);
    
    // Apply preset chosenId at (1,1)
    ops.emplace_back(chosenId, 1, 1);
    for(int i=0;i<np;i++)
        for(int j=0;j<mp;j++){
            int pos = posOf[i][j];
            arr[pos] = useF.mat[i][j];
        }
    
    // Now arr has counts equal to target, permute to B
    transform(arr, targetFlat);
    
    if((int)ops.size() > 400000){
        cout << -1 << '\n';
        return 0;
    }
    cout << ops.size() << '\n';
    for(auto &t: ops){
        int op,x,y;
        tie(op,x,y) = t;
        cout << op << ' ' << x << ' ' << y << '\n';
    }
    return 0;
}