#include <bits/stdc++.h>
using namespace std;

static const int H = 8, W = 14, N = H * W;
struct Bits {
    unsigned long long lo, hi;
    inline void reset(){ lo = 0; hi = 0; }
    inline bool any() const { return (lo | hi) != 0ULL; }
    inline void set(int i){
        if(i < 64) lo |= (1ULL << i);
        else hi |= (1ULL << (i - 64));
    }
    inline void reset_bit(int i){
        if(i < 64) lo &= ~(1ULL << i);
        else hi &= ~(1ULL << (i - 64));
    }
    inline bool test(int i) const {
        if(i < 64) return (lo >> i) & 1ULL;
        else return (hi >> (i - 64)) & 1ULL;
    }
    inline Bits operator|(const Bits& o) const { return {lo | o.lo, hi | o.hi}; }
    inline Bits operator&(const Bits& o) const { return {lo & o.lo, hi & o.hi}; }
    inline Bits& operator|=(const Bits& o){ lo |= o.lo; hi |= o.hi; return *this; }
    inline Bits& operator&=(const Bits& o){ lo &= o.lo; hi &= o.hi; return *this; }
};
static Bits neighborMask[N];
static vector<int> adjList[N];

inline int idx(int r, int c){ return r * W + c; }
inline bool inb(int r, int c){ return r >= 0 && r < H && c >= 0 && c < W; }

struct GridState {
    array<unsigned char, N> a; // digits 0..9
    array<Bits, 10> posMask;   // positions for each digit
};

static inline void buildAdjacency() {
    int dr[8] = {-1,-1,-1,0,0,1,1,1};
    int dc[8] = {-1,0,1,-1,1,-1,0,1};
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            int u = idx(r,c);
            neighborMask[u].reset();
            adjList[u].clear();
            for(int k=0;k<8;k++){
                int nr = r + dr[k], nc = c + dc[k];
                if(inb(nr,nc)){
                    int v = idx(nr,nc);
                    neighborMask[u].set(v);
                    adjList[u].push_back(v);
                }
            }
        }
    }
}

static inline void initPosMask(GridState& st){
    for(int d=0; d<10; d++) st.posMask[d].reset();
    for(int i=0;i<N;i++){
        st.posMask[st.a[i]].set(i);
    }
}

static inline void applyChange(GridState& st, int p, int newd){
    int old = st.a[p];
    if(old == newd) return;
    // update masks
    if(p < 64) {
        st.posMask[old].lo &= ~(1ULL << p);
        st.posMask[newd].lo |= (1ULL << p);
    } else {
        int q = p - 64;
        st.posMask[old].hi &= ~(1ULL << q);
        st.posMask[newd].hi |= (1ULL << q);
    }
    st.a[p] = (unsigned char)newd;
}

static inline Bits neighborsOf(const Bits& cur){
    Bits res{0,0};
    unsigned long long mlo = cur.lo;
    while(mlo){
        int b = __builtin_ctzll(mlo);
        res |= neighborMask[b];
        mlo &= (mlo - 1);
    }
    unsigned long long mhi = cur.hi;
    while(mhi){
        int b = __builtin_ctzll(mhi);
        res |= neighborMask[64 + b];
        mhi &= (mhi - 1);
    }
    return res;
}

static inline bool canRead(const GridState& st, const string& s){
    Bits cur = st.posMask[s[0]-'0'];
    if(!cur.any()) return false;
    for(size_t i=1;i<s.size();i++){
        Bits nb = neighborsOf(cur);
        Bits nxt = nb & st.posMask[s[i]-'0'];
        if(!nxt.any()) return false;
        cur = nxt;
    }
    return true;
}

static inline int evalScore(const GridState& st, int maxCheck = 1000000000){
    // Sequentially check 1..X
    string s;
    s.reserve(16);
    for(int x=1; x<=maxCheck; x++){
        s = to_string(x);
        if(!canRead(st, s)) return x-1;
    }
    return maxCheck;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    buildAdjacency();

    GridState cur, best;
    // Initialize grid with a structured pattern to provide diverse adjacency
    // Use a diagonal stripe + noise
    std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            int base = (r + c) % 10;
            // add small randomization
            int noise = (int)(rng() % 5 == 0 ? (rng()%10) : base);
            cur.a[idx(r,c)] = (unsigned char)noise;
        }
    }
    initPosMask(cur);

    int bestScore = evalScore(cur, 1000000);
    best = cur;

    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 0.95 * 60.0; // 95% of 60s
    const int ITER_BATCH = 64;

    // Simulated annealing-like random local search
    double T0 = 3.0, T1 = 0.01;
    long long iter = 0;
    while(true){
        iter++;
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if(elapsed > TIME_LIMIT) break;
        double t = elapsed / TIME_LIMIT;
        double T = T0 * pow(T1 / T0, t);

        // Propose multiple random tweaks per batch to amortize cost
        GridState cand = cur;
        int changes = 1 + (rng() % 3);
        array<pair<int,int>, 4> changed{};
        for(int k=0;k<changes;k++){
            int p = (int)(rng() % N);
            int nd = (int)(rng() % 10);
            int tries = 0;
            while(nd == cand.a[p] && tries < 5){
                nd = (int)(rng() % 10); tries++;
            }
            changed[k] = {p, cand.a[p]};
            applyChange(cand, p, nd);
        }
        int sc = evalScore(cand, bestScore + 200); // check a bit beyond current best
        if(sc > bestScore || (sc >= bestScore && (double)(rng() % 1000000) / 1000000.0 < exp((sc - bestScore) / max(1e-9, T)))){
            cur = cand;
            if(sc > bestScore){
                bestScore = sc;
                best = cand;
            }
        } else {
            // Revert not needed since cand is separate
        }

        // Occasionally try a more targeted tweak if near plateau
        if(iter % 200 == 0){
            // Try to specifically ensure 2-digit coverage by random local edits around a random cell
            int center = (int)(rng() % N);
            int dcenter = best.a[center];
            // Change neighbors to cover digit set 0..9 around center
            vector<int> neigh = adjList[center];
            shuffle(neigh.begin(), neigh.end(), rng);
            for(size_t k=0;k<neigh.size() && k<10;k++){
                int p = neigh[k];
                int nd = (int)k % 10;
                if(best.a[p] != nd){
                    applyChange(best, p, nd);
                }
            }
            int sc2 = evalScore(best, bestScore + 200);
            if(sc2 >= bestScore){
                bestScore = sc2;
                cur = best;
            } else {
                // revert approximate: we don't keep previous "best" snapshot before edits, but accept only if improved; else recompute from cur
                best = cur;
            }
        }
    }

    // Print best grid
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            cout << char('0' + best.a[idx(r,c)]);
        }
        cout << '\n';
    }
    return 0;
}