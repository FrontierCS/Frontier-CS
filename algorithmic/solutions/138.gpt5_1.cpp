#include <bits/stdc++.h>
using namespace std;

struct Operation {
    int op, x, y;
};

static inline int char2id(char c){
    if('a' <= c && c <= 'z') return c - 'a';
    if('A' <= c && c <= 'Z') return 26 + (c - 'A');
    if('0' <= c && c <= '9') return 52 + (c - '0');
    return 0;
}

struct Formula {
    int h, w;
    vector<string> a;
    array<int,62> cnt;
};

struct Candidate {
    int fidx; // 1-based index of formula
    int x, y; // 0-based top-left
    int h, w;
    int area;
    array<int,62> delta; // counts(formula) - counts(initial on rect)
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, k;
    if(!(cin >> n >> m >> k)) {
        return 0;
    }
    vector<string> A(n), T(n);
    for(int i=0;i<n;i++) cin >> A[i];
    // There may be blank line; operator>> will skip whitespace.
    for(int i=0;i<n;i++) cin >> T[i];

    vector<Formula> F(k+1);
    for(int idx=1; idx<=k; idx++){
        int h,w;
        cin >> h >> w;
        F[idx].h = h; F[idx].w = w;
        F[idx].a.assign(h, string());
        for(int i=0;i<h;i++){
            cin >> F[idx].a[i];
        }
        F[idx].cnt.fill(0);
        for(int i=0;i<h;i++){
            for(int j=0;j<w;j++){
                F[idx].cnt[ char2id(F[idx].a[i][j]) ]++;
            }
        }
    }

