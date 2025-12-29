#include <bits/stdc++.h>
using namespace std;

struct Operation {
    int op, x, y;
};
struct Preset {
    int h, w;
    vector<string> a;
    array<int,62> cnt{};
};
struct Rect {
    int x1, y1, x2, y2;
};
static inline bool disjoint(const Rect& A, const Rect& B){
    return (A.x2 < B.x1 || B.x2 < A.x1 || A.y2 < B.y1 || B.y2 < A.y1);
}

int n, m, k;
vector<string> cur, targetGrid;
vector<Preset> presets;
vector<Operation> ops;
int presetOpsUsed = 0;

int char2idx(char c){
    if(c>='a' && c<='z') return c-'a';
    if(c>='A' && c<='Z') return 26 + (c-'A');
    return 52 + (c-'0');
}

array<int,62> countGrid(const vector<string>& g){
    array<int,62> cnt{};
    cnt.fill(0);
    for(int i=0;i<(int)g.size();++i)
        for(int j=0;j<(int)g[0].size();++j)
            cnt[char2idx(g[i][j])]++;
    return cnt;
}

void pushOp(int op, int x, int y){
    ops.push_back({op, x, y});
}

void applyPreset(int id, int x, int y){
    // id is 1-based in output
    Preset &P = presets[id-1];
    for(int i=0;i<P.h;++i){
        for(int j=0;j<P.w;++j){
            cur[x-1+i][y-1+j] = P.a[i][j];
        }
    }
    pushOp(id, x, y);
    presetOpsUsed++;
}

void doSwap(int x1, int y1, int x2, int y2){
    // 1-based coordinates
    if(x1==x2){
        if(y1+1==y2){
            // swap (x1,y1) with (x1,y1+1)
            pushOp(-1, x1, y1);
        }else if(y1-1==y2){
            // swap (x1,y1) with (x1,y1-1)
            pushOp(-2, x1, y1);
        }else{
            // invalid
        }
    }else if(y1==y2){
        if(x1+1==x2){
            // swap (x1,y1) with (x1+1,y1)
            pushOp(-4, x1, y1);
        }else if(x1-1==x2){
            // swap (x1,y1) with (x1-1,y1)
            pushOp(-3, x1, y1);
        }else{
            // invalid
        }
    }else{
        // invalid
    }
    // update cur
    swap(cur[x1-1][y1-1], cur[x2-1][y2-1]);
}

struct Arr62 {
    array<int,62> v;
};

struct Key {
    uint64_t h1, h2;
    bool operator==(const Key& other) const {
        return h1==other.h1 && h2==other.h2;
    }
};
struct KeyHash {
    size_t operator()(const Key& k) const {
        return (size_t)(k.h1 ^ (k.h2*0x9e3779b97f4a7c15ULL));
    }
};

Key hashArr(const array<int,62>& a){
    static const uint64_t B1 = 1469598103934665603ULL;
    static const uint64_t P1 = 1099511628211ULL;
    static const uint64_t B2 = 11400714819323198485ULL;
    static const uint64_t P2 = 14029467366897019727ULL;
    uint64_t h1 = B1, h2 = B2;
    for(int i=0;i<62;++i){
        uint64_t x = (uint64_t)(a[i] + 1024);
        h1 ^= x; h1 *= P1;
        h2 ^= (x + 0x9e3779b97f4a7c15ULL); h2 *= P2;
    }
    return {h1, h2};
}

array<int,62> arrSub(const array<int,62>& A, const array<int,62>& B){
    array<int,62> R;
    for(int i=0;i<62;++i) R[i] = A[i] - B[i];
    return R;
}
array<int,62> arrAdd(const array<int,62>& A, const array<int,62>& B){
    array<int,62> R;
    for(int i=0;i<62;++i) R[i] = A[i] + B[i];
    return R;
}
bool arrEq(const array<int,62>& A, const array<int,62>& B){
    for(int i=0;i<62;++i) if(A[i]!=B[i]) return false;
    return true;
}
int arrL1(const array<int,62>& A){
    int s=0; for(int i=0;i<62;++i) s += abs(A[i]); return s;
}

void computePresetCounts(){
    for(auto &P : presets){
        P.cnt.fill(0);
        for(int i=0;i<P.h;++i){
            for(int j=0;j<P.w;++j){
                P.cnt[char2idx(P.a[i][j])]++;
            }
        }
    }
}

vector<vector<array<int,62>>> buildPrefix(const vector<string>& g){
    vector<vector<array<int,62>>> pref(n+1, vector<array<int,62>>(m+1));
    for(int i=0;i<=n;++i)
        for(int j=0;j<=m;++j){
            pref[i][j].fill(0);
        }
    for(int i=1;i<=n;++i){
        for(int j=1;j<=m;++j){
            for(int c=0;c<62;++c){
                pref[i][j][c] = pref[i-1][j][c] + pref[i][j-1][c] - pref[i-1][j-1][c];
            }
            int idx = char2idx(g[i-1][j-1]);
            pref[i][j][idx]++;
        }
    }
    return pref;
}
array<int,62> getRectCounts(const vector<vector<array<int,62>>>& pref, int x, int y, int h, int w){
    // x,y 1-based
    int x2 = x + h - 1, y2 = y + w - 1;
    array<int,62> res;
    for(int c=0;c<62;++c){
        res[c] = pref[x2][y2][c] - pref[x-1][y2][c] - pref[x2][y-1][c] + pref[x-1][y-1][c];
    }
    return res;
}

