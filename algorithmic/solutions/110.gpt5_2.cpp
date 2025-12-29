#include <bits/stdc++.h>
using namespace std;

struct Bits112 {
    uint64_t lo, hi;
    Bits112(uint64_t l=0, uint64_t h=0): lo(l), hi(h) {}
    inline void clear(){ lo=0; hi=0; }
    inline bool any() const { return lo | hi; }
    inline void set(int idx){
        if (idx < 64) lo |= (1ull<<idx);
        else hi |= (1ull<<(idx-64));
    }
    inline void reset(int idx){
        if (idx < 64) lo &= ~(1ull<<idx);
        else hi &= ~(1ull<<(idx-64));
    }
    inline bool test(int idx) const {
        if (idx < 64) return (lo >> idx) & 1ull;
        return (hi >> (idx-64)) & 1ull;
    }
    inline void ORwith(const Bits112& b){ lo |= b.lo; hi |= b.hi; }
    inline Bits112 operator&(const Bits112& b) const { return Bits112(lo & b.lo, hi & b.hi); }
    inline Bits112 operator|(const Bits112& b) const { return Bits112(lo | b.lo, hi | b.hi); }
};

static const int R=8, C=14, N=R*C;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Prepare neighbors (8 directions)
    vector<vector<int>> nbr(N);
    auto inside = [&](int r,int c){ return (r>=0 && r<R && c>=0 && c<C); };
    for(int r=0;r<R;r++){
        for(int c=0;c<C;c++){
            int id=r*C+c;
            for(int dr=-1; dr<=1; dr++){
                for(int dc=-1; dc<=1; dc++){
                    if(dr==0 && dc==0) continue;
                    int nr=r+dr, nc=c+dc;
                    if(inside(nr,nc)){
                        nbr[id].push_back(nr*C+nc);
                    }
                }
            }
        }
    }

    // Precompute adjacency bitsets per node (for canRead)
    vector<Bits112> adjMask(N);
    for(int i=0;i<N;i++){
        Bits112 b;
        for(int v: nbr[i]) b.set(v);
        adjMask[i]=b;
    }

    // RNG
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 13);
    seed ^= (seed >> 7);
    seed ^= (seed << 17);
    std::mt19937_64 rng(seed);

    // Balanced initial digits
    vector<int> cells(N);
    for(int i=0;i<N;i++) cells[i]=i;
    shuffle(cells.begin(), cells.end(), rng);
    vector<int> grid(N,-1);
    int base = N/10; // 11
    int rem = N%10;  // 2
    vector<int> counts(10, base);
    for(int d=0; d<rem; d++) counts[d]++;
    int ptr=0;
    for(int d=0; d<10; d++){
        for(int k=0; k<counts[d]; k++){
            grid[cells[ptr++]] = d;
        }
    }

    auto evalQuality = [&](const vector<int>& g)->long long{
        // neighbor digit masks per cell
        int neighborMask[N];
        for(int i=0;i<N;i++){
            int mask = 0;
            for(int v: nbr[i]){
                mask |= (1 << g[v]);
            }
            neighborMask[i]=mask;
        }
        // presence checks
        int present1to9=0, presentAll=0;
        {
            int cnts[10]={0};
            for(int i=0;i<N;i++) cnts[g[i]]++;
            for(int d=1; d<=9; d++) if(cnts[d]>0) present1to9++;
            for(int d=0; d<=9; d++) if(cnts[d]>0) presentAll++;
        }
        // triple coverage: for each b, for each a in 1..9, count c in 0..9 such that there exists a b-cell with neighbor a and neighbor c
        long long tripleCount=0;
        const int nonZeroMask = 0x3FE; // bits 1..9
        for(int b=0; b<10; b++){
            int rowbits[10]={0}; // rowbits[a] is bitmask of c
            for(int i=0;i<N;i++){
                if(g[i]!=b) continue;
                int mask = neighborMask[i];
                int mask1 = mask & nonZeroMask;
                int aa = mask1;
                while(aa){
                    int a = __builtin_ctz(aa);
                    aa &= aa-1;
                    rowbits[a] |= mask;
                }
            }
            for(int a=1; a<=9; a++){
                tripleCount += __builtin_popcount((unsigned)rowbits[a]);
            }
        }
        // bigram coverage: directed pairs a->b if exists adjacency from a-cell to b-digit
        long long bigramCount = 0;
        for(int a=0; a<10; a++){
            int unionMask = 0;
            for(int i=0;i<N;i++){
                if(g[i]==a){
                    unionMask |= neighborMask[i];
                }
            }
            bigramCount += __builtin_popcount((unsigned)unionMask);
        }
        long long score = (long long)present1to9 * 1000000LL + (long long)presentAll * 100000LL + tripleCount*1000LL + bigramCount;
        return score;
    };

    // Hill climbing with swaps
    vector<int> bestGrid = grid;
    long long bestQ = evalQuality(grid);
    long long curQ = bestQ;

    auto swapAndEval = [&](int i, int j){
        swap(grid[i], grid[j]);
        long long q = evalQuality(grid);
        if(q >= curQ || (q + (long long)(rng()%1000) >= curQ)){ // mild randomness
            curQ = q;
            if(q > bestQ){
                bestQ = q;
                bestGrid = grid;
            }
        } else {
            swap(grid[i], grid[j]); // revert
        }
    };

    // Time budget for search
    auto tstart = chrono::high_resolution_clock::now();
    double timeLimitMs = 200.0; // around 0.2s
    // Perform iterations
    while(true){
        auto now = chrono::high_resolution_clock::now();
        double ms = chrono::duration<double, std::milli>(now - tstart).count();
        if(ms > timeLimitMs) break;
        int i = rng()%N, j = rng()%N;
        if(i==j) continue;
        // Small chance to propose changing one cell to another digit instead of swap to escape symmetry
        if((rng() & 1023) == 0){
            int old = grid[i];
            int nd = rng()%10;
            if(nd==old) continue;
            int saved = grid[i];
            grid[i]=nd;
            long long q = evalQuality(grid);
            if(q >= curQ || (q + (long long)(rng()%1000) >= curQ)){
                curQ = q;
                if(q > bestQ){
                    bestQ = q;
                    bestGrid = grid;
                }
            } else {
                grid[i]=saved;
            }
        } else {
            swapAndEval(i,j);
        }
    }

    grid = bestGrid;

    // Optional: tiny refinement passes focusing on creating same-digit adjacencies
    auto sameAdjCount = [&](const vector<int>& g)->int{
        int cnt=0;
        for(int i=0;i<N;i++){
            for(int v: nbr[i]){
                if(v>i && g[v]==g[i]) cnt++;
            }
        }
        return cnt;
    };
    int sameCnt = sameAdjCount(grid);
    for(int iter=0; iter<2000; iter++){
        int i = rng()%N, j = rng()%N;
        if(i==j) continue;
        int gi = grid[i], gj = grid[j];
        if(gi==gj) continue;
        // Try to improve same-digit adjacency
        int before=0, after=0;
        for(int v: nbr[i]) if(grid[v]==gi) before++;
        for(int v: nbr[j]) if(grid[v]==gj) before++;
        for(int v: nbr[i]) if(grid[v]==gj) after++;
        for(int v: nbr[j]) if(grid[v]==gi) after++;
        if(after > before){
            swap(grid[i], grid[j]);
            sameCnt += (after-before);
        } else if ((rng() & 255) == 0) {
            swap(grid[i], grid[j]);
            sameCnt += (after-before);
        }
    }

    // Print final grid
    for(int r=0;r<R;r++){
        for(int c=0;c<C;c++){
            cout << grid[r*C+c];
        }
        cout << '\n';
    }
    return 0;
}