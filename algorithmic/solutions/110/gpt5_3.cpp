#include <bits/stdc++.h>
using namespace std;

static const int R = 8;
static const int C = 14;
static const int N = R*C;

struct Grid {
    array<char, N> d;
};

vector<array<int, 8>> adjList; // up to 8 neighbors per cell, -1 if none
vector<int> degList; // degree per cell

inline int id(int r, int c){ return r*C + c; }
inline pair<int,int> rc(int id){ return {id / C, id % C}; }

void buildAdj() {
    adjList.assign(N, {});
    degList.assign(N, 0);
    int dr[8]={-1,-1,-1,0,0,1,1,1};
    int dc[8]={-1,0,1,-1,1,-1,0,1};
    for(int r=0;r<R;r++){
        for(int c=0;c<C;c++){
            int u=id(r,c);
            int k=0;
            for(int t=0;t<8;t++){
                int nr=r+dr[t], nc=c+dc[t];
                if(nr>=0 && nr<R && nc>=0 && nc<C){
                    adjList[u][k++] = id(nr,nc);
                }
            }
            degList[u]=k;
            for(int t=k;t<8;t++) adjList[u][t]=-1;
        }
    }
}

static inline bool canRead(const Grid& g, const string& s) {
    // BFS-like layered DP using sets of positions matching path prefix
    static int visMark[N];
    static int epoch = 1;
    static int lastResetEpoch = 0;
    static bool inited = false;
    if(!inited){
        memset(visMark, 0, sizeof(visMark));
        inited = true;
    }
    auto nextEpoch = [&](){
        // simple epoch increment with wrap-around safety
        epoch++;
        if(epoch == 0){ // wrapped
            memset(visMark, 0, sizeof(visMark));
            epoch = 1;
        }
    };
    vector<int> cur, nxt;
    char d0 = s[0];
    cur.reserve(N);
    nxt.reserve(N);
    for(int u=0; u<N; ++u){
        if(g.d[u] == d0) cur.push_back(u);
    }
    if(cur.empty()) return false;
    for(size_t i=1; i<s.size(); ++i){
        char need = s[i];
        nextEpoch();
        nxt.clear();
        int e = epoch;
        for(int u: cur){
            int k = degList[u];
            auto &adj = adjList[u];
            for(int j=0;j<k;j++){
                int v = adj[j];
                if(g.d[v] == need && visMark[v] != e){
                    visMark[v] = e;
                    nxt.push_back(v);
                }
            }
        }
        if(nxt.empty()) return false;
        cur.swap(nxt);
    }
    return true;
}

int evaluateX(const Grid& g, const vector<string>& nums) {
    int n = (int)nums.size()-1;
    for(int i=1;i<=n;i++){
        if(!canRead(g, nums[i])) return i-1;
    }
    return n;
}

Grid generateInitial(mt19937 &rng) {
    Grid g;
    // Types: 0 = repeat 0..9 with offset
    //        1 = pairs "00 11 22 ..." with offset
    //        2 = random row
    //        3 = constant digit (param)
    // We'll enforce:
    //  row 4: constant '1'
    //  rows 5 and 6: repeat 0..9 with same offset (ensure vertical 'dd')
    //  rows 2 and 3: repeat 0..9 with random offsets
    //  rows 0,1,7: mix of patterns for diversity
    uniform_int_distribution<int> offDist(0,9);
    uniform_int_distribution<int> digDist(0,9);
    uniform_int_distribution<int> typeDist(0,2);
    int off2 = offDist(rng);
    int off3 = offDist(rng);
    int off5 = offDist(rng);
    int off6 = off5; // vertical duplicates
    int off0 = offDist(rng);
    int off1 = offDist(rng);
    int off7 = offDist(rng);

    // Row 4 constant '1'
    for(int c=0;c<C;c++) g.d[id(4,c)] = '1';

    // Rows 5 and 6: repeat 0..9 with same offset
    for(int c=0;c<C;c++){
        char ch = char('0' + ((c + off5) % 10));
        g.d[id(5,c)] = ch;
        g.d[id(6,c)] = ch; // identical to row 5
    }

    // Rows 2 and 3: repeat 0..9 with random offsets
    for(int c=0;c<C;c++){
        g.d[id(2,c)] = char('0' + ((c + off2) % 10));
        g.d[id(3,c)] = char('0' + ((c + off3) % 10));
    }

    // Row 0: pairs with offset
    for(int c=0;c<C;c++){
        g.d[id(0,c)] = char('0' + (((c/2) + off0) % 10));
    }
    // Row 1: repeat with offset
    for(int c=0;c<C;c++){
        g.d[id(1,c)] = char('0' + ((c + off1) % 10));
    }
    // Row 7: mixed random/pairs
    int t7 = typeDist(rng); // 0/1/2
    if(t7 == 0){
        for(int c=0;c<C;c++) g.d[id(7,c)] = char('0' + ((c + off7) % 10));
    } else if(t7 == 1){
        for(int c=0;c<C;c++) g.d[id(7,c)] = char('0' + (((c/2) + off7) % 10));
    } else {
        for(int c=0;c<C;c++) g.d[id(7,c)] = char('0' + digDist(rng));
    }

    // Add a few targeted tweaks to ensure extra '1' adjacencies besides row 4
    // Put some '1's near varied columns in rows 3 and 5 to help with '11x'
    for(int k=0;k<3;k++){
        int c = uniform_int_distribution<int>(0, C-1)(rng);
        g.d[id(3,c)] = '1';
        int c2 = uniform_int_distribution<int>(0, C-1)(rng);
        g.d[id(5,c2)] = '1';
        g.d[id(6,c2)] = '1'; // keep vertical duplicate for '11'
    }
    return g;
}