struct Candidate {
    int id, x, y, h, w;
    Rect r;
    array<int,62> e;
};

bool adjustCountsWithOverlays(){
    // Try to adjust counts so that counts(cur) == counts(targetGrid).
    // If 1x1 stamps exist for all chars present in target, paint all cells directly and return true.
    array<int,62> tgtCnt = countGrid(targetGrid);
    array<int,62> curCnt = countGrid(cur);

    // 1x1 preset availability
    vector<int> stampForChar(62, -1);
    for(int id=1; id<=k; ++id){
        Preset &P = presets[id-1];
        if(P.h==1 && P.w==1){
            int c = char2idx(P.a[0][0]);
            stampForChar[c] = id;
        }
    }
    bool all1x1 = true;
    for(int c=0;c<62;++c){
        if(tgtCnt[c]>0 && stampForChar[c]==-1){
            all1x1 = false; break;
        }
    }
    if(all1x1){
        // Paint entire grid to target directly
        for(int i=1;i<=n;++i){
            for(int j=1;j<=m;++j){
                int c = char2idx(targetGrid[i-1][j-1]);
                int id = stampForChar[c];
                applyPreset(id, i, j);
                if(presetOpsUsed > 400) return false;
            }
        }
        return true;
    }

    // If counts already match, done (no overlays needed)
    if(arrEq(curCnt, tgtCnt)) return true;

    // Otherwise iterative improvement with candidates (single/pair/greedy)
    int maxIterations = 50; // limit to avoid infinite loops
    for(int iter=0; iter<maxIterations; ++iter){
        curCnt = countGrid(cur);
        array<int,62> d;
        for(int c=0;c<62;++c) d[c] = tgtCnt[c] - curCnt[c];
        if(arrEq(d, array<int,62>{})){
            bool ok=true;
            for(int c=0;c<62;++c) if(d[c]!=0) { ok=false; break; }
            if(ok) return true;
        }
        int l1 = arrL1(d);
        if(l1==0) return true;

        // Build prefix on current grid
        auto pref = buildPrefix(cur);

        // Prepare candidates
        vector<Candidate> cands;
        cands.reserve(8000);
        for(int id=1; id<=k; ++id){
            Preset &P = presets[id-1];
            for(int x=1; x<=n-P.h+1; ++x){
                for(int y=1; y<=m-P.w+1; ++y){
                    array<int,62> rectCnt = getRectCounts(pref, x, y, P.h, P.w);
                    array<int,62> e;
                    for(int c=0;c<62;++c) e[c] = presets[id-1].cnt[c] - rectCnt[c];
                    Candidate cand;
                    cand.id = id; cand.x = x; cand.y = y; cand.h = P.h; cand.w = P.w;
                    cand.r = {x, y, x+P.h-1, y+P.w-1};
                    cand.e = e;
                    cands.push_back(std::move(cand));
                }
            }
        }

        // Try single overlay exact match
        bool applied = false;
        for(size_t i=0;i<cands.size();++i){
            if(arrEq(cands[i].e, d)){
                applyPreset(cands[i].id, cands[i].x, cands[i].y);
                if(presetOpsUsed > 400) return false;
                applied = true;
                break;
            }
        }
        if(applied) continue;

        // Try pair of overlays exact match (disjoint)
        // Build hash map from e vector to indices
        unordered_map<Key, vector<int>, KeyHash> mp;
        mp.reserve(cands.size()*2);
        for(int i=0;i<(int)cands.size();++i){
            Key key = hashArr(cands[i].e);
            mp[key].push_back(i);
        }
        bool paired=false;
        for(int i=0;i<(int)cands.size() && !paired;++i){
            array<int,62> need = arrSub(d, cands[i].e);
            Key key = hashArr(need);
            auto it = mp.find(key);
            if(it!=mp.end()){
                for(int idx2 : it->second){
                    if(arrEq(cands[idx2].e, need) && disjoint(cands[i].r, cands[idx2].r)){
                        applyPreset(cands[i].id, cands[i].x, cands[i].y);
                        if(presetOpsUsed > 400) return false;
                        applyPreset(cands[idx2].id, cands[idx2].x, cands[idx2].y);
                        if(presetOpsUsed > 400) return false;
                        paired = true;
                        break;
                    }
                }
            }
        }
        if(paired) continue;

        // Greedy improvement: choose overlay that reduces L1 norm the most
        int bestImprove = 0;
        int bestIdx = -1;
        for(int i=0;i<(int)cands.size();++i){
            int newL1 = 0;
            for(int c=0;c<62;++c){
                int val = d[c] - cands[i].e[c];
                newL1 += abs(val);
            }
            int improve = l1 - newL1;
            if(improve > bestImprove){
                bestImprove = improve;
                bestIdx = i;
            }
        }
        if(bestIdx==-1 || bestImprove<=0){
            // cannot improve further
            break;
        }
        applyPreset(cands[bestIdx].id, cands[bestIdx].x, cands[bestIdx].y);
        if(presetOpsUsed > 400) return false;
    }

    // Final check
    array<int,62> finalCnt = countGrid(cur);
    if(arrEq(finalCnt, tgtCnt)) return true;
    for(int c=0;c<62;++c) if(finalCnt[c]!=tgtCnt[c]) return false;
    return true;
}

