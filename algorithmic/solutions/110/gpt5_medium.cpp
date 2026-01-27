#include <bits/stdc++.h>
using namespace std;

static const int H = 8;
static const int W = 14;
static const int N = H * W; // 112
struct Bits { uint64_t lo, hi; };
struct Grid { array<uint8_t, N> d; };

inline bool anyBits(const Bits &b){ return (b.lo | b.hi) != 0ULL; }
inline void orAcc(Bits &a, const Bits &b){ a.lo |= b.lo; a.hi |= b.hi; }
inline Bits andBits(const Bits &a, const Bits &b){ return Bits{a.lo & b.lo, a.hi & b.hi}; }
inline Bits zeroBits(){ return Bits{0ULL,0ULL}; }

static Bits NB[N]; // neighbors bitset per cell
static vector<array<uint8_t,6>> numDigits; // precomputed digits for numbers
static int MAX_PRE = 30000;

inline int idx(int r, int c){ return r*W + c; }

void buildNeighbors(){
    int dr[8] = {-1,-1,-1,0,0,1,1,1};
    int dc[8] = {-1,0,1,-1,1,-1,0,1};
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            int id = idx(r,c);
            uint64_t lo=0, hi=0;
            for(int k=0;k<8;k++){
                int nr = r + dr[k], nc = c + dc[k];
                if(nr<0||nr>=H||nc<0||nc>=W) continue;
                int j = idx(nr,nc);
                if(j < 64) lo |= (1ULL<<j);
                else hi |= (1ULL<<(j-64));
            }
            NB[id] = Bits{lo,hi};
        }
    }
}

void precomputeNumbers(int maxX){
    numDigits.assign(maxX+1, {});
    for(int x=1; x<=maxX; x++){
        int y=x;
        array<uint8_t,6> digs{}; // up to 5 digits for 30000
        int len=0;
        while(y>0){
            digs[5 - ++len] = (uint8_t)(y%10);
            y/=10;
        }
        // shift to left so that digits start at index 0
        array<uint8_t,6> nd{};
        for(int i=0;i<len;i++) nd[i] = digs[6-len+i];
        numDigits[x] = nd;
        numDigits[x][5] = (uint8_t)len; // store length in last slot
    }
}

struct EvalCtx{
    Bits D[10]; // positions of each digit
};

inline void buildD(const Grid &g, EvalCtx &ctx){
    for(int d=0; d<10; d++) ctx.D[d] = zeroBits();
    for(int i=0;i<N;i++){
        int d = g.d[i];
        if(i<64) ctx.D[d].lo |= (1ULL<<i);
        else ctx.D[d].hi |= (1ULL<<(i-64));
    }
}

inline Bits neighborUnion(const Bits &curr){
    Bits res{0,0};
    uint64_t w = curr.lo;
    while(w){
        int i = __builtin_ctzll(w);
        orAcc(res, NB[i]);
        w &= w-1;
    }
    w = curr.hi;
    while(w){
        int t = __builtin_ctzll(w);
        int i = 64 + t;
        orAcc(res, NB[i]);
        w &= w-1;
    }
    return res;
}

inline bool readableNumber(const EvalCtx &ctx, int x){
    const auto &digs = numDigits[x];
    int len = digs[5];
    Bits curr = ctx.D[digs[0]];
    if(!anyBits(curr)) return false;
    for(int k=1;k<len;k++){
        Bits nxt = neighborUnion(curr);
        nxt = andBits(nxt, ctx.D[digs[k]]);
        if(!anyBits(nxt)) return false;
        curr = nxt;
    }
    return true;
}

int scoreUpTo(const Grid &g, int limit){
    EvalCtx ctx;
    buildD(g, ctx);
    for(int x=1; x<=limit; x++){
        if(!readableNumber(ctx, x)) return x-1;
    }
    return limit;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    buildNeighbors();
    precomputeNumbers(MAX_PRE);

    // RNG
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    auto rndInt = [&](int a, int b)->int{
        uniform_int_distribution<int> dist(a,b);
        return dist(rng);
    };

    // Initial grid: balanced digits shuffled
    vector<int> pos(N);
    iota(pos.begin(), pos.end(), 0);
    shuffle(pos.begin(), pos.end(), rng);
    Grid best;
    for(int i=0;i<N;i++){
        best.d[pos[i]] = (uint8_t)(i % 10);
    }

    int bestScore = scoreUpTo(best, min(500, MAX_PRE));
    int upperChecked = min(500, MAX_PRE);
    // try to extend evaluation to more if promising
    if(bestScore == upperChecked){
        int extended = scoreUpTo(best, min(2000, MAX_PRE));
        bestScore = extended;
        upperChecked = max(upperChecked, extended);
    }

    // Local search
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.5; // within 1 minute comfortably
    while(true){
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if(elapsed > TIME_LIMIT_SEC) break;

        Grid cand = best;
        int mutType = rndInt(0,2);
        if(mutType == 0){
            int i = rndInt(0,N-1);
            int nd = rndInt(0,9);
            cand.d[i] = (uint8_t)nd;
        }else if(mutType == 1){
            int k = rndInt(1,3);
            for(int t=0;t<k;t++){
                int i = rndInt(0,N-1);
                int nd = rndInt(0,9);
                cand.d[i] = (uint8_t)nd;
            }
        }else{
            int i = rndInt(0,N-1);
            int j = rndInt(0,N-1);
            swap(cand.d[i], cand.d[j]);
        }

        int quickLimit = min(MAX_PRE, max(bestScore, 200) + 50);
        int s1 = scoreUpTo(cand, quickLimit);
        if(s1 > bestScore){
            int fullLimit = min(MAX_PRE, s1 + 500);
            int s2 = scoreUpTo(cand, fullLimit);
            if(s2 > bestScore){
                best = cand;
                bestScore = s2;
            }
        }
    }

    // Output the grid
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            cout << char('0' + best.d[idx(r,c)]);
        }
        cout << '\n';
    }
    return 0;
}