    array<int,62> cntA{}; cntA.fill(0);
    array<int,62> cntB{}; cntB.fill(0);
    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            cntA[ char2id(A[i][j]) ]++;
            cntB[ char2id(T[i][j]) ]++;
        }
    }
    array<int,62> diff{};
    for(int t=0;t<62;t++) diff[t] = cntB[t]-cntA[t];

    // Precompute all candidates (placements) and their delta relative to initial A
    vector<Candidate> cands;
    cands.reserve(10000);
    for(int idx=1; idx<=k; idx++){
        int h = F[idx].h, w = F[idx].w;
        for(int x=0; x + h <= n; x++){
            for(int y=0; y + w <= m; y++){
                array<int,62> cntRect{}; cntRect.fill(0);
                for(int i=0;i<h;i++){
                    for(int j=0;j<w;j++){
                        cntRect[ char2id(A[x+i][y+j]) ]++;
                    }
                }
                Candidate cand;
                cand.fidx = idx;
                cand.x = x; cand.y = y; cand.h = h; cand.w = w; cand.area = h*w;
                for(int t=0;t<62;t++){
                    cand.delta[t] = F[idx].cnt[t] - cntRect[t];
                }
                cands.push_back(cand);
            }
        }
    }

    auto L1 = [&](const array<int,62>& v)->int{
        long long s=0;
        for(int t=0;t<62;t++) s += llabs((long long)v[t]);
        return (int)s;
    };

    vector<Operation> ops;

    // Try to select disjoint placements to make diff zero using greedy
    auto tryGreedy = [&](int attempt)->pair<bool, vector<Candidate>>{
        vector<uint32_t> occ(n, 0u); // bitmask of occupied cells per row (m <= 20)
        array<int,62> D = diff;
        vector<Candidate> chosen;

        auto isFree = [&](const Candidate& c)->bool{
            uint32_t mask = (c.w == 32 ? 0xFFFFFFFFu : ((1u << c.w) - 1u)) << c.y;
            for(int i=0;i<c.h;i++){
                if(occ[c.x + i] & mask) return false;
            }
            return true;
        };
        auto markOcc = [&](const Candidate& c){
            uint32_t mask = (c.w == 32 ? 0xFFFFFFFFu : ((1u << c.w) - 1u)) << c.y;
            for(int i=0;i<c.h;i++){
                occ[c.x + i] |= mask;
            }
        };

        int maxPresets = 400;
        int maxSteps = maxPresets;

        for(int step=0; step<maxSteps; step++){
            int bestIdx = -1;
            long long bestScore = LLONG_MIN;
            int bestImprovement = 0;
            for(int i=0;i<(int)cands.size();i++){
                const Candidate& c = cands[i];
                if(!isFree(c)) continue;
                // compute improvement
                int improvement = 0;
                for(int t=0;t<62;t++){
                    int before = abs(D[t]);
                    int after = abs(D[t] - c.delta[t]);
                    improvement += before - after;
                }
                if(improvement <= 0) continue;
                long long score = improvement;
                // tie-breakers based on attempt
                if(attempt == 0) {
                    // prefer larger improvement, then larger area
                    score = (long long)improvement * 1000000LL + c.area;
                } else if(attempt == 1) {
                    // prefer improvement per area
                    score = (long long)improvement * 1000000LL - (long long)c.area;
                } else if(attempt == 2) {
                    // prefer larger area too
                    score = (long long)improvement * 1000000LL + (long long)c.area * 10;
                } else if(attempt == 3) {
                    // favor placements closer to center (arbitrary)
                    int cx = c.x + c.h/2, cy = c.y + c.w/2;
                    int dx = abs(cx - n/2) + abs(cy - m/2);
                    score = (long long)improvement * 1000000LL - dx;
                } else {
                    score = (long long)improvement * 1000000LL - (long long)c.area;
                }
                if(score > bestScore){
                    bestScore = score;
                    bestIdx = i;
                    bestImprovement = improvement;
                }
            }
            if(bestIdx == -1) break;
            const Candidate& pick = cands[bestIdx];
            // apply
            chosen.push_back(pick);
            markOcc(pick);
            for(int t=0;t<62;t++){
                D[t] -= pick.delta[t];
            }
            if(L1(D) == 0) return {true, chosen};
        }
        if(L1(D) == 0) return {true, chosen};
        else return {false, chosen};
    };

    bool needPresets = (L1(diff) != 0);
    vector<Candidate> chosen;
    if(needPresets){
        bool success = false;
        for(int att=0; att<4 && !success; att++){
            auto res = tryGreedy(att);
            if(res.first){
                chosen = move(res.second);
                success = true;
                break;
            }
        }
        if(!success){
            cout << -1 << "\n";
            return 0;
        }
    }

    // Apply chosen presets to modify A
    for(const auto& c : chosen){
        int fidx = c.fidx;
        int x = c.x, y = c.y;
        for(int i=0;i<F[fidx].h;i++){
            for(int j=0;j<F[fidx].w;j++){
                A[x+i][y+j] = F[fidx].a[i][j];
            }
        }
        ops.push_back({fidx, x+1, y+1});
    }

    // After presets, counts of A should be equal to target
    array<int,62> cntA2{}; cntA2.fill(0);
    for(int i=0;i<n;i++) for(int j=0;j<m;j++) cntA2[ char2id(A[i][j]) ]++;
    bool countsEqual = true;
    for(int t=0;t<62;t++) if(cntA2[t] != cntB[t]) { countsEqual = false; break; }
    if(!countsEqual){
        cout << -1 << "\n";
        return 0;
    }

    // Swapping to rearrange A to T
    auto doSwap = [&](int x1, int y1, int x2, int y2){
        // x,y are 0-based, adjacent
        // Update A and record operation
        if(x1 == x2){
            if(y2 == y1 + 1){
                // swap (x1,y1) and (x1,y1+1): op -1 x y
                ops.push_back({-1, x1+1, y1+1});
            } else if(y2 == y1 - 1){
                // swap (x1,y1) and (x1,y1-1): op -2 x y (x,y is the right cell)
                ops.push_back({-2, x1+1, y1+1});
            } else {
                // not adjacent
            }
        } else if(y1 == y2){
            if(x2 == x1 + 1){
                // swap (x1,y1) and (x1+1,y1): op -4 x y (x,y is top cell)
                ops.push_back({-4, x1+1, y1+1});
            } else if(x2 == x1 - 1){
                // swap (x1,y1) and (x1-1,y1): op -3 x y (x,y is bottom cell)
                ops.push_back({-3, x1+1, y1+1});
            } else {
                // not adjacent
            }
        }
        swap(A[x1][y1], A[x2][y2]);
    };

    // Function to move a char from (sx,sy) to (tx,ty) using allowed swaps
    auto moveToken = [&](int sx, int sy, int tx, int ty){
        int x = sx, y = sy;
        if(x > tx){
            // Move horizontally to column ty first
            while(y > ty){
                doSwap(x, y, x, y-1);
                y--;
            }
            while(y < ty){
                doSwap(x, y, x, y+1);
                y++;
            }
            // Then move up
            while(x > tx){
                doSwap(x, y, x-1, y);
                x--;
            }
        } else {
            // x == tx
            while(y > ty){
                doSwap(x, y, x, y-1);
                y--;
            }
            while(y < ty){
                doSwap(x, y, x, y+1);
                y++;
            }
        }
    };

    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            if(i == n-1 && j == m-1) break; // last cell auto correct due to counts
            if(A[i][j] == T[i][j]) continue;
            char need = T[i][j];
            // First search in the same row to the right (j..m-1)
            int fx = -1, fy = -1;
            for(int y=j; y<m; y++){
                if(A[i][y] == need){
                    fx = i; fy = y; break;
                }
            }
            if(fx == -1){
                int bestCost = INT_MAX;
                for(int x=i+1; x<n; x++){
                    for(int y=0; y<m; y++){
                        if(A[x][y] == need){
                            int cost = abs(y - j) + (x - i);
                            if(cost < bestCost){
                                bestCost = cost;
                                fx = x; fy = y;
                            }
                        }
                    }
                }
            }
            if(fx == -1){
                // should not happen due to counts equal
                cout << -1 << "\n";
                return 0;
            }
            // Move token at (fx,fy) to (i,j)
            if(fx > i){
                // move horizontally on row fx to column j
                while(fy > j){
                    doSwap(fx, fy, fx, fy-1);
                    fy--;
                }
                while(fy < j){
                    doSwap(fx, fy, fx, fy+1);
                    fy++;
                }
                // move up to row i
                while(fx > i){
                    doSwap(fx, fy, fx-1, fy);
                    fx--;
                }
            } else {
                // fx == i
                while(fy > j){
                    doSwap(fx, fy, fx, fy-1);
                    fy--;
                }
                while(fy < j){
                    doSwap(fx, fy, fx, fy+1);
                    fy++;
                }
            }
        }
    }

    // After operations, A should equal T
    bool ok = true;
    for(int i=0;i<n;i++){
        for(int j=0;j<m;j++){
            if(A[i][j] != T[i][j]) { ok = false; break; }
        }
        if(!ok) break;
    }
    if(!ok){
        cout << -1 << "\n";
        return 0;
    }

    if((int)ops.size() > 400000){
        cout << -1 << "\n";
        return 0;
    }

    // Output
    cout << ops.size() << "\n";
    for(auto &op : ops){
        cout << op.op << " " << op.x << " " << op.y << "\n";
    }

    return 0;
}