pair<int,int> findInRect(int si, int sj, char goal){
    for(int x=si; x<=n; ++x){
        for(int y=sj; y<=m; ++y){
            if(cur[x-1][y-1]==goal) return {x,y};
        }
    }
    return {-1,-1};
}

pair<int,int> findInCross(int startRow, char goal){
    // Cross: column m rows [startRow..n], and row n columns [1..m]
    for(int x=n; x>=startRow; --x){
        if(cur[x-1][m-1]==goal) return {x,m};
    }
    for(int y=m; y>=1; --y){
        if(cur[n-1][y-1]==goal) return {n,y};
    }
    return {-1,-1};
}

pair<int,int> findInLastRowFrom(int startCol, char goal){
    for(int y=startCol; y<=m; ++y){
        if(cur[n-1][y-1]==goal) return {n,y};
    }
    return {-1,-1};
}

bool arrangeBySwaps(){
    // Stage 1: fill (1..n-1, 1..m-1)
    for(int i=1;i<=n-1;++i){
        for(int j=1;j<=m-1;++j){
            char need = targetGrid[i-1][j-1];
            if(cur[i-1][j-1]==need) continue;
            auto pos = findInRect(i, j, need);
            if(pos.first==-1) return false; // shouldn't happen if counts match
            int x = pos.first, y = pos.second;
            while(y > j){
                doSwap(x, y, x, y-1);
                y--;
            }
            while(x > i){
                doSwap(x, y, x-1, y);
                x--;
            }
        }
    }
    // Stage 2: fill last column (1..n-1, m)
    for(int i=1;i<=n-1;++i){
        char need = targetGrid[i-1][m-1];
        if(cur[i-1][m-1]==need) continue;
        auto pos = findInCross(i, need);
        if(pos.first==-1) return false;
        int x = pos.first, y = pos.second;
        if(x==n){
            while(y < m){
                doSwap(n, y, n, y+1);
                y++;
            }
            while(y > m){
                doSwap(n, y, n, y-1);
                y--;
            }
            while(x > i){
                doSwap(x, m, x-1, m);
                x--;
            }
        }else{ // y==m and x>i
            while(x > i){
                doSwap(x, m, x-1, m);
                x--;
            }
        }
    }
    // Stage 3: fill last row (n, 1..m-1)
    for(int j=1;j<=m-1;++j){
        char need = targetGrid[n-1][j-1];
        if(cur[n-1][j-1]==need) continue;
        auto pos = findInLastRowFrom(j, need);
        if(pos.first==-1) return false;
        int y = pos.second;
        while(y > j){
            doSwap(n, y, n, y-1);
            y--;
        }
    }
    // Final cell automatically matches if counts equal
    return (cur == targetGrid);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> m >> k;
    cur.resize(n);
    for(int i=0;i<n;++i) cin >> cur[i];
    targetGrid.resize(n);
    for(int i=0;i<n;++i) cin >> targetGrid[i];
    presets.resize(k);
    for(int i=0;i<k;++i){
        int h, w; cin >> h >> w;
        presets[i].h = h; presets[i].w = w;
        presets[i].a.resize(h);
        for(int r=0;r<h;++r) cin >> presets[i].a[r];
    }
    computePresetCounts();

    // First try to adjust counts via overlays
    bool countsAdjusted = adjustCountsWithOverlays();
    if(!countsAdjusted){
        // As fallback, if counts already match, proceed; else unsolvable
        array<int,62> cntCur = countGrid(cur);
        array<int,62> cntTgt = countGrid(targetGrid);
        if(!arrEq(cntCur, cntTgt)){
            cout << -1 << "\n";
            return 0;
        }
    }

    // If after overlays, cur equals target already, done.
    if(cur == targetGrid){
        cout << ops.size() << "\n";
        for(auto &op : ops){
            cout << op.op << " " << op.x << " " << op.y << "\n";
        }
        return 0;
    }

    // Now rearrange by swaps
    bool ok = arrangeBySwaps();
    if(!ok){
        cout << -1 << "\n";
        return 0;
    }
    if((int)ops.size() > 400000){
        // If too many operations (unlikely), output -1
        cout << -1 << "\n";
        return 0;
    }
    cout << ops.size() << "\n";
    for(auto &op : ops){
        cout << op.op << " " << op.x << " " << op.y << "\n";
    }
    return 0;
}