void mutateRow(Grid &g, int r, int type, int param, mt19937 &rng) {
    // type: 0 repeat 0..9 with offset=param
    //       1 pairs with offset=param
    //       2 random row (param unused)
    //       3 constant digit param
    uniform_int_distribution<int> digDist(0,9);
    if(r == 6){
        // Keep row 6 identical to row 5 if we choose to keep design.
        // But allow a rare desync to explore.
        // We'll handle row 6 outside.
    }
    if(type == 0){
        for(int c=0;c<C;c++) g.d[id(r,c)] = char('0' + ((c + param) % 10));
    } else if(type == 1){
        for(int c=0;c<C;c++) g.d[id(r,c)] = char('0' + (((c/2) + param) % 10));
    } else if(type == 2){
        for(int c=0;c<C;c++) g.d[id(r,c)] = char('0' + digDist(rng));
    } else {
        char ch = char('0' + (param % 10));
        for(int c=0;c<C;c++) g.d[id(r,c)] = ch;
    }
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    buildAdj();
    // Precompute number strings up to some limit for evaluation
    int baseLimit = 1200; // plenty; adjust if needed
    vector<string> nums(baseLimit+1);
    for(int i=1;i<=baseLimit;i++) nums[i] = to_string(i);

    random_device rd;
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint32_t)rd());

    // Initial grid
    Grid best = generateInitial(rng);
    int bestScore = evaluateX(best, nums);

    // Simple hill-climbing on rows/patterns
    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT_MS = 900.0; // stay far below 1 minute
    uniform_int_distribution<int> rowDist(0, R-1);
    uniform_int_distribution<int> typeDist(0, 3);
    uniform_int_distribution<int> offDist(0, 9);
    uniform_real_distribution<double> prob(0.0,1.0);

    Grid cur = best;
    int curScore = bestScore;

    // Keep rows 4 constant '1' often; sometimes explore changes to row 6 and 5 relation
    int iterations = 0;
    while(true){
        iterations++;
        auto now = chrono::high_resolution_clock::now();
        double ms = chrono::duration<double, milli>(now - start).count();
        if(ms > TIME_LIMIT_MS) break;

        Grid tmp = cur;
        int r = rowDist(rng);
        int t = typeDist(rng);
        int p = offDist(rng);
        if(r == 4){
            // Keep row 4 constant '1' most times to maintain 1-layer; but allow rare tweak
            if(prob(rng) < 0.97) continue;
            t = 3; p = 1;
        }
        if(r == 6){
            // 70% of time mirror row 5 to keep vertical duplicates; 30% allow different
            if(prob(rng) < 0.7){
                // Mirror row 5
                for(int c=0;c<C;c++) tmp.d[id(6,c)] = tmp.d[id(5,c)];
            } else {
                mutateRow(tmp, r, t, p, rng);
            }
        } else {
            mutateRow(tmp, r, t, p, rng);
            // If we changed row 5, keep row 6 mirrored 70% of time
            if(r == 5 && prob(rng) < 0.7){
                for(int c=0;c<C;c++) tmp.d[id(6,c)] = tmp.d[id(5,c)];
            }
        }

        int sc = evaluateX(tmp, nums);
        if(sc > curScore || (sc == curScore && prob(rng) < 0.15)){
            cur = tmp;
            curScore = sc;
            if(curScore > bestScore){
                best = cur;
                bestScore = curScore;
            }
        }
    }

    // Output best grid
    for(int r=0;r<R;r++){
        for(int c=0;c<C;c++){
            cout << best.d[id(r,c)];
        }
        cout << '\n';
    }

    return 0;
}